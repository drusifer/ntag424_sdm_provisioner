#!/usr/bin/env python3
"""
Example 12: Testing Different Keys for Seritag Authentication

This example tests various keys to see if Seritag tags use different
default keys than standard NXP NTAG424 DNA tags.
"""
import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion, AuthenticateEV2First
from ntag424_sdm_provisioner.commands.base import ApduError


def test_different_keys():
    """Test different keys for Seritag authentication."""
    try:
        print("--- Example 12: Testing Different Keys ---")
        print("Please tap and hold the Seritag NTAG424 DNA tag on the reader...")
        
        with CardManager(0) as card:
            print("\n1. Selecting the PICC application...")
            try:
                SelectPiccApplication().execute(card)
                print("   Application selected")
            except ApduError as se:
                if "0x6985" in str(se):
                    print("   Application already selected")
                else:
                    print(f"   Selection warning: {se}")
            
            print("\n2. Getting chip version...")
            version_info = GetChipVersion().execute(card)
            print(f"   Hardware: {version_info.hw_major_version}.{version_info.hw_minor_version}")
            print(f"   UID: {version_info.uid.hex().upper()}")
            
            print("\n3. Testing different keys for authentication...")
            
            # Test different keys
            test_keys = [
                ("Factory (all zeros)", b'\x00' * 16),
                ("All ones", b'\xFF' * 16),
                ("Seritag default", b'Seritag12345678'),  # 16 bytes
                ("NXP default", b'NXP1234567890123'),     # 16 bytes
                ("Blank key", b''),  # Empty key
                ("Simple pattern", b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A\x0B\x0C\x0D\x0E\x0F\x10'),
                ("Reverse pattern", b'\x10\x0F\x0E\x0D\x0C\x0B\x0A\x09\x08\x07\x06\x05\x04\x03\x02\x01'),
                ("UID-based key", version_info.uid + b'\x00' * 9),  # UID + padding
                ("Hardware-based", bytes([version_info.hw_major_version, version_info.hw_minor_version]) + b'\x00' * 14),
            ]
            
            working_keys = []
            
            for key_name, key in test_keys:
                print(f"\n   Testing {key_name}...")
                print(f"   Key: {key.hex().upper() if len(key) > 0 else 'EMPTY'}")
                
                # Test all key numbers (0-4) for this key
                for key_no in range(5):
                    try:
                        cmd1 = AuthenticateEV2First(key_no=key_no)
                        response1 = cmd1.execute(card)
                        print(f"   SUCCESS: Key {key_no} works! Challenge: {response1.challenge.hex().upper()}")
                        working_keys.append((key_name, key, key_no))
                        break
                    except Exception as e:
                        print(f"   FAILED: Key {key_no} - {e}")
                
                # If we found a working key, we can stop testing this key
                if any((key_name, key, k) in working_keys for k in range(5)):
                    continue
            
            print("\n4. Summary of working keys:")
            if working_keys:
                for key_name, key, key_no in working_keys:
                    print(f"   SUCCESS: {key_name} with key number {key_no}")
                    print(f"   Key: {key.hex().upper() if len(key) > 0 else 'EMPTY'}")
            else:
                print("   NO WORKING KEYS FOUND")
                print("   This suggests Seritag uses a different authentication method")
            
            print("\n5. Testing if authentication is required for NDEF operations...")
            
            # Try NDEF operations without authentication
            print("\n   Testing NDEF read without authentication...")
            try:
                read_apdu = [
                    0x90, 0xB0,  # ReadBinary
                    0x00, 0x00,  # Offset 0
                    0x10,        # Read 16 bytes
                    0x00         # Le
                ]
                
                read_data, sw1, sw2 = card.send_apdu(read_apdu, use_escape=True)
                print(f"   NDEF read result: SW={sw1:02X}{sw2:02X}")
                
                if (sw1, sw2) == (0x90, 0x00):
                    print(f"   SUCCESS: NDEF readable without authentication!")
                    print(f"   Data: {bytes(read_data).hex().upper()}")
                else:
                    print(f"   FAILED: NDEF requires authentication - SW={sw1:02X}{sw2:02X}")
                    
            except Exception as e:
                print(f"   ERROR: NDEF read test - {e}")
            
            # Try NDEF write without authentication
            print("\n   Testing NDEF write without authentication...")
            try:
                # Simple test data
                test_data = [0x03, 0x01, 0x00, 0xFE]  # Empty NDEF TLV
                
                write_apdu = [
                    0x90, 0xD6,  # WriteBinary
                    0x00, 0x00,  # Offset 0
                    len(test_data),  # Data length
                ] + test_data + [0x00]  # Data + Le
                
                _, sw1, sw2 = card.send_apdu(write_apdu, use_escape=True)
                print(f"   NDEF write result: SW={sw1:02X}{sw2:02X}")
                
                if (sw1, sw2) == (0x90, 0x00):
                    print(f"   SUCCESS: NDEF writable without authentication!")
                else:
                    print(f"   FAILED: NDEF write failed - SW={sw1:02X}{sw2:02X}")
                    
            except Exception as e:
                print(f"   ERROR: NDEF write test - {e}")
            
            print("\n" + "=" * 60)
            print("  Key Testing Complete")
            print("=" * 60)
            print("Key findings:")
            if working_keys:
                print("- Seritag tags use different keys than factory defaults")
                print("- Authentication is possible with correct keys")
            else:
                print("- Seritag tags may not use standard EV2 authentication")
                print("- SUN might work without authentication")
                print("- NDEF operations might not require authentication")
            
    except NTag242ConnectionError as e:
        print(f"\nFAILED: CONNECTION FAILED: {e}", file=sys.stderr)
    except Exception as e:
        print(f"\nFAILED: UNEXPECTED ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_different_keys()
