#!/usr/bin/env python3
"""
Test Phase 2 Multi-Frame Handling

Tests if Phase 2 properly handles additional frames (91AF responses).
This test will wait patiently for authentication delays to expire.
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
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def test_phase2_multiframe():
    """Test Phase 2 with multi-frame handling."""
    
    print("=" * 80)
    print("PHASE 2 MULTI-FRAME HANDLING TEST")
    print("=" * 80)
    print()
    print("Testing if Phase 2 properly reads additional frames (91AF responses)")
    print("Will wait patiently for authentication delays to expire...")
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
            
            print("\nStep 3: Attempting Phase 1 (with delay handling)...")
            
            # Try Phase 1 with retries for delay
            max_wait_attempts = 10
            challenge_response = None
            
            for attempt in range(max_wait_attempts):
                try:
                    cmd1 = AuthenticateEV2First(key_no=0)
                    challenge_response = cmd1.execute(card)
                    print(f"[OK] Phase 1 successful on attempt {attempt+1}!")
                    break
                except ApduError as e:
                    if e.sw2 == 0xAD:  # Authentication Delay
                        wait_time = 2.0 * (attempt + 1)  # Exponential backoff
                        print(f"[INFO] Authentication delay (attempt {attempt+1}/{max_wait_attempts})")
                        print(f"       Waiting {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        print(f"[FAIL] Phase 1 failed: SW={e.sw1:02X}{e.sw2:02X}")
                        return False
            
            if challenge_response is None:
                print("[FAIL] Could not complete Phase 1 after waiting")
                print("       Delay counter may require longer wait or fresh tag")
                return False
            
            encrypted_rndb = challenge_response.challenge
            print(f"[OK] Got encrypted RndB: {len(encrypted_rndb)} bytes")
            print(f"     Hex: {encrypted_rndb.hex().upper()[:32]}...")
            
            print("\nStep 4: Attempting Phase 2 with multi-frame handling...")
            
            # Use auth_session to handle Phase 2 properly
            session = Ntag424AuthSession(FACTORY_KEY)
            
            try:
                # Phase 2 with multi-frame handling (now implemented in AuthenticateEV2Second)
                session_keys = session.authenticate(card, key_no=0)
                
                print(f"[OK] PHASE 2 SUCCESSFUL!")
                print(f"     Authentication complete!")
                print(f"     Session keys derived")
                print(f"     MAC Key: {session_keys.mac_key.hex().upper()[:32]}...")
                print(f"     Enc Key: {session_keys.enc_key.hex().upper()[:32]}...")
                
                print("\n" + "=" * 80)
                print("SUCCESS!")
                print("=" * 80)
                print("[OK] EV2 authentication works with multi-frame handling!")
                print("     The fix to read additional frames in Phase 2 was correct!")
                return True
                
            except ApduError as e:
                print(f"[FAIL] Phase 2 failed: SW={e.sw1:02X}{e.sw2:02X}")
                
                # Check if Phase 2 returned 91AF (additional frame needed)
                if e.sw2 == 0xAF:
                    print("[INFO] Phase 2 returned SW=91AF (Additional Frame)")
                    print("       This means multi-frame handling is needed")
                    print("       Our code should handle this - may be another issue")
                elif e.sw2 == 0xAE:
                    print("[INFO] Phase 2 returned SW=91AE (Authentication Error)")
                    print("       Protocol still incorrect for Seritag")
                else:
                    print(f"[INFO] Unexpected response: SW={e.sw1:02X}{e.sw2:02X}")
                
                return False
            except Exception as e:
                print(f"[FAIL] Error during Phase 2: {e}")
                import traceback
                traceback.print_exc()
                return False
            
    except NTag242ConnectionError as e:
        print(f"\n[FAIL] CONNECTION FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_phase2_multiframe()
    sys.exit(0 if success else 1)

