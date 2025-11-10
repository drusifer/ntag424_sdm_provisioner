#!/usr/bin/env python3
"""
Restore tag keys from backup file.

Usage:
    python restore_keys_from_backup.py [UID]
    
If UID is provided, shows backups for that tag only.
Otherwise, shows all backups.
"""

import sys
import csv
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, TagKeys


def list_backups_for_uid(backup_path: Path, uid: str = None):
    """List all backups, optionally filtered by UID."""
    backups = []
    
    if not backup_path.exists():
        print(f"No backup file found at {backup_path}")
        return backups
    
    with open(backup_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if uid is None or row['uid'].upper() == uid.upper():
                backups.append(row)
    
    return backups


def display_backups(backups):
    """Display backups in a readable format."""
    if not backups:
        print("No backups found.")
        return
    
    print("=" * 100)
    print(f"Found {len(backups)} backup(s)")
    print("=" * 100)
    print()
    
    for i, backup in enumerate(backups, 1):
        timestamp = backup.get('backup_timestamp', 'Unknown')
        uid = backup['uid']
        status = backup.get('status', 'unknown')
        notes = backup.get('notes', '')
        picc_key = backup['picc_master_key']
        
        print(f"[{i}] Backup from {timestamp}")
        print(f"    UID:    {uid}")
        print(f"    Status: {status}")
        print(f"    PICC Master Key: {picc_key[:16]}...")
        if notes:
            print(f"    Notes:  {notes}")
        print()


def restore_backup(key_manager: CsvKeyManager, backup_entry: dict):
    """Restore a backup entry to the main database."""
    # Remove backup_timestamp if present
    backup_entry = dict(backup_entry)
    backup_entry.pop('backup_timestamp', None)
    
    # Create TagKeys object
    keys = TagKeys(**backup_entry)
    
    # Mark as restored
    keys.status = "provisioned"
    keys.notes = f"Restored from backup at {datetime.now().isoformat()}"
    
    # Save to main database
    uid_bytes = bytes.fromhex(keys.uid)
    key_manager.save_tag_keys(uid_bytes, keys)
    
    print(f"✅ Restored keys for UID {keys.uid}")
    print(f"   Status: {keys.status}")
    print(f"   PICC Master Key: {keys.picc_master_key[:16]}...")


def main():
    # Parse arguments
    uid = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Setup paths
    csv_path = Path(__file__).parent / "tag_keys.csv"
    backup_path = Path(__file__).parent / "tag_keys_backup.csv"
    
    key_manager = CsvKeyManager(csv_path=csv_path, backup_path=backup_path)
    
    print("=" * 100)
    print("NTAG424 Key Restore Utility")
    print("=" * 100)
    print()
    
    if uid:
        print(f"Searching for backups of UID: {uid.upper()}")
    else:
        print("Showing all backups")
    print()
    
    # List backups
    backups = list_backups_for_uid(backup_path, uid)
    
    if not backups:
        print("No backups found.")
        if uid:
            print(f"\nTip: Check if UID {uid} is correct")
            print("     Run without UID to see all backups: python restore_keys_from_backup.py")
        return
    
    display_backups(backups)
    
    # Ask user to select
    print("=" * 100)
    print("Select backup to restore (or 'q' to quit):")
    selection = input(f"Enter number (1-{len(backups)}): ").strip()
    
    if selection.lower() == 'q':
        print("Cancelled.")
        return
    
    try:
        index = int(selection) - 1
        if index < 0 or index >= len(backups):
            print(f"Invalid selection. Must be between 1 and {len(backups)}")
            return
    except ValueError:
        print("Invalid input. Must be a number.")
        return
    
    # Confirm
    selected_backup = backups[index]
    print()
    print(f"You selected backup from {selected_backup.get('backup_timestamp', 'Unknown')}")
    print(f"UID: {selected_backup['uid']}")
    print(f"Status: {selected_backup.get('status', 'unknown')}")
    print()
    confirm = input("Restore this backup to main database? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("Cancelled.")
        return
    
    # Restore
    print()
    restore_backup(key_manager, selected_backup)
    print()
    print("✅ Done! You can now use the provisioning script with these restored keys.")


if __name__ == '__main__':
    main()

