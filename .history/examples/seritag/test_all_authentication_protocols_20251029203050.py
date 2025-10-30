#!/usr/bin/env python3
"""
Comprehensive Authentication Protocol Investigation

Tests all possible authentication protocols on Seritag tags:
- EV2 Authentication (standard)
- EV2 Variations (modified for Seritag)
- LRP Authentication (Lightweight Remote Protocol)
- Legacy Authentication (EV1-like, command 0x70)
- Command 0x51 (Seritag-specific)
- Alternative protocols
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
from Crypto.Hash import CMAC
import logging

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


class AuthenticationTester:
    """Test all authentication protocol variants."""
    
    def __init__(self, card):
        self.card = card
        self.key = FACTORY_KEY
        self.results = {}
        
    def test_ev2_standard(self):
        """Test standard EV2 protocol."""
        print("\n" + "=" * 80)
        print("TEST: EV2 Standard Protocol")
        print("=" * 80)
        print()
        print("Testing with delay handling...")
        
        try:
            # Phase 1 (with delay handling)
            max_retries = 3
            challenge_response = None
            
            for attempt in range(max_retries):
                try:
                    cmd1 = AuthenticateEV2First(key_no=0)
                    challenge_response = cmd1.execute(self.card)
                    break
                except ApduError as e:
                    if e.sw2 == 0xAD:  # Authentication Delay
                        if attempt < max_retries - 1:
                            wait_time = 1.0 * (attempt + 1)
                            print(f"  [INFO] Authentication delay (attempt {attempt+1}/{max_retries})")
                            print(f"         Waiting {wait_time}s...")
                            time.sleep(wait_time)
                        else:
                            print(f"  [INFO] Authentication delay persists after {max_retries} attempts")
                            print(f"         May need fresh tap to reset delay counter")
                            raise
                    else:
                        raise
            
            if challenge_response is None:
                print("[FAIL] Could not get Phase 1 challenge")
                self.results['ev2_standard'] = False
                return False
            
            encrypted_rndb = challenge_response.challenge
            
            # Decrypt RndB
            cipher = AES.new(self.key, AES.MODE_ECB)
            rndb = cipher.decrypt(encrypted_rndb)
            
            # Generate RndA and encrypt response
            rnda = get_random_bytes(16)
            rndb_rotated = rndb[1:] + rndb[0:1]
            plaintext = rnda + rndb_rotated
            encrypted_response = cipher.encrypt(plaintext)
            
            # Phase 2: Standard format
            apdu = [0x90, 0xAF, 0x00, 0x00, 0x20] + list(encrypted_response) + [0x00]
            data, sw1, sw2 = self.card.send_apdu(apdu, use_escape=True)
            
            if (sw1, sw2) == SW_OK:
                print("[OK] EV2 Standard works!")
                self.results['ev2_standard'] = True
                return True
            else:
                print(f"[FAIL] SW={sw1:02X}{sw2:02X}")
                self.results['ev2_standard'] = False
                return False
                
        except Exception as e:
            print(f"[FAIL] Error: {e}")
            self.results['ev2_standard'] = False
            return False
    
    def test_ev2_variations(self):
        """Test EV2 protocol variations."""
        print("\n" + "=" * 80)
        print("TEST: EV2 Protocol Variations")
        print("=" * 80)
        
            # Phase 1 (with delay handling)
            try:
                try:
                    cmd1 = AuthenticateEV2First(key_no=0)
                    challenge_response = cmd1.execute(self.card)
                except ApduError as e:
                    if e.sw2 == 0xAD:  # Authentication Delay
                        print("  [INFO] Authentication delay - waiting 1s...")
                        time.sleep(1.0)
                        cmd1 = AuthenticateEV2First(key_no=0)
                        challenge_response = cmd1.execute(self.card)
                    else:
                        raise
                encrypted_rndb = challenge_response.challenge
            
            cipher = AES.new(self.key, AES.MODE_ECB)
            rndb = cipher.decrypt(encrypted_rndb)
            rnda = get_random_bytes(16)
            
            variations = [
                {
                    "name": "No rotation (RndB as-is)",
                    "data": rnda + rndb,
                },
                {
                    "name": "Right rotate RndB",
                    "data": rnda + (rndb[-1:] + rndb[:-1]),
                },
                {
                    "name": "Rotate by 2 bytes (left)",
                    "data": rnda + (rndb[2:] + rndb[:2]),
                },
                {
                    "name": "Reverse RndA",
                    "data": rnda[::-1] + (rndb[1:] + rndb[0:1]),
                },
            ]
            
            for var in variations:
                try:
                    encrypted = cipher.encrypt(var['data'])
                    apdu = [0x90, 0xAF, 0x00, 0x00, 0x20] + list(encrypted) + [0x00]
                    data, sw1, sw2 = self.card.send_apdu(apdu, use_escape=True)
                    
                    if (sw1, sw2) == SW_OK:
                        print(f"[OK] {var['name']} works!")
                        self.results[f"ev2_{var['name'].lower().replace(' ', '_')}"] = True
                    else:
                        print(f"[FAIL] {var['name']}: SW={sw1:02X}{sw2:02X}")
                        self.results[f"ev2_{var['name'].lower().replace(' ', '_')}"] = False
                except Exception as e:
                    print(f"[FAIL] {var['name']}: Error: {e}")
                    self.results[f"ev2_{var['name'].lower().replace(' ', '_')}"] = False
                    
                # Need fresh Phase 1 for each variation
                # Wait after authentication failures to avoid delay
                time.sleep(0.5)
                try:
                    cmd1 = AuthenticateEV2First(key_no=0)
                    challenge_response = cmd1.execute(self.card)
                except ApduError as e:
                    if e.sw2 == 0xAD:  # Authentication Delay
                        print(f"    [INFO] Authentication delay - waiting 1s...")
                        time.sleep(1.0)
                        cmd1 = AuthenticateEV2First(key_no=0)
                        challenge_response = cmd1.execute(self.card)
                    else:
                        raise
                encrypted_rndb = challenge_response.challenge
                rndb = cipher.decrypt(encrypted_rndb)
                rnda = get_random_bytes(16)
                
        except Exception as e:
            print(f"[FAIL] Phase 1 error: {e}")
            self.results['ev2_variations'] = False
    
    def test_lrp_authentication(self):
        """Test LRP (Lightweight Remote Protocol) authentication."""
        print("\n" + "=" * 80)
        print("TEST: LRP Authentication Protocol")
        print("=" * 80)
        
        # LRP uses same command 0x71 but with PCDcap2 bit 1 set
        try:
            # Phase 1: Set bit 1 of PCDcap2 to request LRP
            # Format: 90 71 00 00 [Lc] [KeyNo] [LenCap] [PCDcap2] [Le]
            # LenCap = 01h (1 byte), PCDcap2 bit 1 = 02h
            key_no = 0x00
            len_cap = 0x01
            pcdcap2 = 0x02  # Bit 1 set = LRP mode
            
            apdu = [0x90, 0x71, 0x00, 0x00, 0x03, key_no, len_cap, pcdcap2, 0x00]
            
            print("  Phase 1: Requesting LRP challenge...")
            data, sw1, sw2 = self.card.send_apdu(apdu, use_escape=True)
            
            if (sw1, sw2) == SW_ADDITIONAL_FRAME:
                print(f"  [OK] Phase 1 response (expecting LRP format): {len(data)} bytes")
                print(f"      Hex: {data.hex().upper()[:32]}...")
                
                # LRP Phase 2 uses MAC instead of encryption
                # Format: 90 AF 00 00 20 [RndA] [MAC] 00
                # MAC = CMAC(SesAuthMACKey, RndA || RndB)
                
                # For now, just try to see what we get
                rnda = get_random_bytes(16)
                mac = b'\x00' * 16  # Placeholder
                
                apdu2 = [0x90, 0xAF, 0x00, 0x00, 0x20] + list(rnda) + list(mac) + [0x00]
                data2, sw1, sw2 = self.card.send_apdu(apdu2, use_escape=True)
                
                if (sw1, sw2) == SW_OK:
                    print(f"  [OK] LRP Phase 2 works!")
                    self.results['lrp'] = True
                else:
                    print(f"  [FAIL] LRP Phase 2: SW={sw1:02X}{sw2:02X}")
                    self.results['lrp'] = False
            else:
                print(f"  [FAIL] LRP Phase 1: SW={sw1:02X}{sw2:02X}")
                self.results['lrp'] = False
                
        except Exception as e:
            print(f"[FAIL] LRP error: {e}")
            self.results['lrp'] = False
    
    def test_legacy_ev1(self):
        """Test legacy EV1-like authentication (command 0x70)."""
        print("\n" + "=" * 80)
        print("TEST: Legacy EV1 Authentication (Command 0x70)")
        print("=" * 80)
        
        test_configs = [
            {"name": "0x70 Basic", "apdu": [0x90, 0x70, 0x00, 0x00, 0x00]},
            {"name": "0x70 with KeyNo", "apdu": [0x90, 0x70, 0x00, 0x00, 0x01, 0x00, 0x00]},
            {"name": "0x70 with data", "apdu": [0x90, 0x70, 0x00, 0x00, 0x10] + [0x00] * 16 + [0x00]},
        ]
        
        for test in test_configs:
            try:
                data, sw1, sw2 = self.card.send_apdu(test['apdu'], use_escape=True)
                print(f"  {test['name']}: SW={sw1:02X}{sw2:02X}")
                
                if (sw1, sw2) == SW_OK or (sw1, sw2) == SW_ADDITIONAL_FRAME:
                    print(f"    [OK] Command recognized!")
                    self.results[f"ev1_{test['name'].lower().replace(' ', '_')}"] = True
                elif (sw1, sw2) == (0x91, 0x1C):
                    print(f"    [INFO] Command not supported")
                    self.results[f"ev1_{test['name'].lower().replace(' ', '_')}"] = False
                else:
                    print(f"    [INFO] Unexpected response")
                    self.results[f"ev1_{test['name'].lower().replace(' ', '_')}"] = False
            except Exception as e:
                print(f"  {test['name']}: Error - {e}")
                self.results[f"ev1_{test['name'].lower().replace(' ', '_')}"] = False
    
    def test_command_0x51_sequences(self):
        """Test command 0x51 in various sequences."""
        print("\n" + "=" * 80)
        print("TEST: Command 0x51 Sequences")
        print("=" * 80)
        
        # Test 0x51 before Phase 1
        print("\n  Before Phase 1:")
        try:
            apdu = [0x90, 0x51, 0x00, 0x00, 0x00]
            data, sw1, sw2 = self.card.send_apdu(apdu, use_escape=True)
            print(f"    0x51: SW={sw1:02X}{sw2:02X}")
            
            if (sw1, sw2) == (0x91, 0xCA):
                print(f"    [INFO] Command recognized (Command Aborted)")
                self.results['0x51_before_phase1'] = 'recognized'
        except Exception as e:
            print(f"    Error: {e}")
        
        # Test 0x51 immediately after Phase 1
        print("\n  Immediately after Phase 1:")
        try:
            try:
                cmd1 = AuthenticateEV2First(key_no=0)
                challenge_response = cmd1.execute(self.card)
            except ApduError as e:
                if e.sw2 == 0xAD:  # Authentication Delay
                    print("    [INFO] Authentication delay - waiting 1s...")
                    time.sleep(1.0)
                    cmd1 = AuthenticateEV2First(key_no=0)
                    challenge_response = cmd1.execute(self.card)
                else:
                    raise
            
            # Send 0x51 immediately
            apdu = [0x90, 0x51, 0x00, 0x00, 0x00]
            data, sw1, sw2 = self.card.send_apdu(apdu, use_escape=True)
            print(f"    0x51 after Phase 1: SW={sw1:02X}{sw2:02X}")
            
            if (sw1, sw2) == SW_OK:
                print(f"    [OK] 0x51 worked after Phase 1!")
                self.results['0x51_after_phase1'] = True
            elif (sw1, sw2) == (0x91, 0xCA):
                print(f"    [INFO] Command recognized but wrong state")
                self.results['0x51_after_phase1'] = 'recognized'
                
                # Try 0x51 with challenge data
                encrypted_rndb = challenge_response.challenge
                apdu2 = [0x90, 0x51, 0x00, 0x00, 0x10] + list(encrypted_rndb) + [0x00]
                data2, sw1, sw2 = self.card.send_apdu(apdu2, use_escape=True)
                print(f"    0x51 with RndB: SW={sw1:02X}{sw2:02X}")
                
                if (sw1, sw2) == SW_OK:
                    print(f"    [OK] 0x51 with challenge data worked!")
                    self.results['0x51_with_challenge'] = True
                else:
                    self.results['0x51_with_challenge'] = False
            else:
                self.results['0x51_after_phase1'] = False
        except Exception as e:
            print(f"    Error: {e}")
            self.results['0x51_after_phase1'] = False
    
    def test_alternative_commands(self):
        """Test alternative authentication-related commands."""
        print("\n" + "=" * 80)
        print("TEST: Alternative Authentication Commands")
        print("=" * 80)
        
        # Test various command codes
        test_codes = [
            (0x72, "AuthenticateEV2NonFirst"),
            (0x73, "AuthenticateLRPFirst"),
            (0x74, "AuthenticateLRPNonFirst"),
            (0x75, "Alternative auth"),
            (0x76, "Alternative auth 2"),
            (0x77, "Alternative auth 3"),
            (0x78, "Alternative auth 4"),
            (0x79, "Alternative auth 5"),
        ]
        
        for cmd_code, name in test_codes:
            try:
                apdu = [0x90, cmd_code, 0x00, 0x00, 0x00]
                data, sw1, sw2 = self.card.send_apdu(apdu, use_escape=True)
                
                if (sw1, sw2) == (0x91, 0x1C):
                    print(f"  {name:30s} (0x{cmd_code:02X}): Not supported")
                elif (sw1, sw2) == (0x91, 0xCA):
                    print(f"  {name:30s} (0x{cmd_code:02X}): Recognized! SW={sw1:02X}{sw2:02X}")
                    self.results[f'cmd_{cmd_code:02x}'] = 'recognized'
                elif (sw1, sw2) == (0x91, 0x7E):
                    print(f"  {name:30s} (0x{cmd_code:02X}): Length Error (may need data) SW={sw1:02X}{sw2:02X}")
                    self.results[f'cmd_{cmd_code:02x}'] = 'length_error'
                elif (sw1, sw2) == SW_OK or (sw1, sw2) == SW_ADDITIONAL_FRAME:
                    print(f"  {name:30s} (0x{cmd_code:02X}): SUCCESS! SW={sw1:02X}{sw2:02X}")
                    self.results[f'cmd_{cmd_code:02x}'] = True
                else:
                    print(f"  {name:30s} (0x{cmd_code:02X}): SW={sw1:02X}{sw2:02X}")
                    self.results[f'cmd_{cmd_code:02x}'] = False
            except Exception as e:
                print(f"  {name:30s} (0x{cmd_code:02X}): Error - {e}")
                self.results[f'cmd_{cmd_code:02x}'] = False
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("INVESTIGATION SUMMARY")
        print("=" * 80)
        
        success_count = sum(1 for v in self.results.values() if v is True)
        recognized_count = sum(1 for v in self.results.values() if v == 'recognized')
        total_count = len(self.results)
        
        print(f"\nTotal tests: {total_count}")
        print(f"Successful: {success_count}")
        print(f"Recognized: {recognized_count}")
        
        if success_count > 0:
            print("\n[OK] WORKING PROTOCOLS:")
            for name, result in self.results.items():
                if result is True:
                    print(f"  [OK] {name}")
        
        if recognized_count > 0:
            print("\n[INFO] RECOGNIZED COMMANDS:")
            for name, result in self.results.items():
                if result == 'recognized':
                    print(f"  [INFO] {name}")
        
        if success_count == 0:
            print("\n[INFO] No working authentication protocol found")
            print("       All standard protocols fail with SW=91AE")
            print("       Command 0x51 is recognized but parameters unknown")
            print("\nNext steps:")
            print("  1. Continue investigating command 0x51 parameters")
            print("  2. Review Seritag documentation for custom protocols")
            print("  3. Consider static URL approach (already works)")


def main():
    """Run comprehensive authentication tests."""
    print("=" * 80)
    print("COMPREHENSIVE AUTHENTICATION PROTOCOL INVESTIGATION")
    print("=" * 80)
    print()
    print("Testing all possible authentication protocols on Seritag tags:")
    print("  - EV2 Standard")
    print("  - EV2 Variations")
    print("  - LRP Authentication")
    print("  - Legacy EV1 (0x70)")
    print("  - Command 0x51")
    print("  - Alternative commands")
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
            
            tester = AuthenticationTester(card)
            
            # Run all tests
            tester.test_ev2_standard()
            tester.test_ev2_variations()
            tester.test_lrp_authentication()
            tester.test_legacy_ev1()
            tester.test_command_0x51_sequences()
            tester.test_alternative_commands()
            
            # Print summary
            tester.print_summary()
            
    except NTag242ConnectionError as e:
        print(f"\n[FAIL] CONNECTION FAILED: {e}")
        print("Make sure NFC reader is connected and tag is present.")
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

