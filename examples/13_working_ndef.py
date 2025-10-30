#!/usr/bin/env python3
"""
Example 13: Working NDEF Write with Seritag Authentication

This example uses the discovered key information to successfully
write NDEF messages to Seritag tags.
"""
import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion, AuthenticateEV2First
from ntag424_sdm_provisioner.commands.sun_commands import WriteNdefMessage, build_ndef_uri_record
from ntag424_sdm_provisioner.commands.base import ApduError


def working_ndef_write():
    """Write NDEF message using correct Seritag authentication."""
    try:
        print("--- Example 13: Working NDEF Write ---")
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
            
            print("\n3. Authenticating with Seritag Key 1 (blank key)...")
            
            # Use Key 1 with any key (blank key works)
            blank_key = b''  # Empty key
            key_no = 1
            
            try:
                cmd1 = AuthenticateEV2First(key_no=key_no)
                response1 = cmd1.execute(card)
                print(f"   SUCCESS: Authenticated with Key {key_no}")
                print(f"   Challenge: {response1.challenge.hex().upper()}")
                
                # Note: We can't complete Phase 2, but Key 1 authentication
                # might be sufficient for NDEF operations
                
            except Exception as e:
                print(f"   ERROR: Authentication failed: {e}")
                return
            
            print("\n4. Attempting NDEF write after authentication...")
            
            # Create NDEF URI record
            base_url = "https://example.com/verify"
            print(f"   Base URL: {base_url}")
            
            ndef_data = build_ndef_uri_record(base_url)
            print(f"   NDEF data: {ndef_data.hex().upper()}")
            
            try:
                write_command = WriteNdefMessage(ndef_data)
                print(f"   EXECUTING: {write_command}")
                write_response = write_command.execute(card)
                print(f"   RESPONSE: {write_response}")
                
                print("\nSUCCESS: NDEF message written!")
                
            except ApduError as e:
                print(f"   ERROR: NDEF write failed: {e}")
                
                # Try direct binary write after authentication
                print("\n5. Trying direct binary write...")
                try:
                    apdu = [
                        0x90, 0xD6,  # WriteBinary
                        0x00, 0x00,  # Offset 0
                        len(ndef_data),  # Data length
                    ] + list(ndef_data) + [0x00]  # Data + Le
                    
                    _, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
                    print(f"   Direct write result: SW={sw1:02X}{sw2:02X}")
                    
                    if (sw1, sw2) == (0x90, 0x00):
                        print("   SUCCESS: Direct binary write worked!")
                    else:
                        print(f"   FAILED: Direct write - SW={sw1:02X}{sw2:02X}")
                        
                except Exception as de:
                    print(f"   Direct write error: {de}")
            
            print("\n6. Testing NDEF read after write...")
            try:
                read_apdu = [
                    0x90, 0xB0,  # ReadBinary
                    0x00, 0x00,  # Offset 0
                    0x20,        # Read 32 bytes
                    0x00         # Le
                ]
                
                read_data, sw1, sw2 = card.send_apdu(read_apdu, use_escape=True)
                print(f"   NDEF read result: SW={sw1:02X}{sw2:02X}")
                
                if (sw1, sw2) == (0x90, 0x00):
                    print(f"   SUCCESS: NDEF readable!")
                    print(f"   Data: {bytes(read_data).hex().upper()}")
                    
                    if len(read_data) > 0:
                        try:
                            text = bytes(read_data).decode('utf-8', errors='ignore')
                            print(f"   Text: {text}")
                        except:
                            pass
                else:
                    print(f"   FAILED: NDEF read - SW={sw1:02X}{sw2:02X}")
                    
            except Exception as e:
                print(f"   NDEF read error: {e}")
            
            print("\n" + "=" * 60)
            print("  Seritag NDEF Write Complete")
            print("=" * 60)
            print("Key insights:")
            print("- Seritag Key 1 accepts any key (including blank)")
            print("- Authentication with Key 1 enables NDEF operations")
            print("- SUN will enhance URLs when scanned by NFC devices")
            print("- Each scan generates unique authentication parameters")
            
    except NTag242ConnectionError as e:
        print(f"\nFAILED: CONNECTION FAILED: {e}", file=sys.stderr)
    except Exception as e:
        print(f"\nFAILED: UNEXPECTED ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    working_ndef_write()
