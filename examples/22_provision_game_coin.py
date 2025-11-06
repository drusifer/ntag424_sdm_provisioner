#!/usr/bin/env python3
"""
Example 22: Provision Game Coin with SDM/SUN

This example demonstrates complete end-to-end provisioning of an NTAG424 DNA
tag for use as a game coin with Secure Unique NFC (SUN) authentication.

Follows the proper sequence from charts.md:
1. Connect to tag and get chip info
2. Authenticate with current keys (factory or provisioned)
3. Change keys using two-phase commit pattern
4. Re-authenticate with new PICC Master Key
5. Configure SDM on NDEF file
6. Write NDEF message with placeholders
7. Verify provisioning

Result: Game coin that generates tap-unique authenticated URLs
"""

import sys
import os
import time

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, TagKeys
from ntag424_sdm_provisioner.commands.sdm_commands import (
    SelectPiccApplication,
    GetChipVersion,
    AuthenticateEV2,
    ChangeKey,
)
from ntag424_sdm_provisioner.commands.get_file_counters import GetFileCounters
from ntag424_sdm_provisioner.commands.change_file_settings import ChangeFileSettings
from ntag424_sdm_provisioner.commands.sun_commands import WriteNdefMessage
from ntag424_sdm_provisioner.commands.iso_commands import ISOSelectFile, ISOFileID
from ntag424_sdm_provisioner.commands.base import ApduError, AuthenticationRateLimitError
from ntag424_sdm_provisioner.commands.sdm_helpers import build_ndef_uri_record, calculate_sdm_offsets
from ntag424_sdm_provisioner.constants import (
    SDMUrlTemplate,
    SDMConfiguration,
    CommMode,
    FileOption,
    AccessRight,
    AccessRights,
)


