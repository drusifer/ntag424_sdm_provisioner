#!/usr/bin/env python3
"""
Test Phase 2 as Continuation of Phase 1

Maybe Phase 2 needs to be sent as a direct continuation of Phase 1
(without new APDU command header) or with different format.

Testing if Phase 2 should be sent differently based on charts.md specs.
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


def test_phase2_variations():
    """Test Phase 2 with different command sequences."""
    
    print("=" * 80)
    print("PHASE 2 AS CONTINUATION TEST")
    print("=" * 80)
    print()
    print("Testing if Phase 2 needs different command format:")
    print("  1. Standard Phase 2 (current)")
    print("  2. Phase 2 without Le field")
    print("  3. Phase 2 with different P1/P2")
    print("  4. Phase 2 as direct continuation (no command header)")
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
            
            # Phase 1
            print("\n" + "=" * 80)
            print("PHASE 1: Getting Challenge")
            print("=" * 80)
            
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
            rndb_rotated = rndb[1:] + rndb[0:1]
            
            print(f"\n[INFO] Decrypted RndB: {rndb.hex().upper()}")
            print(f"[INFO] Rotated RndB: {rndb_rotated.hex().upper()}")
            print(f"[INFO] Generated RndA: {rnda.hex().upper()}")
            
            # Prepare Phase 2 data
            plaintext = rnda + rndb_rotated
            encrypted_data = cipher.encrypt(plaintext)
            
            print(f"\n[INFO] Phase 2 plaintext: {plaintext.hex().upper()}")
            print(f"[INFO] Phase 2 encrypted: {encrypted_data.hex().upper()}")
            
            # Test variations
            print("\n" + "=" * 80)
            print("PHASE 2: Testing Variations")
            print("=" * 80)
            
            variations = [
                {
                    "name": "Standard (90 AF 00 00 20 [data] 00)",
                    "apdu": [0x90, 0xAF, 0x00, 0x00, 0x20] + list(encrypted_data) + [0x00],
                    "note": "Current implementation"
                },
                {
                    "name": "Without Le (90 AF 00 00 20 [data])",
                    "apdu": [0x90, 0xAF, 0x00, 0x00, 0x20] + list(encrypted_data),
                    "note": "No Le field"
                },
                {
                    "name": "P1=02 (90 AF 02 00 20 [data] 00)",
                    "apdu": [0x90, 0xAF, 0x02, 0x00, 0x20] + list(encrypted_data) + [0x00],
                    "note": "P1=02 (like file selection)"
                },
                {
                    "name": "Direct continuation (90 AF [data])",
                    "apdu": [0x90, 0xAF] + list(encrypted_data),
                    "note": "As direct continuation, no Lc/Le"
                },
            ]
            
            results = {}
            
            for i, var in enumerate(variations, 1):
                print(f"\n  Test {i}: {var['name']}")
                print(f"         Note: {var['note']}")
                print(f"         APDU length: {len(var['apdu'])} bytes")
                print(f"         First bytes: {' '.join([f'{b:02X}' for b in var['apdu'][:8]])}...")
                
                # Need fresh Phase 1 for each variation
                if i > 1:
                    print("         Getting fresh Phase 1...")
                    apdu1 = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
                    data1, sw1, sw2 = card.send_apdu(apdu1, use_escape=True)
                    
                    if (sw1, sw2) == SW_ADDITIONAL_FRAME and len(data1) == 16:
                        encrypted_rndb = bytes(data1)
                        rndb = cipher.decrypt(encrypted_rndb)
                        rnda = get_random_bytes(16)
                        rndb_rotated = rndb[1:] + rndb[0:1]
                        plaintext = rnda + rndb_rotated
                        encrypted_data = cipher.encrypt(plaintext)
                        # Update APDU with new data
                        if var['name'] == "Standard (90 AF 00 00 20 [data] 00)":
                            var['apdu'] = [0x90, 0xAF, 0x00, 0x00, 0x20] + list(encrypted_data) + [0x00]
                        elif var['name'] == "Without Le (90 AF 00 00 20 [data])":
                            var['apdu'] = [0x90, 0xAF, 0x00, 0x00, 0x20] + list(encrypted_data)
                        elif var['name'] == "P1=02 (90 AF 02 00 20 [data] 00)":
                            var['apdu'] = [0x90, 0xAF, 0x02, 0x00, 0x20] + list(encrypted_data) + [0x00]
                        elif var['name'] == "Direct continuation (90 AF [data])":
                            var['apdu'] = [0x90, 0xAF] + list(encrypted_data)
                    else:
                        print(f"         [SKIP] Phase 1 failed: SW={sw1:02X}{sw2:02X}")
                        results[var['name']] = 'skipped'
                        continue
                
                try:
                    data2, sw1, sw2 = card.send_apdu(var['apdu'], use_escape=True)
                    
                    print(f"         Response: SW={sw1:02X}{sw2:02X}, Data={len(data2)} bytes")
                    
                    if (sw1, sw2) == SW_OK:
                        print(f"         [OK] ✅✅✅ SUCCESS! ✅✅✅")
                        print(f"         {var['name']} worked!")
                        results[var['name']] = True
                        
                        if len(data2) > 0:
                            print(f"         Response data: {len(data2)} bytes")
                            print(f"         Hex: {bytes(data2).hex().upper()[:64]}...")
                            
                            # Check if additional frames needed
                            if len(data2) < 32:
                                print(f"         [INFO] Response < 32 bytes, may need additional frames")
                    elif (sw1, sw2) == SW_ADDITIONAL_FRAME:
                        print(f"         [INFO] SW=91AF (Additional Frame)")
                        print(f"         Reading additional frames...")
                        
                        # Read additional frames
                        full_response = bytearray(data2)
                        while (sw1, sw2) == SW_ADDITIONAL_FRAME:
                            af_apdu = [0x90, 0xAF, 0x00, 0x00, 0x00]
                            data3, sw1, sw2 = card.send_apdu(af_apdu, use_escape=True)
                            full_response.extend(bytes(data3))
                            
                            if (sw1, sw2) == SW_OK:
                                print(f"         [OK] Complete response: {len(full_response)} bytes")
                                print(f"         Hex: {bytes(full_response).hex().upper()[:64]}...")
                                results[var['name']] = True
                                break
                            elif (sw1, sw2) != SW_ADDITIONAL_FRAME:
                                break
                    elif (sw1, sw2) == (0x91, 0xAE):
                        print(f"         [FAIL] SW=91AE (Authentication Error)")
                        results[var['name']] = False
                    elif (sw1, sw2) == (0x91, 0xCA):
                        print(f"         [INFO] SW=91CA (Command Aborted)")
                        results[var['name']] = 'aborted'
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
                print("\nResults:")
                for name, result in results.items():
                    status = "[OK]" if result is True else "[FAIL]" if result is False else "[ABORTED]" if result == 'aborted' else "[FRAME]" if result == 'additional_frame' else "[SKIP]"
                    print(f"  {status} {name}: {result}")
            
    except NTag242ConnectionError as e:
        print(f"\n[FAIL] CONNECTION FAILED: {e}")
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_phase2_variations()

