#!/usr/bin/env python3
"""
Example 22: Provision Game Coin with SDM/SUN

This example demonstrates complete end-to-end provisioning of an NTAG424 DNA
tag for use as a game coin with Secure Unique NFC (SUN) authentication.

Steps:
1. Connect to tag and get chip info
2. Authenticate with factory keys
3. Build SDM URL with placeholders
4. Configure SDM on NDEF file
5. Write NDEF message
6. Verify provisioning

Result: Game coin that generates tap-unique authenticated URLs
"""

import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import (
    SelectPiccApplication,
    GetChipVersion,
    AuthenticateEV2,
)
from ntag424_sdm_provisioner.commands.get_file_counters import GetFileCounters
from ntag424_sdm_provisioner.commands.write_data import WriteData
from ntag424_sdm_provisioner.commands.change_file_settings import ChangeFileSettings
from ntag424_sdm_provisioner.commands.sun_commands import WriteNdefMessage
from ntag424_sdm_provisioner.commands.iso_commands import ISOSelectFile, ISOFileID
from ntag424_sdm_provisioner.commands.base import ApduError
from ntag424_sdm_provisioner.commands.sdm_helpers import build_ndef_uri_record, calculate_sdm_offsets
from ntag424_sdm_provisioner.constants import (
    SDMUrlTemplate,
    SDMConfiguration,
    SDMOffsets,
    CommMode,
    FileOption,
    AccessRight,
    AccessRights,
    FACTORY_KEY,
)
from ntag424_sdm_provisioner.key_manager_interface import SimpleKeyManager, KEY_DEFAULT_FACTORY


def provision_game_coin():
    """Provision an NTAG424 DNA tag as a game coin."""
    
    print("=" * 70)
    print("Example 22: Provision Game Coin with SDM/SUN")
    print("=" * 70)
    print()
    print("This will configure your NTAG424 DNA tag for tap-unique URLs.")
    print()
    print("[WARNING] This example requires:")
    print("  - Tag with factory default keys (all zeros)")
    print("  - Fresh or already-authenticated tag")
    print()
    print("Please place your NTAG424 DNA tag on the reader...")
    print()
    
    try:
        with CardManager(reader_index=0) as card:
            print("[OK] Connected to reader")
            print()
            
            # Step 1: Select application and get chip info
            print("Step 1: Get Chip Information")
            print("-" * 70)
            
            SelectPiccApplication().execute(card)
            print("  [OK] Application selected")
            
            version_info = GetChipVersion().execute(card)
            print(f"  Chip: {version_info}")
            print(f"  UID: {version_info.uid.hex().upper()}")
            print()
            
            # Step 2: Define URL template
            print("Step 2: Build SDM URL Template")
            print("-" * 70)
            base_url = "https://script.google.com/macros/s/AKfycbz2gCQYl_OjEJB26jiUL8253I0bX4czxykkcmt-MnF41lIyX18SLkRgUcJ_VJRJbiwh/exec"
            base_url = "https://globalheadsandtails.com/tap"
            uid_placeholder = "00000000000000"      # 7 bytes
            counter_placeholder = "000000"           # 3 bytes
            cmac_placeholder = "0000000000000000"   # 8 bytes
            
            url_with_placeholders = (
                f"{base_url}?"
                f"uid={uid_placeholder}&"
                f"ctr={counter_placeholder}&"
                f"cmac={cmac_placeholder}"
            )
            
            print(f"  URL: {url_with_placeholders}")
            print(f"  Length: {len(url_with_placeholders)} characters")
            
            # Build NDEF message
            ndef_message = build_ndef_uri_record(url_with_placeholders)
            print(f"  NDEF Size: {len(ndef_message)} bytes")
            print()
            
            # Calculate SDM offsets
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
            
            # Step 3: Note about authentication
            print("Step 3: Authentication")
            print("-" * 70)
            print("  [INFO] Authentication will be performed when needed for SDM config")
            print("  [INFO] Using factory key (all zeros)")
            print()
            
            # Step 4: Write NDEF Message FIRST (before enabling SDM)
            print("Step 4: Write NDEF Message")
            print("-" * 70)
            print("  [INFO] Writing NDEF before enabling SDM (data must exist first)")
            
            # Select NDEF file using ISO command
            print("  Selecting NDEF file...")
            select_result = ISOSelectFile(ISOFileID.NDEF_FILE).execute(card)
            print(f"  [OK] {select_result}")
            
            # Write NDEF data
            print(f"  Writing {len(ndef_message)} bytes...")
            write_cmd = WriteNdefMessage(ndef_data=ndef_message)
            result = write_cmd.execute(card)
            print(f"  [OK] {result}")
            print()
            
            # Step 5: Configure SDM with Authentication
            print("Step 5: Configure SDM with Authentication")
            print("-" * 70)
            
            # ChangeFileSettings requires authentication for CommMode.MAC/FULL
            print("  Authenticating with factory key...")
            
            # Use new AuthenticateEV2 pattern with context manager
            with AuthenticateEV2(FACTORY_KEY, key_no=0).execute(card) as auth_conn:
                print(f"  [OK] Authenticated")
                print()
                
                # Build SDM configuration
                # Access rights: Read=FREE (anyone can read), Write=KEY_0 (auth required), 
                #                RW=FREE, Change=FREE (for this example)
                access_rights = AccessRights(
                    read=AccessRight.FREE,
                    write=AccessRight.KEY_0,
                    read_write=AccessRight.FREE,
                    change=AccessRight.FREE
                )
                
                sdm_config = SDMConfiguration(
                    file_no=0x02,  # NDEF file
                    comm_mode=CommMode.PLAIN,  # Plain communication
                    access_rights=access_rights,  # SDMConfiguration handles encoding
                    enable_sdm=True,
                    sdm_options=(
                        FileOption.UID_MIRROR |   # Bit 7
                        FileOption.READ_COUNTER   # Bit 6 (now correct!)
                    ),
                    offsets=offsets  # SDMOffsets dataclass instead of individual fields
                )
                
                print(f"  SDM Config: {sdm_config}")
                print("  Configuring...")
                
                # ChangeFileSettings with authenticated session
                config_cmd = ChangeFileSettings(sdm_config)
                config_cmd.execute(card, session=auth_conn.session)
                print("  [OK] SDM configured successfully!")
            print()
            
            # Step 6: Verify (try to read counter)
            print("Step 6: Verify Provisioning")
            print("-" * 70)
            
            counter = GetFileCounters(file_no=0x02).execute(card)
            print(f"  [OK] SDM counter: {counter}")
            print("  [SUCCESS] Provisioning complete!")
            print()
            
            # Summary
            print("=" * 70)
            print("Provisioning Summary")
            print("=" * 70)
            print()
            print("SUCCESS! Your game coin is provisioned.")
            print()
            print("Tapping the coin will now generate:")
            print(f"  {base_url}?uid={version_info.uid.hex().upper()}&ctr=XXXXXX&cmac=XXXXXXXXXXXXXXXX")
            print()
            print("Next Steps:")
            print("  1. Tap coin with NFC phone")
            print("  2. Phone browser opens with tap-unique URL")
            print("  3. Implement server validation endpoint")
            print("  4. Server verifies CMAC and counter")
            print("  5. Deliver game reward!")
            print()
            
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Stopped by user")
        return 1
    except ApduError as e:
        # Catches all APDU errors (including specific subclasses)
        print(f"\n[ERROR] {e}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(provision_game_coin())

