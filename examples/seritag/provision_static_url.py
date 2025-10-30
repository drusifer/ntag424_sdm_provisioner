#!/usr/bin/env python3
"""
Provision Static URL to Seritag NTAG424 DNA Tag

This script provisions a static URL to a Seritag tag WITHOUT requiring
authentication. This enables basic NFC functionality for game coins.

Note: Static URLs don't include cryptographic authentication (UID, MAC, counter).
For full security, SDM/SUN configuration requires EV2 authentication.
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.commands.sun_commands import (
    WriteNdefMessage, ReadNdefMessage, build_ndef_uri_record
)
from ntag424_sdm_provisioner.commands.base import ApduError
import logging

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


def provision_static_url(url: str, verify: bool = True):
    """
    Provision a static URL to Seritag NTAG424 DNA tag without authentication.
    
    Args:
        url: Base URL to write to tag (e.g., "https://game-server.com/verify")
        verify: If True, read back NDEF to verify
    
    Returns:
        True if successful
    """
    print("=" * 80)
    print("STATIC URL PROVISIONING")
    print("=" * 80)
    print()
    print(f"URL: {url}")
    print("Note: This creates a static URL (no authentication parameters)")
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
            
            print("\nStep 3: Selecting NDEF file...")
            select_apdu = [0x00, 0xA4, 0x02, 0x00, 0x02, 0xE1, 0x04, 0x00]
            _, sw1, sw2 = card.send_apdu(select_apdu, use_escape=True)
            if (sw1, sw2) == (0x90, 0x00):
                print("[OK] NDEF file selected")
            else:
                raise Exception(f"File selection failed: {sw1:02X}{sw2:02X}")
            
            print("\nStep 4: Building NDEF URI record...")
            ndef_data = build_ndef_uri_record(url)
            print(f"[OK] NDEF data prepared: {len(ndef_data)} bytes")
            
            print("\nStep 5: Writing NDEF to tag...")
            try:
                WriteNdefMessage(ndef_data).execute(card)
                print("[OK] NDEF written successfully!")
            except ApduError as e:
                print(f"[FAIL] Write failed: {e.sw1:02X}{e.sw2:02X} - {e}")
                return False
            
            if verify:
                print("\nStep 6: Verifying write...")
                try:
                    read_data = ReadNdefMessage(max_length=256).execute(card)
                    print(f"[OK] Read back {len(read_data)} bytes")
                    
                    # Try to decode URL
                    try:
                        ndef_str = read_data.decode('utf-8', errors='ignore')
                        if url in ndef_str:
                            print(f"[OK] URL verified in NDEF data")
                        else:
                            print(f"[INFO] URL format may differ in NDEF encoding")
                    except:
                        print(f"[INFO] NDEF data (hex): {read_data.hex().upper()[:64]}...")
                except ApduError as e:
                    print(f"[WARN] Verification read failed: {e.sw1:02X}{e.sw2:02X}")
            
            print("\n" + "=" * 80)
            print("PROVISIONING COMPLETE")
            print("=" * 80)
            print(f"[OK] Static URL provisioned: {url}")
            print()
            print("Next steps:")
            print("  1. Tap tag with NFC-enabled phone")
            print("  2. Phone should open the URL")
            print("  3. URL will be static (no UID, counter, or MAC)")
            print()
            print("Note: For authenticated URLs with SDM/SUN, authentication is required.")
            
            return True
            
    except NTag242ConnectionError as e:
        print(f"\n[FAIL] CONNECTION FAILED: {e}")
        print("Make sure NFC reader is connected and tag is present.")
        return False
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Provision static URL to Seritag NTAG424 tag")
    parser.add_argument(
        "url",
        nargs="?",
        default="https://game-server.com/verify",
        help="URL to provision (default: https://game-server.com/verify)"
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip verification read"
    )
    
    args = parser.parse_args()
    
    success = provision_static_url(args.url, verify=not args.no_verify)
    
    sys.exit(0 if success else 1)

