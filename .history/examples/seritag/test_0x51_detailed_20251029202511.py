#!/usr/bin/env python3
"""
Detailed Command 0x51 Investigation

Command 0x51 returns SW=91CA (Command Aborted) which means it's RECOGNIZED.
This suggests it may be a Seritag-specific authentication method.

Test various 0x51 command formats to find working parameters.
"""
import sys
import os
import time

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion, AuthenticateEV2First
from ntag424_sdm_provisioner.commands.base import ApduError
from ntag424_sdm_provisioner.constants import FACTORY_KEY, SW_OK, SW_ADDITIONAL_FRAME
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import logging

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


def test_command_0x51():
    """Test command 0x51 with various formats."""
    
    print("=" * 80)
    print("COMMAND 0x51 DETAILED INVESTIGATION")
    print("=" * 80)
    print()
    print("Command 0x51 returns SW=91CA (Command Aborted)")
    print("This means the command EXISTS and is RECOGNIZED!")
    print("Testing various formats to find working parameters...")
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
            print("\nStep 3: Phase 1 - Getting challenge (for context)...")
            try:
                cmd1 = AuthenticateEV2First(key_no=0)
                challenge_response = cmd1.execute(card)
                encrypted_rndb = challenge_response.challenge
                print(f"[OK] Got encrypted RndB: {encrypted_rndb.hex().upper()}")
                
                # Decrypt RndB
                key = FACTORY_KEY
                cipher = AES.new(key, AES.MODE_ECB)
                rndb = cipher.decrypt(encrypted_rndb)
                print(f"     Decrypted RndB: {rndb.hex().upper()}")
                
            except ApduError as e:
                print(f"[FAIL] Phase 1 failed: {e.sw1:02X}{e.sw2:02X}")
                return False
            
            # Test 0x51 immediately after Phase 1
            print("\n" + "=" * 80)
            print("TESTING COMMAND 0x51 AFTER PHASE 1")
            print("=" * 80)
            
            # Test various 0x51 formats
            test_configs = [
                # Basic formats
                {"name": "0x51 Basic (90 51 00 00 00)", "apdu": [0x90, 0x51, 0x00, 0x00, 0x00], "note": "Minimal format"},
                
                # With different P1/P2
                {"name": "0x51 P1=01", "apdu": [0x90, 0x51, 0x01, 0x00, 0x00], "note": "P1 variation"},
                {"name": "0x51 P2=01", "apdu": [0x90, 0x51, 0x00, 0x01, 0x00], "note": "P2 variation"},
                {"name": "0x51 P1=71 P2=00", "apdu": [0x90, 0x51, 0x71, 0x00, 0x00], "note": "P1=71 (Phase 1 command code)"},
                
                # With data (various lengths)
                {"name": "0x51 with 1 byte", "apdu": [0x90, 0x51, 0x00, 0x00, 0x01, 0x00, 0x00], "note": "Key number 0"},
                {"name": "0x51 with 2 bytes", "apdu": [0x90, 0x51, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00], "note": "KeyNo + LenCap format"},
                {"name": "0x51 with 16 bytes (RndB)", "apdu": [0x90, 0x51, 0x00, 0x00, 0x10] + list(encrypted_rndb) + [0x00], "note": "Encrypted RndB"},
                
                # As continuation of Phase 1 (using 0xAF format)
                {"name": "0x51 as continuation (0xAF)", "apdu": [0x90, 0xAF, 0x00, 0x00, 0x00], "note": "Maybe 0x51 is sent as 0xAF continuation"},
                
                # Multi-frame approach
                {"name": "0x51 first frame (expect 91AF)", "apdu": [0x90, 0x51, 0x00, 0x00, 0x10] + list(encrypted_rndb[:16]) + [0x00], "note": "First frame with data"},
                
                # Try as chained command
                {"name": "0x51 chained", "apdu": [0x90, 0x51, 0x10, 0x00, 0x10] + list(encrypted_rndb) + [0x00], "note": "Chained format"},
            ]
            
            for i, test in enumerate(test_configs, 1):
                print(f"\n  Test {i}: {test['name']}")
                print(f"         Note: {test['note']}")
                print(f"         APDU: {' '.join([f'{b:02X}' for b in test['apdu'][:8]])}... ({len(test['apdu'])} bytes)")
                
                try:
                    data, sw1, sw2 = card.send_apdu(test['apdu'], use_escape=True)
                    
                    # Check for additional frame
                    if (sw1, sw2) == SW_ADDITIONAL_FRAME:
                        print(f"         Result: SW={sw1:02X}{sw2:02X} (Additional frame!)")
                        print(f"         [INFO] Command needs continuation!")
                        # Send GetAdditionalFrame
                        af_apdu = [0x90, 0xAF, 0x00, 0x00, 0x00]
                        data2, sw1, sw2 = card.send_apdu(af_apdu, use_escape=True)
                        print(f"         GetAdditionalFrame: SW={sw1:02X}{sw2:02X}")
                        if (sw1, sw2) == SW_OK:
                            print(f"         [OK] Success with continuation!")
                            results[test['name']] = True
                            continue
                    elif (sw1, sw2) == SW_OK:
                        print(f"         Result: SW={sw1:02X}{sw2:02X} (SUCCESS!)")
                        if len(data) > 0:
                            print(f"         Response: {len(data)} bytes")
                            print(f"         Hex: {data.hex().upper()[:64]}...")
                        results[test['name']] = True
                    else:
                        print(f"         Result: SW={sw1:02X}{sw2:02X}")
                        results[test['name']] = False
                        
                        # Interpret status
                        if (sw1, sw2) == (0x91, 0xCA):
                            print(f"         [INFO] Command Aborted - wrong session state")
                        elif (sw1, sw2) == (0x91, 0x7E):
                            print(f"         [INFO] Length Error - wrong data length")
                        elif (sw1, sw2) == (0x91, 0x1C):
                            print(f"         [INFO] Illegal Command - wrong format")
                except Exception as e:
                    print(f"         [FAIL] Error: {e}")
                    results[test['name']] = False
            
            # Test 0x51 with timing variations
            print("\n" + "=" * 80)
            print("TESTING 0x51 WITH TIMING VARIATIONS")
            print("=" * 80)
            
            # Fresh Phase 1
            cmd1 = AuthenticateEV2First(key_no=0)
            challenge_response = cmd1.execute(card)
            
            delays = [0.1, 0.5, 1.0]
            for delay in delays:
                print(f"\n  Testing with {delay}s delay after Phase 1...")
                time.sleep(delay)
                
                apdu = [0x90, 0x51, 0x00, 0x00, 0x00]
                try:
                    data, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
                    print(f"    Result: SW={sw1:02X}{sw2:02X}")
                    if (sw1, sw2) == SW_OK:
                        print(f"    [OK] Delay {delay}s worked!")
                        results[f"delay_{delay}s"] = True
                    else:
                        results[f"delay_{delay}s"] = False
                except Exception as e:
                    print(f"    [FAIL] Error: {e}")
                    results[f"delay_{delay}s"] = False
            
            # Summary
            print("\n" + "=" * 80)
            print("INVESTIGATION SUMMARY")
            print("=" * 80)
            
            success_count = sum(1 for v in results.values() if v)
            total_count = len(results)
            
            print(f"Total tests: {total_count}")
            print(f"Successful: {success_count}")
            
            if success_count > 0:
                print("\n[OK] Found working 0x51 format!")
                for name, success in results.items():
                    if success:
                        print(f"  [OK] {name}")
            else:
                print("\n[INFO] No working 0x51 format found")
                print("       All returned SW=91CA (Command Aborted)")
                print("       Command recognized but wrong state/parameters")
                print()
                print("Next steps:")
                print("  1. Need authentication first? (Try after Phase 2)")
                print("  2. Different command sequence? (Phase 1 → Wait → 0x51 → Phase 2)")
                print("  3. Multi-frame protocol? (Multiple 0x51 commands)")
            
    except NTag242ConnectionError as e:
        print(f"\n[FAIL] CONNECTION FAILED: {e}")
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_command_0x51()