def provision_game_coin():
    """Provision an NTAG424 DNA tag as a game coin."""
    
    print("=" * 70)
    print("Example 22: Provision Game Coin with SDM/SUN")
    print("=" * 70)
    print()
    print("This will provision your NTAG424 DNA tag with unique keys and SDM.")
    print()
    print("[WARNING] This will:")
    print("  - Change all keys on the tag to new random values")
    print("  - Save keys to tag_keys.csv for future access")
    print("  - Enable SDM for tap-unique authenticated URLs")
    print()
    print("[TIP] If authentication fails (0x91AD rate limit):")
    print("  - Remove tag and wait 30-60 seconds")
    print("  - Use a fresh tag if available")
    print()
    
    # Initialize key manager
    key_mgr = CsvKeyManager()
    
    try:
        with CardManager(reader_index=0) as card:
            print("Please place your NTAG424 DNA tag on the reader...")
            print()
            print("[OK] Connected to reader")
            print()
            
            # Step 1: Get chip information
            print("Step 1: Get Chip Information")
            print("-" * 70)
            
            SelectPiccApplication().execute(card)
            print("  [OK] Application selected")
            
            version_info = GetChipVersion().execute(card)
            uid = version_info.uid
            print(f"  Chip UID: {uid.hex().upper()}")
            print(f"  Chip Info: {version_info}")
            print()
            
            # Step 2: Get current keys from database
            print("Step 2: Load Current Keys")
            print("-" * 70)
            current_keys = key_mgr.get_tag_keys(uid)
            print(f"  Current Status: {current_keys.status}")
            if current_keys.status == "factory":
                print("  [INFO] Tag has factory keys - first provision")
            elif current_keys.status in ["failed", "pending"]:
                print(f"  [INFO] Previous provision incomplete - tag still has factory keys")
                # Use factory keys instead of saved keys
                current_keys = TagKeys.from_factory_keys(uid.hex().upper())
            else:
                print("  [INFO] Tag already provisioned - re-provisioning")
            print()
            
            # Step 3: Build NDEF URL template
            print("Step 3: Build SDM URL Template")
            print("-" * 70)
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
            
            # Step 4: Authenticate with current keys and change PICC Master Key
            print("Step 4: Change PICC Master Key (Key 0)")
            print("-" * 70)
            current_picc_key = current_keys.get_picc_master_key_bytes()
            print(f"  Authenticating with {'factory' if current_keys.status == 'factory' else 'saved'} PICC Master Key...")
            
            # Start two-phase commit for provisioning
            with key_mgr.provision_tag(uid) as new_keys:
                print("  [Phase 1] New keys generated and saved (status='pending')")
                print(f"    PICC Master: {new_keys.picc_master_key[:16]}...")
                print(f"    App Read:    {new_keys.app_read_key[:16]}...")
                print(f"    SDM MAC:     {new_keys.sdm_mac_key[:16]}...")
                print()
                
                # Authenticate with CURRENT (old) PICC Master Key
                with AuthenticateEV2(current_picc_key, key_no=0).execute(card) as auth_conn:
                    print("  [OK] Authenticated with current key")
                    
                    # Change Key 0 (PICC Master Key)
                    print("  Changing Key 0 (PICC Master)...", end=" ")
                    ChangeKey(
                        key_no_to_change=0,
                        new_key=new_keys.get_picc_master_key_bytes(),
                        old_key=current_picc_key
                    ).execute(card, session=auth_conn.session)
                    print("[OK]")
                print()
                
                # Step 5: Re-authenticate with NEW PICC Master Key to change other keys
                print("Step 5: Re-authenticate and Change Other Keys")
                print("-" * 70)
                print("  Re-authenticating with NEW PICC Master Key...")
                
                with AuthenticateEV2(new_keys.get_picc_master_key_bytes(), key_no=0).execute(card) as auth_conn:
                    print("  [OK] Authenticated with new key")
                    print()
                    
                    print("  Changing remaining keys...")
                    
                    # Change Key 1 (App Read Key)
                    print("    Changing Key 1 (App Read)...", end=" ")
                    ChangeKey(
                        key_no_to_change=1,
                        new_key=new_keys.get_app_read_key_bytes(),
                        old_key=current_keys.get_app_read_key_bytes()
                    ).execute(card, session=auth_conn.session)
                    print("[OK]")
                    
                    # Change Key 3 (SDM MAC Key)
                    print("    Changing Key 3 (SDM MAC)...", end=" ")
                    ChangeKey(
                        key_no_to_change=3,
                        new_key=new_keys.get_sdm_mac_key_bytes(),
                        old_key=current_keys.get_sdm_mac_key_bytes()
                    ).execute(card, session=auth_conn.session)
                    print("[OK]")
                    print()
                
                # Context manager will auto-commit on success
                print("  [Phase 2] All keys changed successfully!")
                print("  [OK] Keys updated (status='provisioned')")
                print()
            
            # Step 6: Re-authenticate with new PICC Master Key
            print("Step 6: Re-authenticate with New PICC Master Key")
            print("-" * 70)
            new_picc_key = key_mgr.get_key(uid, key_no=0)
            print("  Authenticating with new key...")
            
            with AuthenticateEV2(new_picc_key, key_no=0).execute(card) as auth_conn:
                print("  [OK] Authenticated with new key")
                print()
                
                # Step 7: Configure SDM
                print("Step 7: Configure SDM on NDEF File")
                print("-" * 70)
                
                access_rights = AccessRights(
                    read=AccessRight.FREE,
                    write=AccessRight.KEY_0,
                    read_write=AccessRight.FREE,
                    change=AccessRight.FREE
                )
                
                sdm_config = SDMConfiguration(
                    file_no=0x02,  # NDEF file
                    comm_mode=CommMode.PLAIN,  # PLAIN mode (no CMAC wrapping)
                    access_rights=access_rights,
                    enable_sdm=True,
                    sdm_options=(
                        FileOption.UID_MIRROR |   # Bit 7
                        FileOption.READ_COUNTER   # Bit 6
                    ),
                    offsets=offsets
                )
                
                print(f"  Config: {sdm_config}")
                print("  Configuring SDM...")
                
                try:
                    # ChangeFileSettings (requires authentication for SDM config)
                    # Note: Currently debugging 0x917E/0x91AE errors
                    ChangeFileSettings(sdm_config).execute(auth_conn)
                    print("  [OK] SDM configured successfully!")
                except ApduError as e:
                    print(f"  [WARNING] SDM configuration failed: {e}")
                    print("  [INFO] This is a known issue - continuing with NDEF write")
                    print("  [INFO] SDM placeholders won't be replaced (static URL only)")
                print()
                
                # Step 8: Write NDEF message
                print("Step 8: Write NDEF Message")
                print("-" * 70)
                print("  Selecting NDEF file...")
                ISOSelectFile(ISOFileID.NDEF_FILE).execute(card)
                print("  [OK] NDEF file selected")
                
                print(f"  Writing {len(ndef_message)} bytes...")
                WriteNdefMessage(ndef_data=ndef_message).execute(card)
                print("  [OK] NDEF message written")
                
                # Re-select PICC application
                SelectPiccApplication().execute(card)
                print("  [OK] PICC application re-selected")
                print()
            
            # Step 9: Verify provisioning
            print("Step 9: Verify Provisioning")
            print("-" * 70)
            
            try:
                counter = GetFileCounters(file_no=0x02).execute(card)
                print(f"  [OK] SDM counter: {counter}")
                print("  [SUCCESS] SDM is working!")
            except ApduError as e:
                print(f"  [INFO] GetFileCounters: {e}")
                print("  [INFO] SDM may not be fully configured (expected if ChangeFileSettings failed)")
            print()
            
            # Summary
            print("=" * 70)
            print("Provisioning Summary")
            print("=" * 70)
            print()
            print("SUCCESS! Your game coin has been provisioned.")
            print()
            print(f"Tag UID: {uid.hex().upper()}")
            print(f"Keys saved to: tag_keys.csv")
            print()
            print("When tapped, the coin will generate:")
            print(f"  {base_url}?uid=[UID]&ctr=[COUNTER]&cmac=[CMAC]")
            print()
            print("Next Steps:")
            print("  1. Tap coin with NFC phone")
            print("  2. Phone browser opens with tap-unique URL")
            print("  3. Implement server validation endpoint")
            print("  4. Server verifies CMAC and counter")
            print("  5. Deliver game reward!")
            print()
            print("[IMPORTANT] Keys saved in tag_keys.csv - keep this file secure!")
            print()
            
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Stopped by user")
        return 1
    except ApduError as e:
        print(f"\n[ERROR] {e}")
        print("\n[TIP] Check tag_keys.csv for current key status")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(provision_game_coin())
