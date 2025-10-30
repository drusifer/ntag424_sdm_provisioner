"""
Defines the interface for key management systems.
"""
from abc import ABC, abstractmethod


class KeyManager(ABC):
    """
    Abstract base class for a key manager.

    This interface defines the contract for retrieving unique, diversified keys
    for a given tag UID, which is a critical security practice.
    """

    @abstractmethod
    def get_key_for_uid(self, uid: bytes, key_no: int) -> bytes:
        """
        Derives and returns a 16-byte AES key for a specific tag UID and key number.

        Args:
            uid: The 7-byte unique ID of the tag.
            key_no: The key number (0-4) to derive.

        Returns:
            A 16-byte AES key.
        """
        raise NotImplementedError


class StaticKeyManager(KeyManager):
    """
    A simple, INSECURE key manager for testing and demonstration purposes.

    This implementation returns a fixed, predefined key for each key number,
    regardless of the tag's UID.

    DO NOT USE THIS IN PRODUCTION.
    """

    def __init__(self, keys: dict[int, bytes]):
        for key_no, key in keys.items():
            if len(key) != 16:
                raise ValueError(f"Key {key_no} must be 16 bytes long.")
        self._keys = keys

    def get_key_for_uid(self, uid: bytes, key_no: int) -> bytes:
        if key_no not in self._keys:
            raise ValueError(f"No static key defined for key number {key_no}")
        print(f"  WARNING: Using static key for UID {uid.hex().upper()} and Key No. {key_no}")
        return self._keys[key_no]
