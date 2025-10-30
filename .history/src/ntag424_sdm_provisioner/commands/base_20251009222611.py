"""
Base classes and constants for APDU commands.
"""
from abc import ABC, abstractmethod

from ntag424_sdm_provisioner.hal import NTag424CardConnection
# --- Standard ISO7816-4 APDU constants ---
CLA_ISO7816 = 0x00
INS_SELECT = 0xA4
P1_SELECT_BY_ID = 0x04
P2_SELECT_FIRST_OCCURRENCE = 0x00

# --- NXP Proprietary APDU constants ---
CLA_PROPRIETARY = 0x90

# --- APDU Status Word constants ---
SW_OK = (0x91, 0x00)
SW_AF = (0x91, 0xAF)  # Additional Frame


class ApduError(Exception):
    """Raised when an APDU command returns a non-OK status word."""

    def __init__(self, message: str, sw1: int, sw2: int):
        super().__init__(f"{message} - SW: {sw1:02X}{sw2:02X}")
        self.sw1 = sw1
        self.sw2 = sw2


class ApduCommand(ABC):
    """Abstract base class for all APDU commands."""

    @abstractmethod
    def encode(connection: NTag424CardConnection):
        """
        Executes the command against a card connection.
        This method must be implemented by all subclasses.
        """
        raise NotImplementedError
