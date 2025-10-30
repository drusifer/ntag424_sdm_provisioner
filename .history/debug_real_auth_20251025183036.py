#!/usr/bin/env python3
"""
Debug script for real hardware EV2 authentication
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, AuthenticateEV2First
from ntag424_sdm_provisioner.constants import FACTORY_KEY

def debug_real_auth():
    print("Debugging real hardware EV2 authentication...")
    
    try:
        with CardManager(0) as card:
            print("Card connected")
            
            # Step 1: Select application
            print("\nStep 1: SelectPICCApplication")
            result = SelectPiccApplication().execute(card)
            print(f"SelectPICCApplication: {result}")
            
            # Step 2: Try AuthenticateEV2First
            print("\nStep 2: AuthenticateEV2First")
            print(f"Using factory key: {FACTORY_KEY.hex().upper()}")
            
            try:
                cmd = AuthenticateEV2First(key_no=0)
                response = cmd.execute(card)
                print(f"SUCCESS: AuthenticateEV2First success!")
                print(f"Challenge length: {len(response.challenge)} bytes")
                print(f"Challenge data: {response.challenge.hex().upper()}")
                print(f"Key number used: {response.key_no_used}")
                
                # Try to decrypt the challenge
                from Crypto.Cipher import AES
                cipher = AES.new(FACTORY_KEY, AES.MODE_ECB)
                decrypted = cipher.decrypt(response.challenge)
                print(f"Decrypted challenge: {decrypted.hex().upper()}")
                
            except Exception as e:
                print(f"FAILED: AuthenticateEV2First failed: {e}")
                
                # Try different key numbers
                print("\nTrying different key numbers...")
                for key_no in range(5):
                    try:
                        cmd = AuthenticateEV2First(key_no=key_no)
                        response = cmd.execute(card)
                        print(f"SUCCESS: Key {key_no} works! Challenge: {response.challenge.hex().upper()}")
                        break
                    except Exception as ke:
                        print(f"FAILED: Key {key_no} failed: {ke}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_real_auth()
