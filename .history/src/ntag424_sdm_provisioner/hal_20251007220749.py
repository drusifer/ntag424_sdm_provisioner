"""
Hardware Abstraction Layer (HAL) for PC/SC NFC Readers.

This module provides a high-level interface for interacting with NFC readers
that are compliant with the PC/SC (Personal Computer/Smart Card) standard.
It handles reader discovery, card connection, and raw APDU command transmission.
"""

from typing import List, Tuple, Optional, Iterator
import threading
from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.System import readers
from smartcard.Exceptions import NoReadersException, CardConnectionException
from smartcard.CardConnection import CardConnection

# --- Public API ---

def list_readers() -> List[str]:
    """
    Discovers and returns a list of available PC/SC reader names.

    Raises:
        NoReadersError: If no readers are found.

    Returns:
        A list of strings, where each string is a reader name.
    """
    reader_list = readers()
    if not reader_list:
        print("Error: No PC/SC readers found.")
        raise NoReadersException("No readers available")
    return [str(r) for r in reader_list]


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

    def __enter__(self) -> CardConnection:
        reader_list = list_readers()
        if self.reader_index >= len(reader_list):
            raise IndexError(f"Reader index {self.reader_index} is out of bounds.")
        
        reader = reader_list[self.reader_index]
        self.connection = CardConnection(reader)
        
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

    def get_atr(self) -> str:
        """
        Retrieves the Answer To Reset (ATR) from a connected card.

        The ATR is a sequence of bytes sent by a smart card upon reset, which
        provides information about its communication parameters.

        Args:
            connection: An active CardConnection object.

        Returns:
            The ATR as a hexadecimal string.
        """
        atr_bytes = self.connection.getATR()
        return "".join(f"{b:02X}" for b in atr_bytes)


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


# --- Card ATR watcher utilities ---


class _AtrObserver(CardObserver):
    """Internal CardObserver that records the latest ATR and notifies waiters.

    The observer stores the most recent ATR (as bytes) when a card is added and
    signals a threading.Event so callers can block until a card appears.
    """

    def __init__(self, target_reader: Optional[str] = None):
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._atr: Optional[bytes] = None
        self._target_reader = target_reader

    def update(self, observable, cards):
        """Called by CardMonitor when cards are added/removed.

        `cards` is typically a (added, removed) pair. We only react to added
        cards and convert their ATR to bytes when possible.
        """
        try:
            # cards is often a tuple (added, removed)
            added = cards[0] if isinstance(cards, (list, tuple)) and len(cards) >= 1 else cards
            for card in added or []:
                # Reader name may be available under different attributes
                reader_name = getattr(card, "reader", None) or getattr(card, "readerName", None)
                if self._target_reader and reader_name is not None:
                    if self._target_reader not in str(reader_name):
                        continue

                atr_val = getattr(card, "atr", None)
                if atr_val is None:
                    # some pyscard objects expose getATR()
                    get_atr = getattr(card, "getATR", None)
                    if callable(get_atr):
                        atr_val = get_atr()

                if atr_val is None:
                    continue

                if isinstance(atr_val, (list, tuple)):
                    atr_bytes = bytes(atr_val)
                elif isinstance(atr_val, bytes):
                    atr_bytes = atr_val
                else:
                    try:
                        atr_bytes = bytes(atr_val)
                    except Exception:
                        continue

                with self._lock:
                    self._atr = atr_bytes
                    self._event.set()
                    # notify once per added card; leave others for subsequent events
                    return
        except Exception:
            # Observers must not raise; swallow and continue listening
            return

    def wait_for_next_atr(self, timeout: Optional[float] = None) -> Optional[bytes]:
        """Block until the next added-card event, or timeout. Returns ATR bytes or None."""
        got = self._event.wait(timeout)
        if not got:
            return None
        with self._lock:
            atr = self._atr
            # reset for next wait
            self._atr = None
            self._event.clear()
        return atr


def watch_atrs(target_reader: Optional[str] = None) -> Iterator[bytes]:
    """Generator that yields ATR bytes each time a card is presented.

    Usage:
        for atr in watch_atrs('ACR122'):
            print('ATR:', atr.hex())
    """
    monitor = CardMonitor()
    obs = _AtrObserver(target_reader=target_reader)
    monitor.addObserver(obs)
    try:
        while True:
            atr = obs.wait_for_next_atr(timeout=None)
            if atr is None:
                continue
            yield atr
    finally:
        monitor.deleteObserver(obs)

# --- Example Usage ---

def _main():
    """
    Demonstrates the usage of the HAL module for connecting to a card.
    This function is intended for direct execution of this file as a script.
    """
    print("--- HAL Module Test: Discover and Connect ---")
    try:
        readers_list = list_readers()
        print("Available readers:", readers_list)

        # Use the first available reader
        with CardManager(reader_index=0) as conn:
            print(f"\nConnected to card on '{readers_list[0]}'")
            atr_hex = conn.get_atr()
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

