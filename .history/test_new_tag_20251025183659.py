#!/usr/bin/env python3
"""
Test new tag authentication approaches
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, AuthenticateEV2First, AuthenticateEV2Second
from ntag424_sdm_provisioner.constants import FACTORY_KEY
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

def test_new_tag_auth():
    print("Testing new tag authentication approaches...")
    
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
            
            # Test Phase 1
            print("\n--- Phase 1 Test ---")
            cmd1 = AuthenticateEV2First(key_no=0)
            response1 = cmd1.execute(card)
            print(f"Phase 1 SUCCESS: {response1.challenge.hex().upper()}")
            
            # Try different Phase 2 approaches
            cipher = AES.new(FACTORY_KEY, AES.MODE_ECB)
            rndb = cipher.decrypt(response1.challenge)
            print(f"Decrypted RndB: {rndb.hex().upper()}")
            
            # Approach 1: Standard EV2 Phase 2
            print("\n--- Approach 1: Standard EV2 Phase 2 ---")
            try:
                rndb_rotated = rndb[1:] + rndb[0:1]
                rnda = get_random_bytes(16)
                response_data = rnda + rndb_rotated
                encrypted_response = cipher.encrypt(response_data)
                
                cmd2 = AuthenticateEV2Second(data_to_card=encrypted_response)
                response2 = cmd2.execute(card)
                print(f"SUCCESS: {response2.hex().upper()}")
            except Exception as e:
                print(f"FAILED: {e}")
            
            # Approach 2: Try without rotation
            print("\n--- Approach 2: No rotation ---")
            try:
                rnda = get_random_bytes(16)
                response_data = rnda + rndb  # No rotation
                encrypted_response = cipher.encrypt(response_data)
                
                cmd2 = AuthenticateEV2Second(data_to_card=encrypted_response)
                response2 = cmd2.execute(card)
                print(f"SUCCESS: {response2.hex().upper()}")
            except Exception as e:
                print(f"FAILED: {e}")
            
            # Approach 3: Try different response format
            print("\n--- Approach 3: Different response format ---")
            try:
                # Maybe Seritag expects just RndA?
                rnda = get_random_bytes(16)
                encrypted_response = cipher.encrypt(rnda)
                
                cmd2 = AuthenticateEV2Second(data_to_card=encrypted_response)
                response2 = cmd2.execute(card)
                print(f"SUCCESS: {response2.hex().upper()}")
            except Exception as e:
                print(f"FAILED: {e}")
            
            # Approach 4: Try CBC mode
            print("\n--- Approach 4: CBC mode ---")
            try:
                cipher_cbc = AES.new(FACTORY_KEY, AES.MODE_CBC, iv=b'\x00' * 16)
                rndb_rotated = rndb[1:] + rndb[0:1]
                rnda = get_random_bytes(16)
                response_data = rnda + rndb_rotated
                encrypted_response = cipher_cbc.encrypt(response_data)
                
                cmd2 = AuthenticateEV2Second(data_to_card=encrypted_response)
                response2 = cmd2.execute(card)
                print(f"SUCCESS: {response2.hex().upper()}")
            except Exception as e:
                print(f"FAILED: {e}")
            
            # Approach 5: Try different key numbers
            print("\n--- Approach 5: Different key numbers ---")
            for key_no in range(1, 5):
                try:
                    cmd1 = AuthenticateEV2First(key_no=key_no)
                    response1 = cmd1.execute(card)
                    print(f"Key {key_no} Phase 1 SUCCESS: {response1.challenge.hex().upper()}")
                    
                    # Try Phase 2 with this key
                    cipher = AES.new(FACTORY_KEY, AES.MODE_ECB)
                    rndb = cipher.decrypt(response1.challenge)
                    rndb_rotated = rndb[1:] + rndb[0:1]
                    rnda = get_random_bytes(16)
                    response_data = rnda + rndb_rotated
                    encrypted_response = cipher.encrypt(response_data)
                    
                    cmd2 = AuthenticateEV2Second(data_to_card=encrypted_response)
                    response2 = cmd2.execute(card)
                    print(f"Key {key_no} Phase 2 SUCCESS: {response2.hex().upper()}")
                    break
                except Exception as e:
                    print(f"Key {key_no} FAILED: {e}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_new_tag_auth()
