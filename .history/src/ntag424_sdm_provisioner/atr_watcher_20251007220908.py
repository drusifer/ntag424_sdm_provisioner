"""ATR watcher utilities using pyscard's CardMonitor/CardObserver.

Provides a simple generator `watch_atrs(target_reader)` which yields ATR bytes
each time a card is presented. This module keeps its implementation small and
testable and avoids interacting with the rest of the HAL directly.
"""

from typing import Optional, Iterator
import threading

from smartcard.CardMonitoring import CardMonitor, CardObserver


class _AtrObserver(CardObserver):
    def __init__(self, target_reader: Optional[str] = None):
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._atr: Optional[bytes] = None
        self._target_reader = target_reader

    def update(self, observable, cards):
        try:
            added = cards[0] if isinstance(cards, (list, tuple)) and len(cards) >= 1 else cards
            for card in added or []:
                reader_name = getattr(card, "reader", None) or getattr(card, "readerName", None)
                if self._target_reader and reader_name is not None:
                    if self._target_reader not in str(reader_name):
                        continue

                atr_val = getattr(card, "atr", None)
                if atr_val is None:
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
                    return
        except Exception:
            return

    def wait_for_next_atr(self, timeout: Optional[float] = None) -> Optional[bytes]:
        got = self._event.wait(timeout)
        if not got:
            return None
        with self._lock:
            atr = self._atr
            self._atr = None
            self._event.clear()
        return atr


def watch_atrs(target_reader: Optional[str] = None) -> Iterator[bytes]:
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
