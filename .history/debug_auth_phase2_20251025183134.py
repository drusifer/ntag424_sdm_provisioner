#!/usr/bin/env python3
"""
Debug script for AuthenticateEV2Second phase
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, AuthenticateEV2First, AuthenticateEV2Second
from ntag424_sdm_provisioner.constants import FACTORY_KEY
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

def debug_auth_phase2():
    print("Debugging AuthenticateEV2Second phase...")
    
    try:
        with CardManager(0) as card:
            print("Card connected")
            
            # Step 1: Select application (handle gracefully)
            try:
                SelectPiccApplication().execute(card)
                print("Application selected")
            except Exception as se:
                if "0x6985" in str(se):
                    print("Application already selected")
                else:
                    print(f"Selection warning: {se}")
            
            # Step 2: AuthenticateEV2First
            print("\nPhase 1: AuthenticateEV2First")
            cmd1 = AuthenticateEV2First(key_no=0)
            response1 = cmd1.execute(card)
            print(f"Challenge received: {response1.challenge.hex().upper()}")
            
            # Step 3: Decrypt and prepare response
            print("\nPhase 2: Preparing response")
            cipher = AES.new(FACTORY_KEY, AES.MODE_ECB)
            rndb = cipher.decrypt(response1.challenge)
            print(f"Decrypted RndB: {rndb.hex().upper()}")
            
            # Rotate RndB
            rndb_rotated = rndb[1:] + rndb[0:1]
            print(f"Rotated RndB: {rndb_rotated.hex().upper()}")
            
            # Generate RndA
            rnda = get_random_bytes(16)
            print(f"Generated RndA: {rnda.hex().upper()}")
            
            # Prepare response data
            response_data = rnda + rndb_rotated
            print(f"Response data: {response_data.hex().upper()}")
            
            # Encrypt response
            encrypted_response = cipher.encrypt(response_data)
            print(f"Encrypted response: {encrypted_response.hex().upper()}")
            
            # Step 4: Send AuthenticateEV2Second
            print("\nPhase 2: AuthenticateEV2Second")
            try:
                cmd2 = AuthenticateEV2Second(data_to_card=encrypted_response)
                response2 = cmd2.execute(card)
                print(f"SUCCESS: Authentication complete!")
                print(f"Card response: {response2.hex().upper()}")
            except Exception as e:
                print(f"FAILED: AuthenticateEV2Second failed: {e}")
                
                # Try different approaches
                print("\nTrying alternative approaches...")
                
                # Maybe the issue is with ECB vs CBC mode?
                print("Trying CBC mode...")
                try:
                    cipher_cbc = AES.new(FACTORY_KEY, AES.MODE_CBC, iv=b'\x00' * 16)
                    encrypted_response_cbc = cipher_cbc.encrypt(response_data)
                    cmd2_cbc = AuthenticateEV2Second(data_to_card=encrypted_response_cbc)
                    response2_cbc = cmd2_cbc.execute(card)
                    print(f"SUCCESS with CBC: {response2_cbc.hex().upper()}")
                except Exception as cbc_e:
                    print(f"CBC also failed: {cbc_e}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_auth_phase2()
