"""Key manager interfaces and simple implementations.

This module defines two orthogonal interfaces:
 - KeyGenerator: derives and (optionally) wraps keys for a UID/key number
 - KeyStorage: stores and retrieves keys (could be in-memory, file-based, HSM, etc.)

It also provides a small, test-friendly implementation:
 - DerivingKeyGenerator: derives per-UID keys using AES-CMAC over the master key
 - InMemoryKeyStorage: a volatile dictionary-backed storage
 - DerivedKeyManager: a KeyManager that composes a generator and storage

The goal is to separate key generation/wrapping from persistence so production
backends can be introduced without changing derivation logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Dict, Tuple
import os

from Crypto.Hash import CMAC
from Crypto.Cipher import AES


class KeyManager(ABC):
    """Legacy-compatible KeyManager interface.

    Implementations should return a 16-byte AES key for a given tag UID and
    key number.
    """

    @abstractmethod
    def get_key_for_uid(self, uid: bytes, key_no: int) -> bytes:
        raise NotImplementedError


class KeyGenerator(ABC):
    """Generates or derives keys and supports optional wrapping.

    Implementations MUST NOT log or expose key material.
    """

    @abstractmethod
    def derive_key(self, uid: bytes, key_no: int) -> bytes:
        """Deterministically derive a 16-byte key for a UID and key number."""

    @abstractmethod
    def wrap_key(self, key: bytes, kek: bytes) -> bytes:
        """Wraps (encrypts) a key with a Key-Encryption-Key. Returns wrapped blob."""

    @abstractmethod
    def unwrap_key(self, wrapped: bytes, kek: bytes) -> bytes:
        """Unwraps (decrypts) a wrapped key with a Key-Encryption-Key."""


class KeyStorage(ABC):
    """Abstract key storage backend.

    Storage backends decide whether keys are stored plaintext or wrapped.
    """

    @abstractmethod
    def get_key(self, uid: bytes, key_no: int) -> Optional[bytes]:
        pass

    @abstractmethod
    def store_key(self, uid: bytes, key_no: int, key: bytes) -> None:
        pass

    @abstractmethod
    def delete_key(self, uid: bytes, key_no: int) -> None:
        pass


class DerivingKeyGenerator(KeyGenerator):
    """Derives per-UID keys using AES-CMAC (deterministic) and provides a
    simple AES-CBC based wrapper for examples/tests.

    Notes:
    - Derivation: SesKey = CMAC(master_key, uid || key_no_byte)
    - Wrapping: AES-CBC with random IV prefixed (not RFC3394). This is
      sufficient for demonstration and tests but not recommended for HSM-grade
      key transport.
    """

    def __init__(self, master_key: bytes):
        if len(master_key) not in (16, 24, 32):
            raise ValueError("master_key must be 16/24/32 bytes for AES")
        self.master_key = master_key

    def derive_key(self, uid: bytes, key_no: int) -> bytes:
        if not 0 <= key_no <= 0xFF:
            raise ValueError("key_no must be 0-255")
        # Use CMAC(master_key, uid || key_no)
        c = CMAC.new(self.master_key, ciphermod=AES)
        c.update(uid + bytes([key_no]))
        # Return first 16 bytes (AES-128 key)
        return c.digest()[:16]

    def wrap_key(self, key: bytes, kek: bytes) -> bytes:
        if len(kek) not in (16, 24, 32):
            raise ValueError("KEK must be 16/24/32 bytes for AES")
        iv = os.urandom(16)
        cipher = AES.new(kek, AES.MODE_CBC, iv=iv)
        # simple PKCS7 padding
        pad_len = 16 - (len(key) % 16)
        padded = key + bytes([pad_len]) * pad_len
        ct = cipher.encrypt(padded)
        return iv + ct

    def unwrap_key(self, wrapped: bytes, kek: bytes) -> bytes:
        if len(wrapped) < 16:
            raise ValueError("wrapped blob too short")
        iv = wrapped[:16]
        ct = wrapped[16:]
        cipher = AES.new(kek, AES.MODE_CBC, iv=iv)
        padded = cipher.decrypt(ct)
        pad_len = padded[-1]
        if pad_len < 1 or pad_len > 16:
            raise ValueError("Invalid padding on unwrap")
        return padded[:-pad_len]


class InMemoryKeyStorage(KeyStorage):
    """A simple volatile storage used for tests and examples."""

    def __init__(self):
        # keys: (uid_hex, key_no) -> bytes
        self._store: Dict[Tuple[str, int], bytes] = {}

    def _k(self, uid: bytes, key_no: int) -> Tuple[str, int]:
        return (uid.hex().upper(), key_no)

    def get_key(self, uid: bytes, key_no: int) -> Optional[bytes]:
        return self._store.get(self._k(uid, key_no))

    def store_key(self, uid: bytes, key_no: int, key: bytes) -> None:
        self._store[self._k(uid, key_no)] = key

    def delete_key(self, uid: bytes, key_no: int) -> None:
        self._store.pop(self._k(uid, key_no), None)


class DerivedKeyManager(KeyManager):
    """High-level KeyManager that composes a KeyGenerator and KeyStorage.

    Behavior:
    - When `get_key_for_uid` is called, storage is consulted first.
    - If not present, the generator derives the key, it is stored, and returned.
    """

    def __init__(self, generator: KeyGenerator, storage: KeyStorage):
        self.generator = generator
        self.storage = storage

    def get_key_for_uid(self, uid: bytes, key_no: int) -> bytes:
        key = self.storage.get_key(uid, key_no)
        if key is not None:
            return key
        key = self.generator.derive_key(uid, key_no)
        self.storage.store_key(uid, key_no, key)
        return key


class StaticKeyManager(KeyManager):
    """Backwards-compatible static key manager (keeps previous behavior).

    Internally uses InMemoryKeyStorage to satisfy the KeyManager API.
    """

    def __init__(self, keys: Dict[int, bytes]):
        for key_no, key in keys.items():
            if len(key) != 16:
                raise ValueError(f"Key {key_no} must be 16 bytes long.")
        self._keys = keys
        self._storage = InMemoryKeyStorage()
        # preload
        for kno, k in keys.items():
            self._storage.store_key(b"STATIC", kno, k)

    def get_key_for_uid(self, uid: bytes, key_no: int) -> bytes:
        # user-visible warning kept intentionally
        print(f"  WARNING: Using static key for UID {uid.hex().upper()} and Key No. {key_no}")
        # fall back to provided static map
        if key_no in self._keys:
            return self._keys[key_no]
        raise ValueError(f"No static key defined for key number {key_no}")

