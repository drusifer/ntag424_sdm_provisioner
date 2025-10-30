#!/usr/bin/env python3
"""
Example 14: Reading SUN-Enhanced URL After Tap

This example demonstrates how to read the SUN-enhanced URL from a Seritag tag
after it has been scanned by an NFC device. SUN automatically appends
authentication parameters to URLs when scanned.
"""
import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion, AuthenticateEV2First
from ntag424_sdm_provisioner.commands.base import ApduError


def read_sun_url_after_tap():
    """Read SUN-enhanced URL after tag has been scanned."""
    try:
        print("--- Example 14: Reading SUN-Enhanced URL After Tap ---")
        print("Please tap and hold the Seritag NTAG424 DNA tag on the reader...")
        print("NOTE: This tag should have been scanned by an NFC device first!")
        
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
            
            print("\n3. Authenticating to access SUN data...")
            
            # Authenticate with Key 1 (works with any key)
            try:
                cmd1 = AuthenticateEV2First(key_no=1)
                response1 = cmd1.execute(card)
                print(f"   SUCCESS: Authenticated with Key 1")
                print(f"   Challenge: {response1.challenge.hex().upper()}")
            except Exception as e:
                print(f"   ERROR: Authentication failed: {e}")
                return
            
            print("\n4. Attempting to read SUN data from different files...")
            
            # Try reading from different files that might contain SUN data
            files_to_check = [
                (0x01, "Standard Data File"),
                (0x02, "NDEF File"),
                (0x03, "Proprietary File"),
                (0x04, "Key File"),
            ]
            
            sun_data_found = False
            
            for file_no, file_name in files_to_check:
                print(f"\n   Checking {file_name} (File {file_no})...")
                
                # Try to read file settings first
                try:
                    settings_apdu = [
                        0x90, 0xF5,  # GetFileSettings
                        0x00, 0x00,  # P1, P2
                        file_no,     # File number
                        0x00         # Le
                    ]
                    
                    settings_data, sw1, sw2 = card.send_apdu(settings_apdu, use_escape=True)
                    print(f"   File settings: SW={sw1:02X}{sw2:02X}")
                    
                    if (sw1, sw2) == (0x90, 0x00):
                        print(f"   File exists! Settings: {bytes(settings_data).hex().upper()}")
                        
                        # Try to read file data
                        try:
                            read_apdu = [
                                0x90, 0xB0,  # ReadBinary
                                0x00, 0x00,  # Offset 0
                                0x40,        # Read 64 bytes
                                0x00         # Le
                            ]
                            
                            read_data, sw1, sw2 = card.send_apdu(read_apdu, use_escape=True)
                            print(f"   File data: SW={sw1:02X}{sw2:02X}")
                            
                            if (sw1, sw2) == (0x90, 0x00) and len(read_data) > 0:
                                print(f"   Data: {bytes(read_data).hex().upper()}")
                                
                                # Try to parse as text/URL
                                try:
                                    text = bytes(read_data).decode('utf-8', errors='ignore')
                                    print(f"   Text: {text}")
                                    
                                    # Look for URLs
                                    import re
                                    url_pattern = r'https?://[^\s]+'
                                    urls = re.findall(url_pattern, text)
                                    
                                    if urls:
                                        print(f"   FOUND URLs:")
                                        for i, url in enumerate(urls, 1):
                                            print(f"     URL {i}: {url}")
                                            
                                            # Parse SUN parameters
                                            from ntag424_sdm_provisioner.commands.sun_commands import parse_sun_url
                                            sun_data = parse_sun_url(url)
                                            if sun_data:
                                                print(f"     SUN parameters:")
                                                for key, value in sun_data.items():
                                                    print(f"       {key}: {value}")
                                                sun_data_found = True
                                            else:
                                                print(f"     No SUN parameters (base URL)")
                                                
                                except Exception as pe:
                                    print(f"   Text parsing error: {pe}")
                            else:
                                print(f"   No readable data")
                                
                        except Exception as re:
                            print(f"   File read error: {re}")
                    else:
                        print(f"   File does not exist or not accessible")
                        
                except Exception as se:
                    print(f"   File settings error: {se}")
            
            print("\n5. Alternative: Check for SUN-specific commands...")
            
            # Try SUN-specific commands that might exist
            sun_commands = [
                (0x90, 0x30, "Get SUN Data"),
                (0x90, 0x31, "Get SUN URL"),
                (0x90, 0x32, "Get SUN Status"),
                (0x90, 0x33, "Get SUN Counter"),
            ]
            
            for cla, ins, cmd_name in sun_commands:
                try:
                    test_apdu = [cla, ins, 0x00, 0x00, 0x00]
                    _, sw1, sw2 = card.send_apdu(test_apdu, use_escape=True)
                    print(f"   {cmd_name}: SW={sw1:02X}{sw2:02X}")
                    
                    if (sw1, sw2) == (0x90, 0x00):
                        print(f"   SUCCESS: {cmd_name} command exists!")
                    elif (sw1, sw2) == (0x6D, 0x00):
                        print(f"   Command not supported")
                    else:
                        print(f"   Unexpected response")
                        
                except Exception as ce:
                    print(f"   {cmd_name} error: {ce}")
            
            print("\n" + "=" * 60)
            print("  SUN URL Reading Complete")
            print("=" * 60)
            
            if sun_data_found:
                print("SUCCESS: SUN-enhanced URLs found!")
                print("The tag has been scanned and SUN has enhanced the URLs.")
            else:
                print("No SUN-enhanced URLs found.")
                print("This could mean:")
                print("1. The tag hasn't been scanned by an NFC device yet")
                print("2. SUN data is stored in a different location")
                print("3. SUN uses a different mechanism than file storage")
                print("4. The tag needs to be configured for SUN first")
            
            print("\nTo see SUN in action:")
            print("1. Scan the tag with an NFC-enabled smartphone")
            print("2. Run this example again to see the enhanced URL")
            print("3. SUN will append authentication parameters automatically")
            
    except NTag242ConnectionError as e:
        print(f"\nFAILED: CONNECTION FAILED: {e}", file=sys.stderr)
    except Exception as e:
        print(f"\nFAILED: UNEXPECTED ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    read_sun_url_after_tap()
