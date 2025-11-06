#!/usr/bin/env python3
"""
Demo: Two-Phase Commit Provisioning with Context Manager

This example demonstrates the safe provisioning pattern using the
provision_tag() context manager for atomic key management.
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager


def demo_successful_provisioning():
    """Demonstrate successful provisioning."""
    print("=" * 70)
    print("Demo: Successful Provisioning")
    print("=" * 70)
    print()
    
    key_mgr = CsvKeyManager(
        csv_path="demo_keys.csv",
        backup_path="demo_keys_backup.csv"
    )
    
    test_uid = bytes.fromhex("04B3664A2F7080")
    
    print(f"Provisioning tag: {test_uid.hex().upper()}")
    print()
    
    try:
        with key_mgr.provision_tag(test_uid) as keys:
            print("[Phase 1] Keys generated and saved with status='pending'")
            print(f"  PICC Master Key: {keys.picc_master_key[:16]}...")
            print(f"  App Read Key:    {keys.app_read_key[:16]}...")
            print(f"  SDM MAC Key:     {keys.sdm_mac_key[:16]}...")
            print(f"  Status:          {keys.status}")
            print()
            
            # In real code, you would:
            # - Authenticate with factory keys
            # - Change Key 0 (PICC Master)
            # - Change Key 1 (App Read)
            # - Change Key 3 (SDM MAC)
            print("[Simulated] Changing keys on tag...")
            print("  ChangeKey(0, picc_master_key) -> Success")
            print("  ChangeKey(1, app_read_key) -> Success")
            print("  ChangeKey(3, sdm_mac_key) -> Success")
            print()
            
        # Context manager auto-updates status to 'provisioned'
        print("[Phase 2] Provisioning successful!")
        
        # Verify final status
        final_keys = key_mgr.get_tag_keys(test_uid)
        print(f"  Final Status: {final_keys.status}")
        print(f"  Notes: {final_keys.notes}")
        print()
        
    except Exception as e:
        print(f"[ERROR] {e}")
    
    print()


def demo_failed_provisioning():
    """Demonstrate failed provisioning."""
    print("=" * 70)
    print("Demo: Failed Provisioning (Safe Recovery)")
    print("=" * 70)
    print()
    
    key_mgr = CsvKeyManager(
        csv_path="demo_keys.csv",
        backup_path="demo_keys_backup.csv"
    )
    
    test_uid = bytes.fromhex("04C4775B308191")
    
    print(f"Provisioning tag: {test_uid.hex().upper()}")
    print()
    
    try:
        with key_mgr.provision_tag(test_uid) as keys:
            print("[Phase 1] Keys generated and saved with status='pending'")
            print(f"  Status: {keys.status}")
            print()
            
            print("[Simulated] Changing keys on tag...")
            print("  ChangeKey(0, picc_master_key) -> Success")
            print("  ChangeKey(1, app_read_key) -> FAILED (0x91AE)")
            print()
            
            # Simulate failure
            raise RuntimeError("Tag authentication failed during ChangeKey(1)")
            
    except RuntimeError as e:
        # Context manager auto-updates status to 'failed'
        print(f"[Phase 2] Provisioning failed: {e}")
        print()
        
        # Verify status was updated
        final_keys = key_mgr.get_tag_keys(test_uid)
        print(f"  Final Status: {final_keys.status}")
        print(f"  Notes: {final_keys.notes}")
        print()
        print("  [SAFE] Tag still has factory keys - can retry")
        print()


def demo_list_tags():
    """List all tags in database."""
    print("=" * 70)
    print("Tag Database Status")
    print("=" * 70)
    print()
    
    key_mgr = CsvKeyManager(
        csv_path="demo_keys.csv",
        backup_path="demo_keys_backup.csv"
    )
    
    key_mgr.print_summary()


if __name__ == "__main__":
    demo_successful_provisioning()
    demo_failed_provisioning()
    demo_list_tags()
    
    print("=" * 70)
    print("Demo Complete")
    print("=" * 70)
    print()
    print("Check files:")
    print("  - demo_keys.csv")
    print("  - demo_keys_backup.csv")
    print()
    print("Notice how:")
    print("  - Successful provision → status='provisioned'")
    print("  - Failed provision → status='failed'")
    print("  - Database always reflects reality")
    print("  - No race conditions or lost keys!")
    print()

