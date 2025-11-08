"""
CSV-based key manager for NTAG424 DNA tags.

Stores tag keys in a simple CSV file for persistence across sessions.
Implements the KeyManager protocol for compatibility with provisioning flow.
"""

import csv
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from contextlib import contextmanager

from ntag424_sdm_provisioner.key_manager_interface import KeyManager, KEY_DEFAULT_FACTORY


@dataclass
class TagKeys:
    """Keys and metadata for a single NTAG424 DNA tag."""
    uid: str  # Hex string (e.g., "04B3664A2F7080")
    picc_master_key: str  # Key 0 (hex string, 32 chars)
    app_read_key: str     # Key 1 (hex string, 32 chars)
    sdm_mac_key: str      # Key 3 (hex string, 32 chars)
    provisioned_date: str  # ISO format timestamp
    status: str  # 'factory', 'provisioned', 'locked', 'error'
    notes: str = ""
    
    def get_picc_master_key_bytes(self) -> bytes:
        """Get PICC master key as bytes."""
        return bytes.fromhex(self.picc_master_key)
    
    def get_app_read_key_bytes(self) -> bytes:
        """Get app read key as bytes."""
        return bytes.fromhex(self.app_read_key)
    
    def get_sdm_mac_key_bytes(self) -> bytes:
        """Get SDM MAC key as bytes."""
        return bytes.fromhex(self.sdm_mac_key)
    
    def get_asset_tag(self) -> str:
        """Get short asset tag code from UID."""
        from ntag424_sdm_provisioner.uid_utils import uid_to_asset_tag
        return uid_to_asset_tag(bytes.fromhex(self.uid))
    
    def __str__(self) -> str:
        """Format TagKeys for display."""
        from ntag424_sdm_provisioner.uid_utils import uid_to_asset_tag
        asset_tag = uid_to_asset_tag(bytes.fromhex(self.uid))
        return (
            f"TagKeys(\n"
            f"  UID: {self.uid} [Tag: {asset_tag}]\n"
            f"  Status: {self.status}\n"
            f"  Provisioned: {self.provisioned_date}\n"
            f"  Notes: {self.notes[:50]}{'...' if len(self.notes) > 50 else ''}\n"
            f")"
        )
    
    @staticmethod
    def from_factory_keys(uid: str) -> 'TagKeys':
        """Create TagKeys entry with factory default keys."""
        factory_key = "00000000000000000000000000000000"
        return TagKeys(
            uid=uid,
            picc_master_key=factory_key,
            app_read_key=factory_key,
            sdm_mac_key=factory_key,
            provisioned_date=datetime.now().isoformat(),
            status="factory",
            notes="Factory default keys"
        )


