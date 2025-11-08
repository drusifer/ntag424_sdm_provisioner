#!/usr/bin/env python3
"""
Reset NTAG424 DNA tag keys back to factory defaults.

This script attempts to change all keys back to 0x00 (factory default).
Use this if the tag is in a bad state from failed provisioning attempts.
"""

import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.commands.sdm_commands import (
    SelectPiccApplication,
    GetChipVersion,
    AuthenticateEV2,
)
from ntag424_sdm_provisioner.commands.change_key import ChangeKey
from ntag424_sdm_provisioner.commands.base import ApduError


def reset_to_factory():
    """Reset all keys to factory defaults (0x00*16)."""
    
    print("=" * 70)
    print("Reset NTAG424 DNA to Factory Defaults")
    print("=" * 70)
    print()
    print("This will attempt to reset all keys to 0x00 (factory default).")
    print()
    
    factory_key = bytes(16)  # All zeros
    key_mgr = CsvKeyManager()
    
    try:
        with CardManager() as card:
            print("Place tag on reader...")
            print()
            
            # Get UID
            SelectPiccApplication().execute(card)
            version_info = GetChipVersion().execute(card)
            uid = version_info.uid
            print(f"Tag UID: {uid.hex().upper()}")
            print()
            
            # Try to get current keys from database
            try:
                current_keys = key_mgr.get_tag_keys(uid)
                if current_keys.status == "factory":
                    print("[INFO] Tag already has factory keys")
                    return 0
                    
                print(f"[INFO] Tag status: {current_keys.status}")
                print("[INFO] Will try to authenticate with saved keys...")
                
                # Try to auth with saved key
                saved_key = current_keys.get_picc_master_key_bytes()
                print(f"[INFO] Attempting auth with saved key: {saved_key.hex()[:16]}...")
                
                try:
                    with AuthenticateEV2(saved_key, 0)(card) as auth_conn:
                        print("[OK] Authenticated with saved key!")
                        print()
                        print("Resetting keys to factory defaults...")
                        
                        # Reset each key back to 0x00
                        for key_no in [0, 1, 3]:
                            print(f"  Resetting Key {key_no}...", end=" ")
                            auth_conn.send(ChangeKey(key_no, factory_key, saved_key, 0x00))
                            print("[OK]")
                        
                        print()
                        print("[SUCCESS] All keys reset to factory defaults!")
                        
                        # Update database
                        key_mgr.delete_tag(uid)
                        print("[INFO] Removed from database")
                        return 0
                        
                except ApduError as e:
                    print(f"[FAILED] Auth with saved key failed: {e}")
                    print("[INFO] Will try factory key...")
                    
            except Exception:
                print("[INFO] No saved keys found, using factory key...")
            
            # Try factory key
            print()
            print("[INFO] Attempting auth with factory key (0x00*16)...")
            
            try:
                with AuthenticateEV2(factory_key, 0)(card) as auth_conn:
                    print("[OK] Tag already has factory key!")
                    print()
                    
                    # Clean up database
                    try:
                        key_mgr.delete_tag(uid)
                        print("[INFO] Cleaned up database")
                    except:
                        pass
                    
                    return 0
                    
            except ApduError as e:
                print(f"[FAILED] Auth with factory key failed: {e}")
                print()
                print("=" * 70)
                print("[ERROR] Cannot authenticate with either saved or factory keys!")
                print("=" * 70)
                print()
                print("Possible reasons:")
                print("  1. Tag keys are unknown (need physical reset)")
                print("  2. Tag is locked/rate-limited (0x91AD - wait 60 seconds)")
                print("  3. Tag hardware issue")
                print()
                print("Try:")
                print("  1. Remove tag, wait 60 seconds, try again")
                print("  2. Use NXP TagWriter app to reset (if available)")
                print("  3. Contact tag supplier for factory reset")
                return 1
                
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED]")
        return 1
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(reset_to_factory())

