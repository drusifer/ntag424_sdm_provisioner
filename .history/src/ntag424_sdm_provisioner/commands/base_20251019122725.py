"""
Base classes and constants for APDU commands.
"""
from typing import Tuple, List, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
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