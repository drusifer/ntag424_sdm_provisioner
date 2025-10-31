#!/usr/bin/env python3
"""
Test Phase 1 Response Data

Investigate what Phase 1 actually returns - maybe we're not getting
all the data, or maybe RndB isn't in the expected location.

This will help verify if:
1. Phase 1 returns additional frames we're not reading
2. RndB location/format is correct
3. Our rotation logic is correct
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
import time
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def test_phase1_response():
    """Test what Phase 1 actually returns."""
    
    print("=" * 80)
    print("PHASE 1 RESPONSE DATA INVESTIGATION")
    print("=" * 80)
    print()
    print("Testing what Phase 1 actually returns:")
    print("  1. Do we get all frames?")
    print("  2. Where is the encrypted RndB?")
    print("  3. What does the decrypted RndB look like?")
    print()
    
    try:
        with CardManager(0) as card:
            print("Step 1: Selecting PICC application...")
            SelectPiccApplication().execute(card)
            print("[OK] PICC application selected")
            
            print("\nStep 2: Getting chip version...")
            version_info = GetChipVersion().execute(card)
            print(f"[OK] Tag: HW {version_info.hw_major_version}.{version_info.hw_minor_version}")
            print(f"      UID: {version_info.uid.hex().upper()}")
            
            print("\nStep 3: Attempting Phase 1 with delay handling...")
            
            # Wait for delay to expire
            max_wait = 10
            for attempt in range(max_wait):
                try:
                    # Phase 1 command: 90 71 00 00 02 [KeyNo] 00 00
                    apdu = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
                    data, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
                    print(f"Attempt {attempt+1}: SW={sw1:02X}{sw2:02X}, Data={len(data)} bytes")
                    
                    if (sw1, sw2) == SW_ADDITIONAL_FRAME:
                        print(f"[OK] Phase 1 successful! Got SW=91AF (Additional Frame)")
                        print(f"     First frame data: {len(data)} bytes")
                        print(f"     Hex: {data.hex().upper()}")
                        
                        # Try reading additional frames
                        full_response = bytearray(data)
                        frame_count = 1
                        
                        while (sw1, sw2) == SW_ADDITIONAL_FRAME:
                            print(f"\n  Frame {frame_count}: {len(data)} bytes")
                            print(f"  Hex: {data.hex().upper()}")
                            
                            # Send GetAdditionalFrame
                            af_apdu = [0x90, 0xAF, 0x00, 0x00, 0x00]
                            data, sw1, sw2 = card.send_apdu(af_apdu, use_escape=True)
                            print(f"  GetAdditionalFrame: SW={sw1:02X}{sw2:02X}, Data={len(data)} bytes")
                            
                            if (sw1, sw2) == SW_ADDITIONAL_FRAME or (sw1, sw2) == SW_OK:
                                full_response.extend(data)
                                frame_count += 1
                                
                                if (sw1, sw2) == SW_OK:
                                    print(f"  Final frame: {len(data)} bytes")
                                    print(f"  Hex: {data.hex().upper()}")
                                    break
                            else:
                                break
                        
                        print(f"\n[INFO] Total response: {len(full_response)} bytes ({frame_count} frames)")
                        print(f"Full hex: {bytes(full_response).hex().upper()}")
                        
                        # Try to identify encrypted RndB
                        # Standard spec says Phase 1 returns encrypted RndB (16 bytes)
                        if len(full_response) >= 16:
                            # Assume first 16 bytes is encrypted RndB
                            encrypted_rndb = bytes(full_response[:16])
                            print(f"\n[INFO] Assuming first 16 bytes = encrypted RndB")
                            print(f"Encrypted RndB: {encrypted_rndb.hex().upper()}")
                            
                            # Try to decrypt it
                            key = FACTORY_KEY
                            cipher = AES.new(key, AES.MODE_ECB)
                            rndb = cipher.decrypt(encrypted_rndb)
                            print(f"Decrypted RndB: {rndb.hex().upper()}")
                            
                            # Rotate it
                            rndb_rotated = rndb[1:] + rndb[0:1]
                            print(f"RndB rotated: {rndb_rotated.hex().upper()}")
                            print(f"  Original: {rndb.hex().upper()}")
                            print(f"  Rotated:  {rndb_rotated.hex().upper()}")
                            print(f"  First byte moved to end")
                            
                            # Check if there's more data
                            if len(full_response) > 16:
                                remaining = bytes(full_response[16:])
                                print(f"\n[INFO] Additional data ({len(remaining)} bytes):")
                                print(f"Hex: {remaining.hex().upper()}")
                                print(f"This might be important!")
                        else:
                            print(f"\n[WARN] Response too short ({len(full_response)} bytes)")
                            print(f"Expected at least 16 bytes for encrypted RndB")
                        
                        break
                    elif (sw1, sw2) == (0x91, 0xAD):  # Authentication Delay
                        wait_time = 2.0 * (attempt + 1)
                        print(f"[INFO] Authentication delay - waiting {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        print(f"[FAIL] Unexpected response: SW={sw1:02X}{sw2:02X}")
                        break
                        
                except Exception as e:
                    print(f"[FAIL] Error: {e}")
                    import traceback
                    traceback.print_exc()
                    break
            
            print("\n" + "=" * 80)
            print("INVESTIGATION SUMMARY")
            print("=" * 80)
            print()
            print("Key findings:")
            print("  1. Phase 1 returns SW=91AF (Additional Frame)")
            print("  2. We need to read all frames to get complete response")
            print("  3. Encrypted RndB should be in first 16 bytes")
            print("  4. Any additional data might affect the protocol")
            
    except NTag242ConnectionError as e:
        print(f"\n[FAIL] CONNECTION FAILED: {e}")
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_phase1_response()

