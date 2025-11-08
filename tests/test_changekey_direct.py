"""
Direct ChangeKey test using our HAL but with verified crypto primitives.

This uses our HAL (CardManager) but injects the verified crypto from crypto_components.py
to test ChangeKey with the actual tag.
"""

import os
import sys
from pathlib import Path

# Add tests directory to path for crypto_components import
tests_dir = Path(__file__).parent
sys.path.insert(0, str(tests_dir))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication
from Crypto.Cipher import AES
from Crypto.Hash import CMAC
from ntag424_sdm_provisioner.crypto.crypto_primitives import build_changekey_apdu


def test_changekey_with_cardmanager():
    """
    Test ChangeKey using CardManager (handles ACR122U properly) with verified crypto.
    """
    
    print("\n=== TESTING CHANGEKEY WITH VERIFIED CRYPTO ===\n")
    
    with CardManager() as card:
        # Step 1: Select PICC
        print("Step 1: Selecting PICC Application...")
        SelectPiccApplication().execute(card)
        print("  [OK] Selected\n")
        
        # Step 2: Manual Authentication
        print("Step 2: Authenticating...")
        factory_key = bytes(16)  # All zeros
        rnda = os.urandom(16)
        
        print(f"  RndA: {rnda.hex()}")
        
        # Auth Phase 1
        apdu = [0x90, 0x71, 0x00, 0x00, 0x11, 0x00, *list(rnda), 0x00]
        response, sw1, sw2 = card.send_apdu(apdu, use_escape=False)
        
        if (sw1, sw2) != (0x91, 0xAF):
            print(f"  ERROR: Auth Phase 1 failed with {sw1:02X}{sw2:02X}")
            return False
        
        # Decrypt RndB
        rndb_enc = bytes(response[:16])
        cipher = AES.new(factory_key, AES.MODE_CBC, iv=b'\x00'*16)
        rndb = cipher.decrypt(rndb_enc)
        print(f"  RndB: {rndb.hex()}")
        
        # Rotate RndB
        rndb_rotated = rndb[1:] + rndb[:1]
        
        # Encrypt RndB' || RndA
        plaintext = rndb_rotated + rnda
        cipher = AES.new(factory_key, AES.MODE_CBC, iv=rndb_enc)
        encrypted_part = cipher.encrypt(plaintext)
        
        # Auth Phase 2
        apdu = [0x90, 0xAF, 0x00, 0x00, 0x20, *list(encrypted_part), 0x00]
        response, sw1, sw2 = card.send_apdu(apdu, use_escape=False)
        
        if (sw1, sw2) != (0x91, 0x00):
            print(f"  ERROR: Auth Phase 2 failed with {sw1:02X}{sw2:02X}")
            return False
        
        # Parse response
        response_enc = bytes(response)
        iv_for_response = encrypted_part[-16:]
        cipher = AES.new(factory_key, AES.MODE_CBC, iv=iv_for_response)
        response_dec = cipher.decrypt(response_enc)
        
        ti = response_dec[0:4]
        rnda_rotated_response = response_dec[4:20]
        
        # Verify RndA'
        rnda_rotated_expected = rnda[1:] + rnda[:1]
        if rnda_rotated_response != rnda_rotated_expected:
            print("  ERROR: RndA' verification failed!")
            return False
        
        print(f"  [OK] Authenticated! Ti: {ti.hex()}\n")
        
        # Derive session keys
        sv1 = b'\xA5\x5A\x00\x01\x00\x80' + rnda[0:2]
        cmac_enc = CMAC.new(factory_key, ciphermod=AES)
        cmac_enc.update(sv1 + b'\x00' * 8)
        session_enc_key = cmac_enc.digest()
        
        sv2 = b'\x5A\xA5\x00\x01\x00\x80' + rnda[0:2]
        cmac_mac = CMAC.new(factory_key, ciphermod=AES)
        cmac_mac.update(sv2 + b'\x00' * 8)
        session_mac_key = cmac_mac.digest()
        
        print(f"  Session ENC key: {session_enc_key.hex()}")
        print(f"  Session MAC key: {session_mac_key.hex()}\n")
        
        # Step 3: ChangeKey using VERIFIED crypto primitives
        print("Step 3: Executing ChangeKey...")
        
        new_key = bytes([1] + [0]*15)  # Simple test key
        key_version = 0x01
        cmd_ctr = 0  # First command after auth
        
        # Build APDU using our VERIFIED crypto from crypto_components
        apdu = build_changekey_apdu(
            key_no=0,
            new_key=new_key,
            old_key=None,
            version=key_version,
            ti=ti,
            cmd_ctr=cmd_ctr,
            session_enc_key=session_enc_key,
            session_mac_key=session_mac_key
        )
        
        print(f"  APDU length: {len(apdu)} bytes")
        print(f"  APDU: {' '.join(f'{b:02X}' for b in apdu)}\n")
        
        # Send the APDU
        response, sw1, sw2 = card.send_apdu(apdu, use_escape=False)
        
        print(f"  Response: SW={sw1:02X}{sw2:02X}")
        
        if (sw1, sw2) == (0x91, 0x00):
            print("\n" + "="*60)
            print("SUCCESS! CHANGEKEY WORKED WITH VERIFIED CRYPTO!")
            print("="*60)
            print("\nThe crypto primitives are CORRECT!")
            print("The issue must be in how our production code integrates them.")
            return True
        else:
            print(f"\n[ERROR] ChangeKey failed with {sw1:02X}{sw2:02X}")
            error_names = {
                0x911E: "INTEGRITY_ERROR - CMAC verification failed",
                0x917E: "LENGTH_ERROR - Wrong data length",
                0x919E: "PARAMETER_ERROR - Invalid parameter",
                0x91AD: "AUTHENTICATION_DELAY - Too many attempts",
            }
            error_code = (sw1 << 8) | sw2
            if error_code in error_names:
                print(f"       ({error_names[error_code]})")
            
            print("\nDespite our crypto primitives matching NXP specs,")
            print("ChangeKey still fails! Need to investigate further...")
            return False


if __name__ == '__main__':
    try:
        success = test_changekey_with_cardmanager()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\nException: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

