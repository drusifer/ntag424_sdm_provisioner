#!/usr/bin/env python3
"""
Test Command 0x77 (Returns SW=917E - Length Error)

Command 0x77 returns SW=917E (Length Error), not SW=911C (Not Supported).
This means the command EXISTS and is RECOGNIZED, but needs correct data format.

Test various 0x77 formats to find working parameters.
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.constants import SW_OK, SW_ADDITIONAL_FRAME
from Crypto.Random import get_random_bytes
import logging

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


def test_command_0x77():
    """Test command 0x77 with various formats."""
    
    print("=" * 80)
    print("COMMAND 0x77 INVESTIGATION")
    print("=" * 80)
    print()
    print("Command 0x77 returns SW=917E (Length Error)")
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
            
            # Test various 0x77 formats
            print("\n" + "=" * 80)
            print("TESTING COMMAND 0x77")
            print("=" * 80)
            
            test_configs = [
                # Basic formats
                {"name": "0x77 Basic (90 77 00 00 00)", "apdu": [0x90, 0x77, 0x00, 0x00, 0x00]},
                {"name": "0x77 no Le", "apdu": [0x90, 0x77, 0x00, 0x00]},
                
                # With different P1/P2
                {"name": "0x77 P1=01", "apdu": [0x90, 0x77, 0x01, 0x00, 0x00]},
                {"name": "0x77 P2=01", "apdu": [0x90, 0x77, 0x00, 0x01, 0x00]},
                {"name": "0x77 P1=71 P2=00", "apdu": [0x90, 0x77, 0x71, 0x00, 0x00]},
                
                # With data (various lengths)
                {"name": "0x77 with 1 byte", "apdu": [0x90, 0x77, 0x00, 0x00, 0x01, 0x00, 0x00]},
                {"name": "0x77 with 2 bytes", "apdu": [0x90, 0x77, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]},
                {"name": "0x77 with 16 bytes", "apdu": [0x90, 0x77, 0x00, 0x00, 0x10] + [0x00] * 16 + [0x00]},
                {"name": "0x77 with 32 bytes", "apdu": [0x90, 0x77, 0x00, 0x00, 0x20] + [0x00] * 32 + [0x00]},
                
                # With key number (like EV2 Phase 1)
                {"name": "0x77 with KeyNo 00", "apdu": [0x90, 0x77, 0x00, 0x00, 0x01, 0x00, 0x00]},
                {"name": "0x77 with KeyNo 01", "apdu": [0x90, 0x77, 0x00, 0x00, 0x01, 0x01, 0x00]},
                
                # As first frame (expect 91AF)
                {"name": "0x77 expecting additional frame", "apdu": [0x90, 0x77, 0x00, 0x00, 0x10] + [0x00] * 16 + [0x00]},
                
                # Chained format
                {"name": "0x77 chained", "apdu": [0x90, 0x77, 0x10, 0x00, 0x10] + [0x00] * 16 + [0x00]},
            ]
            
            for i, test in enumerate(test_configs, 1):
                print(f"\n  Test {i}: {test['name']}")
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
                            print(f"         Response: {len(data2)} bytes")
                            if len(data2) > 0:
                                print(f"         Hex: {data2.hex().upper()[:64]}...")
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
                        elif (sw1, sw2) == (0x91, 0xAE):
                            print(f"         [INFO] Authentication Error - may need auth first")
                except Exception as e:
                    print(f"         [FAIL] Error: {e}")
                    results[test['name']] = False
            
            # Summary
            print("\n" + "=" * 80)
            print("INVESTIGATION SUMMARY")
            print("=" * 80)
            
            success_count = sum(1 for v in results.values() if v is True)
            total_count = len(results)
            
            print(f"Total tests: {total_count}")
            print(f"Successful: {success_count}")
            
            if success_count > 0:
                print("\n[OK] Found working 0x77 format!")
                for name, success in results.items():
                    if success:
                        print(f"  [OK] {name}")
            else:
                print("\n[INFO] No working 0x77 format found")
                print("       All returned SW=917E (Length Error)")
                print("       Command recognized but needs correct data length")
            
    except NTag242ConnectionError as e:
        print(f"\n[FAIL] CONNECTION FAILED: {e}")
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_command_0x77()

