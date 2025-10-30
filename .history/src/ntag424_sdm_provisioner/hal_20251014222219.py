"""
Hardware Abstraction Layer (HAL) for PC/SC NFC Readers.

This module provides a high-level interface for interacting with NFC readers
that are compliant with the PC/SC (Personal Computer/Smart Card) standard.
It handles reader discovery, card connection, and raw APDU command transmission.
"""

from typing import Any, List, Tuple, Optional
from ntag424_sdm_provisioner.atr_watcher import wait_for_card_atr
from smartcard.System import readers
from smartcard.Exceptions import NoReadersException, CardConnectionException
from smartcard.CardConnection import CardConnection
from smartcard.util import toHexString
from enum import Enum




from logging import getLogger
log = getLogger("hal")
log.setLevel("DEBUG")
if not log.handlers:
    import sys
    import logging
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    log.addHandler(ch)

from typing import Tuple

# --- Standard ISO7816-4 APDU constants ---
CLA_ISO7816: int = 0x00
INS_SELECT: int = 0xA4
P1_SELECT_BY_DF_NAME: int = 0x04  # Select by Application ID (AID)
P2_SELECT_FIRST_OCCURRENCE: int = 0x00 # First or only occurrence, return FCI

# --- NXP Proprietary APDU constants ---
CLA_PROPRIETARY: int = 0x90

# --- Standard ISO7816-4 Status Word constants ---
# NOTE: A tuple of ints is a good way to represent this
SW_OK: Tuple[int, int] = (0x90, 0x00)          # Process completed successfully
SW_AF: Tuple[int, int] = (0x91, 0xAF)          # Additional Frame (more data available)
SW_FILE_NOT_FOUND: Tuple[int, int] = (0x6A, 0x82) # File or application not found
SW_WRONG_LENGTH: Tuple[int, int] = (0x67, 0x00) # Wrong length (e.g., in Lc field)

# --- PC/SC Constants (Import, don't define) ---
try:
    # This is the correct way to get the escape code constant
    from smartcard.scard import IOCTL_CCID_ESCAPE
except ImportError:
    # Fallback for environments without pyscard, for linting, etc.
    # The actual value is OS-dependent, pyscard handles this.
    import sys
    if sys.platform == "win32":
        IOCTL_CCID_ESCAPE = 3500
    else:
        IOCTL_CCID_ESCAPE = 0x42000001 # Value for PCSC-Lite (Linux/macOS)

# --- Helper Enums based on the manual ---

class KeyType(Enum):
    """Key type for MIFARE Classic authentication."""
    TYPE_A = 0x60 # [cite: 228]
    TYPE_B = 0x61 # [cite: 228]

class ValueBlockOperationType(Enum):
    """Operation type for MIFARE Classic value blocks."""
    STORE = 0x00      # [cite: 411]
    INCREMENT = 0x01  # [cite: 411]
    DECREMENT = 0x02  # [cite: 411]


class ApduError(Exception):
    """Raised when an APDU command returns a non-OK status word."""

    def __init__(self, message: str, sw1: int, sw2: int):
        super().__init__(f"{message} - SW: [{hexb([sw1, sw2])}]")
        self.sw1 = sw1
        self.sw2 = sw2


def has_readers() -> bool:
    """Check if any PC/SC readers are available."""
    try:
        print("Checking for available PC/SC readers...")
        reader_list = readers()
        log.info(f"Got {len(reader_list)} readers")
        return len(reader_list) > 0
    except NoReadersException:
        return False

class NTag242ConnectionError(Exception):
    """Custom exception raised when no PC/SC readers are found."""
    pass

class NTag242NoReadersError(Exception):
    """Custom exception raised when no PC/SC readers are found."""
    pass

class CardManager:
    """
    A context manager to handle the connection to an NFC card.

    Ensures that the connection is properly established and automatically
    disconnected when the context is exited, even if errors occur.

    Usage:
        with CardManager(reader_index=0) as connection:
            # interact with the card via the 'connection' object
            ...
    """
    def __init__(self, reader_index: int = 0):
        self.reader_index = reader_index
        self.connection = None

    def make_connection(self) -> CardConnection:
        """Establishes a connection to the card on the specified reader."""
        try:
            reader_list = readers()
            if len(reader_list) == 0:
                raise NTag242NoReadersError("No PC/SC readers found.")

            rlist = (f"Available readers: {"\n  ".join( f'{i}: {str(r)}' \
                                                    for i, r in enumerate(reader_list) )}")    
            log.info(rlist)
            reader = reader_list[self.reader_index]
            self.connection = CardConnection(reader)
            log.info(f"Using reader: {reader}")
        except IndexError:
                error = f"Reader index {self.reader_index} is out of bounds. "
                log.error(error)
                raise IndexError(error)
        except NoReadersException as e:
            log.error("No PC/SC readers found.")
            raise NTag242NoReadersError("No PC/SC readers found.") from e

    def __enter__(self) -> NTag424CardConnection:
        self.make_connection() 
        try:
            self.connection.connect()
            return NTag424CardConnection(self.connection)
        except Exception as e:
            # Provide a more user-friendly message for common connection issues
            log.error(f"Failed to connect to a reader: {e}")
            raise NTag242ConnectionError(f"Failed to connect to a reader: {e}") from e

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.disconnect()
        # The 'False' return value re-raises any exceptions that occurred
        # inside the 'with' block, which is the standard behavior.
        return False

def hexb(b: List[int]) -> str: 
    return toHexString(b)

class NTag424CardConnection():
    """
    A specialized CardConnection for NTAG424 cards.

    This class can be extended in the future to include NTAG424-specific
    methods and properties.
    """
    def __init__(self, connection: CardConnection):
        self.connection = connection

        

    def __str__(self) -> str:
        return str(self.connection.getReader())

    def wait_for_atr(self, target_reader: Optional[str] = None, timeout: Optional[float] = None) -> Optional[str]:
        """Block until the next card is presented on `target_reader` and return ATR hex or None on timeout.

        This helper uses the shared atr_watcher implementation and is intended for
        simple CLI or script usage where blocking until a tap is desired.
        """
        atr = wait_for_card_atr(target_reader=target_reader, timeout=timeout)
        if atr is None:
            return None
        return "".join(f"{b:02X}" for b in atr)

    def send_apdu(self, apdu: List[int], use_escape: bool=False) -> Tuple[List[int], int, int]:
        """Sends a raw APDU command to the card and returns the response."""
        # This function would contain your logic for sending via transmit() or control()
        # For this example, we assume a working implementation.
        # This is a mock implementation for demonstration purposes.
        print(f"  >> C-APDU: {''.join(f'{b:02X}' for b in apdu)}")
        if self.use_escape:
             # In a real scenario, IOCTL_CCID_ESCAPE would be imported from smartcard.scard
            resp = self.connection.control(IOCTL_CCID_ESCAPE, apdu)
            if len(resp) < 2:
                raise ApduError("APDU response too short", 0, 0)
            data, sw1, sw2 = resp[:-2], resp[-2], resp[-1]
            status_str = hexb((sw1, sw2))
            print(f"  << R-APDU (from Control): {hexb(data)} [{status_str}]")
            return list(data), sw1, sw2
        else:
            data, sw1, sw2 = self.connection.transmit(apdu)
            status_str = hexb((sw1, sw2))
            print(f"  << R-APDU: {hexb(data)} [{status_str}]")
            return data, sw1, sw2 

