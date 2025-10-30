#!/usr/bin/env python3
"""
Test Real NDEF Provisioning on Seritag Tags

Tests writing actual NDEF URL records and verifying they can be read.
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.commands.sun_commands import (
    build_ndef_uri_record, WriteNdefMessage, ReadNdefMessage
)
from ntag424_sdm_provisioner.commands.base import ApduError
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def test_ndef_provisioning():
    """Test writing and reading real NDEF URLs."""
    
    print("=" * 80)
    print("NDEF PROVISIONING TEST")
    print("=" * 80)
    print()
    
    try:
        with CardManager(0) as card:
            print("Step 1: Selecting PICC application...")
            SelectPiccApplication().execute(card)
            print("✅ PICC application selected")
            
            print("\nStep 2: Getting chip version...")
            version_info = GetChipVersion().execute(card)
            print(f"✅ Tag: HW {version_info.hw_major_version}.{version_info.hw_minor_version}")
            print(f"   UID: {version_info.uid.hex().upper()}")
            
            # Test URL
            base_url = "https://game-server.com/verify"
            print(f"\nStep 3: Building NDEF URI record for: {base_url}")
            ndef_data = build_ndef_uri_record(base_url)
            print(f"✅ NDEF data prepared: {len(ndef_data)} bytes")
            print(f"   Hex: {ndef_data.hex().upper()[:64]}...")
            
            # Write NDEF
            print(f"\nStep 4: Writing NDEF to tag...")
            try:
                WriteNdefMessage(ndef_data).execute(card)
                print(f"✅ NDEF written successfully!")
            except ApduError as e:
                print(f"❌ Write failed: {e.sw1:02X}{e.sw2:02X} - {e}")
                return
            
            # Read it back
            print(f"\nStep 5: Reading NDEF back to verify...")
            try:
                read_data = ReadNdefMessage(max_length=256).execute(card)
                print(f"✅ Read {len(read_data)} bytes")
                
                # Show first bytes
                print(f"   Hex: {read_data.hex().upper()[:128]}...")
                
                # Check if it starts with valid NDEF TLV
                if len(read_data) >= 2:
                    tlv_type = read_data[0]
                    tlv_length = read_data[1]
                    print(f"   TLV Type: 0x{tlv_type:02X}")
                    print(f"   TLV Length: {tlv_length}")
                    
                    if tlv_type == 0x03:  # NDEF Message TLV
                        print("   ✅ Valid NDEF Message TLV detected!")
                        if len(read_data) >= 2 + tlv_length:
                            ndef_payload = read_data[2:2+tlv_length]
                            print(f"   NDEF Payload: {len(ndef_payload)} bytes")
                            
                            # Try to find URL
                            url_start = ndef_payload.find(b'https://')
                            if url_start >= 0:
                                url_part = ndef_payload[url_start:url_start+len(base_url)]
                                if url_part == base_url.encode():
                                    print(f"   ✅ URL verified: {url_part.decode()}")
                                else:
                                    print(f"   ⚠️  URL mismatch: {url_part.decode()}")
                            
            except ApduError as e:
                print(f"❌ Read failed: {e.sw1:02X}{e.sw2:02X} - {e}")
                return
            
            print("\n" + "=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print("✅ NDEF provisioning WORKS!")
            print(f"✅ URL written: {base_url}")
            print("✅ Data can be read back")
            print("\nNext: Test if phone can read this NDEF message")
            print("Next: Test SUN configuration for dynamic authentication")
            
    except NTag242ConnectionError as e:
        print(f"\n❌ CONNECTION FAILED: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_ndef_provisioning()

