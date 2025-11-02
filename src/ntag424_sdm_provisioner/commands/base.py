"""
Base classes and constants for APDU commands.
"""
from typing import Tuple, List, Any, Optional, TYPE_CHECKING
from abc import ABC, abstractmethod
import logging
from ntag424_sdm_provisioner.hal import NTag424CardConnection
from ntag424_sdm_provisioner.constants import (
    StatusWord, StatusWordPair, ErrorCategory, get_error_category, describe_status_word
)

if TYPE_CHECKING:
    from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession

log = logging.getLogger(__name__)


class Ntag424Error(Exception):
    """Base exception for all NTAG424 errors."""
    pass


class ApduError(Ntag424Error):
    """Raised when an APDU command returns a non-OK status word."""
    
    def __init__(self, message: str, sw1: int, sw2: int):
        self.sw1 = sw1
        self.sw2 = sw2
        self.status_word = StatusWord.from_bytes(sw1, sw2)
        self.category = get_error_category(self.status_word)
        
        # Build detailed error message
        sw_desc = describe_status_word(sw1, sw2)
        full_message = f"{message}\n  {sw_desc}"
        
        super().__init__(full_message)
    
    def is_authentication_error(self) -> bool:
        """Check if this is an authentication error."""
        return self.category == ErrorCategory.AUTHENTICATION
    
    def is_permission_error(self) -> bool:
        """Check if this is a permission error."""
        return self.category == ErrorCategory.PERMISSION
    
    def is_not_found_error(self) -> bool:
        """Check if this is a not found error."""
        return self.category == ErrorCategory.NOT_FOUND


class AuthenticationRateLimitError(ApduError):
    """Authentication rate-limited (0x91AD) - wait between attempts."""
    
    def __init__(self, command_name: str = "Authentication"):
        super().__init__(
            f"{command_name} rate-limited.\n"
            "  Solution: Wait 5 seconds between authentication attempts",
            0x91, 0xAD
        )


class CommandLengthError(ApduError):
    """Command length error (0x917E) - payload format issue."""
    
    def __init__(self, command_name: str = "Command"):
        super().__init__(
            f"{command_name} length error.\n"
            "  Known Issue: ChangeFileSettings payload format\n"
            "  Status: Under investigation",
            0x91, 0x7E
        )


class CommandNotAllowedError(ApduError):
    """Command not allowed (0x911C) - precondition not met."""
    
    def __init__(self, command_name: str = "Command"):
        super().__init__(
            f"{command_name} not allowed.\n"
            "  Possible causes:\n"
            "    - File not in correct state\n"
            "    - Authentication required but not provided",
            0x91, 0x1C
        )


class SecurityNotSatisfiedError(ApduError):
    """Security condition not satisfied (0x6985) - authentication issue."""
    
    def __init__(self, command_name: str = "Command"):
        super().__init__(
            f"{command_name} security not satisfied.\n"
            "  Possible causes:\n"
            "    - Authentication required\n"
            "    - Wrong key used\n"
            "    - File not selected",
            0x69, 0x85
        )


class AuthenticationError(Ntag424Error):
    """Authentication failed."""
    pass


class PermissionError(Ntag424Error):
    """Permission denied for operation."""
    pass


class ConfigurationError(Ntag424Error):
    """Invalid configuration."""
    pass


class CommunicationError(Ntag424Error):
    """Communication with card/reader failed."""
    pass


