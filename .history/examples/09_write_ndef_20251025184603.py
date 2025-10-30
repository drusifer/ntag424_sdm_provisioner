#!/usr/bin/env python3
"""
Example 09: Writing NDEF Messages to Seritag Tags

This example demonstrates how to write NDEF messages to Seritag NTAG424 DNA tags.
NDEF messages can contain URLs that SUN will automatically enhance with
dynamic authentication parameters when scanned.
"""
import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.commands.sun_commands import WriteNdefMessage, build_ndef_uri_record
from ntag424_sdm_provisioner.commands.base import ApduError


def write_ndef_example():
    """Write NDEF message to Seritag tag."""
    try:
        print("--- Example 09: Writing NDEF Messages ---")
        print("Please tap and hold the Seritag NTAG424 DNA tag on the reader...")
        
        with CardManager(0) as card:
            print("\n1. Selecting the PICC application...")
            try:
                select_command = SelectPiccApplication()
                print(f"   EXECUTING: {select_command}")
                select_response = select_command.execute(card)
                print(f"   RESPONSE: {select_response}")
            except ApduError as se:
                if "0x6985" in str(se):
                    print(f"   INFO: Application already selected (SW=6985)")
                else:
                    print(f"   WARNING: {se}")
                    print("   Continuing anyway...")
            
            print("\n2. Getting chip version...")
            version_command = GetChipVersion()
            print(f"   EXECUTING: {version_command}")
            version_info = version_command.execute(card)
            print(f"   RESPONSE: {version_info}")
            
            # Check if this is a Seritag tag
            if version_info.hw_major_version == 48:
                print("\nSUCCESS: Detected Seritag NTAG424 DNA (HW 48.0)")
                print("   SUN will automatically enhance URLs with authentication parameters")
            else:
                print(f"\nINFO: Standard NXP NTAG424 DNA detected (HW {version_info.hw_major_version}.{version_info.hw_minor_version})")
            
            print("\n3. Creating NDEF URI record...")
            
            # Define the base URL - SUN will append authentication parameters
            base_url = "https://example.com/verify"
            print(f"   Base URL: {base_url}")
            print("   SUN will append: ?uid=XXXX&c=YYYY&mac=ZZZZ")
            
            # Build NDEF URI record
            ndef_data = build_ndef_uri_record(base_url)
            print(f"   NDEF data length: {len(ndef_data)} bytes")
            print(f"   NDEF data (hex): {ndef_data.hex().upper()}")
            
            print("\n4. Writing NDEF message to tag...")
            try:
                write_command = WriteNdefMessage(ndef_data)
                print(f"   EXECUTING: {write_command}")
                write_response = write_command.execute(card)
                print(f"   RESPONSE: {write_response}")
                
                print("\nSUCCESS: NDEF message written successfully!")
                
            except ApduError as e:
                print(f"   ERROR: NDEF write failed: {e}")
                
                # Try alternative approaches
                print("\n5. Trying alternative NDEF write approaches...")
                
                # Try writing to different file or with different parameters
                print("   Attempting direct binary write...")
                try:
                    # Try direct binary write command
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
                        print(f"   FAILED: Direct write failed with SW={sw1:02X}{sw2:02X}")
                        
                except Exception as de:
                    print(f"   Direct write error: {de}")
                
                return
            
            print("\n" + "=" * 60)
            print("  NDEF Write Complete")
            print("=" * 60)
            print("Next steps:")
            print("1. Scan the tag with an NFC-enabled smartphone")
            print("2. SUN will automatically enhance the URL with authentication parameters")
            print("3. The enhanced URL will look like:")
            print(f"   {base_url}?uid={version_info.uid.hex().upper()}&c=XXXX&mac=YYYY")
            print("4. Use examples/08_read_sun_url.py to read the enhanced URL")
            print("5. Use examples/07_sun_server_verification.py for server-side verification")
            
    except NTag242ConnectionError as e:
        print(f"\nFAILED: CONNECTION FAILED: {e}", file=sys.stderr)
        print("Make sure the NFC reader is connected and a tag is present.", file=sys.stderr)
    except Exception as e:
        print(f"\nFAILED: UNEXPECTED ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


def write_simple_text_ndef():
    """Alternative: Write simple text NDEF message."""
    try:
        print("\n--- Alternative: Simple Text NDEF ---")
        
        with CardManager(0) as card:
            # Select application
            try:
                SelectPiccApplication().execute(card)
            except ApduError:
                pass  # Continue anyway
            
            # Create simple text NDEF record
            text_data = "Hello from Seritag!"
            
            # NDEF Text record structure
            ndef_record = bytearray()
            ndef_record.append(0x01)  # TNF = Well Known Type
            ndef_record.append(0x01)  # Type Length = 1
            ndef_record.append(len(text_data))  # Payload Length
            ndef_record.append(ord('T'))  # Type = "T" (Text)
            ndef_record.append(0x02)  # Status byte (UTF-8, 2-byte language)
            ndef_record.append(ord('e'))  # Language code byte 1
            ndef_record.append(ord('n'))  # Language code byte 2
            ndef_record.extend(text_data.encode('utf-8'))  # Text payload
            
            # Wrap in NDEF TLV
            ndef_tlv = bytearray()
            ndef_tlv.append(0x03)  # NDEF TLV tag
            ndef_tlv.append(len(ndef_record))  # Length
            ndef_tlv.extend(ndef_record)  # NDEF record
            ndef_tlv.append(0xFE)  # Terminator TLV
            
            print(f"Text NDEF data: {bytes(ndef_tlv).hex().upper()}")
            
            # Try to write text NDEF
            try:
                write_command = WriteNdefMessage(bytes(ndef_tlv))
                write_response = write_command.execute(card)
                print(f"SUCCESS: Text NDEF written: {write_response}")
            except ApduError as e:
                print(f"Text NDEF write failed: {e}")
                
    except Exception as e:
        print(f"Text NDEF error: {e}")


if __name__ == "__main__":
    write_ndef_example()
    
    # Try alternative text NDEF
    print("\n" + "="*60)
    write_simple_text_ndef()
