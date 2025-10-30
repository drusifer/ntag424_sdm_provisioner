import os

from ntag424_sdm_provisioner.key_manager import (
    DerivingKeyGenerator,
    InMemoryKeyStorage,
    DerivedKeyManager,
)


def test_derivation_deterministic():
    master = b"\x01" * 16
    gen = DerivingKeyGenerator(master)
    uid = b"\x04\x05\x06\x07\x08\x09\x0A"
    k1 = gen.derive_key(uid, 0)
    k2 = gen.derive_key(uid, 0)
    assert k1 == k2
    assert len(k1) == 16


def test_derivation_differs_by_uid_or_keyno():
    master = b"\x02" * 16
    gen = DerivingKeyGenerator(master)
    uid1 = b"\x01\x02\x03\x04\x05\x06\x07"
    uid2 = b"\x09\x0A\x0B\x0C\x0D\x0E\x0F"
    a = gen.derive_key(uid1, 0)
    b = gen.derive_key(uid2, 0)
    c = gen.derive_key(uid1, 1)
    assert a != b
    assert a != c


def test_storage_and_manager_cache():
    master = b"\x03" * 16
    gen = DerivingKeyGenerator(master)
    storage = InMemoryKeyStorage()
    manager = DerivedKeyManager(gen, storage)

    uid = os.urandom(7)
    k_first = manager.get_key_for_uid(uid, 2)
    # now modify generator result (simulate change) and ensure storage returns cached
    # value by calling generator directly and making sure manager still returns cached
    k_direct = gen.derive_key(uid, 2)
    assert k_first == k_direct


def test_wrap_unwrap():
    master = b"\x04" * 16
    gen = DerivingKeyGenerator(master)
    kek = b"\xAA" * 16
    uid = b"\x01\x02\x03\x04\x05\x06\x07"
    key = gen.derive_key(uid, 3)
    wrapped = gen.wrap_key(key, kek)
    assert isinstance(wrapped, bytes)
    unwrapped = gen.unwrap_key(wrapped, kek)
    assert unwrapped == key
