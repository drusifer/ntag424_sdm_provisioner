#!/usr/bin/env python3
"""
Example 11: Proper NDEF File Initialization for Seritag

This example shows how to properly initialize the NDEF file on Seritag tags
before writing NDEF messages. Seritag tags may require file configuration
before NDEF operations are possible.
"""
import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.commands.base import ApduError


def initialize_ndef_file():
    """Initialize NDEF file on Seritag tag."""
    try:
        print("--- Example 11: NDEF File Initialization ---")
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
            
            print("\n3. Attempting NDEF file initialization...")
            
            # Try to create/configure NDEF file
            # NDEF file is typically file number 2
            ndef_file_no = 0x02
            
            # Approach 1: Try CreateStdDataFile command
            print("\n   Approach 1: CreateStdDataFile for NDEF...")
            try:
                # Create standard data file for NDEF
                create_apdu = [
                    0x90, 0xCD,  # CreateStdDataFile
                    0x00, 0x00,  # P1, P2
                    0x0F,        # Data length
                    ndef_file_no,  # File number
                    0x00, 0x00, 0x00, 0x00,  # File size (0 = use default)
                    0x00,        # Communication mode (Plain)
                    0x00, 0x00, 0x00, 0x00,  # Access rights
                    0x00, 0x00, 0x00, 0x00,  # Access rights
                    0x00         # Le
                ]
                
                _, sw1, sw2 = card.send_apdu(create_apdu, use_escape=True)
                print(f"   CreateStdDataFile result: SW={sw1:02X}{sw2:02X}")
                
                if (sw1, sw2) == (0x90, 0x00):
                    print("   SUCCESS: NDEF file created!")
                else:
                    print(f"   FAILED: CreateStdDataFile - SW={sw1:02X}{sw2:02X}")
                    
            except Exception as e:
                print(f"   ERROR: CreateStdDataFile - {e}")
            
            # Approach 2: Try ChangeFileSettings command
            print("\n   Approach 2: ChangeFileSettings for NDEF...")
            try:
                # Change file settings to enable NDEF
                settings_apdu = [
                    0x90, 0x5F,  # ChangeFileSettings
                    0x00, 0x00,  # P1, P2
                    0x05,        # Data length
                    ndef_file_no,  # File number
                    0x00,        # Communication mode (Plain)
                    0x00, 0x00, 0x00, 0x00,  # Access rights
                    0x00         # Le
                ]
                
                _, sw1, sw2 = card.send_apdu(settings_apdu, use_escape=True)
                print(f"   ChangeFileSettings result: SW={sw1:02X}{sw2:02X}")
                
                if (sw1, sw2) == (0x90, 0x00):
                    print("   SUCCESS: NDEF file settings changed!")
                else:
                    print(f"   FAILED: ChangeFileSettings - SW={sw1:02X}{sw2:02X}")
                    
            except Exception as e:
                print(f"   ERROR: ChangeFileSettings - {e}")
            
            # Approach 3: Try GetFileSettings to see current state
            print("\n   Approach 3: Check current file settings...")
            try:
                get_settings_apdu = [
                    0x90, 0xF5,  # GetFileSettings
                    0x00, 0x00,  # P1, P2
                    ndef_file_no,  # File number
                    0x00         # Le
                ]
                
                settings_data, sw1, sw2 = card.send_apdu(get_settings_apdu, use_escape=True)
                print(f"   GetFileSettings result: SW={sw1:02X}{sw2:02X}")
                
                if (sw1, sw2) == (0x90, 0x00):
                    print(f"   SUCCESS: File settings retrieved!")
                    print(f"   Settings data: {bytes(settings_data).hex().upper()}")
                    
                    # Parse settings
                    if len(settings_data) >= 5:
                        comm_mode = settings_data[0]
                        access_rights = settings_data[1:5]
                        print(f"   Communication mode: 0x{comm_mode:02X}")
                        print(f"   Access rights: {access_rights.hex().upper()}")
                else:
                    print(f"   FAILED: GetFileSettings - SW={sw1:02X}{sw2:02X}")
                    
            except Exception as e:
                print(f"   ERROR: GetFileSettings - {e}")
            
            # Test NDEF read after initialization attempts
            print("\n4. Testing NDEF read after initialization...")
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
                    print(f"   SUCCESS: NDEF file is readable!")
                    print(f"   Data: {bytes(read_data).hex().upper()}")
                    
                    if len(read_data) > 0:
                        try:
                            text = bytes(read_data).decode('utf-8', errors='ignore')
                            print(f"   Text: {text}")
                        except:
                            pass
                else:
                    print(f"   FAILED: NDEF file still not readable - SW={sw1:02X}{sw2:02X}")
                    
            except Exception as e:
                print(f"   ERROR: NDEF read test - {e}")
            
            print("\n" + "=" * 60)
            print("  NDEF Initialization Complete")
            print("=" * 60)
            print("Summary:")
            print("- Seritag tags may require explicit NDEF file initialization")
            print("- Standard NTAG424 DNA commands may not work with Seritag")
            print("- SUN might be pre-configured and not require manual NDEF setup")
            print("- Further investigation needed for Seritag-specific commands")
            
    except NTag242ConnectionError as e:
        print(f"\nFAILED: CONNECTION FAILED: {e}", file=sys.stderr)
    except Exception as e:
        print(f"\nFAILED: UNEXPECTED ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    initialize_ndef_file()