class AuthenticatedConnection:
    """
    Wraps a card connection with an authenticated session.
    
    This class acts as a context manager and handles automatic CMAC
    application for all authenticated commands.
    
    Usage:
        with AuthenticateEV2(key).execute(connection) as auth_conn:
            settings = GetFileSettings(file_no=2).execute(auth_conn)
            key_ver = GetKeyVersion(key_no=0).execute(auth_conn)
    """
    
    def __init__(self, connection: NTag424CardConnection, session: 'Ntag424AuthSession'):
        """
        Args:
            connection: The underlying card connection
            session: The authenticated session with session keys
        """
        self.connection = connection
        self.session = session
    
    def __enter__(self) -> 'AuthenticatedConnection':
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit context manager."""
        # Session cleanup could go here if needed
        return False
    
    def send_apdu(self, apdu: List[int], use_escape: bool = False) -> Tuple[List[int], int, int]:
        """
        Send plain APDU without CMAC (for files with CommMode.PLAIN).
        
        This delegates directly to the underlying connection.
        
        Args:
            apdu: APDU bytes to send
            use_escape: Whether to use escape command
        
        Returns:
            Tuple of (data, sw1, sw2)
        """
        return self.connection.send_apdu(apdu, use_escape=use_escape)
    
    def send_authenticated_apdu(
        self,
        cmd_header: bytes,
        cmd_data: bytes,
        use_escape: bool = False
    ) -> Tuple[bytes, int, int]:
        """
        Send an authenticated APDU with automatic CMAC application.
        
        Handles:
        1. Applies CMAC to command data
        2. Sends APDU
        3. Handles continuation frames with CMAC
        4. Checks status word
        
        Args:
            cmd_header: Command header (CLA INS P1 P2)
            cmd_data: Command data to be authenticated
            use_escape: Whether to use escape command for reader
        
        Returns:
            Tuple of (response_data, sw1, sw2)
        
        Raises:
            ApduError: If status word indicates error
        """
        # Apply CMAC to command data
        authenticated_data = self.session.apply_cmac(cmd_header, cmd_data)
        
        # Build APDU: header + Lc + data + Le
        apdu = list(cmd_header) + [len(authenticated_data)] + list(authenticated_data) + [0x00]
        
        # Send initial command
        data, sw1, sw2 = self.connection.send_apdu(apdu, use_escape=use_escape)
        
        # Handle continuation frames with CMAC
        full_response = bytearray(data)
        while (sw1, sw2) == StatusWordPair.SW_ADDITIONAL_FRAME:
            log.debug(f"Authenticated command: {StatusWordPair.SW_ADDITIONAL_FRAME}, fetching next frame...")
            # GET_ADDITIONAL_FRAME with CMAC
            af_header = bytes([0x90, 0xAF, 0x00, 0x00])
            af_data = self.session.apply_cmac(af_header, b'')
            af_apdu = list(af_header) + [len(af_data)] + list(af_data) + [0x00]
            
            data, sw1, sw2 = self.connection.send_apdu(af_apdu, use_escape=use_escape)
            full_response.extend(data)
        
        # Check final status
        if (sw1, sw2) not in [StatusWordPair.SW_OK, StatusWordPair.SW_OK_ALTERNATIVE]:
            raise ApduError("Authenticated command failed", sw1, sw2)
        
        return bytes(full_response), sw1, sw2
    
    def __str__(self) -> str:
        return f"AuthenticatedConnection(connection={self.connection})"


class ApduCommand(ABC):
    """
    Abstract base class for all APDU commands.

    This class holds the APDU structure and logic but delegates the actual
    sending of the command to the connection object.
    """
    def __init__(self, use_escape: bool = False) -> None:
        """
        Args:
            use_escape: Whether to wrap the APDU in a reader-specific escape
                        command (required for some readers like the ACR122U).
        """
        self.use_escape = use_escape

    @abstractmethod
    def execute(self, connection: 'NTag424CardConnection') -> Any: 
        """
        Executes the command against a card connection. This method must be
        implemented by all subclasses.
        """
        raise NotImplementedError

    def send_command(
        self,
        connection: 'NTag424CardConnection',
        apdu: List[int],
        allow_alternative_ok: bool = True
    ) -> Tuple[List[int], int, int]:
        """
        High-level command send with automatic multi-frame handling and error checking.
        
        This method:
        1. Sends the APDU directly via connection.send_apdu()
        2. Automatically handles SW_ADDITIONAL_FRAME (0x91AF) responses by sending
           GET_ADDITIONAL_FRAME (0x90AF0000) commands until complete
        3. Checks that final status is SW_OK or SW_OK_ALTERNATIVE
        4. Raises ApduError if status indicates failure
        5. Returns complete response data and final status word
        
        Args:
            connection: Card connection
            apdu: APDU command bytes to send
            allow_alternative_ok: If True, accept both SW_OK (0x9000) and 
                                 SW_OK_ALTERNATIVE (0x9100) as success
        
        Returns:
            Tuple of (data, sw1, sw2) where:
                - data: Complete response data (all frames concatenated)
                - sw1, sw2: Final status word bytes
        
        Raises:
            ApduError: If final status word indicates error
        """
        # Send initial command directly to connection
        data, sw1, sw2 = connection.send_apdu(apdu, use_escape=self.use_escape)
        
        # Collect full response if multiple frames
        full_response = bytearray(data)
        
        # Handle additional frames (0x91AF)
        while (sw1, sw2) == StatusWordPair.SW_ADDITIONAL_FRAME:
            log.debug(f"Additional frame requested ({StatusWordPair.SW_ADDITIONAL_FRAME}), fetching next frame...")
            # GET_ADDITIONAL_FRAME: CLA=0x90, INS=0xAF, P1=0x00, P2=0x00, Le=0x00
            get_af_apdu = [0x90, 0xAF, 0x00, 0x00, 0x00]
            data, sw1, sw2 = connection.send_apdu(get_af_apdu, use_escape=self.use_escape)
            full_response.extend(data)
        
        # Check final status word
        success_codes = [StatusWordPair.SW_OK]
        if allow_alternative_ok:
            success_codes.append(StatusWordPair.SW_OK_ALTERNATIVE)
        
        if (sw1, sw2) not in success_codes:
            # Use reflection to get command class name
            command_name = self.__class__.__name__
            
            # Raise specific exception based on status word
            if (sw1, sw2) == (0x91, 0xAD):
                raise AuthenticationRateLimitError(command_name)
            elif (sw1, sw2) == (0x91, 0x7E):
                raise CommandLengthError(command_name)
            elif (sw1, sw2) == (0x91, 0x1C):
                raise CommandNotAllowedError(command_name)
            elif (sw1, sw2) == (0x69, 0x85):
                raise SecurityNotSatisfiedError(command_name)
            else:
                # Generic error
                raise ApduError(f"{command_name} failed", sw1, sw2)
        
        return list(full_response), sw1, sw2