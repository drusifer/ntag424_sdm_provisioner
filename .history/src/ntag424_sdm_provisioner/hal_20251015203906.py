import sys
import logging
from typing import List, Tuple, Optional, Union

# Assuming your atr_watcher.py file is accessible
from ntag424_sdm_provisioner.atr_watcher import wait_for_card_atr

from smartcard.System import readers
from smartcard.Exceptions import NoReadersException, CardConnectionException
from smartcard.CardConnection import CardConnection
from smartcard.util import toHexString, toBytes
from ntag424_sdm_provisioner.atr_watcher import wait_for_card_atr

# --- PC/SC Constants (Corrected Cross-Platform Import) ---
try:
    # This is the correct import for Windows systems
    from smartcard.scard import  SCARD_CTL_CODE
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

class ApduError(Exception):
    def __init__(self, message: str, sw1: int, sw2: int):
        super().__init__(f"{message} - SW: {sw1:02X}{sw2:02X}")
        self.sw1 = sw1
        self.sw2 = sw2

log = logging.getLogger("hal")
# (Your logging setup code here...)

class NTag242ConnectionError(Exception): pass
class NTag242NoReadersError(Exception): pass



class CardManager:
    """
    A fully self-contained context manager that waits for a card tap and
    manages the connection without needing any external watcher modules.
    """

    # ✅ _AtrObserver is now a private inner class of CardManager.
    class _AtrObserver(CardObserver):
        """A private observer to signal when a card has been presented."""
        def __init__(self, target_reader: Optional[str] = None):
            self._event = threading.Event()
            self._lock = threading.Lock()
            self._atr: Optional[bytes] = None
            self._target_reader = target_reader

        def update(self, observable, actions):
            (added_cards, removed_cards) = actions
            if not added_cards:
                return

            card = added_cards[0]
            reader_name = str(card.reader)

            # Ignore taps on other readers if a target is specified
            if self._target_reader and self._target_reader != reader_name:
                return
            
            with self._lock:
                # Signal only on the first tap
                if not self._event.is_set():
                    self._atr = bytes(card.atr)
                    self._event.set()

        def wait_for_next_atr(self, timeout: Optional[float] = None) -> Optional[bytes]:
            """Blocks until the event is set by the update() method."""
            if self._event.wait(timeout):
                with self._lock:
                    return self._atr
            return None


    def __init__(self, reader_index: int = 0):
        self.reader_index = reader_index
        self.connection: Optional[CardConnection] = None
        self.monitor: Optional[CardMonitor] = None
        self.observer: Optional[CardManager._AtrObserver] = None

    def __enter__(self) -> 'NTag424CardConnection':
        try:
            reader_list = readers()
            if not reader_list:
                raise NTag242NoReadersError("No PC/SC readers found.")

            target_reader_name = str(reader_list[self.reader_index])
            
            # Create and manage the monitor and our inner observer here
            self.monitor = CardMonitor()
            self.observer = self._AtrObserver(target_reader=target_reader_name)
            self.monitor.addObserver(self.observer)
            
            log.info(f"Using reader '{target_reader_name}'. Waiting for a card tap...")

            # Block until the observer's background thread detects a card
            atr = self.observer.wait_for_next_atr(timeout=15)
            if atr is None:
                raise NTag242ConnectionError("Timeout: No card was presented.")
            
            log.info(f"Card detected with ATR: {''.join(f'{b:02X}' for b in atr)}")
            
            # Now that a card is present, we can safely connect
            reader = reader_list[self.reader_index]
            self.connection = reader.createConnection()
            self.connection.connect()
            log.info("Successfully connected to the card.")
            
            # This class is defined in your code; assumes it takes a connection object
            return NTag424CardConnection(self.connection)

        except (NoReadersException, CardConnectionException, NTag242NoReadersError, IndexError) as e:
            self.__exit__(None, None, None) # Ensure full cleanup on failure
            log.error(f"Failed to establish card connection: {e}")
            raise NTag242ConnectionError(f"Failed to connect to the card: {e}") from e

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            log.info("Disconnecting from the card.")
            self.connection.disconnect()
        
        if self.monitor and self.observer:
            log.info("Stopping card monitor.")
            self.monitor.deleteObserver(self.observer)
            
        return False # Re-raise exceptions


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
                    raise ApduError("APDU response via control() was too short", 0x00, 0x00)
                
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
