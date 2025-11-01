"""
Key Management Interface for NTAG424 DNA Provisioning

This module defines the interface for key management. The actual implementation
of unique key derivation per coin is deferred for later implementation.

For now, we provide a simple implementation that uses factory keys.
"""

from abc import ABC, abstractmethod
from typing import Protocol


# Default factory key (all zeros)
KEY_DEFAULT_FACTORY = b"\x00" * 16


class KeyManager(Protocol):
    """
    Protocol (interface) for key management.
    
    This defines the contract that any key manager implementation must follow.
    Implementations can use factory keys, derived keys, or retrieve from database.
    """
    
    def get_key(self, uid: bytes, key_no: int) -> bytes:
        """
        Retrieve the key for a specific tag and key number.
        
        Args:
            uid: Tag's 7-byte unique identifier
            key_no: Key number (0-4 for application keys)
                    0 = Application Master Key
                    1-4 = Application Keys (can be used for SDM)
        
        Returns:
            16-byte AES-128 key
            
        Raises:
            ValueError: If key_no is invalid (not 0-4)
            KeyError: If key cannot be retrieved for this UID
        """
        ...


class SimpleKeyManager:
    """
    Simple key manager that uses factory default keys for all tags.
    
    This is a temporary implementation for initial development and testing.
    It does NOT provide unique keys per coin - all coins use the same keys.
    
    Use this during development. Replace with UniqueKeyManager later for production.
    """
    
    def __init__(self, factory_key: bytes = KEY_DEFAULT_FACTORY):
        """
        Initialize with factory key.
        
        Args:
            factory_key: 16-byte AES-128 key to use for all tags (default: all zeros)
        """
        if len(factory_key) != 16:
            raise ValueError(f"Key must be 16 bytes, got {len(factory_key)}")
        self.factory_key = factory_key
    
    def get_key(self, uid: bytes, key_no: int) -> bytes:
        """
        Returns the factory key for all UIDs and key numbers.
        
        Args:
            uid: Tag's 7-byte UID (ignored in this implementation)
            key_no: Key number 0-4
        
        Returns:
            Factory key (same for all tags)
        """
        if key_no < 0 or key_no > 4:
            raise ValueError(f"Key number must be 0-4, got {key_no}")
        
        # For now, all keys are the same factory key
        # TODO: Later, return different keys per key_no if needed
        return self.factory_key
    
    def __str__(self) -> str:
        return f"SimpleKeyManager(factory_key={'00'*16 if self.factory_key == KEY_DEFAULT_FACTORY else '***'})"


# TODO: Implement later when unique keys per coin are needed
class UniqueKeyManager:
    """
    FUTURE: Key manager that derives unique keys per coin.
    
    This will implement CMAC-based key derivation function (KDF) to generate
    unique keys for each coin based on:
    - Master key (secret, stored securely)
    - Tag UID (unique per coin)
    - Key number (0-4)
    
    Algorithm (from NXP AN12196):
        derived_key = CMAC(master_key, 0x01 || UID || key_no)
    
    Benefits:
    - Each coin has unique keys
    - Compromising one coin doesn't affect others
    - Keys can be regenerated from UID (no database needed)
    """
    
    def __init__(self, master_key: bytes):
        """
        Initialize with master key.
        
        Args:
            master_key: 16-byte secret master key for derivation
        """
        raise NotImplementedError(
            "UniqueKeyManager not yet implemented. "
            "Use SimpleKeyManager for now."
        )
    
    def get_key(self, uid: bytes, key_no: int) -> bytes:
        """Derives unique key for UID + key_no using CMAC-KDF."""
        raise NotImplementedError("Use SimpleKeyManager for now")


# Factory function for creating key managers
def create_key_manager(
    use_unique_keys: bool = False,
    master_key: bytes = KEY_DEFAULT_FACTORY
) -> KeyManager:
    """
    Factory function to create appropriate key manager.
    
    Args:
        use_unique_keys: If True, use UniqueKeyManager (not yet implemented)
                        If False, use SimpleKeyManager
        master_key: Master key for derivation, or factory key for simple mode
    
    Returns:
        KeyManager instance
        
    Example:
        # For development/testing
        key_mgr = create_key_manager(use_unique_keys=False)
        
        # For production (when implemented)
        key_mgr = create_key_manager(use_unique_keys=True, master_key=SECRET_KEY)
    """
    if use_unique_keys:
        # Future: return UniqueKeyManager(master_key)
        raise NotImplementedError(
            "Unique key derivation not yet implemented. "
            "Set use_unique_keys=False to use factory keys."
        )
    else:
        return SimpleKeyManager(factory_key=master_key)


__all__ = [
    'KeyManager',
    'SimpleKeyManager',
    'UniqueKeyManager',
    'create_key_manager',
    'KEY_DEFAULT_FACTORY',
]

