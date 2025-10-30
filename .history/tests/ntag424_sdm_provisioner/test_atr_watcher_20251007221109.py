import types

from ntag424_sdm_provisioner.atr_watcher import _AtrObserver


class FakeCard:
    def __init__(self, atr, reader=None):
        # atr can be list[int] or bytes
        self.atr = atr
        self.reader = reader


def test_atr_observer_receives_atr():
    obs = _AtrObserver(target_reader=None)

    # Simulate CardMonitor calling update with (added, removed)
    fake = FakeCard([0x3B, 0x88, 0x80, 0x01])
    obs.update(None, ([fake], []))

    result = obs.wait_for_next_atr(timeout=1.0)
    assert result == bytes([0x3B, 0x88, 0x80, 0x01])


def test_atr_observer_filters_reader():
    obs = _AtrObserver(target_reader="MyReader")
    fake_ok = FakeCard([0x01, 0x02], reader="MyReader 0")
    fake_bad = FakeCard([0x03, 0x04], reader="OtherReader")

    # First send a card for a different reader
    obs.update(None, ([fake_bad], []))
    # No ATR yet
    assert obs.wait_for_next_atr(timeout=0.1) is None

    # Now send a matching reader card
    obs.update(None, ([fake_ok], []))
    result = obs.wait_for_next_atr(timeout=1.0)
    assert result == bytes([0x01, 0x02])
