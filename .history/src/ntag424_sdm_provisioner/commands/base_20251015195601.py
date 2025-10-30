"""
Base classes and constants for APDU commands.
"""
from abc import ABC, abstractmethod
from typing import Any, List, Tuple

from ntag424_sdm_provisioner.hal import NTag424CardConnection
from typing import Tuple
from abc import ABC, abstractmethod

# --- Standard ISO/IEC 7816-4 Status Word Constants ---

# Success Codes
SW_OK: Tuple[int, int] = (0x90, 0x00)          # The operation completed successfully. [cite: 188, 208, 666]
SW_ADDITIONAL_FRAME: Tuple[int, int] = (0x91, 0xAF) # Used by DESFire cards to indicate more data is available. [cite: 691]

# Error Codes
SW_OPERATION_FAILED: Tuple[int, int] = (0x63, 0x00) # The operation failed. [cite: 188, 208, 666]
SW_WRONG_LENGTH: Tuple[int, int] = (0x67, 0x00)     # Wrong length specified in Lc field.
SW_FUNC_NOT_SUPPORTED: Tuple[int, int] = (0x6A, 0x81) # The card does not support the requested function. [cite: 188]
SW_FILE_NOT_FOUND: Tuple[int, int] = (0x6A, 0x82)     # File or application not found.

class ApduError(Exception):
    """Raised when an APDU command returns a non-OK status word."""
    def __init__(self, message: str, sw1: int, sw2: int):
        super().__init__(f"{message} - SW: {sw1:02X}{sw2:02X}")
        self.sw1 = sw1
        self.sw2 = sw2

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