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
P2_FIRST_OR_ONLY = 0x0C

# --- Standard ISO7816-4 APDU constants ---
P2_SELECT_FIRST_OCCURRENCE = 0x00

# --- NXP Proprietary APDU constants ---
CLA_PROPRIETARY = 0x90

# ISO7816-4 Status Words
SW_OK: Tuple[int, int] = (0x91, 0x00)

# --- APDU Status Word constants ---
SW_AF: Tuple[int,int] = (0x91, 0xAF)  # Additional Frame


# Windows IOCTL for ACR122 escape (SCARD_CTL_CODE(3500)):
IOCTL_CCID_ESCAPE = (0x31 << 16) | (3500 << 2)

# Example usage:
# payload = acr122_escape_apdu([0x90, 0x60, 0x00, 0x00, 0x00])
# resp = conn.control(IOCTL_CCID_ESCAPE, payload)
def acr122_escape_apdu(apdu: bytes | list[int]) -> bytes:
    """
    Wrap a raw APDU into the ACR122 vendor escape payload:
    Header:  FF 00 00 00 <Lc> <APDU bytes>
    Returns bytes ready for conn.control(IOCTL_CCID_ESCAPE, payload).
    """
    if isinstance(apdu, (list, tuple)):
        apdu = bytes(apdu)
    if not isinstance(apdu, (bytes, bytearray)):
        raise TypeError("apdu must be bytes or list[int]")
    if len(apdu) > 255:
        raise ValueError("APDU too long for single-byte Lc wrapper")
    return bytes([0xFF, 0x00, 0x00, 0x00, len(apdu)]) + apdu


class ApduError(Exception):
    """Raised when an APDU command returns a non-OK status word."""

    def __init__(self, message: str, sw1: int, sw2: int):
        super().__init__(f"{message} - SW: {sw1:02X}{sw2:02X}")
        self.sw1 = sw1
        self.sw2 = sw2


class ApduCommand(ABC):
    """Abstract base class for all APDU commands."""

    @abstractmethod
    def execute(self, connection: NTag424CardConnection):
        """
        Executes the command against a card connection.
        This method must be implemented by all subclasses.
        """
        raise NotImplementedError

    def send_apdu(self, connection: NTag424CardConnection, apdu: List[int]) -> Tuple[List[int], int, int]:
        """
        Sends a raw APDU command to the card and returns the response.

        Args:
            connection: An active CardConnection object.
            apdu: The command APDU as a list of integers (bytes).

        Returns:
            A tuple containing:
            - The response data as a list of integers.
            - The first status word (SW1) as an integer.
            - The second status word (SW2) as an integer.
        """
        print(f"  >> C-APDU: {''.join(f'{b:02X}' for b in apdu)}")

        # Wrap the APDU in the ACR122 escape format
        escaped = acr122_escape_apdu(apdu)
        print(f"  >> acr122 Escaped: {''.join(f'{b:02X}' for b in escaped)}")
        data, sw1, sw2 = connection.transmit(escaped)
        
        status_str = f"{sw1:02X}{sw2:02X}"
        print(f"  << R-APDU: {''.join(f'{b:02X}' for b in data)} [{status_str}]")

        return data, sw1, sw2
