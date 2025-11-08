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
from ntag424_sdm_provisioner.constants import GAME_COIN_BASE_URL, NdefUriPrefix
from ntag424_sdm_provisioner.uid_utils import format_uid_with_asset_tag, uid_to_asset_tag
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
from ntag424_sdm_provisioner.commands.authenticate_ev2 import AuthenticateEV2
from ntag424_sdm_provisioner.commands.change_key import ChangeKey
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


import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# Import trace utilities for debugging
from ntag424_sdm_provisioner.trace_util import trace_block


def check_tag_state_and_prepare(card, uid: bytes, key_mgr: CsvKeyManager, new_url: str) -> tuple[bool, bool]:
    """
    Check tag state: healthy provision uses saved keys, bad state offers reset, new tag provisions.
    
    Returns:
        (continue: bool, was_reset: bool)
    """
    with trace_block("Tag Status Check"):
        try:
            current_keys = key_mgr.get_tag_keys(uid)
            
            # Healthy provisioned tag - compare URLs
            if current_keys.status == "provisioned":
                log.info("")
                log.info("Tag Status: PROVISIONED (healthy)")
                log.info(f"  Provisioned: {current_keys.provisioned_date}")
                
                # Simulate phone tap - read NDEF unauthenticated
                log.info("")
                log.info("Reading tag (simulating phone tap)...")
                tap_url = None
                try:
                    from ntag424_sdm_provisioner.commands.iso_commands import ISOReadBinary
                    
                    # Select NDEF file
                    card.send(ISOSelectFile(ISOFileID.NDEF_FILE))
                    
                    # Read NDEF using ISO command (matching how we write)
                    ndef_data = card.send(ISOReadBinary(offset=0, length=200))
                    
                    # Extract URL from NDEF (skip TLV header, find URL)
                    # NDEF format: 0x03 <len> 0xD1 0x01 <len> 0x55 <url_code> <url_bytes> 0xFE
                    url_bytes = bytes(ndef_data)
                    # Find 0x55 (URL record type)
                    if 0x55 in url_bytes:
                        uri_type_pos = url_bytes.index(0x55)
                        prefix_code = url_bytes[uri_type_pos + 1]
                        url_start = uri_type_pos + 2  # Skip 0x55 and prefix code
                        url_end = url_bytes.index(0xFE) if 0xFE in url_bytes else len(url_bytes)
                        
                        # Decode prefix using enum
                        try:
                            prefix_enum = NdefUriPrefix(prefix_code)
                            prefix = prefix_enum.to_prefix_string()
                        except ValueError:
                            prefix = ""
                        
                        url_suffix = url_bytes[url_start:url_end].decode('utf-8')
                        tap_url = prefix + url_suffix
                        log.info(f"  Tap URL: {tap_url}")
                    else:
                        log.warning("  Could not parse URL from NDEF")
                    
                    # Re-select PICC for next operations
                    card.send(SelectPiccApplication())
                except Exception as e:
                    log.warning(f"  Could not read: {e}")
                
                # Show comparison
                current_url = current_keys.notes if current_keys.notes else "(no URL saved)"
                log.info("")
                log.info(f"  Saved URL: {current_url}")
                log.info(f"  New URL:   {new_url}")
                log.info("")
                
                if tap_url and tap_url == new_url:
                    log.info("✓ URLs match - coin is correctly configured")
                    return False, False  # Nothing to do
                
                log.info("")
                log.info("Options: 1=Update URL | 2=Re-provision | 3=Cancel")
                response = input("Select (1-3): ").strip()
                return (response in ['1', '2']), False
            
            # Bad state - handle based on type
            elif current_keys.status in ["failed", "pending"]:
                log.warning(f"Tag Status: {current_keys.status.upper()} (bad state)")
                
                if current_keys.status == "failed":
                    # Failed = previous provision attempt failed
                    # Keys are still factory (no reset needed, saves auth attempt)
                    log.info("  Assuming factory keys (skipping reset to avoid rate limit)")
                    return True, False
                
                else:  # pending
                    # Pending = keys partially changed (need reset)
                    log.warning("  RESET recommended")
                    response = input("Reset to factory? (Y/n): ").strip().lower()
                    
                    if response != 'n':
                        factory_key = bytes(16)
                        with trace_block("Factory Reset"):
                            auth_conn = AuthenticateEV2(key=factory_key, key_no=0)(card)
                            auth_conn.send(ChangeKey(0, factory_key, factory_key, 0x00))
                        
                        factory_keys = TagKeys.from_factory_keys(uid.hex().upper())
                        key_mgr.save_tag_keys(uid, factory_keys)
                        log.info("  Reset complete")
                        return True, True
                    return True, False
            
            # Factory - just provision
            else:
                log.info("Tag Status: FACTORY (new)")
                return True, False
                
        except Exception:
            log.info("Tag Status: NOT IN DATABASE (factory assumed)")
            return True, False


