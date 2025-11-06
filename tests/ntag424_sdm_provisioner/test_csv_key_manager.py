"""
Unit tests for CSV Key Manager.

Tests the CsvKeyManager implementation of the KeyManager protocol.
"""

import pytest
from pathlib import Path
import tempfile
import os

from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, TagKeys
from ntag424_sdm_provisioner.key_manager_interface import KEY_DEFAULT_FACTORY


@pytest.fixture
def temp_csv_files():
    """Create temporary CSV files for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "test_keys.csv"
        backup_path = Path(tmpdir) / "test_keys_backup.csv"
        yield str(csv_path), str(backup_path)


@pytest.fixture
def key_manager(temp_csv_files):
    """Create a CsvKeyManager instance with temporary files."""
    csv_path, backup_path = temp_csv_files
    return CsvKeyManager(csv_path=csv_path, backup_path=backup_path)


@pytest.fixture
def test_uid():
    """Test UID."""
    return bytes.fromhex("04B3664A2F7080")


class TestTagKeys:
    """Test TagKeys dataclass."""
    
    def test_from_factory_keys(self):
        """Factory keys should be all zeros."""
        uid_hex = "04B3664A2F7080"
        tag_keys = TagKeys.from_factory_keys(uid_hex)
        
        assert tag_keys.uid == uid_hex
        assert tag_keys.picc_master_key == "00" * 16
        assert tag_keys.app_read_key == "00" * 16
        assert tag_keys.sdm_mac_key == "00" * 16
        assert tag_keys.status == "factory"
    
    def test_get_key_bytes(self):
        """Key bytes should be correctly converted from hex."""
        tag_keys = TagKeys(
            uid="04B3664A2F7080",
            picc_master_key="0123456789ABCDEF" * 2,
            app_read_key="FEDCBA9876543210" * 2,
            sdm_mac_key="AAAAAAAAAAAAAAAA" * 2,
            provisioned_date="2025-11-02T10:00:00",
            status="provisioned",
            notes="Test"
        )
        
        picc_key = tag_keys.get_picc_master_key_bytes()
        app_key = tag_keys.get_app_read_key_bytes()
        sdm_key = tag_keys.get_sdm_mac_key_bytes()
        
        assert len(picc_key) == 16
        assert len(app_key) == 16
        assert len(sdm_key) == 16
        assert picc_key.hex().upper() == "0123456789ABCDEF" * 2
        assert app_key.hex().upper() == "FEDCBA9876543210" * 2
        assert sdm_key.hex().upper() == "AAAAAAAAAAAAAAAA" * 2


class TestCsvKeyManager:
    """Test CsvKeyManager."""
    
    def test_initialization_creates_files(self, temp_csv_files):
        """Initialization should create CSV files if they don't exist."""
        csv_path, backup_path = temp_csv_files
        
        # Files should not exist yet
        assert not Path(csv_path).exists()
        assert not Path(backup_path).exists()
        
        # Create key manager
        key_mgr = CsvKeyManager(csv_path=csv_path, backup_path=backup_path)
        
        # Files should now exist
        assert Path(csv_path).exists()
        assert Path(backup_path).exists()
    
    def test_get_key_unknown_uid_returns_factory_keys(self, key_manager, test_uid):
        """Getting key for unknown UID should return factory keys."""
        key0 = key_manager.get_key(test_uid, key_no=0)
        
        assert key0 == KEY_DEFAULT_FACTORY
        assert len(key0) == 16
        assert key0 == b'\x00' * 16
    
    def test_get_key_invalid_key_no_raises_error(self, key_manager, test_uid):
        """Invalid key number should raise ValueError."""
        with pytest.raises(ValueError, match="Key number must be 0-4"):
            key_manager.get_key(test_uid, key_no=-1)
        
        with pytest.raises(ValueError, match="Key number must be 0-4"):
            key_manager.get_key(test_uid, key_no=5)
    
    def test_generate_random_keys(self, key_manager, test_uid):
        """Generated keys should be random and unique."""
        keys1 = key_manager.generate_random_keys(test_uid)
        keys2 = key_manager.generate_random_keys(test_uid)
        
        # All keys should be 32 hex chars (16 bytes)
        assert len(keys1.picc_master_key) == 32
        assert len(keys1.app_read_key) == 32
        assert len(keys1.sdm_mac_key) == 32
        
        # Keys should be different from each other
        assert keys1.picc_master_key != keys1.app_read_key
        assert keys1.picc_master_key != keys1.sdm_mac_key
        assert keys1.app_read_key != keys1.sdm_mac_key
        
        # Two generations should produce different keys
        assert keys1.picc_master_key != keys2.picc_master_key
        assert keys1.app_read_key != keys2.app_read_key
        assert keys1.sdm_mac_key != keys2.sdm_mac_key
        
        # Status should be provisioned
        assert keys1.status == "provisioned"
        assert keys2.status == "provisioned"
    
    def test_save_and_retrieve_keys(self, key_manager, test_uid):
        """Saved keys should be retrievable."""
        # Generate and save keys
        new_keys = key_manager.generate_random_keys(test_uid)
        key_manager.save_tag_keys(test_uid, new_keys)
        
        # Retrieve keys
        retrieved_key0 = key_manager.get_key(test_uid, key_no=0)
        retrieved_key1 = key_manager.get_key(test_uid, key_no=1)
        retrieved_key3 = key_manager.get_key(test_uid, key_no=3)
        
        # Verify they match
        assert retrieved_key0.hex() == new_keys.picc_master_key
        assert retrieved_key1.hex() == new_keys.app_read_key
        assert retrieved_key3.hex() == new_keys.sdm_mac_key
    
    def test_save_updates_existing_entry(self, key_manager, test_uid):
        """Saving keys for same UID should update, not duplicate."""
        # Save first set of keys
        keys1 = key_manager.generate_random_keys(test_uid)
        key_manager.save_tag_keys(test_uid, keys1)
        
        # Save second set of keys (same UID)
        keys2 = key_manager.generate_random_keys(test_uid)
        keys2.notes = "Updated keys"
        key_manager.save_tag_keys(test_uid, keys2)
        
        # Should only have one entry
        all_tags = key_manager.list_tags()
        assert len(all_tags) == 1
        
        # Should have the second set of keys
        assert all_tags[0].picc_master_key == keys2.picc_master_key
        assert all_tags[0].notes == "Updated keys"
    
    def test_backup_keys_on_update(self, key_manager, test_uid, temp_csv_files):
        """Updating keys should create backup."""
        csv_path, backup_path = temp_csv_files
        
        # Save first set of keys
        keys1 = key_manager.generate_random_keys(test_uid)
        keys1.status = "provisioned"
        key_manager.save_tag_keys(test_uid, keys1)
        
        # Backup file should be empty (no backup on first save)
        with open(backup_path, 'r') as f:
            lines = f.readlines()
        assert len(lines) == 1  # Just header
        
        # Update keys
        keys2 = key_manager.generate_random_keys(test_uid)
        keys2.status = "updated"
        key_manager.save_tag_keys(test_uid, keys2)
        
        # Backup file should now have one entry
        with open(backup_path, 'r') as f:
            lines = f.readlines()
        assert len(lines) == 2  # Header + one backup
        assert keys1.picc_master_key in lines[1]  # First keys backed up
    
    def test_list_tags(self, key_manager):
        """List tags should return all saved tags."""
        uid1 = bytes.fromhex("04B3664A2F7080")
        uid2 = bytes.fromhex("04C4775B308191")
        
        keys1 = key_manager.generate_random_keys(uid1)
        keys2 = key_manager.generate_random_keys(uid2)
        
        key_manager.save_tag_keys(uid1, keys1)
        key_manager.save_tag_keys(uid2, keys2)
        
        all_tags = key_manager.list_tags()
        
        assert len(all_tags) == 2
        uids = [tag.uid for tag in all_tags]
        assert uid1.hex().upper() in uids
        assert uid2.hex().upper() in uids
    
    def test_get_tag_keys_returns_all_keys(self, key_manager, test_uid):
        """get_tag_keys should return TagKeys object."""
        new_keys = key_manager.generate_random_keys(test_uid)
        key_manager.save_tag_keys(test_uid, new_keys)
        
        tag_keys = key_manager.get_tag_keys(test_uid)
        
        assert isinstance(tag_keys, TagKeys)
        assert tag_keys.uid == test_uid.hex().upper()
        assert tag_keys.picc_master_key == new_keys.picc_master_key
        assert tag_keys.app_read_key == new_keys.app_read_key
        assert tag_keys.sdm_mac_key == new_keys.sdm_mac_key
    
    def test_key_no_mapping(self, key_manager, test_uid):
        """Different key numbers should return different keys."""
        new_keys = key_manager.generate_random_keys(test_uid)
        key_manager.save_tag_keys(test_uid, new_keys)
        
        key0 = key_manager.get_key(test_uid, key_no=0)
        key1 = key_manager.get_key(test_uid, key_no=1)
        key3 = key_manager.get_key(test_uid, key_no=3)
        
        # All keys should be different
        assert key0 != key1
        assert key0 != key3
        assert key1 != key3
        
        # Keys 2 and 4 should return factory key (not used yet)
        key2 = key_manager.get_key(test_uid, key_no=2)
        key4 = key_manager.get_key(test_uid, key_no=4)
        assert key2 == KEY_DEFAULT_FACTORY
        assert key4 == KEY_DEFAULT_FACTORY
    
    def test_uid_case_insensitive(self, key_manager):
        """UID lookup should be case-insensitive."""
        # Save with lowercase
        uid_lower = bytes.fromhex("04b3664a2f7080")
        keys = key_manager.generate_random_keys(uid_lower)
        key_manager.save_tag_keys(uid_lower, keys)
        
        # Retrieve with uppercase
        uid_upper = bytes.fromhex("04B3664A2F7080")
        retrieved_key = key_manager.get_key(uid_upper, key_no=0)
        
        assert retrieved_key.hex() == keys.picc_master_key


