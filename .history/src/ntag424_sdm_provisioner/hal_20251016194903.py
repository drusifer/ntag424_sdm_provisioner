import logging
import sys
import threading
from typing import List, Optional, Tuple, Union

from smartcard.CardConnection import CardConnection
from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.Exceptions import CardConnectionException, NoReadersException
# pyscard imports
from smartcard.System import readers
from smartcard.util import toBytes, toHexString

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
# (Your logging setup code here...)

class NTag242ConnectionError(Exception): pass
class NTag242NoReadersError(Exception): pass

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
