"""
Tests for Key Manager Interface

These tests validate the key manager interface and simple implementation.
"""

import pytest
from ntag424_sdm_provisioner.key_manager_interface import (
    SimpleKeyManager,
    UniqueKeyManager,
    create_key_manager,
    KEY_DEFAULT_FACTORY,
)


class TestSimpleKeyManager:
    """Test SimpleKeyManager implementation"""
    
    def test_default_factory_key(self):
        """SimpleKeyManager uses default factory key"""
        mgr = SimpleKeyManager()
        
        uid = b"\x04\x1B\x67\x4A\x5C\x3D\x80"
        key = mgr.get_key(uid, key_no=0)
        
        assert key == KEY_DEFAULT_FACTORY
        assert len(key) == 16
    
    def test_custom_factory_key(self):
        """SimpleKeyManager can use custom factory key"""
        custom_key = b"\xFF" * 16
        mgr = SimpleKeyManager(factory_key=custom_key)
        
        uid = b"\x04\x1B\x67\x4A\x5C\x3D\x80"
        key = mgr.get_key(uid, key_no=0)
        
        assert key == custom_key
    
    def test_all_key_numbers(self):
        """SimpleKeyManager handles all key numbers 0-4"""
        mgr = SimpleKeyManager()
        uid = b"\x04\x1B\x67\x4A\x5C\x3D\x80"
        
        for key_no in range(5):
            key = mgr.get_key(uid, key_no)
            assert key == KEY_DEFAULT_FACTORY
    
    def test_invalid_key_number(self):
        """SimpleKeyManager rejects invalid key numbers"""
        mgr = SimpleKeyManager()
        uid = b"\x04\x1B\x67\x4A\x5C\x3D\x80"
        
        with pytest.raises(ValueError, match="must be 0-4"):
            mgr.get_key(uid, key_no=5)
        
        with pytest.raises(ValueError, match="must be 0-4"):
            mgr.get_key(uid, key_no=-1)
    
    def test_invalid_key_length(self):
        """SimpleKeyManager rejects keys that aren't 16 bytes"""
        with pytest.raises(ValueError, match="must be 16 bytes"):
            SimpleKeyManager(factory_key=b"\x00" * 8)  # Too short
        
        with pytest.raises(ValueError, match="must be 16 bytes"):
            SimpleKeyManager(factory_key=b"\x00" * 32)  # Too long
    
    def test_same_key_for_all_uids(self):
        """SimpleKeyManager returns same key regardless of UID"""
        mgr = SimpleKeyManager()
        
        uid1 = b"\x04\x1B\x67\x4A\x5C\x3D\x80"
        uid2 = b"\x04\xAA\xBB\xCC\xDD\xEE\xFF"
        
        key1 = mgr.get_key(uid1, key_no=0)
        key2 = mgr.get_key(uid2, key_no=0)
        
        assert key1 == key2 == KEY_DEFAULT_FACTORY
    
    def test_string_representation(self):
        """SimpleKeyManager has useful string representation"""
        mgr = SimpleKeyManager()
        s = str(mgr)
        
        assert "SimpleKeyManager" in s
        assert "factory_key" in s


class TestKeyManagerFactory:
    """Test key manager factory function"""
    
    def test_create_simple_key_manager(self):
        """Factory creates SimpleKeyManager by default"""
        mgr = create_key_manager(use_unique_keys=False)
        
        assert isinstance(mgr, SimpleKeyManager)
    
    def test_create_with_custom_key(self):
        """Factory accepts custom factory key"""
        custom_key = b"\xAB" * 16
        mgr = create_key_manager(use_unique_keys=False, master_key=custom_key)
        
        uid = b"\x04\x1B\x67\x4A\x5C\x3D\x80"
        key = mgr.get_key(uid, key_no=0)
        
        assert key == custom_key
    
    def test_unique_key_manager_not_implemented(self):
        """Factory raises NotImplementedError for unique keys"""
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            create_key_manager(use_unique_keys=True)


class TestUniqueKeyManager:
    """Test UniqueKeyManager (stub - not yet implemented)"""
    
    def test_not_implemented(self):
        """UniqueKeyManager raises NotImplementedError"""
        master_key = b"\xFF" * 16
        
        with pytest.raises(NotImplementedError):
            UniqueKeyManager(master_key)


class TestKeyManagerProtocol:
    """Test that implementations follow KeyManager protocol"""
    
    def test_simple_manager_follows_protocol(self):
        """SimpleKeyManager implements KeyManager protocol"""
        mgr = SimpleKeyManager()
        
        # Protocol requires get_key method with correct signature
        assert hasattr(mgr, 'get_key')
        assert callable(mgr.get_key)
        
        # Should work with protocol
        uid = b"\x04\x1B\x67\x4A\x5C\x3D\x80"
        key = mgr.get_key(uid, key_no=0)
        
        assert isinstance(key, bytes)
        assert len(key) == 16


# Example usage for documentation
def test_example_usage():
    """Example of how to use KeyManager in provisioning"""
    # Create key manager
    key_mgr = create_key_manager(use_unique_keys=False)
    
    # Get key for a specific coin
    coin_uid = b"\x04\x1B\x67\x4A\x5C\x3D\x80"
    
    # Get application master key (key 0)
    master_key = key_mgr.get_key(coin_uid, key_no=0)
    
    # Get SDM keys (keys 1 and 2)
    sdm_meta_key = key_mgr.get_key(coin_uid, key_no=1)
    sdm_file_key = key_mgr.get_key(coin_uid, key_no=2)
    
    # All are factory keys for now
    assert master_key == KEY_DEFAULT_FACTORY
    assert sdm_meta_key == KEY_DEFAULT_FACTORY
    assert sdm_file_key == KEY_DEFAULT_FACTORY

