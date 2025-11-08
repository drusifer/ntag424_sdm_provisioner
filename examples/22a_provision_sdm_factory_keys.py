#!/usr/bin/env python3
"""
Example 22a: Provision SDM with Factory Keys (Testing)

This is a simplified provisioning flow for TESTING ONLY.
Uses factory keys (no ChangeKey) to test SDM configuration.

Steps:
1. Connect and get chip info
2. Authenticate with factory keys
3. Configure SDM on NDEF file
4. Write NDEF message with placeholders
5. Verify SDM works (GetFileCounters)

WARNING: For testing only! Production tags should use unique keys.
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import (
    SelectPiccApplication,
    GetChipVersion,
    AuthenticateEV2,
)
from ntag424_sdm_provisioner.commands.get_file_counters import GetFileCounters
from ntag424_sdm_provisioner.commands.change_file_settings import ChangeFileSettings
from ntag424_sdm_provisioner.commands.sun_commands import WriteNdefMessage
from ntag424_sdm_provisioner.commands.iso_commands import ISOSelectFile, ISOFileID
from ntag424_sdm_provisioner.commands.base import ApduError
from ntag424_sdm_provisioner.commands.sdm_helpers import build_ndef_uri_record, calculate_sdm_offsets
from ntag424_sdm_provisioner.constants import (
    SDMUrlTemplate,
    SDMConfiguration,
    CommMode,
    FileOption,
    AccessRight,
    AccessRights,
)
from ntag424_sdm_provisioner.key_manager_interface import KEY_DEFAULT_FACTORY


def provision_sdm_factory_keys():
    """Provision SDM using factory keys (testing only)."""
    
    print("=" * 70)
    print("Example 22a: Provision SDM with Factory Keys (TESTING)")
    print("=" * 70)
    print()
    print("[WARNING] This uses FACTORY KEYS - for testing only!")
    print("  Production tags should use unique keys (see example 22)")
    print()
    print("This will test:")
    print("  - SDM configuration (ChangeFileSettings)")
    print("  - NDEF write with placeholders")
    print("  - SDM counter (GetFileCounters)")
    print()
    
    try:
        with CardManager(reader_index=0) as card:
            print("Please place your NTAG424 DNA tag on the reader...")
            print()
            print("[OK] Connected to reader")
            print()
            
            # Step 1: Get chip info
            print("Step 1: Get Chip Information")
            print("-" * 70)
            
            SelectPiccApplication().execute(card)
            print("  [OK] Application selected")
            
            version_info = GetChipVersion().execute(card)
            uid = version_info.uid
            print(f"  Chip UID: {uid.hex().upper()}")
            print()
            
            # Step 2: Build SDM URL
            print("Step 2: Build SDM URL Template")
            print("-" * 70)
            base_url = "https://globalheadsandtails.com/tap"
            uid_placeholder = "00000000000000"
            counter_placeholder = "000000"
            cmac_placeholder = "0000000000000000"
            
            url_with_placeholders = (
                f"{base_url}?"
                f"uid={uid_placeholder}&"
                f"ctr={counter_placeholder}&"
                f"cmac={cmac_placeholder}"
            )
            
            print(f"  URL: {url_with_placeholders}")
            
            ndef_message = build_ndef_uri_record(url_with_placeholders)
            print(f"  NDEF Size: {len(ndef_message)} bytes")
            
            template = SDMUrlTemplate(
                base_url=base_url,
                uid_placeholder=uid_placeholder,
                cmac_placeholder=cmac_placeholder,
                read_ctr_placeholder=counter_placeholder,
                enc_placeholder=None
            )
            
            offsets = calculate_sdm_offsets(template)
            print(f"  SDM Offsets: {offsets}")
            print()
            
            # Step 3: Authenticate and configure SDM
            print("Step 3: Configure SDM (Authenticated)")
            print("-" * 70)
            print("  Authenticating with factory key...")
            
            with AuthenticateEV2(KEY_DEFAULT_FACTORY, key_no=0)(card) as auth_conn:
                print("  [OK] Authenticated")
                print()
                
                # Build SDM configuration
                # Match current access rights EXACTLY (E0EE)
                # Current decoded: Read=E, Write=0, ReadWrite=E, Change=E
                access_rights = AccessRights(
                    read=AccessRight.FREE,      # E
                    write=AccessRight.KEY_0,    # 0 (matches current!)
                    read_write=AccessRight.FREE,   # E
                    change=AccessRight.FREE     # E (matches current!)
                )
                
                sdm_config = SDMConfiguration(
                    file_no=0x02,
                    comm_mode=CommMode.FULL,  # Try FULL for ChangeFileSettings command
                    access_rights=access_rights,
                    enable_sdm=True,
                    sdm_options=(
                        FileOption.UID_MIRROR |
                        FileOption.READ_COUNTER
                    ),
                    offsets=offsets
                )
                
                print(f"  Config: {sdm_config}")
                print("  Calling ChangeFileSettings...")
                
                try:
                    from ntag424_sdm_provisioner.commands.change_file_settings import ChangeFileSettingsAuth
                    ChangeFileSettingsAuth(sdm_config).execute(auth_conn)
                    print("  [OK] SDM configured successfully!")
                except ApduError as e:
                    print(f"  [FAIL] {e}")
                    print("  [INFO] ChangeFileSettings still has issues")
                    raise
                print()
            
            # Step 4: Write NDEF
            print("Step 4: Write NDEF Message")
            print("-" * 70)
            print("  Selecting NDEF file...")
            ISOSelectFile(ISOFileID.NDEF_FILE).execute(card)
            print("  [OK] Selected")
            
            print(f"  Writing {len(ndef_message)} bytes...")
            WriteNdefMessage(ndef_data=ndef_message).execute(card)
            print("  [OK] Written")
            
            # Re-select PICC
            SelectPiccApplication().execute(card)
            print("  [OK] PICC re-selected")
            print()
            
            # Step 5: Verify SDM
            print("Step 5: Verify SDM Configuration")
            print("-" * 70)
            
            try:
                counter = GetFileCounters(file_no=0x02).execute(card)
                print(f"  [SUCCESS] SDM Counter: {counter}")
                print("  [SUCCESS] SDM is working!")
            except ApduError as e:
                print(f"  [FAIL] {e}")
                print("  [INFO] SDM may not be enabled")
            print()
            
            # Summary
            print("=" * 70)
            print("Test Summary")
            print("=" * 70)
            print()
            print(f"Tag UID: {uid.hex().upper()}")
            print("Keys: Factory defaults (all zeros)")
            print()
            print("Next:")
            print("  1. If SDM works, tap tag with NFC phone")
            print("  2. Check if placeholders are replaced")
            print("  3. Fix ChangeKey to enable unique keys per tag")
            print()
            
    except ApduError as e:
        print(f"\n[ERROR] {e}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Unexpected: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(provision_sdm_factory_keys())