class CsvKeyManager:
    """
    CSV-based key manager implementing the KeyManager protocol.
    
    Keys are stored in a primary CSV file (tag_keys.csv) and backed up
    to a backup file (tag_keys_backup.csv) before any changes.
    
    This provides:
    - Persistent storage of unique keys per tag
    - Automatic backup before key changes
    - Factory key fallback for new tags
    - Compatible with KeyManager protocol
    """
    
    FIELDNAMES = ['uid', 'picc_master_key', 'app_read_key', 'sdm_mac_key', 
                  'provisioned_date', 'status', 'notes']
    
    def __init__(self, csv_path: str = "tag_keys.csv", backup_path: str = "tag_keys_backup.csv"):
        """
        Initialize key manager.
        
        Args:
            csv_path: Path to main keys CSV file
            backup_path: Path to backup CSV file
        """
        self.csv_path = Path(csv_path)
        self.backup_path = Path(backup_path)
        self._ensure_csv_exists()
    
    def _ensure_csv_exists(self):
        """Create CSV file with headers if it doesn't exist."""
        if not self.csv_path.exists():
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()
            print(f"[INFO] Created new key database: {self.csv_path}")
        
        if not self.backup_path.exists():
            with open(self.backup_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES + ['backup_timestamp'])
                writer.writeheader()
            print(f"[INFO] Created backup database: {self.backup_path}")
    
    def get_key(self, uid: bytes, key_no: int) -> bytes:
        """
        Get key for a specific tag and key number (implements KeyManager protocol).
        
        Args:
            uid: Tag UID as bytes
            key_no: Key number (0 = PICC Master, 1 = App Read, 3 = SDM MAC)
            
        Returns:
            16-byte AES-128 key
            
        Raises:
            ValueError: If key_no is invalid
        """
        if key_no < 0 or key_no > 4:
            raise ValueError(f"Key number must be 0-4, got {key_no}")
        
        tag_keys = self.get_tag_keys(uid)
        
        # Map key_no to the appropriate key
        if key_no == 0:
            return tag_keys.get_picc_master_key_bytes()
        elif key_no == 1:
            return tag_keys.get_app_read_key_bytes()
        elif key_no == 3:
            return tag_keys.get_sdm_mac_key_bytes()
        else:
            # For other key numbers, return factory key (we don't use them yet)
            return KEY_DEFAULT_FACTORY
    
    def get_tag_keys(self, uid: bytes) -> TagKeys:
        """
        Get all keys for a specific tag UID.
        
        Args:
            uid: Tag UID as bytes
            
        Returns:
            TagKeys object with tag's keys
        """
        uid_hex = uid.hex().upper()
        
        # Read CSV and find matching UID
        with open(self.csv_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['uid'].upper() == uid_hex:
                    return TagKeys(**row)
        
        # UID not found - return factory keys as default
        print(f"[WARNING] UID {uid_hex} not found in database")
        print(f"[INFO] Using factory default keys")
        return TagKeys.from_factory_keys(uid_hex)
    
    def save_tag_keys(self, uid: bytes, keys: TagKeys):
        """
        Save or update all keys for a tag.
        
        Args:
            uid: Tag UID as bytes
            keys: TagKeys object to save
        """
        uid_hex = uid.hex().upper()
        keys.uid = uid_hex  # Ensure UID matches
        
        # Backup existing keys before updating
        try:
            existing_keys = self.get_tag_keys(uid)
            if existing_keys.status != 'factory':
                self.backup_keys(uid, existing_keys)
        except KeyError:
            pass  # No existing keys to backup
        
        # Read all rows
        rows = []
        found = False
        
        if self.csv_path.exists():
            with open(self.csv_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['uid'].upper() == uid_hex:
                        # Update existing row
                        rows.append(asdict(keys))
                        found = True
                    else:
                        rows.append(row)
        
        # Append new row if not found
        if not found:
            rows.append(asdict(keys))
        
        # Write back
        with open(self.csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"[OK] Saved keys for UID {uid_hex} (status: {keys.status})")
    
    def backup_keys(self, uid: bytes, keys: Optional[TagKeys] = None):
        """
        Backup keys to backup file with timestamp.
        
        Args:
            uid: Tag UID as bytes
            keys: Optional TagKeys to backup (if None, loads from main DB)
        """
        if keys is None:
            keys = self.get_tag_keys(uid)
        
        backup_entry = asdict(keys)
        backup_entry['backup_timestamp'] = datetime.now().isoformat()
        
        # Append to backup file
        with open(self.backup_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES + ['backup_timestamp'])
            writer.writerow(backup_entry)
        
        print(f"[OK] Backed up keys for UID {keys.uid}")
    
    def list_tags(self) -> List[TagKeys]:
        """
        List all tags in the database.
        
        Returns:
            List of TagKeys objects
        """
        tags = []
        
        with open(self.csv_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tags.append(TagKeys(**row))
        
        return tags
    
    def generate_random_keys(self, uid: bytes) -> TagKeys:
        """
        Generate random keys for a tag.
        
        Args:
            uid: Tag UID as bytes
            
        Returns:
            TagKeys with randomly generated keys
        """
        import secrets
        
        uid_hex = uid.hex().upper()
        
        return TagKeys(
            uid=uid_hex,
            picc_master_key=secrets.token_hex(16),  # 16 bytes = 32 hex chars
            app_read_key=secrets.token_hex(16),
            sdm_mac_key=secrets.token_hex(16),
            provisioned_date=datetime.now().isoformat(),
            status="provisioned",
            notes="Randomly generated keys"
        )
    
    @contextmanager
    def provision_tag(self, uid: bytes, url: str = None):
        """
        Context manager for two-phase commit of tag provisioning.
        
        Usage:
            with key_manager.provision_tag(uid, url="https://example.com") as keys:
                # Phase 1: Keys saved with status='pending'
                # Provision tag with keys.picc_master_key, etc.
                ChangeKey(keys.picc_master_key).execute(...)
                # If no exception, status updated to 'provisioned' on exit
                # If exception, status updated to 'failed'
        
        Args:
            uid: Tag UID as bytes
            url: Base URL to save in notes field
            
        Yields:
            TagKeys with newly generated keys (status='pending')
            
        Example:
            try:
                with key_mgr.provision_tag(uid, "https://app.com/tap") as keys:
                    # Change keys on tag
                    auth.change_key(0, keys.get_picc_master_key_bytes())
                    auth.change_key(1, keys.get_app_read_key_bytes())
                    auth.change_key(3, keys.get_sdm_mac_key_bytes())
                # SUCCESS: Status automatically updated to 'provisioned'
            except Exception as e:
                # FAILURE: Status automatically updated to 'failed'
                print(f"Provisioning failed: {e}")
        """
        # Phase 1: Generate keys and save with 'pending' status
        new_keys = self.generate_random_keys(uid)
        new_keys.status = "pending"
        new_keys.notes = "Provisioning in progress..."
        self.save_tag_keys(uid, new_keys)
        
        success = False
        try:
            # Yield keys to caller for provisioning
            yield new_keys
            success = True
        except Exception as e:
            # Phase 2a: Provisioning failed
            new_keys.status = "failed"
            new_keys.notes = f"Provisioning failed: {str(e)}"
            self.save_tag_keys(uid, new_keys)
            raise  # Re-raise exception
        finally:
            if success:
                # Phase 2b: Provisioning succeeded
                new_keys.status = "provisioned"
                new_keys.notes = url if url else "Successfully provisioned"
                self.save_tag_keys(uid, new_keys)
    
    def print_summary(self):
        """Print summary of all tags in database."""
        tags = self.list_tags()
        
        print("=" * 80)
        print("Tag Key Database Summary")
        print("=" * 80)
        print(f"Total tags: {len(tags)}")
        print()
        
        for tag in tags:
            print(f"UID: {tag.uid}")
            print(f"  Status: {tag.status}")
            print(f"  Provisioned: {tag.provisioned_date}")
            print(f"  PICC Master Key: {tag.picc_master_key[:8]}...{tag.picc_master_key[-8:]}")
            if tag.notes:
                print(f"  Notes: {tag.notes}")
            print()

