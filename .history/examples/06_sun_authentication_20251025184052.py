#!/usr/bin/env python3
"""
Example 06: SUN (Secure Unique NFC) for Seritag Tags

This example demonstrates how to use SUN (Secure Unique NFC) with Seritag NTAG424 DNA tags.
SUN provides dynamic authentication without requiring complex EV2 authentication protocols.

SUN automatically appends unique authentication codes to URLs when the tag is scanned,
providing secure authentication that can be verified server-side.
"""
import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.commands.sun_commands import (
    WriteNdefMessage, ReadNdefMessage, ConfigureSunSettings,
    build_ndef_uri_record, parse_sun_url
)
from ntag424_sdm_provisioner.commands.base import ApduError


def sun_example():
    """Demonstrate SUN (Secure Unique NFC) functionality with Seritag tags."""
    try:
        print("--- Example 06: SUN (Secure Unique NFC) ---")
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
                print("\n✅ Detected Seritag NTAG424 DNA (HW 48.0)")
                print("   Using SUN (Secure Unique NFC) instead of SDM")
            else:
                print(f"\n⚠️  Standard NXP NTAG424 DNA detected (HW {version_info.hw_major_version}.{version_info.hw_minor_version})")
                print("   SUN may not be available - using standard approach")
            
            print("\n3. Configuring SUN settings...")
            try:
                sun_config = ConfigureSunSettings(enable_sun=True)
                print(f"   EXECUTING: {sun_config}")
                sun_response = sun_config.execute(card)
                print(f"   RESPONSE: {sun_response}")
            except ApduError as e:
                print(f"   WARNING: SUN configuration failed: {e}")
                print("   Continuing with NDEF write...")
            
            print("\n4. Writing NDEF URL for SUN authentication...")
            
            # Create a base URL - SUN will automatically append authentication parameters
            base_url = "https://example.com/verify"
            print(f"   Base URL: {base_url}")
            print("   SUN will automatically append: ?uid=XXXX&c=YYYY&mac=ZZZZ")
            
            # Build NDEF URI record
            ndef_data = build_ndef_uri_record(base_url)
            print(f"   NDEF data: {ndef_data.hex().upper()}")
            
            try:
                write_command = WriteNdefMessage(ndef_data)
                print(f"   EXECUTING: {write_command}")
                write_response = write_command.execute(card)
                print(f"   RESPONSE: {write_response}")
            except ApduError as e:
                print(f"   ERROR: NDEF write failed: {e}")
                return
            
            print("\n5. Reading back NDEF message...")
            try:
                read_command = ReadNdefMessage(max_length=256)
                print(f"   EXECUTING: {read_command}")
                ndef_readback = read_command.execute(card)
                print(f"   NDEF data: {ndef_readback.hex().upper()}")
                
                # Try to parse the NDEF data
                if len(ndef_readback) > 0:
                    print(f"   NDEF as text: {ndef_readback}")
            except ApduError as e:
                print(f"   ERROR: NDEF read failed: {e}")
            
            print("\n" + "=" * 60)
            print("  ✅ SUN Configuration Complete")
            print("=" * 60)
            print("Next steps:")
            print("1. Scan the tag with an NFC-enabled device")
            print("2. SUN will automatically append authentication parameters to the URL")
            print("3. The URL will look like: https://example.com/verify?uid=XXXX&c=YYYY&mac=ZZZZ")
            print("4. Implement server-side verification of the SUN parameters")
            print("\nExample server verification:")
            print("  - Extract UID, counter (c), and MAC from URL parameters")
            print("  - Verify MAC using the tag's secret key")
            print("  - Check counter for replay attacks")
            print("  - Confirm UID matches expected tag")
            
    except NTag242ConnectionError as e:
        print(f"\n❌ CONNECTION FAILED: {e}", file=sys.stderr)
        print("Make sure the NFC reader is connected and a tag is present.", file=sys.stderr)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    sun_example()
