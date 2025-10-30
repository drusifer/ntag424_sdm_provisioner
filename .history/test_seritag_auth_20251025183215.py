#!/usr/bin/env python3
"""
Test if Seritag authentication works with just Phase 1
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, AuthenticateEV2First, GetChipVersion
from ntag424_sdm_provisioner.constants import FACTORY_KEY

def test_seritag_auth():
    print("Testing Seritag authentication approach...")
    
    try:
        with CardManager(0) as card:
            print("Card connected")
            
            # Step 1: Select application
            try:
                SelectPiccApplication().execute(card)
                print("Application selected")
            except Exception as se:
                if "0x6985" in str(se):
                    print("Application already selected")
                else:
                    print(f"Selection warning: {se}")
            
            # Step 2: Get version to confirm it's Seritag
            print("\nGetting chip version...")
            version = GetChipVersion().execute(card)
            print(f"Hardware version: {version.hw_major_version}.{version.hw_minor_version}")
            print(f"UID: {version.uid.hex().upper()}")
            
            if version.hw_major_version == 48:
                print("CONFIRMED: This is a Seritag NTAG424 DNA")
            else:
                print("WARNING: This might not be a Seritag tag")
            
            # Step 3: Try AuthenticateEV2First
            print("\nTrying AuthenticateEV2First...")
            try:
                cmd1 = AuthenticateEV2First(key_no=0)
                response1 = cmd1.execute(card)
                print(f"✅ AuthenticateEV2First SUCCESS!")
                print(f"Challenge: {response1.challenge.hex().upper()}")
                print(f"Key used: {response1.key_no_used}")
                
                # Maybe Seritag only needs Phase 1?
                print("\nTesting if Phase 1 is sufficient...")
                print("This might be all that's needed for Seritag authentication")
                
            except Exception as e:
                print(f"❌ AuthenticateEV2First failed: {e}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_seritag_auth()
