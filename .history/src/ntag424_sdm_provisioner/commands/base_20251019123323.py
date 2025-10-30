"""
Base classes and constants for APDU commands.
"""
from typing import Tuple, List, Any
from abc import ABC, abstractmethod
from ntag424_sdm_provisioner.hal import NTag424CardConnection
from ntag424_sdm_provisioner.constants import (
    StatusWord, ErrorCategory, get_error_category, describe_status_word
)


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


# ============================================================================
# Response Dataclasses
# ============================================================================

@dataclass
class SuccessResponse:
    """Response for successful operations."""
    message: str


@dataclass
class AuthenticationChallengeResponse:
    """Response from EV2 authentication first phase."""
    key_no_used: int
    challenge: bytes


@dataclass
class Ntag424VersionInfo:
    """Version information from NTAG424 DNA chip."""
    hw_vendor_id: int
    hw_type: int
    hw_subtype: int
    hw_major_version: int
    hw_minor_version: int
    hw_storage_size: int
    hw_protocol: int
    sw_vendor_id: int
    sw_type: int
    sw_subtype: int
    sw_major_version: int
    sw_minor_version: int
    sw_storage_size: int
    sw_protocol: int
    uid: bytes
    batch_no: bytes
    fab_week: int
    fab_year: int


@dataclass
class ReadDataResponse:
    """Response from file read operations."""
    file_no: int
    offset: int
    data: bytes


# ============================================================================
# Configuration Dataclasses
# ============================================================================

@dataclass
class SDMConfiguration:
    """Configuration for Secure Dynamic Messaging."""
    file_no: int
    comm_mode: 'CommMode'
    access_rights: bytes
    enable_sdm: bool
    sdm_options: int
    picc_data_offset: int
    mac_input_offset: int
    mac_offset: int
    enc_data_offset: Optional[int] = None
    enc_data_length: Optional[int] = None
    read_ctr_offset: Optional[int] = None


@dataclass
class SDMUrlTemplate:
    """Template for SDM URL with placeholders."""
    base_url: str
    uid_placeholder: str = "00000000000000"
    cmac_placeholder: str = "0" * 16
    enc_placeholder: Optional[str] = None
    read_ctr_placeholder: Optional[str] = None


# ============================================================================
# Command Base Class
# ============================================================================

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

    def send_apdu(self, connection: 'NTag424CardConnection', apdu: List[int]) -> Tuple[List[int], int, int]:
        """
        A proxy method that calls the send_apdu method on the connection object.

        This keeps the pyscard dependency out of the command classes.
        """
        # This now calls the method on the connection object, fulfilling your design goal.
        return connection.send_apdu(apdu, use_escape=self.use_escape)