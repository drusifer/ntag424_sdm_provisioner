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

# file: hal.py

import logging
from typing import Optional

# Import the observer and monitor from your watcher implementation
from ntag424_sdm_provisioner.atr_watcher import _AtrObserver
from smartcard.CardMonitoring import CardMonitor

from smartcard.System import readers
from smartcard.Exceptions import NoReadersException, CardConnectionException
from smartcard.CardConnection import CardConnection

# (Your other classes and imports here...)

class CardManager:
    """
    A context manager that correctly handles waiting for a card and managing
    the connection without race conditions.
    """
    def __init__(self, reader_index: int = 0):
        self.reader_index = reader_index
        self.connection: Optional[CardConnection] = None
        self.monitor: Optional[CardMonitor] = None
        self.observer: Optional[_AtrObserver] = None

    def __enter__(self) -> 'NTag424CardConnection':
        try:
            reader_list = readers()
            if not reader_list:
                raise NTag242NoReadersError("No PC/SC readers found.")

            target_reader_name = str(reader_list[self.reader_index])
            
            # --- FIX: Create and manage the monitor and observer here ---
            self.monitor = CardMonitor()
            self.observer = _AtrObserver(target_reader=target_reader_name)
            self.monitor.addObserver(self.observer)
            
            log.info(f"Using reader '{target_reader_name}'. Waiting for a card tap...")

            # Block until the observer's background thread detects a card
            atr = self.observer.wait_for_next_atr(timeout=15) # 15-second timeout
            if atr is None:
                raise NTag242ConnectionError("Timeout: No card was presented.")
            
            log.info(f"Card detected with ATR: {''.join(f'{b:02X}' for b in atr)}")
            
            # Now that a card is present and the monitor is stable, connect.
            reader = reader_list[self.reader_index]
            self.connection = reader.createConnection()
            self.connection.connect()
            log.info("Successfully connected to the card.")
            
            return NTag424CardConnection(self.connection)

        except (NoReadersException, CardConnectionException, NTag242NoReadersError, IndexError) as e:
            # Ensure cleanup happens even if connection fails midway
            self.__exit__(None, None, None)
            log.error(f"Failed to establish card connection: {e}")
            raise NTag242ConnectionError(f"Failed to connect to the card: {e}") from e

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Disconnect the primary connection first
        if self.connection:
            log.info("Disconnecting from the card.")
            self.connection.disconnect()
        
        # --- FIX: Clean up the monitor and observer last ---
        if self.monitor and self.observer:
            log.info("Stopping card monitor.")
            self.monitor.deleteObserver(self.observer)
            
        return False # Re-raise any exceptions from the 'with' block# file: hal.py

import logging
from typing import Optional

# Import the observer and monitor from your watcher implementation
from ntag424_sdm_provisioner.atr_watcher import _AtrObserver
from smartcard.CardMonitoring import CardMonitor

from smartcard.System import readers
from smartcard.Exceptions import NoReadersException, CardConnectionException
from smartcard.CardConnection import CardConnection

# (Your other classes and imports here...)

class CardManager:
    """
    A context manager that correctly handles waiting for a card and managing
    the connection without race conditions.
    """
    def __init__(self, reader_index: int = 0):
        self.reader_index = reader_index
        self.connection: Optional[CardConnection] = None
        self.monitor: Optional[CardMonitor] = None
        self.observer: Optional[_AtrObserver] = None

    def __enter__(self) -> 'NTag424CardConnection':
        try:
            reader_list = readers()
            if not reader_list:
                raise NTag242NoReadersError("No PC/SC readers found.")

            target_reader_name = str(reader_list[self.reader_index])
            
            # --- FIX: Create and manage the monitor and observer here ---
            self.monitor = CardMonitor()
            self.observer = _AtrObserver(target_reader=target_reader_name)
            self.monitor.addObserver(self.observer)
            
            log.info(f"Using reader '{target_reader_name}'. Waiting for a card tap...")

            # Block until the observer's background thread detects a card
            atr = self.observer.wait_for_next_atr(timeout=15) # 15-second timeout
            if atr is None:
                raise NTag242ConnectionError("Timeout: No card was presented.")
            
            log.info(f"Card detected with ATR: {''.join(f'{b:02X}' for b in atr)}")
            
            # Now that a card is present and the monitor is stable, connect.
            reader = reader_list[self.reader_index]
            self.connection = reader.createConnection()
            self.connection.connect()
            log.info("Successfully connected to the card.")
            
            return NTag424CardConnection(self.connection)

        except (NoReadersException, CardConnectionException, NTag242NoReadersError, IndexError) as e:
            # Ensure cleanup happens even if connection fails midway
            self.__exit__(None, None, None)
            log.error(f"Failed to establish card connection: {e}")
            raise NTag242ConnectionError(f"Failed to connect to the card: {e}") from e

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Disconnect the primary connection first
        if self.connection:
            log.info("Disconnecting from the card.")
            self.connection.disconnect()
        
        # --- FIX: Clean up the monitor and observer last ---
        if self.monitor and self.observer:
            log.info("Stopping card monitor.")
            self.monitor.deleteObserver(self.observer)
            
        return False # Re-raise any exceptions from the 'with' block# file: hal.py

