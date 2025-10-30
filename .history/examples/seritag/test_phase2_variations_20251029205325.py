#!/usr/bin/env python3
"""
Test Phase 2 Protocol Variations

Since Phase 1 works and RndB rotation is correct, test different
Phase 2 protocol variations to find what Seritag expects.
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
import time
import logging

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


def test_phase2_variations():
    """Test various Phase 2 protocol variations."""
    
    print("=" * 80)
    print("PHASE 2 PROTOCOL VARIATIONS TEST")
    print("=" * 80)
    print()
    print("Testing different Phase 2 formats:")
    print("  1. Standard (RndA || RndB')")
    print("  2. Reverse (RndB' || RndA)")
    print("  3. Different encryption modes")
    print("  4. Different data lengths")
    print()
    print("Please place a FRESH tag on the reader.")
    print()
    
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
            
            key = FACTORY_KEY
            cipher = AES.new(key, AES.MODE_ECB)
            
            # Phase 1 to get RndB
            print("\n" + "=" * 80)
            print("PHASE 1: Getting Challenge")
            print("=" * 80)
            
            max_attempts = 5
            encrypted_rndb = None
            
            for attempt in range(max_attempts):
                try:
                    apdu = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
                    data, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
                    
                    if (sw1, sw2) == SW_ADDITIONAL_FRAME and len(data) == 16:
                        encrypted_rndb = bytes(data)
                        print(f"[OK] Phase 1 successful (attempt {attempt+1})")
                        print(f"     Encrypted RndB: {encrypted_rndb.hex().upper()}")
                        break
                    elif (sw1, sw2) == (0x91, 0xAD):
                        wait = 2.0 * (attempt + 1)
                        print(f"[INFO] Delay - waiting {wait}s...")
                        time.sleep(wait)
                    else:
                        print(f"[FAIL] Phase 1 failed: SW={sw1:02X}{sw2:02X}")
                        return False
                except Exception as e:
                    print(f"[FAIL] Error: {e}")
                    return False
            
            if encrypted_rndb is None:
                print("[FAIL] Could not get Phase 1 challenge")
                return False
            
            # Decrypt RndB
            rndb = cipher.decrypt(encrypted_rndb)
            rnda = get_random_bytes(16)
            rndb_rotated = rndb[1:] + rndb[0:1]
            
            print(f"\n[INFO] Decrypted RndB: {rndb.hex().upper()}")
            print(f"[INFO] Rotated RndB: {rndb_rotated.hex().upper()}")
            print(f"[INFO] Generated RndA: {rnda.hex().upper()}")
            
            print("\n" + "=" * 80)
            print("PHASE 2: Testing Variations")
            print("=" * 80)
            
            # Need fresh Phase 1 for each variation
            variations = [
                {
                    "name": "Standard (RndA || RndB')",
                    "data": rnda + rndb_rotated,
                    "note": "Current implementation"
                },
                {
                    "name": "Reverse (RndB' || RndA)",
                    "data": rndb_rotated + rnda,
                    "note": "Reversed order"
                },
                {
                    "name": "No rotation (RndA || RndB)",
                    "data": rnda + rndb,
                    "note": "No rotation"
                },
                {
                    "name": "Right rotate (RndA || RndB_right)",
                    "data": rnda + (rndb[-1:] + rndb[:-1]),
                    "note": "Right rotation instead of left"
                },
            ]
            
            results = {}
            
            for i, var in enumerate(variations, 1):
                print(f"\n  Test {i}: {var['name']}")
                print(f"         Note: {var['note']}")
                
                # Get fresh Phase 1 for each variation
                try:
                    # Wait a bit between attempts
                    if i > 1:
                        time.sleep(0.5)
                    
                    apdu = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
                    data, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
                    
                    if (sw1, sw2) != SW_ADDITIONAL_FRAME or len(data) != 16:
                        print(f"         [SKIP] Phase 1 failed: SW={sw1:02X}{sw2:02X}")
                        results[var['name']] = 'skipped'
                        continue
                    
                    encrypted_rndb = bytes(data)
                    rndb = cipher.decrypt(encrypted_rndb)
                    
                    # Update data for this variation
                    if var['name'] == "Standard (RndA || RndB')":
                        var['data'] = rnda + (rndb[1:] + rndb[0:1])
                    elif var['name'] == "Reverse (RndB' || RndA)":
                        var['data'] = (rndb[1:] + rndb[0:1]) + rnda
                    elif var['name'] == "No rotation (RndA || RndB)":
                        var['data'] = rnda + rndb
                    elif var['name'] == "Right rotate (RndA || RndB_right)":
                        var['data'] = rnda + (rndb[-1:] + rndb[:-1])
                    
                    # Encrypt
                    encrypted_data = cipher.encrypt(var['data'])
                    
                    # Phase 2
                    apdu2 = [0x90, 0xAF, 0x00, 0x00, 0x20] + list(encrypted_data) + [0x00]
                    data2, sw1, sw2 = card.send_apdu(apdu2, use_escape=True)
                    
                    print(f"         Phase 2: SW={sw1:02X}{sw2:02X}")
                    
                    if (sw1, sw2) == SW_OK:
                        print(f"         [OK] ✅ SUCCESS! ✅")
                        print(f"         {var['name']} worked!")
                        results[var['name']] = True
                    elif (sw1, sw2) == (0x91, 0xAE):
                        print(f"         [FAIL] SW=91AE (Authentication Error)")
                        results[var['name']] = False
                    elif (sw1, sw2) == (0x91, 0x1C):
                        print(f"         [FAIL] SW=911C (Illegal Command)")
                        results[var['name']] = False
                    elif (sw1, sw2) == (0x91, 0xCA):
                        print(f"         [INFO] SW=91CA (Command Aborted)")
                        results[var['name']] = 'aborted'
                    elif (sw1, sw2) == SW_ADDITIONAL_FRAME:
                        print(f"         [INFO] SW=91AF (Additional Frame!)")
                        print(f"         May need additional frames")
                        results[var['name']] = 'additional_frame'
                    else:
                        print(f"         [INFO] Unexpected: SW={sw1:02X}{sw2:02X}")
                        results[var['name']] = False
                        
                except Exception as e:
                    print(f"         [FAIL] Error: {e}")
                    results[var['name']] = False
            
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
                print("       All variations failed")
                print("\nStatus:")
                for name, result in results.items():
                    status = "✅" if result is True else "❌" if result is False else "⏳" if result == 'aborted' else "📦" if result == 'additional_frame' else "⏭️"
                    print(f"  {status} {name}: {result}")
            
    except NTag242ConnectionError as e:
        print(f"\n[FAIL] CONNECTION FAILED: {e}")
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_phase2_variations()

