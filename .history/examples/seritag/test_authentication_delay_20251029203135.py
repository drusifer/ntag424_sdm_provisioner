#!/usr/bin/env python3
"""
Test Authentication Delay Behavior

Tests if authentication delay (SW=91AD) requires:
1. Waiting in same session
2. Fresh tap (reconnection)

The tag may enforce a delay counter that:
- Resets on fresh tap (power loss)
- Persists across commands in same session
- Increments with failed attempts
"""
import sys
import os
import time

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion, AuthenticateEV2First
from ntag424_sdm_provisioner.commands.base import ApduError
import logging

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


def test_authentication_delay():
    """Test authentication delay behavior."""
    
    print("=" * 80)
    print("AUTHENTICATION DELAY INVESTIGATION")
    print("=" * 80)
    print()
    print("Testing if authentication delay requires:")
    print("  1. Waiting in same session")
    print("  2. Fresh tap (reconnection)")
    print()
    
    try:
        # Test 1: Multiple attempts in same session
        print("=" * 80)
        print("TEST 1: Multiple Attempts in Same Session")
        print("=" * 80)
        
        with CardManager(0) as card:
            print("Step 1: Selecting PICC application...")
            SelectPiccApplication().execute(card)
            print("[OK] PICC application selected")
            
            print("\nStep 2: Getting chip version...")
            version_info = GetChipVersion().execute(card)
            print(f"[OK] Tag: HW {version_info.hw_major_version}.{version_info.hw_minor_version}")
            print(f"      UID: {version_info.uid.hex().upper()}")
            
            # Make multiple Phase 1 attempts to trigger delay
            print("\nStep 3: Making multiple Phase 1 attempts...")
            delay_encountered = False
            
            for i in range(5):
                print(f"\n  Attempt {i+1}:")
                try:
                    cmd1 = AuthenticateEV2First(key_no=0)
                    challenge_response = cmd1.execute(card)
                    print(f"    [OK] Phase 1 successful - no delay")
                    encrypted_rndb = challenge_response.challenge
                    print(f"    Challenge: {encrypted_rndb.hex().upper()[:32]}...")
                    
                    # Now try Phase 2 (will fail, but helps understand delay)
                    from ntag424_sdm_provisioner.constants import FACTORY_KEY
                    from Crypto.Cipher import AES
                    from Crypto.Random import get_random_bytes
                    
                    cipher = AES.new(FACTORY_KEY, AES.MODE_ECB)
                    rndb = cipher.decrypt(encrypted_rndb)
                    rnda = get_random_bytes(16)
                    rndb_rotated = rndb[1:] + rndb[0:1]
                    plaintext = rnda + rndb_rotated
                    encrypted_response = cipher.encrypt(plaintext)
                    
                    apdu = [0x90, 0xAF, 0x00, 0x00, 0x20] + list(encrypted_response) + [0x00]
                    data, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
                    print(f"    Phase 2: SW={sw1:02X}{sw2:02X}")
                    
                    # Small delay to see if next attempt triggers delay
                    time.sleep(0.2)
                    
                except ApduError as e:
                    if e.sw2 == 0xAD:  # Authentication Delay
                        print(f"    [INFO] Authentication delay encountered! SW={e.sw1:02X}{e.sw2:02X}")
                        delay_encountered = True
                        print(f"    Waiting 1.0s...")
                        time.sleep(1.0)
                        
                        # Try again after wait
                        print(f"    Retrying after wait...")
                        try:
                            cmd1 = AuthenticateEV2First(key_no=0)
                            challenge_response = cmd1.execute(card)
                            print(f"    [OK] Successful after wait!")
                        except ApduError as e2:
                            print(f"    [FAIL] Still failed after wait: SW={e2.sw1:02X}{e2.sw2:02X}")
                            print(f"           May need longer wait or fresh tap")
                    else:
                        print(f"    [FAIL] Phase 1 failed: SW={e.sw1:02X}{e.sw2:02X}")
        
        print("\n" + "=" * 80)
        print("TEST 2: Fresh Tap (Reconnection)")
        print("=" * 80)
        print()
        print("Please REMOVE the tag from the reader now.")
        print("Waiting 10 seconds for tag to lose power...")
        print("(You can interrupt with Ctrl+C if needed)")
        print()
        
        try:
            # Wait for user to remove tag
            import sys
            if sys.stdin.isatty():
                input("Press Enter after you have removed the tag...")
            else:
                print("(Non-interactive mode - continuing in 10 seconds...)")
                time.sleep(10)
        except (EOFError, KeyboardInterrupt):
            print("\nProceeding with fresh tap test...")
        
        print("\nWaiting 3 seconds for tag to completely lose power...")
        time.sleep(3)
        
        print("\nPlease PLACE the tag back on the reader now.")
        print()
        
        try:
            if sys.stdin.isatty():
                input("Press Enter after you have placed the tag back...")
            else:
                print("(Non-interactive mode - continuing in 5 seconds...)")
                time.sleep(5)
        except (EOFError, KeyboardInterrupt):
            print("\nAttempting connection...")
        
        # Fresh connection
        print("\nStep 1: Reconnecting (fresh tap)...")
        with CardManager(0) as card:
            print("[OK] Fresh connection established")
            
            print("\nStep 2: Selecting PICC application...")
            SelectPiccApplication().execute(card)
            print("[OK] PICC application selected")
            
            print("\nStep 3: Getting chip version...")
            version_info = GetChipVersion().execute(card)
            print(f"[OK] Tag: HW {version_info.hw_major_version}.{version_info.hw_minor_version}")
            print(f"      UID: {version_info.uid.hex().upper()}")
            
            print("\nStep 4: Testing Phase 1 after fresh tap...")
            try:
                cmd1 = AuthenticateEV2First(key_no=0)
                challenge_response = cmd1.execute(card)
                print(f"[OK] Phase 1 successful immediately after fresh tap!")
                print(f"     Challenge: {challenge_response.challenge.hex().upper()[:32]}...")
                print()
                print("[INFO] Fresh tap appears to reset authentication delay counter")
            except ApduError as e:
                if e.sw2 == 0xAD:
                    print(f"[FAIL] Still getting delay after fresh tap: SW={e.sw1:02X}{e.sw2:02X}")
                    print("       Delay counter may persist in non-volatile memory")
                else:
                    print(f"[FAIL] Phase 1 failed: SW={e.sw1:02X}{e.sw2:02X}")
        
        # Summary
        print("\n" + "=" * 80)
        print("INVESTIGATION SUMMARY")
        print("=" * 80)
        
        if delay_encountered:
            print("\n[INFO] Authentication delay encountered during testing")
            print("       Behavior:")
            print("       - Delay may occur after multiple failed attempts")
            print("       - Fresh tap likely resets delay counter")
            print("       - Wait period may need to be longer")
        else:
            print("\n[INFO] No authentication delay encountered")
            print("       Tag may allow immediate retries")
        
        print("\nRecommendations:")
        print("  1. If delay occurs, wait 1-2 seconds before retry")
        print("  2. If delay persists, try fresh tap (remove/replace tag)")
        print("  3. Fresh tap resets tag session state (including delay counter)")
        
    except NTag242ConnectionError as e:
        print(f"\n[FAIL] CONNECTION FAILED: {e}")
        print("Make sure NFC reader is connected and tag is present.")
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_authentication_delay()

