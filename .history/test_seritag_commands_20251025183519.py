#!/usr/bin/env python3
"""
Test what commands work with Seritag hardware
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion, AuthenticateEV2First, ReadData, WriteData
from ntag424_sdm_provisioner.constants import FACTORY_KEY, FileNo

def test_seritag_commands():
    print("Testing what commands work with Seritag hardware...")
    
    try:
        with CardManager(0) as card:
            print("Card connected")
            
            # Test basic commands
            commands_to_test = [
                ("SelectPiccApplication", lambda: SelectPiccApplication().execute(card)),
                ("GetChipVersion", lambda: GetChipVersion().execute(card)),
                ("AuthenticateEV2First", lambda: AuthenticateEV2First(key_no=0).execute(card)),
                ("ReadData (file 0)", lambda: ReadData(file_no=FileNo.STANDARD_DATA_FILE, offset=0, length=16).execute(card)),
                ("ReadData (NDEF file)", lambda: ReadData(file_no=FileNo.NDEF_FILE, offset=0, length=16).execute(card)),
            ]
            
            for cmd_name, cmd_func in commands_to_test:
                print(f"\n--- Testing {cmd_name} ---")
                try:
                    result = cmd_func()
                    print(f"SUCCESS: {result}")
                except Exception as e:
                    print(f"FAILED: {e}")
            
            # Test if we can read NDEF data without authentication
            print(f"\n--- Testing NDEF Read without auth ---")
            try:
                ndef_data = ReadData(file_no=FileNo.NDEF_FILE, offset=0, length=64).execute(card)
                print(f"NDEF data: {ndef_data.hex().upper()}")
                
                # Try to parse as NDEF
                if ndef_data.startswith(b'\x03'):  # NDEF TLV
                    length = ndef_data[1]
                    if length > 0:
                        ndef_payload = ndef_data[2:2+length]
                        print(f"NDEF payload: {ndef_payload.hex().upper()}")
                        print(f"NDEF as text: {ndef_payload}")
            except Exception as e:
                print(f"NDEF read failed: {e}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_seritag_commands()