class TestCsvKeyManagerIntegration:
    """Integration tests showing complete workflow."""
    
    def test_complete_provisioning_workflow(self, key_manager, test_uid):
        """
        Test complete workflow: unknown tag → provision → save → retrieve.
        
        This simulates the full provisioning sequence:
        1. Tag is unknown (gets factory keys)
        2. Generate new random keys
        3. Save keys to database
        4. Retrieve keys for re-authentication
        5. Verify keys match
        """
        # Step 1: Unknown tag gets factory keys
        initial_key = key_manager.get_key(test_uid, key_no=0)
        assert initial_key == KEY_DEFAULT_FACTORY
        
        # Step 2: Generate new keys for provisioning
        new_keys = key_manager.generate_random_keys(test_uid)
        assert new_keys.status == "provisioned"
        assert new_keys.picc_master_key != "00" * 16
        
        # Step 3: Save keys (simulates successful provisioning)
        key_manager.save_tag_keys(test_uid, new_keys)
        
        # Step 4: Later, retrieve keys for re-authentication
        picc_key = key_manager.get_key(test_uid, key_no=0)
        app_key = key_manager.get_key(test_uid, key_no=1)
        sdm_key = key_manager.get_key(test_uid, key_no=3)
        
        # Step 5: Verify retrieved keys match what we saved
        assert picc_key.hex() == new_keys.picc_master_key
        assert app_key.hex() == new_keys.app_read_key
        assert sdm_key.hex() == new_keys.sdm_mac_key
        
        # Verify keys are unique
        assert picc_key != app_key
        assert picc_key != sdm_key
        assert app_key != sdm_key
    
    def test_key_update_workflow(self, key_manager, test_uid):
        """
        Test key update workflow with backup.
        
        Simulates changing keys on a previously provisioned tag.
        """
        # Initial provisioning
        keys_v1 = key_manager.generate_random_keys(test_uid)
        keys_v1.status = "provisioned"
        keys_v1.notes = "Initial provisioning"
        key_manager.save_tag_keys(test_uid, keys_v1)
        
        # Update keys (e.g., security rotation)
        keys_v2 = key_manager.generate_random_keys(test_uid)
        keys_v2.status = "updated"
        keys_v2.notes = "Security rotation"
        key_manager.save_tag_keys(test_uid, keys_v2)
        
        # Current keys should be v2
        current_key = key_manager.get_key(test_uid, key_no=0)
        assert current_key.hex() == keys_v2.picc_master_key
        
        # Should only have one entry in main database
        all_tags = key_manager.list_tags()
        assert len(all_tags) == 1
        assert all_tags[0].status == "updated"
    
    def test_multiple_tags_workflow(self, key_manager):
        """Test managing multiple tags simultaneously."""
        # Provision 3 different tags
        uid1 = bytes.fromhex("04B3664A2F7080")
        uid2 = bytes.fromhex("04C4775B308191")
        uid3 = bytes.fromhex("04D5886C419202")
        
        keys1 = key_manager.generate_random_keys(uid1)
        keys2 = key_manager.generate_random_keys(uid2)
        keys3 = key_manager.generate_random_keys(uid3)
        
        keys1.notes = "Tag 1"
        keys2.notes = "Tag 2"
        keys3.notes = "Tag 3"
        
        key_manager.save_tag_keys(uid1, keys1)
        key_manager.save_tag_keys(uid2, keys2)
        key_manager.save_tag_keys(uid3, keys3)
        
        # All tags should be in database
        all_tags = key_manager.list_tags()
        assert len(all_tags) == 3
        
        # Each tag should have unique keys
        key1 = key_manager.get_key(uid1, key_no=0)
        key2 = key_manager.get_key(uid2, key_no=0)
        key3 = key_manager.get_key(uid3, key_no=0)
        
        assert key1 != key2
        assert key1 != key3
        assert key2 != key3
        
        # Each tag should retrieve its own keys
        assert key1.hex() == keys1.picc_master_key
        assert key2.hex() == keys2.picc_master_key
        assert key3.hex() == keys3.picc_master_key


