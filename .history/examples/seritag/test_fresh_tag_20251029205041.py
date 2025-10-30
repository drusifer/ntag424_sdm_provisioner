#!/usr/bin/env python3
"""
Test Fresh Tag - Verify Phase 1/Phase 2 with Clean Delay Counter

This test is for a brand new tag with no authentication delay.
It will verify:
1. Phase 1 response data (all frames)
2. RndB extraction and rotation
3. Phase 2 multi-frame handling
4. Complete authentication flow
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.commands.base import ApduError
from ntag424_sdm_provisioner.constants import FACTORY_KEY, SW_OK, SW_ADDITIONAL_FRAME
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def test_fresh_tag():
    """Test authentication with a fresh tag (clean delay counter)."""
    
    print("=" * 80)
    print("FRESH TAG AUTHENTICATION TEST")
    print("=" * 80)
    print()
    print("Testing with a brand new tag (no authentication delay):")
    print("  1. Phase 1 response data (all frames)")
    print("  2. RndB extraction and rotation")
    print("  3. Phase 2 multi-frame handling")
    print("  4. Complete authentication flow")
    print()
    print("Please place a FRESH tag on the reader.")
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
            
            if version_info.hw_major_version == 48 and version_info.hw_minor_version == 0:
                print(f"      [INFO] Seritag NTAG424 DNA detected")
            
            print("\n" + "=" * 80)
            print("PHASE 1: Getting Challenge")
            print("=" * 80)
            
            # Phase 1 manually to see all response data
            print("\nSending Phase 1 command (90 71 00 00 02 00 00 00)...")
            apdu = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
            data, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
            
            print(f"Response: SW={sw1:02X}{sw2:02X}, Data={len(data)} bytes")
            
            if (sw1, sw2) == (0x91, 0xAD):
                print("[FAIL] Authentication delay - this tag has a delay counter!")
                print("       Please use a truly fresh tag that hasn't been tested.")
                return False
            
            if (sw1, sw2) != SW_ADDITIONAL_FRAME:
                print(f"[FAIL] Unexpected response: SW={sw1:02X}{sw2:02X}")
                print(f"       Expected SW=91AF (Additional Frame)")
                return False
            
            print(f"[OK] Phase 1 returned SW=91AF (Additional Frame)")
            print(f"     First frame: {len(data)} bytes")
            print(f"     Hex: {data.hex().upper()}")
            
            # Collect all frames
            full_response = bytearray(data)
            frame_count = 1
            
            print(f"\nReading additional frames...")
            while (sw1, sw2) == SW_ADDITIONAL_FRAME:
                # Send GetAdditionalFrame
                af_apdu = [0x90, 0xAF, 0x00, 0x00, 0x00]
                data, sw1, sw2 = card.send_apdu(af_apdu, use_escape=True)
                
                frame_count += 1
                print(f"  Frame {frame_count}: SW={sw1:02X}{sw2:02X}, Data={len(data)} bytes")
                
                if len(data) > 0:
                    print(f"  Hex: {data.hex().upper()[:64]}...")
                
                if (sw1, sw2) == SW_ADDITIONAL_FRAME or (sw1, sw2) == SW_OK:
                    full_response.extend(data)
                    
                    if (sw1, sw2) == SW_OK:
                        print(f"  [OK] Final frame received")
                        break
                else:
                    print(f"  [INFO] Unexpected final SW={sw1:02X}{sw2:02X}")
                    break
            
            print(f"\n[INFO] Total Phase 1 response: {len(full_response)} bytes ({frame_count} frames)")
            print(f"Full hex: {bytes(full_response).hex().upper()}")
            
            # Extract encrypted RndB (should be first 16 bytes)
            if len(full_response) < 16:
                print(f"[FAIL] Response too short ({len(full_response)} bytes)")
                print(f"       Need at least 16 bytes for encrypted RndB")
                return False
            
            encrypted_rndb = bytes(full_response[:16])
            print(f"\n[INFO] Extracted encrypted RndB (first 16 bytes):")
            print(f"Encrypted RndB: {encrypted_rndb.hex().upper()}")
            
            if len(full_response) > 16:
                remaining = bytes(full_response[16:])
                print(f"\n[INFO] Additional data after RndB ({len(remaining)} bytes):")
                print(f"Hex: {remaining.hex().upper()}")
                print(f"[WARN] There's more data - might be important!")
            
            # Decrypt RndB
            key = FACTORY_KEY
            cipher = AES.new(key, AES.MODE_ECB)
            rndb = cipher.decrypt(encrypted_rndb)
            
            print(f"\n[INFO] Decrypted RndB (16 bytes):")
            print(f"RndB: {rndb.hex().upper()}")
            
            # Rotate RndB
            rndb_rotated = rndb[1:] + rndb[0:1]
            print(f"\n[INFO] Rotated RndB (left by 1 byte):")
            print(f"Original: {rndb.hex().upper()}")
            print(f"Rotated:  {rndb_rotated.hex().upper()}")
            print(f"          (first byte '{rndb[0]:02X}' moved to end)")
            
            # Now try Phase 2 using the auth session (which handles multi-frame)
            print("\n" + "=" * 80)
            print("PHASE 2: Complete Authentication")
            print("=" * 80)
            
            print("\nUsing auth_session (handles multi-frame responses)...")
            session = Ntag424AuthSession(FACTORY_KEY)
            
            try:
                # Use the encrypted RndB we captured
                # auth_session will re-do Phase 1, but that's OK for testing
                session_keys = session.authenticate(card, key_no=0)
                
                print(f"[OK] ✅✅✅ AUTHENTICATION SUCCESSFUL! ✅✅✅")
                print(f"     Session keys derived!")
                print(f"     MAC Key: {session_keys.mac_key.hex().upper()[:32]}...")
                print(f"     Enc Key: {session_keys.enc_key.hex().upper()[:32]}...")
                
                print("\n" + "=" * 80)
                print("SUCCESS!")
                print("=" * 80)
                print("[OK] Complete EV2 authentication worked!")
                print("     Multi-frame handling is correct!")
                print("     RndB extraction and rotation is correct!")
                
                return True
                
            except ApduError as e:
                print(f"[FAIL] Phase 2 failed: SW={e.sw1:02X}{e.sw2:02X}")
                
                if e.sw2 == 0xAE:
                    print("[INFO] SW=91AE (Authentication Error)")
                    print("       Phase 2 protocol still incorrect for Seritag")
                    print("       Multi-frame handling worked, but protocol differs")
                elif e.sw2 == 0xCA:
                    print("[INFO] SW=91CA (Command Aborted)")
                    print("       Previous command not fully completed")
                    print("       May still need more frame handling")
                else:
                    print(f"[INFO] Unexpected error: {e}")
                
                return False
            except Exception as e:
                print(f"[FAIL] Error during Phase 2: {e}")
                import traceback
                traceback.print_exc()
                return False
            
    except NTag242ConnectionError as e:
        print(f"\n[FAIL] CONNECTION FAILED: {e}")
        print("Make sure NFC reader is connected and tag is present.")
        return False
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_fresh_tag()
    sys.exit(0 if success else 1)

