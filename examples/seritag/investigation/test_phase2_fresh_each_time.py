#!/usr/bin/env python3
"""
Test Phase 2 Variations - Fresh Tag Each Time

Since Phase 2 failure causes tag to reject subsequent Phase 1 (SW=91CA),
we need to test each variation with a truly fresh Phase 1/2 attempt.

This script will pause between tests so user can provide fresh tag.
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


def test_single_variation(name, data_func):
    """Test a single Phase 2 variation with fresh Phase 1."""
    
    print("\n" + "=" * 80)
    print(f"TEST: {name}")
    print("=" * 80)
    
    try:
        with CardManager(0) as card:
            print("Step 1: Selecting PICC application...")
            try:
                SelectPiccApplication().execute(card)
                print("[OK] PICC application selected")
            except ApduError as e:
                if e.sw2 == 0x85:
                    print("[INFO] SelectPICC rejected - continuing...")
                else:
                    raise
            
            print("\nStep 2: Getting chip version...")
            version_info = GetChipVersion().execute(card)
            print(f"[OK] Tag: HW {version_info.hw_major_version}.{version_info.hw_minor_version}")
            print(f"      UID: {version_info.uid.hex().upper()}")
            
            # Phase 1
            key = FACTORY_KEY
            cipher = AES.new(key, AES.MODE_ECB)
            
            print("\nStep 3: Phase 1 - Getting challenge...")
            apdu = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
            data, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
            
            if (sw1, sw2) != SW_ADDITIONAL_FRAME or len(data) != 16:
                print(f"[FAIL] Phase 1 failed: SW={sw1:02X}{sw2:02X}")
                return False
            
            encrypted_rndb = bytes(data)
            print(f"[OK] Phase 1 successful")
            print(f"     Encrypted RndB: {encrypted_rndb.hex().upper()}")
            
            # Decrypt and prepare
            rndb = cipher.decrypt(encrypted_rndb)
            rnda = get_random_bytes(16)
            
            # Prepare Phase 2 data using provided function
            phase2_data = data_func(rnda, rndb)
            
            print(f"\nStep 4: Phase 2 - Sending authentication...")
            print(f"     RndA: {rnda.hex().upper()}")
            print(f"     RndB: {rndb.hex().upper()}")
            print(f"     Phase 2 data function: {name}")
            
            # Encrypt
            encrypted_data = cipher.encrypt(phase2_data)
            print(f"     Encrypted data length: {len(encrypted_data)} bytes")
            
            # Phase 2
            apdu2 = [0x90, 0xAF, 0x00, 0x00, 0x20] + list(encrypted_data) + [0x00]
            data2, sw1, sw2 = card.send_apdu(apdu2, use_escape=True)
            
            print(f"     Phase 2 response: SW={sw1:02X}{sw2:02X}")
            
            if (sw1, sw2) == SW_OK:
                print(f"[OK] ✅✅✅ SUCCESS! ✅✅✅")
                print(f"     {name} worked!")
                return True
            elif (sw1, sw2) == (0x91, 0xAE):
                print(f"[FAIL] SW=91AE (Authentication Error)")
                return False
            elif (sw1, sw2) == (0x91, 0xCA):
                print(f"[INFO] SW=91CA (Command Aborted)")
                return 'aborted'
            elif (sw1, sw2) == SW_ADDITIONAL_FRAME:
                print(f"[INFO] SW=91AF (Additional Frame - may need more frames)")
                return 'additional_frame'
            else:
                print(f"[INFO] Unexpected: SW={sw1:02X}{sw2:02X}")
                return False
                
    except NTag242ConnectionError as e:
        print(f"[FAIL] Connection failed: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Test Phase 2 variations, pausing for fresh tag each time."""
    
    print("=" * 80)
    print("PHASE 2 VARIATIONS - FRESH TAG EACH TEST")
    print("=" * 80)
    print()
    print("This test requires a FRESH tag for each variation.")
    print("After each Phase 2 failure, tag won't accept another Phase 1 (SW=91CA).")
    print()
    
    variations = [
        {
            "name": "Standard (RndA || RndB left-rotated)",
            "func": lambda rnda, rndb: rnda + (rndb[1:] + rndb[0:1])
        },
        {
            "name": "Reverse (RndB left-rotated || RndA)",
            "func": lambda rnda, rndb: (rndb[1:] + rndb[0:1]) + rnda
        },
        {
            "name": "No rotation (RndA || RndB)",
            "func": lambda rnda, rndb: rnda + rndb
        },
        {
            "name": "Right rotate (RndA || RndB right-rotated)",
            "func": lambda rnda, rndb: rnda + (rndb[-1:] + rndb[:-1])
        },
        {
            "name": "2-byte rotate (RndA || RndB 2-byte left)",
            "func": lambda rnda, rndb: rnda + (rndb[2:] + rndb[:2])
        },
    ]
    
    results = {}
    
    for i, var in enumerate(variations, 1):
        if i > 1:
            print("\n" + "=" * 80)
            print(f"Please provide a FRESH tag for Test {i}")
            print("=" * 80)
            input("Press Enter after placing fresh tag on reader...")
        
        result = test_single_variation(var["name"], var["func"])
        results[var["name"]] = result
        
        if result is True:
            print(f"\n[OK] ✅ FOUND WORKING PROTOCOL! ✅")
            print(f"     {var['name']} works!")
            break
    
    # Summary
    print("\n" + "=" * 80)
    print("INVESTIGATION SUMMARY")
    print("=" * 80)
    
    success = [name for name, result in results.items() if result is True]
    
    if success:
        print(f"\n[OK] ✅ FOUND WORKING PROTOCOL! ✅")
        for name in success:
            print(f"  [OK] {name}")
    else:
        print("\n[INFO] No working Phase 2 variation found")
        print("\nResults:")
        for name, result in results.items():
            status = "[OK]" if result is True else "[FAIL]" if result is False else "[ABORTED]" if result == 'aborted' else "[FRAME]" if result == 'additional_frame' else "[SKIP]"
            print(f"  {status} {name}: {result}")


if __name__ == "__main__":
    main()

