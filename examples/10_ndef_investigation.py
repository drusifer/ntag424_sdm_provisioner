#!/usr/bin/env python3
"""
Example 10: NDEF File Initialization and Writing

This example investigates why NDEF writing fails with Seritag tags
and tries different approaches to initialize and write NDEF messages.
"""
import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.commands.base import ApduError


def investigate_ndef_file():
    """Investigate NDEF file structure and initialization."""
    try:
        print("--- Example 10: NDEF File Investigation ---")
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
            
            print("\n3. Investigating NDEF file (File 2)...")
            
            # Try different read approaches
            test_offsets = [0, 1, 2, 4, 8, 16]
            test_lengths = [1, 4, 8, 16, 32, 64]
            
            for offset in test_offsets:
                for length in test_lengths:
                    try:
                        # Try to read from NDEF file
                        apdu = [
                            0x90, 0xB0,  # ReadBinary
                            (offset >> 8) & 0xFF,  # Offset high
                            offset & 0xFF,         # Offset low
                            length,                 # Read length
                            0x00                   # Le
                        ]
                        
                        data, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
                        
                        if (sw1, sw2) == (0x90, 0x00):
                            print(f"   SUCCESS: Read offset {offset}, length {length}")
                            print(f"   Data: {bytes(data).hex().upper()}")
                            if len(data) > 0:
                                try:
                                    text = bytes(data).decode('utf-8', errors='ignore')
                                    print(f"   Text: {text}")
                                except:
                                    pass
                            break
                        else:
                            print(f"   FAILED: Read offset {offset}, length {length}, SW={sw1:02X}{sw2:02X}")
                            
                    except Exception as e:
                        print(f"   ERROR: Read offset {offset}, length {length}: {e}")
                
                # If we found readable data, stop trying other offsets
                if (sw1, sw2) == (0x90, 0x00) and len(data) > 0:
                    break
            
            print("\n4. Trying NDEF file initialization...")
            
            # Try to initialize NDEF file with different approaches
            init_approaches = [
                # Approach 1: Write NDEF TLV header
                {
                    'name': 'NDEF TLV Header',
                    'data': [0x03, 0x00, 0xFE]  # Empty NDEF TLV
                },
                # Approach 2: Write simple URI
                {
                    'name': 'Simple URI',
                    'data': [0x03, 0x0A, 0x01, 0x01, 0x08, 0x55, 0x04, 0x65, 0x78, 0x61, 0x6D, 0x70, 0x6C, 0x65, 0xFE]
                },
                # Approach 3: Write minimal NDEF
                {
                    'name': 'Minimal NDEF',
                    'data': [0x03, 0x01, 0x00, 0xFE]  # Empty NDEF record
                }
            ]
            
            for approach in init_approaches:
                print(f"\n   Trying {approach['name']}...")
                try:
                    apdu = [
                        0x90, 0xD6,  # WriteBinary
                        0x00, 0x00,  # Offset 0
                        len(approach['data']),  # Data length
                    ] + approach['data'] + [0x00]  # Data + Le
                    
                    _, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
                    print(f"   Result: SW={sw1:02X}{sw2:02X}")
                    
                    if (sw1, sw2) == (0x90, 0x00):
                        print(f"   SUCCESS: {approach['name']} written!")
                        
                        # Try to read it back
                        try:
                            read_apdu = [
                                0x90, 0xB0,  # ReadBinary
                                0x00, 0x00,  # Offset 0
                                len(approach['data']),  # Read length
                                0x00         # Le
                            ]
                            
                            read_data, read_sw1, read_sw2 = card.send_apdu(read_apdu, use_escape=True)
                            if (read_sw1, read_sw2) == (0x90, 0x00):
                                print(f"   Read back: {bytes(read_data).hex().upper()}")
                            else:
                                print(f"   Read back failed: SW={read_sw1:02X}{read_sw2:02X}")
                        except Exception as re:
                            print(f"   Read back error: {re}")
                        
                        break
                    else:
                        print(f"   FAILED: {approach['name']} - SW={sw1:02X}{sw2:02X}")
                        
                except Exception as e:
                    print(f"   ERROR: {approach['name']} - {e}")
            
            print("\n5. Checking file settings...")
            
            # Try to read file settings
            try:
                settings_apdu = [
                    0x90, 0xF5,  # GetFileSettings
                    0x00, 0x00,  # P1, P2
                    0x02,        # File number (NDEF file)
                    0x00        # Le
                ]
                
                settings_data, sw1, sw2 = card.send_apdu(settings_apdu, use_escape=True)
                print(f"   File settings: SW={sw1:02X}{sw2:02X}")
                if (sw1, sw2) == (0x90, 0x00):
                    print(f"   Settings data: {bytes(settings_data).hex().upper()}")
                else:
                    print(f"   File settings read failed")
                    
            except Exception as e:
                print(f"   File settings error: {e}")
            
            print("\n" + "=" * 60)
            print("  NDEF Investigation Complete")
            print("=" * 60)
            print("Findings:")
            print("- Seritag tags may require different NDEF initialization")
            print("- Error 0x911C suggests file access or permission issue")
            print("- May need to configure file settings before writing")
            print("- SUN might be pre-configured differently than standard NTAG424")
            
    except NTag242ConnectionError as e:
        print(f"\nFAILED: CONNECTION FAILED: {e}", file=sys.stderr)
    except Exception as e:
        print(f"\nFAILED: UNEXPECTED ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    investigate_ndef_file()
