"""
Base classes and constants for APDU commands.
"""
from abc import ABC, abstractmethod
from typing import List, Tuple

from ntag424_sdm_provisioner.hal import NTag424CardConnection

# ISO7816-4 APDU Constants
CLA_ISO7816 = 0x00
INS_SELECT = 0xA4
P1_SELECT_BY_ID = 0x00
P2_FIRST_OR_ONLY = 0x00

# --- Standard ISO7816-4 APDU constants ---
P2_SELECT_FIRST_OCCURRENCE = 0x00

# --- NXP Proprietary APDU constants ---
CLA_PROPRIETARY = 0x90

# ISO7816-4 Status Words
SW_OK: Tuple[int, int] = (0x90, 0x00)

# --- APDU Status Word constants ---
SW_AF: Tuple[int,int] = (0x91, 0xAF)  # Additional Frame


# Windows IOCTL for ACR122 escape (SCARD_CTL_CODE(3500)):
#IOCTL_CCID_ESCAPE = (0x31 << 16) | (3500 << 2)
IOCTL_CCID_ESCAPE = bytes([0xFF,0x00,0x48,0x00])

class ApduError(Exception):
    """Raised when an APDU command returns a non-OK status word."""

    def __init__(self, message: str, sw1: int, sw2: int):
        super().__init__(f"{message} - SW: {sw1:02X}{sw2:02X}")
        self.sw1 = sw1
        self.sw2 = sw2


class ApduCommand(ABC):
    """Abstract base class for all APDU commands."""

    def __init__(self, use_escape: bool = False):
        """
        Args:
            use_escape: Whether to wrap APDUs in the ACR122 escape format.
        """
        self.use_escape = use_escape    

    @abstractmethod
    def execute(self, ncc: NTag424CardConnection):
        """
        Executes the command against a card connection.
        This method must be implemented by all subclasses.
        """
        raise NotImplementedError