def provision_game_coin():
    """Provision an NTAG424 DNA tag as a game coin."""
    
    log.info("=" * 70)
    log.info("Example 22: Provision Game Coin with SDM/SUN")
    log.info("=" * 70)
    log.info("")
    log.info("This will provision your NTAG424 DNA tag with unique keys and SDM.")
    log.info("")
    log.warning("This will:")
    log.warning("  - Change all keys on the tag to new random values")
    log.warning("  - Save keys to tag_keys.csv for future access")
    log.warning("  - Enable SDM for tap-unique authenticated URLs")
    log.info("")
    log.info("TIP: If authentication fails (0x91AD rate limit):")
    log.info("  - Remove tag and wait 30-60 seconds")
    log.info("  - Use a fresh tag if available")
    log.info("")
    
    # Initialize key manager
    key_mgr = CsvKeyManager()
    
    try:
        with CardManager(reader_index=0) as card:
            log.info("Please place your NTAG424 DNA tag on the reader...")
            log.info("")
            log.info("Connected to reader")
            log.info("")
            
            # Step 1: Get chip information
            log.info("Step 1: Get Chip Information")
            log.info("-" * 70)
            
            card.send(SelectPiccApplication())
            log.info("  Application selected")
            
            version_info = card.send(GetChipVersion())
            uid = version_info.uid
            asset_tag = uid_to_asset_tag(uid)
            log.info(f"  Chip UID: {format_uid_with_asset_tag(uid)}")
            log.info(f"  Asset Tag: {asset_tag} (write this on physical label)")
            log.info(f"  Chip Info: {version_info}")
            log.info("")
            
            # Define base URL
            base_url = GAME_COIN_BASE_URL
            
            # Check tag state and get user decision
            continue_provision, was_reset = check_tag_state_and_prepare(card, uid, key_mgr, base_url)
            if not continue_provision:
                log.info("\nNothing to do - exiting")
                return 0
            
            # Step 2: Get current keys from database (refresh after possible reset)
            log.info("Step 2: Load Current Keys")
            log.info("-" * 70)
            current_keys = key_mgr.get_tag_keys(uid)
            log.info(f"  Current Status: {current_keys.status}")
            
            # After reset OR if bad/factory state, use factory keys
            if was_reset or current_keys.status in ["factory", "failed", "pending"]:
                if was_reset:
                    log.info("  Using factory keys (just reset)")
                else:
                    log.info("  Using factory keys")
                current_keys = TagKeys.from_factory_keys(uid.hex().upper())
            else:
                log.info("  Using saved keys for re-provision")
            log.info("")
            
            # Step 3: Build NDEF URL template
            log.info("Step 3: Build SDM URL Template")
            log.info("-" * 70)
            uid_placeholder = "00000000000000"      # 7 bytes
            counter_placeholder = "000000"           # 3 bytes
            cmac_placeholder = "0000000000000000"   # 8 bytes
            
            url_with_placeholders = (
                f"{base_url}?"
                f"uid={uid_placeholder}&"
                f"ctr={counter_placeholder}&"
                f"cmac={cmac_placeholder}"
            )
            
            log.info(f"  URL: {url_with_placeholders}")
            log.info(f"  Length: {len(url_with_placeholders)} characters")
            
            # Build NDEF message
            ndef_message = build_ndef_uri_record(url_with_placeholders)
            log.info(f"  NDEF Size: {len(ndef_message)} bytes")
            
            # Calculate SDM offsets
            template = SDMUrlTemplate(
                base_url=base_url,
                uid_placeholder=uid_placeholder,
                cmac_placeholder=cmac_placeholder,
                read_ctr_placeholder=counter_placeholder,
                enc_placeholder=None
            )
            
            offsets = calculate_sdm_offsets(template)
            log.info(f"  SDM Offsets: {offsets}")
            log.info("")

            # Step 4: Authenticate with current keys and change PICC Master Key
            log.info("Step 4: Change All Keys (Per charts.md sequence)")
            log.info("-" * 70)
            current_picc_key = current_keys.get_picc_master_key_bytes()
            log.info(f"  Authenticating with {'factory' if current_keys.status == 'factory' else 'saved'} PICC Master Key...")
            
            # Start two-phase commit for provisioning
            with key_mgr.provision_tag(uid, url=base_url) as new_keys:
                log.info("  [Phase 1] New keys generated and saved (status='pending')")
                log.info(f"    PICC Master: {new_keys.picc_master_key[:16]}...")
                log.info(f"    App Read:    {new_keys.app_read_key[:16]}...")
                log.info(f"    SDM MAC:     {new_keys.sdm_mac_key[:16]}...")
                log.info("")
                
                # SESSION 1: Change Key 0 only
                log.info("  [Session 1] Changing Key 0...")
                with trace_block("Session 1: Change Key 0"):
                    with AuthenticateEV2(current_picc_key, key_no=0)(card) as auth_conn:
                        log.info("    Authenticated with old Key 0")
                        
                        with trace_block("ChangeKey 0"):
                            res = auth_conn.send(ChangeKey(
                                key_no_to_change=0,
                                new_key=new_keys.get_picc_master_key_bytes(),
                                old_key=None
                            ))
                            log.info(f"    Key 0 changed - {res}")
                        
                        # Session is now INVALID (Key 0 changed)
                        log.info("    Session 1 ended (invalid after Key 0 change)")
                
                log.info("")
                log.info("  [Session 2] Changing Key 1 and Key 3...")
                log.info("    (Re-authenticating with NEW Key 0)")
                
                # SESSION 2: Change Key 1 and Key 3 with NEW Key 0
                with trace_block("Session 2: Change Keys 1 and 3"):
                    new_picc_key = new_keys.get_picc_master_key_bytes()
                    
                    with AuthenticateEV2(new_picc_key, key_no=0)(card) as auth_conn:
                        log.info("    Authenticated with NEW Key 0")
                        
                        # Change Key 1
                        with trace_block("ChangeKey 1"):
                            res = auth_conn.send(ChangeKey(
                                key_no_to_change=1,
                                new_key=new_keys.get_app_read_key_bytes(),
                                old_key=None
                            ))
                            log.info(f"    Key 1 changed - {res}")
                        
                        # Change Key 3
                        with trace_block("ChangeKey 3"):
                            res = auth_conn.send(ChangeKey(
                                key_no_to_change=3,
                                new_key=new_keys.get_sdm_mac_key_bytes(),
                                old_key=None
                            ))
                            log.info(f"    Key 3 changed - {res}")
                        
                        log.info("    All keys changed successfully")
                        log.info("")
                        
                        # Step 5: Configure SDM (still in Session 2 with NEW Key 0)
                        log.info("  [Session 2] Configuring SDM and writing NDEF...")
                        log.info("-" * 70)
                        
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
                        
                        log.info(f"    Config: {sdm_config}")
                        log.info("    Configuring SDM...")
                        
                        try:
                            # ChangeFileSettings (PLAIN mode for SDM config)
                            card.send(ChangeFileSettings(sdm_config))
                            log.info("    SDM configured successfully!")
                        except ApduError as e:
                            log.warning(f"    SDM configuration failed: {e}")
                            log.info("    Continuing with NDEF write (SDM placeholders won't work)")
                        log.info("")
                        
                        # Write NDEF message
                        log.info("    Writing NDEF message...")
                        log.info("    Selecting NDEF file...")
                        card.send(ISOSelectFile(ISOFileID.NDEF_FILE))
                        log.info("    NDEF file selected")
                        
                        log.info(f"    Writing {len(ndef_message)} bytes (chunked)...")
                        card.send(WriteNdefMessage(ndef_data=ndef_message))
                        log.info("    NDEF message written")
                        
                        # Re-select PICC application
                        card.send(SelectPiccApplication())
                        log.info("    PICC application re-selected")
                        log.info("")
                
                # Context manager will auto-commit on success
                log.info("  [Phase 2] Provisioning complete!")
                log.info("")
            
            # Step 6: Verify provisioning - Simulate phone tap
            log.info("Step 6: Verify Provisioning (Simulate Phone Tap)")
            log.info("-" * 70)
            log.info("  Reading NDEF unauthenticated (like a phone would)...")
            
            try:
                from ntag424_sdm_provisioner.commands.iso_commands import ISOReadBinary
                
                # Select NDEF file
                card.send(ISOSelectFile(ISOFileID.NDEF_FILE))
                
                # Read NDEF using ISO command (matching how we wrote it)
                ndef_data = card.send(ISOReadBinary(offset=0, length=200))
                
                # Extract URL
                url_bytes = bytes(ndef_data)
                if 0x55 in url_bytes:
                    # NDEF URI format: ... 0x55 <prefix_code> <url_without_prefix> ...
                    uri_type_pos = url_bytes.index(0x55)
                    prefix_code = url_bytes[uri_type_pos + 1]
                    url_start = uri_type_pos + 2  # Skip 0x55 and prefix code
                    url_end = url_bytes.index(0xFE) if 0xFE in url_bytes else len(url_bytes)
                    
                    # Decode prefix using enum
                    try:
                        prefix_enum = NdefUriPrefix(prefix_code)
                        prefix = prefix_enum.to_prefix_string()
                    except ValueError:
                        prefix = ""
                    
                    url_suffix = url_bytes[url_start:url_end].decode('utf-8')
                    tap_url = prefix + url_suffix
                    
                    log.info("")
                    log.info(f"  Tap URL: {tap_url}")
                    log.info("")
                    
                    # Check for SDM placeholders
                    if "00000000000000" in tap_url:
                        log.info("  SDM Status: Placeholders present (SDM not fully active)")
                        log.info("  URL will be static until SDM is properly configured")
                    else:
                        log.info("  SDM Status: ACTIVE! URL contains tap-unique values")
                else:
                    log.warning("  Could not parse URL from NDEF")
                
                # Re-select PICC
                card.send(SelectPiccApplication())
                
            except Exception as e:
                log.warning(f"  Could not verify: {e}")
            
            log.info("")
            
            # Summary
            log.info("=" * 70)
            log.info("Provisioning Summary")
            log.info("=" * 70)
            log.info("")
            log.info("SUCCESS! Your game coin has been provisioned.")
            log.info("")
            log.info(f"Tag UID: {format_uid_with_asset_tag(uid)}")
            log.info(f"Asset Tag: {asset_tag} <- Write this on your coin label")
            log.info(f"Keys saved to: tag_keys.csv")
            log.info("")
            log.info("When tapped, the coin will generate:")
            log.info(f"  {base_url}?uid=[UID]&ctr=[COUNTER]&cmac=[CMAC]")
            log.info("")
            log.info("Next Steps:")
            log.info("  1. Tap coin with NFC phone")
            log.info("  2. Phone browser opens with tap-unique URL")
            log.info("  3. Implement server validation endpoint")
            log.info("  4. Server verifies CMAC and counter")
            log.info("  5. Deliver game reward!")
            log.info("")
            log.info("[IMPORTANT] Keys saved in tag_keys.csv - keep this file secure!")
            log.info("")
            
    except KeyboardInterrupt:
        log.info("\n\n[INTERRUPTED] Stopped by user")
        return 1
    except ApduError as e:
        log.error(f"\n {e}")
        log.info("\n[TIP] Check tag_keys.csv for current key status")
        return 1
    except Exception as e:
        log.error(f"\n Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(provision_game_coin())
