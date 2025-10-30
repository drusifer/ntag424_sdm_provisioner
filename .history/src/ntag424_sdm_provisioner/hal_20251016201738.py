import logging
from typing import List, Optional, Tuple, Union

from smartcard.CardConnection import CardConnection
# ✅ Import the necessary low-level functions and constants
from smartcard.scard import (SCARD_SCOPE_USER, SCARD_STATE_PRESENT,
                             SCARD_STATE_UNAWARE, SCardEstablishContext,
                             SCardGetStatusChange, SCardReleaseContext)
# pyscard imports
# pyscard imports
from smartcard.System import readers
from smartcard.util import toHexString

# Assuming your atr_watcher.py file is accessible
from ntag424_sdm_provisioner.atr_watcher import wait_for_card_atr

# --- PC/SC Constants (Corrected Cross-Platform Import) ---
try:
    # This is the correct import for Windows systems
    from smartcard.scard import SCARD_CTL_CODE
    IOCTL_CCID_ESCAPE = SCARD_CTL_CODE(3500)
except ImportError:
    # This is the correct import for PCSC-Lite (Linux/macOS)
    IOCTL_CCID_ESCAPE = 3500

def hexb(data: Union[bytes, List[int]]) -> str:
    """
    Pretty-prints a bytes object or a list of integers as a
    space-separated, uppercase hexadecimal string.

    Args:
        data: The data to be formatted, either as bytes or a list of ints.

    Returns:
        A formatted hexadecimal string (e.g., "00 A4 04 00 07").
    """
    if not isinstance(data, (bytes, list)):
        raise TypeError("Input must be of type 'bytes' or 'list[int]'")
        
    return ' '.join(f'{byte:02X}' for byte in data)

log = logging.getLogger("hal")

class NTag242ConnectionError(Exception):
    """Custom exception for connection failures."""
    pass

class NTag242NoReadersError(Exception):
    """Custom exception for when no readers are found."""
    pass

class CardManager:
    """
    A robust context manager that uses a direct, blocking call to wait for a
    card tap, then establishes a clean connection.
    """
    def __init__(self, reader_index: int = 0, timeout_seconds: int = 15):
        self.reader_index = reader_index
        self.timeout_ms = timeout_seconds * 1000
        self.connection: Optional[CardConnection] = None
        self.context = None

    def __enter__(self) -> 'NTag424CardConnection':
        try:
            # 1. Establish a PC/SC context. This is the handle to the resource manager.
            hresult, self.context = SCardEstablishContext(SCARD_SCOPE_USER)
            if hresult != 0:
                raise NTag242ConnectionError(f"Failed to establish PC/SC context: {hresult}")

            all_readers = readers()
            if not all_readers:
                raise NTag242NoReadersError("No PC/SC readers found.")

            reader = all_readers[self.reader_index]
            log.info(f"Using reader '{reader}'. Waiting for a card tap...")

            # 2. Set up the state we are waiting for.
            reader_states = [(str(reader), SCARD_STATE_UNAWARE)]

            # 3. Make the blocking call with the correct arguments.
            hresult, current_states = SCardGetStatusChange(self.context, self.timeout_ms, reader_states)
            if hresult != 0:
                raise NTag242ConnectionError(f"SCardGetStatusChange failed: {hresult}")

            (reader_name, event_state, atr) = current_states[0]

            # 4. Check if a card was actually presented.
            if not (event_state & SCARD_STATE_PRESENT):
                raise NTag242ConnectionError("Timeout: No card was presented.")
            
            log.info(f"Card detected with ATR: {''.join(f'{b:02X}' for b in atr)}. Connecting...")

            # 5. Now, create a standard connection and connect to it.
            self.connection = reader.createConnection()
            self.connection.connect()
            log.info("Successfully connected to the card.")
            
            return NTag424CardConnection(self.connection)

        except Exception as e:
            # Ensure context is released on failure
            self.__exit__(None, None, None)
            log.error(f"Failed to establish card connection: {e}")
            raise NTag242ConnectionError(f"Failed to connect: {e}") from e

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            log.info("Disconnecting from the card.")
            self.connection.disconnect()
        # 6. Release the PC/SC context to clean up resources.
        if self.context:
            SCardReleaseContext(self.context)
        return False

    
# --- NTag424CardConnection (with send_apdu method restored) ---
class NTag424CardConnection:
    """
    A wrapper for a pyscard CardConnection that handles the low-level
    details of APDU transmission.
    """
    def __init__(self, connection: CardConnection):
        self.connection = connection

    def __str__(self) -> str:
        return str(self.connection.getReader())

    def wait_for_atr(self) -> List[int]:
        return wait_for_card_atr
        
    def send_apdu(self, apdu: List[int], use_escape: bool = False) -> Tuple[List[int], int, int]:
        """
        Sends a raw APDU command to the card and returns the response.

        This method contains the pyscard-specific logic, abstracting it away
        from the command classes.
        """
        log.debug(f"  >> C-APDU: {toHexString(apdu)}")

        if use_escape:
            try:
                # Use the low-level control() for readers that need it (e.g., ACR122U)
                resp = self.connection.control(IOCTL_CCID_ESCAPE, apdu)
                
                if len(resp) < 2:
                    raise NTag242NoReadersError(f"APDU response via control() was too short: [{hexb(resp)}]")
                
                # Manually parse the raw response
                data, sw1, sw2 = resp[:-2], resp[-2], resp[-1]
                log.debug(f"  << R-APDU (Control): {toHexString(data)} [{sw1:02X}{sw2:02X}]")
                return list(data), sw1, sw2
            except Exception as e:
                log.error(f"Error during control() command: {e}")
                raise
        else:
            # Use the standard transmit() for compliant readers
            data, sw1, sw2 = self.connection.transmit(apdu)
            log.debug(f"  << R-APDU (Transmit): {toHexString(data)} [{sw1:02X}{sw2:02X}]")
            return data, sw1, sw2
