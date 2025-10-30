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
SW_OK_ALTERNATIVE: Tuple[int, int] = (0x91, 0x00) # Alternative "OK" status
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

# file: responses.py

from dataclasses import dataclass, field
from typing import List, Union

def hexb(data: Union[bytes, List[int]]) -> str:
    """Pretty-prints bytes or a list of ints as a space-separated hex string."""
    return ' '.join(f'{byte:02X}' for byte in data)

@dataclass
class SuccessResponse:
    """A generic response for operations that succeed without returning data."""
    message: str = "Operation successful."

    def __str__(self) -> str:
        return f"✅ SUCCESS: {self.message}"

@dataclass
class AuthenticationChallengeResponse:
    """Holds the encrypted challenge returned by the card during authentication."""
    key_no_used: int
    challenge: bytes

    def __str__(self) -> str:
        return (
            f"✅ AUTHENTICATION CHALLENGE\n"
            f"  ► Key Number Used: 0x{self.key_no_used:02X}\n"
            f"  ► Encrypted Challenge (RndB): {hexb(self.challenge)}"
        )

@dataclass
class ReadDataResponse:
    """Holds the data read from a file on the card."""
    file_no: int
    offset: int
    data: bytes

    def __str__(self) -> str:
        return (
            f"✅ READ DATA SUCCESS\n"
            f"  ► File: 0x{self.file_no:02X}\n"
            f"  ► Offset: {self.offset}\n"
            f"  ► Length Read: {len(self.data)} bytes\n"
            f"  ► Data: {hexb(self.data)}"
        )
# file: responses.py

from dataclasses import dataclass

@dataclass
class Ntag424VersionInfo:
    """Represents the parsed version info from an NTAG424 DNA chip."""
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

    def __str__(self) -> str:
        """Returns a human-readable string representation."""
        return (
            f"✅ NTAG 424 DNA CHIP VERSION\n"
            f"  ► Hardware:\n"
            f"    - Vendor: 0x{self.hw_vendor_id:02X} (NXP)\n"
            f"    - Version: v{self.hw_major_version}.{self.hw_minor_version}\n"
            f"    - Storage: {self.hw_storage_size} bytes\n"
            f"  ► Software:\n"
            f"    - Vendor: 0x{self.sw_vendor_id:02X} (NXP)\n"
            f"    - Version: v{self.sw_major_version}.{self.sw_minor_version}\n"
            f"  ► Manufacturing:\n"
            f"    - UID: {self.uid.hex().upper()}\n"
            f"    - Batch No: {self.batch_no.hex().upper()}\n"
            f"    - Fab Date: Week {self.fab_week}, 20{self.fab_year:02d}"
        )
        
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