#!/usr/bin/env python3
"""
Test Phase 1 Additional Frames Handling

Phase 1 returns SW=91AF (Additional Frame). Maybe we need to
send GetAdditionalFrame command (90 AF 00 00 00) to complete
the transaction and avoid leaving tag in pending state?

This could explain why delay counter persists - we're not
completing the authentication transaction properly.
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
import logging

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


def test_phase1_additional_frames():
    """Test if Phase 1 needs additional frame reads to complete."""
    
    print("=" * 80)
    print("PHASE 1 ADDITIONAL FRAMES INVESTIGATION")
    print("=" * 80)
    print()
    print("Hypothesis: Phase 1 returns SW=91AF (Additional Frame)")
    print("            Maybe we need to read additional frames?")
    print("            Or send GetAdditionalFrame to complete transaction?")
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
            
            print("\n" + "=" * 80)
            print("TEST 1: Standard Phase 1 (as currently implemented)")
            print("=" * 80)
            
            # Standard Phase 1 - returns 91AF with encrypted RndB
            try:
                cmd1 = AuthenticateEV2First(key_no=0)
                challenge_response = cmd1.execute(card)
                encrypted_rndb = challenge_response.challenge
                print(f"[OK] Phase 1 successful - got {len(encrypted_rndb)} bytes")
                print(f"     Challenge: {encrypted_rndb.hex().upper()[:32]}...")
                print(f"     Status: Returns SW=91AF (Additional Frame)")
                print(f"     Question: Do we need to complete with GetAdditionalFrame?")
            except ApduError as e:
                print(f"[FAIL] Phase 1 failed: {e.sw1:02X}{e.sw2:02X}")
                return False
            
            print("\n" + "=" * 80)
            print("TEST 2: Send GetAdditionalFrame after Phase 1")
            print("=" * 80)
            
            # Try sending GetAdditionalFrame (90 AF 00 00 00)
            # This might complete the transaction
            try:
                af_apdu = [0x90, 0xAF, 0x00, 0x00, 0x00]
                data, sw1, sw2 = card.send_apdu(af_apdu, use_escape=True)
                print(f"GetAdditionalFrame after Phase 1: SW={sw1:02X}{sw2:02X}")
                
                if (sw1, sw2) == SW_OK:
                    print(f"[OK] GetAdditionalFrame successful!")
                    print(f"     Response: {len(data)} bytes")
                    if len(data) > 0:
                        print(f"     Hex: {data.hex().upper()[:64]}...")
                elif (sw1, sw2) == (0x91, 0xCA):
                    print(f"[INFO] SW=91CA (Command Aborted)")
                    print(f"       Previous command not fully completed")
                    print(f"       This confirms transaction wasn't completed!")
                else:
                    print(f"[INFO] Unexpected response: SW={sw1:02X}{sw2:02X}")
                    
            except Exception as e:
                print(f"[FAIL] Error: {e}")
            
            print("\n" + "=" * 80)
            print("TEST 3: Phase 2 with multi-frame handling")
            print("=" * 80)
            
            # Try Phase 2, but check if it returns 91AF first
            try:
                # Phase 1 again for fresh attempt
                cmd1 = AuthenticateEV2First(key_no=0)
                challenge_response = cmd1.execute(card)
                encrypted_rndb = challenge_response.challenge
                
                # Decrypt RndB
                key = FACTORY_KEY
                cipher = AES.new(key, AES.MODE_ECB)
                rndb = cipher.decrypt(encrypted_rndb)
                
                # Generate RndA and encrypt response
                rnda = get_random_bytes(16)
                rndb_rotated = rndb[1:] + rndb[0:1]
                plaintext = rnda + rndb_rotated
                encrypted_response = cipher.encrypt(plaintext)
                
                # Phase 2: Standard format
                apdu = [0x90, 0xAF, 0x00, 0x00, 0x20] + list(encrypted_response) + [0x00]
                data, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
                
                print(f"Phase 2 response: SW={sw1:02X}{sw2:02X}, Data={len(data)} bytes")
                
                # Check if Phase 2 returns 91AF (needs additional frame)
                if (sw1, sw2) == SW_ADDITIONAL_FRAME:
                    print(f"[INFO] Phase 2 returned SW=91AF (Additional Frame)!")
                    print(f"       Need to read additional frames...")
                    
                    # Send GetAdditionalFrame
                    af_apdu = [0x90, 0xAF, 0x00, 0x00, 0x00]
                    data2, sw1, sw2 = card.send_apdu(af_apdu, use_escape=True)
                    
                    print(f"GetAdditionalFrame: SW={sw1:02X}{sw2:02X}, Data={len(data2)} bytes")
                    
                    if (sw1, sw2) == SW_OK:
                        print(f"[OK] Phase 2 complete with additional frame!")
                        print(f"     Total response: {len(data) + len(data2)} bytes")
                        print(f"     First frame: {data.hex().upper()[:64]}...")
                        print(f"     Second frame: {data2.hex().upper()[:64]}...")
                        print(f"[OK] This might be the correct protocol!")
                        
                        # Check combined response
                        full_response = bytes(data) + bytes(data2)
                        print(f"     Full response: {len(full_response)} bytes")
                        return True
                    else:
                        print(f"[FAIL] GetAdditionalFrame failed: SW={sw1:02X}{sw2:02X}")
                elif (sw1, sw2) == SW_OK:
                    print(f"[INFO] Phase 2 returned SW=9000 (immediate success)")
                    print(f"       No additional frames needed")
                else:
                    print(f"[FAIL] Phase 2 failed: SW={sw1:02X}{sw2:02X}")
                    
            except Exception as e:
                print(f"[FAIL] Error: {e}")
                import traceback
                traceback.print_exc()
            
            # Summary
            print("\n" + "=" * 80)
            print("INVESTIGATION SUMMARY")
            print("=" * 80)
            print()
            print("Key findings:")
            print("  1. Phase 1 returns SW=91AF (Additional Frame)")
            print("  2. Need to test if GetAdditionalFrame completes transaction")
            print("  3. Phase 2 might also return 91AF first")
            print()
            print("If Phase 2 returns 91AF, we need to:")
            print("  1. Read first frame (returns 91AF)")
            print("  2. Send GetAdditionalFrame (90 AF 00 00 00)")
            print("  3. Read remaining data")
            print()
            print("This could explain:")
            print("  - Why delay counter persists (transaction not completed)")
            print("  - Why fresh tap doesn't reset (transaction still pending)")
            print("  - Why SW=91CA (Command Aborted) occurs")
            
    except NTag242ConnectionError as e:
        print(f"\n[FAIL] CONNECTION FAILED: {e}")
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_phase1_additional_frames()

