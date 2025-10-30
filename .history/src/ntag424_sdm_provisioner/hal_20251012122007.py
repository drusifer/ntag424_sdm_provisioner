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

from logging import getLogger

log = getLogger("smartcard")
log.setLevel("DEBUG")


def has_readers() -> bool:
    """Check if any PC/SC readers are available."""
    try:
        print("hi")
        ("Checking for available PC/SC readers...")
        reader_list = readers()
        log.info(f"Got {len(reader_list)} readers")
        return len(reader_list) > 0
    except NoReadersException:
        return False

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

    def __enter__(self) -> CardConnection:
        self.make_connection() 
        try:
            self.connection.connect()
            return NTag424CardConnection(self.connection)
        except CardConnectionException as e:
            # Provide a more user-friendly message for common connection issues
            if "Card not found" in str(e) or "No card inserted" in str(e):
                raise CardConnectionException(
                    f"No card found on reader '{reader}'. Please present a card."
                ) from e
            raise

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
        
        data, sw1, sw2 = self.connection.transmit(apdu)
        
        status_str = f"{sw1:02X}{sw2:02X}"
        print(f"  << R-APDU: {''.join(f'{b:02X}' for b in data)} [{status_str}]")

        return data, sw1, sw2


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
            print(f"\nConnected to card on '{readers_list[0]}'")
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