import logging
from typing import Optional

# Import the observer and monitor from your watcher implementation
from ntag424_sdm_provisioner.atr_watcher import _AtrObserver
from smartcard.CardMonitoring import CardMonitor

from smartcard.System import readers
from smartcard.Exceptions import NoReadersException, CardConnectionException
from smartcard.CardConnection import CardConnection

# (Your other classes and imports here...)

class CardManager:
    """
    A context manager that correctly handles waiting for a card and managing
    the connection without race conditions.
    """
    def __init__(self, reader_index: int = 0):
        self.reader_index = reader_index
        self.connection: Optional[CardConnection] = None
        self.monitor: Optional[CardMonitor] = None
        self.observer: Optional[_AtrObserver] = None

    def __enter__(self) -> 'NTag424CardConnection':
        try:
            reader_list = readers()
            if not reader_list:
                raise NTag242NoReadersError("No PC/SC readers found.")

            target_reader_name = str(reader_list[self.reader_index])
            
            # --- FIX: Create and manage the monitor and observer here ---
            self.monitor = CardMonitor()
            self.observer = _AtrObserver(target_reader=target_reader_name)
            self.monitor.addObserver(self.observer)
            
            log.info(f"Using reader '{target_reader_name}'. Waiting for a card tap...")

            # Block until the observer's background thread detects a card
            atr = self.observer.wait_for_next_atr(timeout=15) # 15-second timeout
            if atr is None:
                raise NTag242ConnectionError("Timeout: No card was presented.")
            
            log.info(f"Card detected with ATR: {''.join(f'{b:02X}' for b in atr)}")
            
            # Now that a card is present and the monitor is stable, connect.
            reader = reader_list[self.reader_index]
            self.connection = reader.createConnection()
            self.connection.connect()
            log.info("Successfully connected to the card.")
            
            return NTag424CardConnection(self.connection)

        except (NoReadersException, CardConnectionException, NTag242NoReadersError, IndexError) as e:
            # Ensure cleanup happens even if connection fails midway
            self.__exit__(None, None, None)
            log.error(f"Failed to establish card connection: {e}")
            raise NTag242ConnectionError(f"Failed to connect to the card: {e}") from e

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Disconnect the primary connection first
        if self.connection:
            log.info("Disconnecting from the card.")
            self.connection.disconnect()
        
        # --- FIX: Clean up the monitor and observer last ---
        if self.monitor and self.observer:
            log.info("Stopping card monitor.")
            self.monitor.deleteObserver(self.observer)
            
        return False # Re-raise any exceptions from the 'with' block# file: hal.py

import logging
from typing import Optional

# Import the observer and monitor from your watcher implementation
from ntag424_sdm_provisioner.atr_watcher import _AtrObserver
from smartcard.CardMonitoring import CardMonitor

from smartcard.System import readers
from smartcard.Exceptions import NoReadersException, CardConnectionException
from smartcard.CardConnection import CardConnection

# (Your other classes and imports here...)

class CardManager:
    """
    A context manager that correctly handles waiting for a card and managing
    the connection without race conditions.
    """
    def __init__(self, reader_index: int = 0):
        self.reader_index = reader_index
        self.connection: Optional[CardConnection] = None
        self.monitor: Optional[CardMonitor] = None
        self.observer: Optional[_AtrObserver] = None

    def __enter__(self) -> 'NTag424CardConnection':
        try:
            reader_list = readers()
            if not reader_list:
                raise NTag242NoReadersError("No PC/SC readers found.")

            target_reader_name = str(reader_list[self.reader_index])
            
            # --- FIX: Create and manage the monitor and observer here ---
            self.monitor = CardMonitor()
            self.observer = _AtrObserver(target_reader=target_reader_name)
            self.monitor.addObserver(self.observer)
            
            log.info(f"Using reader '{target_reader_name}'. Waiting for a card tap...")

            # Block until the observer's background thread detects a card
            atr = self.observer.wait_for_next_atr(timeout=15) # 15-second timeout
            if atr is None:
                raise NTag242ConnectionError("Timeout: No card was presented.")
            
            log.info(f"Card detected with ATR: {''.join(f'{b:02X}' for b in atr)}")
            
            # Now that a card is present and the monitor is stable, connect.
            reader = reader_list[self.reader_index]
            self.connection = reader.createConnection()
            self.connection.connect()
            log.info("Successfully connected to the card.")
            
            return NTag424CardConnection(self.connection)

        except (NoReadersException, CardConnectionException, NTag242NoReadersError, IndexError) as e:
            # Ensure cleanup happens even if connection fails midway
            self.__exit__(None, None, None)
            log.error(f"Failed to establish card connection: {e}")
            raise NTag242ConnectionError(f"Failed to connect to the card: {e}") from e

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Disconnect the primary connection first
        if self.connection:
            log.info("Disconnecting from the card.")
            self.connection.disconnect()
        
        # --- FIX: Clean up the monitor and observer last ---
        if self.monitor and self.observer:
            log.info("Stopping card monitor.")
            self.monitor.deleteObserver(self.observer)
            
        return False # Re-raise any exceptions from the 'with' block# file: hal.py

