#!/usr/bin/env python3
"""Test CBC mode authentication fix."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.constants import FACTORY_KEY

def main():
    print("=" * 70)
    print("Testing CBC Mode Authentication Fix")
    print("=" * 70)
    print("\nChanged from ECB mode to CBC mode with zero IV")
    print("(matching Arduino implementation and NXP spec Section 9.1.4)")
    print("\nPlease tap and hold the NTAG424 tag on the reader...\n")
    
    try:
        with CardManager() as card:
            # Initial setup
            SelectPiccApplication().execute(card)
            version = GetChipVersion().execute(card)
            print(f"[OK] Connected to tag UID: {version.uid.hex().upper()}")
            print(f"[OK] Hardware: {version.hw_major_version}.{version.hw_minor_version}")
            print(f"[OK] Software: {version.sw_major_version}.{version.sw_minor_version}")
            
            # Authenticate with CBC mode
            print("\n[TEST] Attempting authentication with CBC mode...")
            session = Ntag424AuthSession(FACTORY_KEY)
            
            try:
                keys = session.authenticate(card, key_no=0)
                print("\n" + "=" * 70)
                print("[SUCCESS] Authentication succeeded with CBC mode!")
                print("=" * 70)
                print(f"\nSession Encryption Key: {keys.session_enc_key.hex().upper()}")
                print(f"Session MAC Key: {keys.session_mac_key.hex().upper()}")
                print(f"Transaction ID: {keys.ti.hex().upper()}")
                print("\nThis confirms CBC mode with zero IV is correct!")
                return 0
            except Exception as e:
                print(f"\n[FAILED] Authentication failed: {e}")
                print(f"Error type: {type(e).__name__}")
                return 1
                
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Test cancelled by user.")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

