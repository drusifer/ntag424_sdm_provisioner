#!/usr/bin/env python3
"""
Test different keys for Seritag authentication
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, AuthenticateEV2First, AuthenticateEV2Second
from ntag424_sdm_provisioner.constants import FACTORY_KEY
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

def test_different_keys():
    print("Testing different keys for Seritag authentication...")
    
    # Common keys to test
    test_keys = [
        ("Factory (all zeros)", b'\x00' * 16),
        ("All ones", b'\xFF' * 16),
        ("Seritag default", b'Seritag12345678'),  # 16 bytes
        ("NXP default", b'NXP1234567890123'),     # 16 bytes
        ("Simple pattern", b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A\x0B\x0C\x0D\x0E\x0F\x10'),
        ("Reverse pattern", b'\x10\x0F\x0E\x0D\x0C\x0B\x0A\x09\x08\x07\x06\x05\x04\x03\x02\x01'),
    ]
    
    try:
        with CardManager(0) as card:
            print("Card connected")
            
            # Select application
            try:
                SelectPiccApplication().execute(card)
                print("Application selected")
            except Exception as se:
                if "0x6985" in str(se):
                    print("Application already selected")
                else:
                    print(f"Selection warning: {se}")
            
            # Test each key
            for key_name, key in test_keys:
                print(f"\n--- Testing {key_name} ---")
                print(f"Key: {key.hex().upper()}")
                
                try:
                    # Phase 1
                    cmd1 = AuthenticateEV2First(key_no=0)
                    response1 = cmd1.execute(card)
                    print(f"Phase 1 SUCCESS: {response1.challenge.hex().upper()}")
                    
                    # Try to decrypt with this key
                    cipher = AES.new(key, AES.MODE_ECB)
                    rndb = cipher.decrypt(response1.challenge)
                    print(f"Decrypted RndB: {rndb.hex().upper()}")
                    
                    # Phase 2
                    rndb_rotated = rndb[1:] + rndb[0:1]
                    rnda = get_random_bytes(16)
                    response_data = rnda + rndb_rotated
                    encrypted_response = cipher.encrypt(response_data)
                    
                    cmd2 = AuthenticateEV2Second(data_to_card=encrypted_response)
                    response2 = cmd2.execute(card)
                    print(f"Phase 2 SUCCESS: {response2.hex().upper()}")
                    print(f"*** {key_name} WORKS! ***")
                    break
                    
                except Exception as e:
                    print(f"FAILED: {e}")
                    
                    # Try different key numbers for this key
                    for key_no in range(1, 5):
                        try:
                            cmd1 = AuthenticateEV2First(key_no=key_no)
                            response1 = cmd1.execute(card)
                            print(f"Key {key_no} Phase 1 SUCCESS: {response1.challenge.hex().upper()}")
                            
                            # Try Phase 2
                            cipher = AES.new(key, AES.MODE_ECB)
                            rndb = cipher.decrypt(response1.challenge)
                            rndb_rotated = rndb[1:] + rndb[0:1]
                            rnda = get_random_bytes(16)
                            response_data = rnda + rndb_rotated
                            encrypted_response = cipher.encrypt(response_data)
                            
                            cmd2 = AuthenticateEV2Second(data_to_card=encrypted_response)
                            response2 = cmd2.execute(card)
                            print(f"Key {key_no} Phase 2 SUCCESS: {response2.hex().upper()}")
                            print(f"*** {key_name} with key {key_no} WORKS! ***")
                            break
                            
                        except Exception as ke:
                            print(f"Key {key_no} FAILED: {ke}")
                    else:
                        continue  # No key number worked for this key
                    break  # Found working key, exit outer loop
            
            else:
                print("\n*** NO WORKING KEY FOUND ***")
                print("Seritag might use a different authentication protocol")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_different_keys()