import logging
from typing import Optional

# Import the observer and monitor from your watcher implementation
from ntag424_sdm_provisioner.atr_watcher import _AtrObserver
from smartcard.CardMonitoring import CardMonitor

from smartcard.System import readers
from smartcard.Exceptions import NoReadersException, CardConnectionException
from smartcard.CardConnection import CardConnection

# (Your other classes and imports here...)

class CardManager:
    """
    A context manager that correctly handles waiting for a card and managing
    the connection without race conditions.
    """
    def __init__(self, reader_index: int = 0):
        self.reader_index = reader_index
        self.connection: Optional[CardConnection] = None
        self.monitor: Optional[CardMonitor] = None
        self.observer: Optional[_AtrObserver] = None

    def __enter__(self) -> 'NTag424CardConnection':
        try:
            reader_list = readers()
            if not reader_list:
                raise NTag242NoReadersError("No PC/SC readers found.")

            target_reader_name = str(reader_list[self.reader_index])
            
            # --- FIX: Create and manage the monitor and observer here ---
            self.monitor = CardMonitor()
            self.observer = _AtrObserver(target_reader=target_reader_name)
            self.monitor.addObserver(self.observer)
            
            log.info(f"Using reader '{target_reader_name}'. Waiting for a card tap...")

            # Block until the observer's background thread detects a card
            atr = self.observer.wait_for_next_atr(timeout=15) # 15-second timeout
            if atr is None:
                raise NTag242ConnectionError("Timeout: No card was presented.")
            
            log.info(f"Card detected with ATR: {''.join(f'{b:02X}' for b in atr)}")
            
            # Now that a card is present and the monitor is stable, connect.
            reader = reader_list[self.reader_index]
            self.connection = reader.createConnection()
            self.connection.connect()
            log.info("Successfully connected to the card.")
            
            return NTag424CardConnection(self.connection)

        except (NoReadersException, CardConnectionException, NTag242NoReadersError, IndexError) as e:
            # Ensure cleanup happens even if connection fails midway
            self.__exit__(None, None, None)
            log.error(f"Failed to establish card connection: {e}")
            raise NTag242ConnectionError(f"Failed to connect to the card: {e}") from e

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Disconnect the primary connection first
        if self.connection:
            log.info("Disconnecting from the card.")
            self.connection.disconnect()
        
        # --- FIX: Clean up the monitor and observer last ---
        if self.monitor and self.observer:
            log.info("Stopping card monitor.")
            self.monitor.deleteObserver(self.observer)
            
        return False # Re-raise any exceptions from the 'with' block

# --- CardManager (Unchanged from previous correct version) ---
class CardManager:
    """
    A context manager to handle the connection to an NFC card.
    """
    def __init__(self, reader_index: int = 0):
        self.reader_index = reader_index
        self.connection: Optional[CardConnection] = None

    def __enter__(self) -> 'NTag424CardConnection':
        try:
            reader_list = readers()
            if not reader_list:
                raise NTag242NoReadersError("No PC/SC readers found.")

            target_reader_name = str(reader_list[self.reader_index])
            log.info(f"Using reader '{target_reader_name}'. Waiting for a card tap...")

            atr = wait_for_card_atr(target_reader=target_reader_name, timeout=10)
            if atr is None:
                raise NTag242ConnectionError("Timeout: No card was presented.")
            
            log.info(f"Card detected with ATR: {''.join(f'{b:02X}' for b in atr)}")
            
            reader = reader_list[self.reader_index]
            self.connection = reader.createConnection()
            self.connection.connect()
            log.info("Successfully connected to the card.")
            
            return NTag424CardConnection(self.connection)

        except (NoReadersException, CardConnectionException, NTag242NoReadersError, IndexError) as e:
            log.error(f"Failed to establish card connection: {e}")
            if self.connection:
                self.connection.disconnect()
            raise NTag242ConnectionError(f"Failed to connect to the card: {e}") from e

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            log.info("Disconnecting from the card.")
            self.connection.disconnect()
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