class TestProvisionTagContextManager:
    """Test two-phase commit context manager for provisioning."""
    
    def test_provision_success(self, key_manager, test_uid):
        """Successful provisioning should update status to 'provisioned'."""
        # Use context manager - simulates successful provisioning
        with key_manager.provision_tag(test_uid) as keys:
            # Phase 1: Keys saved with 'pending' status
            assert keys.status == "pending"
            assert keys.notes == "Provisioning in progress..."
            
            # Verify keys are in database with pending status
            db_keys = key_manager.get_tag_keys(test_uid)
            assert db_keys.status == "pending"
            
            # Simulate successful provisioning
            # (In real code: ChangeKey commands here)
            pass
        
        # Phase 2: After successful exit, status should be 'provisioned'
        final_keys = key_manager.get_tag_keys(test_uid)
        assert final_keys.status == "provisioned"
        assert final_keys.notes == "Successfully provisioned"
        assert final_keys.uid == test_uid.hex().upper()
    
    def test_provision_failure(self, key_manager, test_uid):
        """Failed provisioning should update status to 'failed'."""
        # Use context manager - simulates failed provisioning
        try:
            with key_manager.provision_tag(test_uid) as keys:
                # Phase 1: Keys saved with 'pending' status
                assert keys.status == "pending"
                
                # Simulate provisioning failure
                raise RuntimeError("Tag communication failed")
        except RuntimeError as e:
            assert str(e) == "Tag communication failed"
        
        # Phase 2: After exception, status should be 'failed'
        final_keys = key_manager.get_tag_keys(test_uid)
        assert final_keys.status == "failed"
        assert "Tag communication failed" in final_keys.notes
    
    def test_provision_generates_new_keys(self, key_manager, test_uid):
        """Each provision attempt should generate fresh random keys."""
        # First attempt
        with key_manager.provision_tag(test_uid) as keys1:
            key1_picc = keys1.picc_master_key
        
        # Second attempt (e.g., re-provision)
        # Delete first entry to simulate clean slate
        all_tags = key_manager.list_tags()
        for tag in all_tags:
            if tag.uid == test_uid.hex().upper():
                # In real implementation, would have delete method
                pass
        
        with key_manager.provision_tag(test_uid) as keys2:
            key2_picc = keys2.picc_master_key
        
        # Keys should be different (randomly generated)
        assert key1_picc != key2_picc
    
    def test_provision_atomic_commit(self, key_manager, test_uid):
        """
        Verify atomic commit behavior.
        
        Database should show:
        - 'pending' during provisioning
        - 'provisioned' after success
        - 'failed' after exception
        """
        # Test 1: Check intermediate state
        class ProvisioningSimulator:
            """Simulates checking state during provisioning."""
            def __init__(self, key_mgr, uid):
                self.key_mgr = key_mgr
                self.uid = uid
                self.checked_pending = False
            
            def provision(self):
                with self.key_mgr.provision_tag(self.uid) as keys:
                    # Check state during provisioning
                    db_keys = self.key_mgr.get_tag_keys(self.uid)
                    assert db_keys.status == "pending"
                    self.checked_pending = True
        
        simulator = ProvisioningSimulator(key_manager, test_uid)
        simulator.provision()
        
        assert simulator.checked_pending  # Confirmed we checked during provisioning
        
        # After exit, should be provisioned
        final_keys = key_manager.get_tag_keys(test_uid)
        assert final_keys.status == "provisioned"
    
    def test_provision_backup_created(self, key_manager, test_uid, temp_csv_files):
        """Provisioning should create backups on updates."""
        csv_path, backup_path = temp_csv_files
        
        # First provision
        with key_manager.provision_tag(test_uid) as keys1:
            pass
        
        # Second provision (update)
        with key_manager.provision_tag(test_uid) as keys2:
            pass
        
        # Backup should exist
        with open(backup_path, 'r') as f:
            lines = f.readlines()
        
        # Should have header + at least one backup
        assert len(lines) >= 2
    
    def test_provision_exception_propagates(self, key_manager, test_uid):
        """Exception during provisioning should propagate to caller."""
        class CustomProvisioningError(Exception):
            pass
        
        with pytest.raises(CustomProvisioningError):
            with key_manager.provision_tag(test_uid) as keys:
                # Simulate specific error
                raise CustomProvisioningError("Hardware authentication failed")
        
        # Status should be 'failed'
        final_keys = key_manager.get_tag_keys(test_uid)
        assert final_keys.status == "failed"
        assert "Hardware authentication failed" in final_keys.notes

