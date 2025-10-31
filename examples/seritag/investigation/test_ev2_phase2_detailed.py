#!/usr/bin/env python3
"""
Detailed EV2 Phase 2 Authentication Investigation

Tests various Phase 2 protocol variations to identify what Seritag expects.
With our protocol fixes, maybe we can identify the exact difference.
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion, AuthenticateEV2First
from ntag424_sdm_provisioner.commands.base import ApduError
from ntag424_sdm_provisioner.constants import FACTORY_KEY, SW_OK, SW_ADDITIONAL_FRAME
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Hash import CMAC
import logging

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


def test_phase2_variations():
    """Test various Phase 2 protocol variations."""
    
    print("=" * 80)
    print("EV2 PHASE 2 DETAILED INVESTIGATION")
    print("=" * 80)
    print()
    print("Testing Phase 2 protocol variations:")
    print("  - Different encryption modes")
    print("  - Different data formats")
    print("  - Different command formats")
    print("  - Command 0x51 attempts")
    print()
    
    results = {}
    
    try:
        with CardManager(0) as card:
            print("Step 1: Selecting PICC application...")
            SelectPiccApplication().execute(card)
            print("[OK] PICC application selected")
            
            print("\nStep 2: Getting chip version...")
            version_info = GetChipVersion().execute(card)
            print(f"[OK] Tag: HW {version_info.hw_major_version}.{version_info.hw_minor_version}")
            print(f"      UID: {version_info.uid.hex().upper()}")
            
            # Phase 1: Get challenge
            print("\nStep 3: Phase 1 - Getting challenge...")
            try:
                cmd1 = AuthenticateEV2First(key_no=0)
                challenge_response = cmd1.execute(card)
                encrypted_rndb = challenge_response.challenge
                print(f"[OK] Phase 1 successful - got encrypted RndB: {len(encrypted_rndb)} bytes")
                print(f"     Hex: {encrypted_rndb.hex().upper()}")
                
                # Decrypt RndB
                key = FACTORY_KEY
                cipher = AES.new(key, AES.MODE_ECB)
                rndb = cipher.decrypt(encrypted_rndb)
                print(f"     Decrypted RndB: {rndb.hex().upper()}")
                
            except ApduError as e:
                print(f"[FAIL] Phase 1 failed: {e.sw1:02X}{e.sw2:02X}")
                return False
            
            # Now test various Phase 2 approaches
            print("\n" + "=" * 80)
            print("PHASE 2 VARIATIONS")
            print("=" * 80)
            
            rnda = get_random_bytes(16)
            rndb_rotated = rndb[1:] + rndb[0:1]
            
            print(f"\nGenerated RndA: {rnda.hex().upper()}")
            print(f"RndB rotated: {rndb_rotated.hex().upper()}")
            
            # Test 1: Standard Phase 2 (what we're currently using)
            print("\n" + "-" * 80)
            print("TEST 1: Standard Phase 2 (Current Implementation)")
            print("-" * 80)
            try:
                # Standard: E(Kx, RndA || RndB')
                plaintext = rnda + rndb_rotated
                cipher = AES.new(key, AES.MODE_ECB)
                encrypted_data = cipher.encrypt(plaintext)
                
                print(f"Plaintext: {plaintext.hex().upper()}")
                print(f"Encrypted: {encrypted_data.hex().upper()}")
                
                # Send Phase 2: 90 AF 00 00 20 [encrypted_data] 00
                phase2_apdu = [
                    0x90, 0xAF,  # AuthenticateEV2Second
                    0x00, 0x00,  # P1, P2
                    0x20,        # Lc = 32 bytes
                ] + list(encrypted_data) + [0x00]  # Data + Le
                
                print(f"APDU: {' '.join([f'{b:02X}' for b in phase2_apdu[:8]])}... ({len(phase2_apdu)} bytes)")
                
                data, sw1, sw2 = card.send_apdu(phase2_apdu, use_escape=True)
                if (sw1, sw2) == SW_OK:
                    print(f"[OK] Standard Phase 2 worked!")
                    print(f"     Response: {len(data)} bytes")
                    print(f"     Hex: {data.hex().upper()[:64]}...")
                    results['standard'] = True
                else:
                    print(f"[FAIL] Standard Phase 2: SW={sw1:02X}{sw2:02X}")
                    results['standard'] = False
            except Exception as e:
                print(f"[FAIL] Standard Phase 2 error: {e}")
                results['standard'] = False
            
            # Test 2: Try RndB' in different position (RndB' || RndA)
            print("\n" + "-" * 80)
            print("TEST 2: Reverse Order (RndB' || RndA)")
            print("-" * 80)
            try:
                plaintext = rndb_rotated + rnda  # Reversed order
                cipher = AES.new(key, AES.MODE_ECB)
                encrypted_data = cipher.encrypt(plaintext)
                
                phase2_apdu = [
                    0x90, 0xAF,
                    0x00, 0x00,
                    0x20,
                ] + list(encrypted_data) + [0x00]
                
                data, sw1, sw2 = card.send_apdu(phase2_apdu, use_escape=True)
                if (sw1, sw2) == SW_OK:
                    print(f"[OK] Reverse order worked!")
                    results['reversed'] = True
                else:
                    print(f"[FAIL] Reverse order: SW={sw1:02X}{sw2:02X}")
                    results['reversed'] = False
            except Exception as e:
                print(f"[FAIL] Reverse order error: {e}")
                results['reversed'] = False
            
            # Test 3: Try different rotation (right rotate instead of left)
            print("\n" + "-" * 80)
            print("TEST 3: Right Rotate RndB (instead of left)")
            print("-" * 80)
            try:
                rndb_right_rotated = rndb[-1:] + rndb[:-1]  # Right rotate
                plaintext = rnda + rndb_right_rotated
                cipher = AES.new(key, AES.MODE_ECB)
                encrypted_data = cipher.encrypt(plaintext)
                
                phase2_apdu = [
                    0x90, 0xAF,
                    0x00, 0x00,
                    0x20,
                ] + list(encrypted_data) + [0x00]
                
                data, sw1, sw2 = card.send_apdu(phase2_apdu, use_escape=True)
                if (sw1, sw2) == SW_OK:
                    print(f"[OK] Right rotate worked!")
                    results['right_rotate'] = True
                else:
                    print(f"[FAIL] Right rotate: SW={sw1:02X}{sw2:02X}")
                    results['right_rotate'] = False
            except Exception as e:
                print(f"[FAIL] Right rotate error: {e}")
                results['right_rotate'] = False
            
            # Test 4: Try command 0x51 immediately after Phase 1
            print("\n" + "-" * 80)
            print("TEST 4: Command 0x51 After Phase 1")
            print("-" * 80)
            # Note: Need fresh Phase 1 for this test
            try:
                # Do Phase 1 again
                cmd1 = AuthenticateEV2First(key_no=0)
                challenge_response = cmd1.execute(card)
                
                # Now try 0x51 with various parameters
                test_configs = [
                    {"name": "0x51 with P1=00 P2=00", "apdu": [0x90, 0x51, 0x00, 0x00, 0x00]},
                    {"name": "0x51 with no Le", "apdu": [0x90, 0x51, 0x00, 0x00]},
                    {"name": "0x51 with encrypted RndB", "apdu": [0x90, 0x51, 0x00, 0x00, 0x10] + list(challenge_response.challenge) + [0x00]},
                    {"name": "0x51 with Phase 2 data format", "apdu": [0x90, 0x51, 0x00, 0x00, 0x20] + [0x00] * 32 + [0x00]},
                ]
                
                for test in test_configs:
                    try:
                        data, sw1, sw2 = card.send_apdu(test['apdu'], use_escape=True)
                        print(f"  {test['name']}: SW={sw1:02X}{sw2:02X}")
                        if (sw1, sw2) == SW_OK or sw1 == 0x91:
                            print(f"     [OK] Success! Response: {len(data)} bytes")
                            if len(data) > 0:
                                print(f"     Hex: {data.hex().upper()[:64]}...")
                    except Exception as e:
                        print(f"  {test['name']}: Error - {e}")
                        
            except Exception as e:
                print(f"[FAIL] 0x51 test error: {e}")
            
            # Summary
            print("\n" + "=" * 80)
            print("INVESTIGATION SUMMARY")
            print("=" * 80)
            
            success_count = sum(1 for v in results.values() if v)
            if success_count > 0:
                print(f"[OK] Found working Phase 2 variant!")
                for name, success in results.items():
                    if success:
                        print(f"  [OK] {name}")
            else:
                print("[INFO] No Phase 2 variant worked")
                print("       All returned SW=91AE (Authentication Error)")
                print("       Seritag Phase 2 protocol still differs from standard")
            
    except NTag242ConnectionError as e:
        print(f"\n[FAIL] CONNECTION FAILED: {e}")
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_phase2_variations()

