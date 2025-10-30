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

class ApduError(Exception):
    """Raised when an APDU command returns a non-OK status word."""

    def __init__(self, message: str, sw1: int, sw2: int):
        super().__init__(f"{message} - SW: {sw1:02X}{sw2:02X}")
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

class NTag424CardConnection():
    """
    A specialized CardConnection for NTAG424 cards.

    This class can be extended in the future to include NTAG424-specific
    methods and properties.
    """
    def __init__(self, connection: CardConnection):
        self.connection = connection

    def hexb(self, b):
        return toHexString(b)
        
    def get_escape(self) -> int:
        return 3500

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

    def send_apdu(self, apdu: List[int]) -> Tuple[List[int], int, int]:
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
        if self.use_escape:
            resp = self.connection.control(self.get_escape(), apdu)

            print(f"Raw response {len(resp)} bytes: {self.hexb(resp)}" )

            # If response includes status bytes at end, print them separated:
            if isinstance(resp, (bytes, bytearray)) and len(resp) >= 2:
                sw1, sw2 = resp[-2:]
                data = resp[:-2]
                print(f"Possible SW1:{self.hexb(sw1)} SW2:{self.hexb(sw2)} Data:{self.hexb(data)}")
                return list(data), sw1, sw2
            else: 
                raise ApduError(f"APDU response[{self.hexb(resp)}] too short or invalid", 0x00, 0x00)
        else:
            data, sw1, sw2 = self.connection.transmit(apdu)
            print(f"  << R-APDU: {self.hexb(data)} status: {self.hexb([sw1, sw2])}")]")
            return data, sw1, sw2

    def transmit(self, message: List[int]) -> Tuple[List[int], int, int]:
        """
        Transmits an message command to the card and returns the response.

        Args:
            message: The command message as a list of integers (bytes).
        Returns:
            A tuple containing:
            - The response data as a list of integers.
            - The first status word (SW1) as an integer.
            - The second status word (SW2) as an integer.
        """
        return self.connection.transmit(message)   




# watch_atrs is provided by the separate atr_watcher module

# --- Example Usage ---

def _main():
    """
    Demonstrates the usage of the HAL module for connecting to a card.
    This function is intended for direct execution of this file as a script.
    """
    print("--- HAL Module Test: Discover and Connect ---")
    try:
        # Use the first available reader
        with CardManager(reader_index=0) as conn:
            atr_hex = conn.wait_for_atr()
            print(f"  Card ATR: {atr_hex}")

    except (CardConnectionException, IndexError) as e:
        print(f"\nError: {e}")
        raise e
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        raise e
    finally:
        print("\n--- Test complete ---")

if __name__ == '__main__':
    _main()

