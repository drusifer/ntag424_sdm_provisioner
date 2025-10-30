#!/usr/bin/env python3
"""
Example 08: Reading SUN-Enhanced URLs

This example demonstrates how to read the current NDEF message from a Seritag tag
to see the SUN-enhanced URL with dynamic authentication parameters.

SUN automatically appends parameters like ?uid=XXXX&c=YYYY&mac=ZZZZ to URLs
when the tag is scanned by an NFC device.
"""
import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.commands.sun_commands import ReadNdefMessage, parse_sun_url
from ntag424_sdm_provisioner.commands.base import ApduError


def read_sun_url():
    """Read the current NDEF message to see SUN-enhanced URL."""
    try:
        print("--- Example 08: Reading SUN-Enhanced URLs ---")
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
                print("   SUN will enhance URLs with dynamic authentication parameters")
            else:
                print(f"\nINFO: Standard NXP NTAG424 DNA detected (HW {version_info.hw_major_version}.{version_info.hw_minor_version})")
                print("   SUN may not be available")
            
            print("\n3. Reading current NDEF message...")
            try:
                read_command = ReadNdefMessage(max_length=256)
                print(f"   EXECUTING: {read_command}")
                ndef_data = read_command.execute(card)
                
                print(f"   NDEF data (hex): {ndef_data.hex().upper()}")
                print(f"   NDEF data (bytes): {len(ndef_data)} bytes")
                
                if len(ndef_data) > 0:
                    # Try to parse as text to see the URL
                    try:
                        ndef_text = ndef_data.decode('utf-8', errors='ignore')
                        print(f"   NDEF as text: {ndef_text}")
                        
                        # Look for URLs in the text
                        import re
                        url_pattern = r'https?://[^\s]+'
                        urls = re.findall(url_pattern, ndef_text)
                        
                        if urls:
                            print(f"\n4. Found URLs in NDEF message:")
                            for i, url in enumerate(urls, 1):
                                print(f"   URL {i}: {url}")
                                
                                # Parse SUN parameters if present
                                sun_data = parse_sun_url(url)
                                if sun_data:
                                    print(f"   SUN parameters:")
                                    for key, value in sun_data.items():
                                        print(f"     {key}: {value}")
                                else:
                                    print(f"   No SUN parameters found (base URL)")
                        else:
                            print(f"\n4. No URLs found in NDEF message")
                            print(f"   Raw data: {ndef_data}")
                            
                    except Exception as e:
                        print(f"   Error parsing NDEF text: {e}")
                        print(f"   Raw data: {ndef_data}")
                else:
                    print(f"   NDEF message is empty")
                    
            except ApduError as e:
                print(f"   ERROR: NDEF read failed: {e}")
                return
            
            print("\n" + "=" * 60)
            print("  SUN URL Reading Complete")
            print("=" * 60)
            print("How SUN works:")
            print("1. Base URL is written to NDEF message")
            print("2. When scanned by NFC device, SUN automatically appends:")
            print("   - ?uid=XXXX (tag UID)")
            print("   - &c=YYYY (scan counter)")
            print("   - &mac=ZZZZ (authentication MAC)")
            print("3. Each scan generates a unique URL")
            print("4. Server can verify authenticity using the parameters")
            
            print("\nTo see SUN in action:")
            print("1. Write a base URL to the tag (see examples/06_sun_authentication.py)")
            print("2. Scan the tag with an NFC-enabled smartphone")
            print("3. Read the NDEF message again to see the enhanced URL")
            
    except NTag242ConnectionError as e:
        print(f"\nFAILED: CONNECTION FAILED: {e}", file=sys.stderr)
        print("Make sure the NFC reader is connected and a tag is present.", file=sys.stderr)
    except Exception as e:
        print(f"\nFAILED: UNEXPECTED ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    read_sun_url()
