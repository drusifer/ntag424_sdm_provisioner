"""
Compare production ChangeKey implementation vs verified crypto primitives.

This will help identify where the bug is by comparing byte-for-byte.
"""

import os
import sys
from pathlib import Path

# Add tests directory to path
tests_dir = Path(__file__).parent
sys.path.insert(0, str(tests_dir))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.crypto.crypto_primitives import build_changekey_apdu


def test_production_changekey_apdu():
    """
    Build ChangeKey APDU using both production code and verified crypto,
    then compare them byte-for-byte.
    """
    
    print("\n=== COMPARING PRODUCTION VS VERIFIED CRYPTO ===\n")
    
    with CardManager() as card:
        # Step 1: Select PICC
        print("Step 1: Selecting PICC Application...")
        SelectPiccApplication().execute(card)
        print("  [OK]\n")
        
        # Step 2: Authenticate using production code
        print("Step 2: Authenticating...")
        factory_key = bytes(16)
        key_no = 0
        
        session = Ntag424AuthSession(factory_key)
        session.authenticate(card, key_no)
        
        print(f"  Ti: {session.session_keys.ti.hex()}")
        print(f"  Session ENC key: {session.session_keys.session_enc_key.hex()}")
        print(f"  Session MAC key: {session.session_keys.session_mac_key.hex()}")
        print(f"  Cmd Counter: {session.session_keys.cmd_counter}")
        print("  [OK]\n")
        
        # Step 3: Build ChangeKey APDU using BOTH methods
        print("Step 3: Building ChangeKey APDU...")
        
        new_key = bytes([1] + [0]*15)
        key_version = 0x01
        
        # Method 1: Verified crypto primitives
        print("\nMethod 1: VERIFIED CRYPTO (from crypto_components.py)")
        verified_apdu = build_changekey_apdu(
            key_no=0,
            new_key=new_key,
            old_key=None,
            version=key_version,
            ti=session.session_keys.ti,
            cmd_ctr=session.session_keys.cmd_counter,
            session_enc_key=session.session_keys.session_enc_key,
            session_mac_key=session.session_keys.session_mac_key
        )
        
        print(f"  Length: {len(verified_apdu)} bytes")
        print(f"  APDU:")
        for i in range(0, len(verified_apdu), 16):
            chunk = verified_apdu[i:i+16]
            print(f"    {' '.join(f'{b:02X}' for b in chunk)}")
        
        # Method 2: Production code (via ChangeKey command)
        print("\nMethod 2: PRODUCTION CODE (from ChangeKey.execute)")
        from ntag424_sdm_provisioner.commands.change_key import ChangeKey
        
        change_key_cmd = ChangeKey(0, new_key, None, key_version)
        
        # Build the command data
        key_data = change_key_cmd._build_key_data()
        print(f"  Key data (32 bytes): {key_data.hex()}")
        
        # Our production code builds the APDU through encrypt_and_mac_no_padding
        # Let me manually build it to compare
        from ntag424_sdm_provisioner.commands.base import AuthenticatedConnection
        
        # Create fake auth connection just to access crypto methods
        auth_conn = AuthenticatedConnection(card, session)
        
        # Get the encrypted + MAC'd data
        cmd_byte = change_key_cmd.get_command_byte()  # 0xC4
        cmd_header = change_key_cmd.get_unencrypted_header()  # KeyNo
        
        # Calculate IV
        iv_plaintext = bytearray(16)
        iv_plaintext[0] = 0xA5
        iv_plaintext[1] = 0x5A
        iv_plaintext[2:6] = session.session_keys.ti
        iv_plaintext[6:8] = session.session_keys.cmd_counter.to_bytes(2, 'little')
        
        from Crypto.Cipher import AES
        cipher = AES.new(session.session_keys.session_enc_key, AES.MODE_CBC, iv=b'\x00'*16)
        iv_encrypted = cipher.encrypt(bytes(iv_plaintext))
        
        print(f"  IV (plaintext): {bytes(iv_plaintext).hex()}")
        print(f"  IV (encrypted): {iv_encrypted.hex()}")
        
        # Encrypt key data
        cipher = AES.new(session.session_keys.session_enc_key, AES.MODE_CBC, iv=iv_encrypted)
        encrypted = cipher.encrypt(key_data)
        print(f"  Encrypted data: {encrypted.hex()}")
        
        # Calculate CMAC
        from Crypto.Hash import CMAC
        mac_input = bytearray()
        mac_input.append(cmd_byte)
        mac_input.extend(session.session_keys.cmd_counter.to_bytes(2, 'little'))
        mac_input.extend(session.session_keys.ti)
        mac_input.extend(cmd_header)
        mac_input.extend(encrypted)
        
        print(f"  CMAC input ({len(mac_input)} bytes): {bytes(mac_input).hex()}")
        
        cmac_obj = CMAC.new(session.session_keys.session_mac_key, ciphermod=AES)
        cmac_obj.update(bytes(mac_input))
        cmac_full = cmac_obj.digest()
        
        # Truncate (even-numbered bytes)
        cmac_truncated = bytes([cmac_full[i] for i in range(1, 16, 2)])
        
        print(f"  CMAC (full): {cmac_full.hex()}")
        print(f"  CMAC (truncated): {cmac_truncated.hex()}")
        
        # Build production APDU
        production_apdu = [
            0x90, 0xC4, 0x00, 0x00, 0x29,
            *list(cmd_header),
            *list(encrypted),
            *list(cmac_truncated),
            0x00
        ]
        
        print(f"\n  Production APDU ({len(production_apdu)} bytes):")
        for i in range(0, len(production_apdu), 16):
            chunk = production_apdu[i:i+16]
            print(f"    {' '.join(f'{b:02X}' for b in chunk)}")
        
        # Step 4: COMPARE
        print("\n" + "="*60)
        print("COMPARISON:")
        print("="*60)
        
        if verified_apdu == production_apdu:
            print("[OK] APDUs MATCH! Both methods produce identical output.")
            print("\nNow testing with real tag...\n")
            
            # Send it!
            response, sw1, sw2 = card.send_apdu(verified_apdu, use_escape=False)
            print(f"Response: SW={sw1:02X}{sw2:02X}")
            
            if (sw1, sw2) == (0x91, 0x00):
                print("\n" + "="*60)
                print("SUCCESS! CHANGEKEY WORKED!")
                print("="*60)
                return True
            else:
                print(f"\n[ERROR] Failed with {sw1:02X}{sw2:02X}")
                return False
        else:
            print("[MISMATCH] APDUs differ!")
            print("\nFinding differences...")
            for i, (v, p) in enumerate(zip(verified_apdu, production_apdu)):
                if v != p:
                    print(f"  Byte {i}: Verified={v:02X}, Production={p:02X}")
            
            if len(verified_apdu) != len(production_apdu):
                print(f"\nLength mismatch: Verified={len(verified_apdu)}, Production={len(production_apdu)}")
            
            return False


if __name__ == '__main__':
    try:
        success = test_production_changekey_apdu()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\nException: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

