#!/usr/bin/env python3
"""
Test Factory Key Variations

Maybe Seritag doesn't use all-zero factory keys?
Test with different key possibilities.
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.commands.base import ApduError
from ntag424_sdm_provisioner.constants import FACTORY_KEY, SW_OK, SW_ADDITIONAL_FRAME
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import logging

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


def test_with_key(key, key_name):
    """Test Phase 1/Phase 2 with a specific key."""
    
    print(f"\n{'='*80}")
    print(f"TESTING WITH KEY: {key_name}")
    print(f"{'='*80}")
    print(f"Key: {key.hex().upper()}")
    
    try:
        with CardManager(0) as card:
            try:
                SelectPiccApplication().execute(card)
            except ApduError as e:
                if e.sw2 == 0x85:
                    pass  # Continue
                else:
                    raise
            
            GetChipVersion().execute(card)
            
            # Phase 1
            cipher = AES.new(key, AES.MODE_ECB)
            apdu = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
            data, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
            
            if (sw1, sw2) != SW_ADDITIONAL_FRAME or len(data) != 16:
                print(f"[FAIL] Phase 1 failed: SW={sw1:02X}{sw2:02X}")
                return False
            
            encrypted_rndb = bytes(data)
            print(f"[OK] Phase 1 successful")
            
            # Try to decrypt - if wrong key, will get garbage but won't fail yet
            try:
                rndb = cipher.decrypt(encrypted_rndb)
                print(f"[OK] Decrypted RndB with key: {rndb.hex().upper()[:32]}...")
            except:
                print(f"[INFO] Decryption with key failed (wrong key)")
                return False
            
            # Phase 2
            rnda = get_random_bytes(16)
            rndb_rotated = rndb[1:] + rndb[0:1]
            plaintext = rnda + rndb_rotated
            encrypted_data = cipher.encrypt(plaintext)
            
            apdu2 = [0x90, 0xAF, 0x00, 0x00, 0x20] + list(encrypted_data) + [0x00]
            data2, sw1, sw2 = card.send_apdu(apdu2, use_escape=True)
            
            print(f"     Phase 2: SW={sw1:02X}{sw2:02X}")
            
            if (sw1, sw2) == SW_OK:
                print(f"[OK] ✅✅✅ SUCCESS WITH KEY: {key_name} ✅✅✅")
                return True
            elif (sw1, sw2) == (0x91, 0xAE):
                print(f"[FAIL] SW=91AE (Authentication Error)")
                return False
            else:
                print(f"[INFO] Unexpected: SW={sw1:02X}{sw2:02X}")
                return False
                
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


def test_key_variations():
    """Test various factory key possibilities."""
    
    print("=" * 80)
    print("FACTORY KEY VARIATIONS TEST")
    print("=" * 80)
    print()
    print("Testing if Seritag uses different factory keys:")
    print("  1. All zeros (standard)")
    print("  2. UID-based keys")
    print("  3. Fixed patterns")
    print()
    print("Please place a FRESH tag on the reader.")
    print()
    
    try:
        with CardManager(0) as card:
            try:
                SelectPiccApplication().execute(card)
            except ApduError:
                pass
            
            version_info = GetChipVersion().execute(card)
            uid = version_info.uid
            
            print(f"[OK] Tag UID: {uid.hex().upper()}")
            
    except:
        pass
    
    # Test keys
    test_keys = [
        (bytes(16), "All zeros (standard)"),
        (uid + bytes(9), "UID + 9 zeros"),
        (bytes(9) + uid[:7], "9 zeros + 7-byte UID"),
        (uid[:7] * 2 + uid[:2], "UID repeated pattern"),
        (b'\xFF' * 16, "All 0xFF"),
        (b'\x00' * 8 + b'\xFF' * 8, "Half zeros, half 0xFF"),
    ]
    
    results = {}
    
    for key_bytes, key_name in test_keys:
        print(f"\n{'='*80}")
        result = test_with_key(key_bytes, key_name)
        results[key_name] = result
        
        if result is True:
            print(f"\n[OK] ✅ FOUND WORKING KEY! ✅")
            print(f"     Key: {key_bytes.hex().upper()}")
            break
    
    # Summary
    print("\n" + "=" * 80)
    print("INVESTIGATION SUMMARY")
    print("=" * 80)
    
    success = [name for name, result in results.items() if result is True]
    
    if success:
        print(f"\n[OK] ✅ FOUND WORKING KEY! ✅")
        for name in success:
            print(f"  [OK] {name}")
    else:
        print("\n[INFO] No working factory key found")
        print("       All keys failed with SW=91AE")
        print("\nResults:")
        for name, result in results.items():
            status = "[OK]" if result is True else "[FAIL]"
            print(f"  {status} {name}: {result}")


if __name__ == "__main__":
    test_key_variations()

