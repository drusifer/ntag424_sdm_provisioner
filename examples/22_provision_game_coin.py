#!/usr/bin/env python3
"""
Example 22: Provision Game Coin with SDM/SUN

This example demonstrates complete end-to-end provisioning of an NTAG424 DNA
tag for use as a game coin with Secure Unique NFC (SUN) authentication.

Refactored using OOP principles for clarity and maintainability.
"""

import sys
import os
from typing import Optional, Tuple
from dataclasses import dataclass

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ntag424_sdm_provisioner.hal import CardManager, NTag424CardConnection
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, TagKeys
from ntag424_sdm_provisioner.constants import GAME_COIN_BASE_URL, NdefUriPrefix
from ntag424_sdm_provisioner.uid_utils import format_uid_with_asset_tag, uid_to_asset_tag
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
from ntag424_sdm_provisioner.commands.authenticate_ev2 import AuthenticateEV2
from ntag424_sdm_provisioner.commands.change_key import ChangeKey
from ntag424_sdm_provisioner.commands.change_file_settings import ChangeFileSettings
from ntag424_sdm_provisioner.commands.sun_commands import WriteNdefMessage
from ntag424_sdm_provisioner.commands.iso_commands import ISOSelectFile, ISOFileID, ISOReadBinary
from ntag424_sdm_provisioner.commands.base import ApduError
from ntag424_sdm_provisioner.commands.sdm_helpers import build_ndef_uri_record, calculate_sdm_offsets
from ntag424_sdm_provisioner.constants import (
    SDMUrlTemplate, SDMConfiguration, CommMode, FileOption,
    AccessRight, AccessRights, Ntag424VersionInfo
)
from ntag424_sdm_provisioner.trace_util import trace_block

import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


@dataclass
class TagStateDecision:
    """Decision about how to proceed with tag provisioning."""
    should_provision: bool
    was_reset: bool
    use_factory_keys: bool


class NdefUrlReader:
    """Handles reading and parsing NDEF URL records from tags."""
    
    def __init__(self, card: NTag424CardConnection):
        self.card = card
    
    def read_url(self) -> Optional[str]:
        """Read URL from NDEF file, return None if unable to parse."""
        try:
            self.card.send(ISOSelectFile(ISOFileID.NDEF_FILE))
            ndef_data = self.card.send(ISOReadBinary(offset=0, length=200))
            url = self._parse_url_from_ndef(bytes(ndef_data))
            self.card.send(SelectPiccApplication())  # Re-select for next ops
            return url
        except Exception as e:
            log.warning(f"Could not read NDEF: {e}")
            return None
    
    def _parse_url_from_ndef(self, ndef_bytes: bytes) -> Optional[str]:
        """Extract URL from NDEF TLV structure."""
        if 0x55 not in ndef_bytes:
            return None
        
        uri_type_pos = ndef_bytes.index(0x55)
        prefix_code = ndef_bytes[uri_type_pos + 1]
        url_start = uri_type_pos + 2
        url_end = ndef_bytes.index(0xFE) if 0xFE in ndef_bytes else len(ndef_bytes)
        
        try:
            prefix = NdefUriPrefix(prefix_code).to_prefix_string()
        except ValueError:
            prefix = ""
        
        url_suffix = ndef_bytes[url_start:url_end].decode('utf-8', errors='ignore')
        return prefix + url_suffix


class TagStateManager:
    """Manages tag state detection and user interaction."""
    
    def __init__(self, card: NTag424CardConnection, key_mgr: CsvKeyManager):
        self.card = card
        self.key_mgr = key_mgr
        self.url_reader = NdefUrlReader(card)
    
    def check_and_prepare(self, uid: bytes, target_url: str) -> TagStateDecision:
        """
        Check tag state and determine provisioning strategy.
        
        Returns TagStateDecision with provisioning instructions.
        """
        with trace_block("Tag Status Check"):
            # Always show database status first
            try:
                current_keys = self.key_mgr.get_tag_keys(uid)
                log.info("")
                log.info(f"Database Status: {current_keys.status.upper()}")
                if current_keys.provisioned_date:
                    log.info(f"  Last Modified: {current_keys.provisioned_date}")
                if current_keys.notes:
                    log.info(f"  Notes: {current_keys.notes}")
            except Exception:
                log.info("")
                log.info("Database Status: NOT IN DATABASE")
                current_keys = None
            
            # Decide action based on database status (don't test auth - saves attempts)
            log.info("")
            
            if not current_keys:
                # Not in database - assume factory
                log.info("✓ Assuming factory keys - ready to provision")
                return TagStateDecision(True, False, True)
            
            # In database - decide based on status
            if current_keys.status == "provisioned":
                return self._handle_provisioned_tag(current_keys, target_url)
            
            elif current_keys.status in ["failed", "pending"]:
                # Bad state - offer reset
                log.warning("✗ Tag in bad state (failed/pending provision)")
                log.info("  Options:")
                log.info("    1 = Reset with saved keys")
                log.info("    2 = Reset with factory keys")
                log.info("    3 = Try provision anyway")
                log.info("    4 = Cancel")
                response = input("Select (1-4): ").strip()
                
                if response == '1':
                    try:
                        saved_key = current_keys.get_picc_master_key_bytes()
                        self._reset_to_factory_complete(uid, auth_key=saved_key, key_desc="saved")
                        return TagStateDecision(True, True, True)
                    except Exception as e:
                        log.error(f"✗ Reset failed: {e}")
                        return TagStateDecision(False, False, False)
                elif response == '2':
                    try:
                        self._reset_to_factory_complete(uid, auth_key=bytes(16), key_desc="factory")
                        return TagStateDecision(True, True, True)
                    except Exception as e:
                        log.error(f"✗ Reset failed: {e}")
                        return TagStateDecision(False, False, False)
                elif response == '3':
                    log.info("  Attempting provision with factory keys...")
                    return TagStateDecision(True, False, True)
                else:
                    log.info("Cancelled")
                    return TagStateDecision(False, False, False)
            
            else:  # factory
                log.info("✓ Factory state - ready to provision")
                return TagStateDecision(True, False, True)
    
    def _handle_provisioned_tag(self, keys: TagKeys, target_url: str) -> TagStateDecision:
        """Handle healthy provisioned tag - offer URL update."""
        # Read current URL
        tap_url = self.url_reader.read_url()
        if tap_url:
            log.info(f"  Current Tap URL: {tap_url}")
        
        # Show comparison
        saved_url = keys.notes if keys.notes else "(no URL saved)"
        log.info(f"  Saved URL: {saved_url}")
        log.info(f"  Target URL: {target_url}")
        log.info("")
        
        if tap_url and tap_url == target_url:
            log.info("✓ URLs match - coin is correctly configured")
            return TagStateDecision(False, False, False)
        
        log.info("Options: 1=Update URL | 2=Re-provision | 3=Cancel")
        response = input("Select (1-3): ").strip()
        
        should_provision = response in ['1', '2']
        return TagStateDecision(should_provision, False, False)
    
    def _reset_with_key(self, uid: bytes, auth_key: bytes, key_description: str):
        """Reset ONLY Key 0 to factory defaults."""
        factory_key = bytes(16)
        with trace_block(f"Reset Key 0 (auth with {key_description} key)"):
            auth_conn = AuthenticateEV2(key=auth_key, key_no=0)(self.card)
            auth_conn.send(ChangeKey(0, factory_key, factory_key, 0x00))
        log.info(f"  Key 0 reset (used {key_description} key)")
    
    def _reset_to_factory_complete(self, uid: bytes, auth_key: bytes = None, key_desc: str = "factory"):
        """Reset ALL keys (0, 1, 3) to factory defaults."""
        if auth_key is None:
            auth_key = bytes(16)
        
        factory_key = bytes(16)
        
        log.info(f"Resetting all keys to factory defaults (auth with {key_desc} key)...")
        
        # Get current keys from database to know old Key 1 and Key 3
        try:
            current_keys = self.key_mgr.get_tag_keys(uid)
            old_key_1 = current_keys.get_app_read_key_bytes()
            old_key_3 = current_keys.get_sdm_mac_key_bytes()
        except Exception:
            # Not in database or keys unavailable - assume factory
            log.warning("  Cannot get old keys from database - assuming factory")
            old_key_1 = factory_key
            old_key_3 = factory_key
        
        try:
            with trace_block("Factory Reset - All Keys"):
                with AuthenticateEV2(key=auth_key, key_no=0)(self.card) as auth_conn:
                    # Reset Key 0
                    log.info("  Resetting Key 0...")
                    auth_conn.send(ChangeKey(0, factory_key, None, 0x00))
                    log.info("    ✓ Key 0 reset")
                
                # Re-authenticate with factory Key 0
                log.info("  Re-authenticating with factory Key 0...")
                with AuthenticateEV2(key=factory_key, key_no=0)(self.card) as auth_conn:
                    # Reset Key 1 (need old key for XOR)
                    log.info(f"  Resetting Key 1 (old key: {old_key_1.hex()[:16]}...)...")
                    auth_conn.send(ChangeKey(1, factory_key, old_key_1, 0x00))
                    log.info("    ✓ Key 1 reset")
                    
                    # Reset Key 3 (need old key for XOR)
                    log.info(f"  Resetting Key 3 (old key: {old_key_3.hex()[:16]}...)...")
                    auth_conn.send(ChangeKey(3, factory_key, old_key_3, 0x00))
                    log.info("    ✓ Key 3 reset")
            
            # Update database
            factory_keys = TagKeys.from_factory_keys(uid.hex().upper())
            self.key_mgr.save_tag_keys(uid, factory_keys)
            
            log.info("")
            log.info("✓ Factory reset complete - all keys are 0x00")
            log.info("")
            
        except Exception as e:
            log.error(f"Factory reset failed: {e}")
            raise
    
    def _reset_to_factory(self, uid: bytes):
        """Reset tag keys to factory defaults (convenience wrapper)."""
        self._reset_to_factory_complete(uid, bytes(16), "factory")


class KeyChangeOrchestrator:
    """Orchestrates the two-session key change process."""
    
    def __init__(self, card: NTag424CardConnection):
        self.card = card
    
    def change_all_keys(self, old_picc_key: bytes, new_keys: TagKeys):
        """Change keys using two-phase protocol (prevents brick)."""
        log.info("  [Session 1] Changing Key 0...")
        self._change_picc_master_key(old_picc_key, new_keys)
        
        log.info("")
        log.info("  [Session 2] Changing Key 1 and Key 3...")
        log.info("    (Re-authenticating with NEW Key 0)")
        self._change_application_keys(new_keys)
        
        log.info("    All keys changed successfully")
        log.info("")
    
    def _change_picc_master_key(self, old_key: bytes, new_keys: TagKeys):
        """Session 1: Change PICC Master Key (Key 0)."""
        with trace_block("Session 1: Change Key 0"):
            with AuthenticateEV2(old_key, key_no=0)(self.card) as auth_conn:
                log.info("    Authenticated with old Key 0")
                
                with trace_block("ChangeKey 0"):
                    res = auth_conn.send(ChangeKey(
                        key_no_to_change=0,
                        new_key=new_keys.get_picc_master_key_bytes(),
                        old_key=None
                    ))
                    log.info(f"    Key 0 changed - {res}")
                
                log.info("    Session 1 ended (invalid after Key 0 change)")
    
    def _change_application_keys(self, new_keys: TagKeys):
        """Session 2: Change Application Keys (Key 1 and 3)."""
        with trace_block("Session 2: Change Keys 1 and 3"):
            new_picc_key = new_keys.get_picc_master_key_bytes()
            
            with AuthenticateEV2(new_picc_key, key_no=0)(self.card) as auth_conn:
                log.info("    Authenticated with NEW Key 0")
                
                # Change Key 1 (App Read)
                with trace_block("ChangeKey 1"):
                    res = auth_conn.send(ChangeKey(
                        key_no_to_change=1,
                        new_key=new_keys.get_app_read_key_bytes(),
                        old_key=None
                    ))
                    log.info(f"    Key 1 changed - {res}")
                
                # Change Key 3 (SDM MAC)
                with trace_block("ChangeKey 3"):
                    res = auth_conn.send(ChangeKey(
                        key_no_to_change=3,
                        new_key=new_keys.get_sdm_mac_key_bytes(),
                        old_key=None
                    ))
                    log.info(f"    Key 3 changed - {res}")


class SDMConfigurator:
    """Configures SDM (Secure Dynamic Messaging) on NDEF file."""
    
    def __init__(self, card: NTag424CardConnection):
        self.card = card
    
    def configure_and_write_ndef(self, url_template: str, base_url: str):
        """Configure SDM and write NDEF message."""
        log.info("  [Session 2] Configuring SDM and writing NDEF...")
        log.info("-" * 70)
        
        # Build NDEF with placeholders
        ndef_message = build_ndef_uri_record(url_template)
        log.info(f"    NDEF Size: {len(ndef_message)} bytes")
        
        # Calculate offsets
        offsets = self._calculate_offsets(base_url, url_template)
        log.info(f"    SDM Offsets: {offsets}")
        
        # Configure SDM
        self._configure_sdm(offsets)
        
        # Write NDEF
        self._write_ndef(ndef_message)
        
        log.info("")
    
    def _calculate_offsets(self, base_url: str, url_template: str):
        """Calculate SDM placeholder offsets."""
        template = SDMUrlTemplate(
            base_url=base_url,
            uid_placeholder="00000000000000",
            cmac_placeholder="0000000000000000",
            read_ctr_placeholder="000000",
            enc_placeholder=None
        )
        return calculate_sdm_offsets(template)
    
    def _configure_sdm(self, offsets):
        """Apply SDM configuration to NDEF file."""
        access_rights = AccessRights(
            read=AccessRight.FREE,
            write=AccessRight.KEY_0,
            read_write=AccessRight.FREE,
            change=AccessRight.FREE
        )
        
        sdm_config = SDMConfiguration(
            file_no=0x02,
            comm_mode=CommMode.PLAIN,
            access_rights=access_rights,
            enable_sdm=True,
            sdm_options=(FileOption.UID_MIRROR | FileOption.READ_COUNTER),
            offsets=offsets
        )
        
        log.info(f"    Config: {sdm_config}")
        log.info("    Configuring SDM...")
        
        try:
            self.card.send(ChangeFileSettings(sdm_config))
            log.info("    SDM configured successfully!")
        except ApduError as e:
            log.warning(f"    SDM configuration failed: {e}")
            log.info("    Continuing with NDEF write (SDM placeholders won't work)")
    
    def _write_ndef(self, ndef_message: bytes):
        """Write NDEF message to tag."""
        log.info("    Writing NDEF message...")
        self.card.send(ISOSelectFile(ISOFileID.NDEF_FILE))
        log.info(f"    Writing {len(ndef_message)} bytes (chunked)...")
        # WriteNdefMessage uses special chunked write - keep old execute() pattern
        WriteNdefMessage(ndef_data=ndef_message).execute(self.card)
        log.info("    NDEF message written")
        self.card.send(SelectPiccApplication())


class ProvisioningOrchestrator:
    """Orchestrates the complete provisioning workflow."""
    
    def __init__(self, card: NTag424CardConnection, key_mgr: CsvKeyManager):
        self.card = card
        self.key_mgr = key_mgr
        self.state_mgr = TagStateManager(card, key_mgr)
        self.key_changer = KeyChangeOrchestrator(card)
        self.sdm_config = SDMConfigurator(card)
        self.url_reader = NdefUrlReader(card)
    
    def provision(self, base_url: str = GAME_COIN_BASE_URL) -> int:
        """Execute complete provisioning workflow."""
        self._print_banner()
        
        try:
            # Get chip info
            version_info = self._get_chip_info()
            uid = version_info.uid
            
            # Check tag state and get decision
            decision = self.state_mgr.check_and_prepare(uid, base_url)
            if not decision.should_provision:
                log.info("\nNothing to do - exiting")
                return 0
            
            # Get current keys
            current_keys = self._get_current_keys(uid, decision)
            
            # Build URL template
            url_template = self._build_url_template(base_url)
            
            # Provision with two-phase commit
            self._execute_provisioning(uid, current_keys, url_template, base_url)
            
            # Verify
            self._verify_provisioning(uid, base_url)
            
            self._print_summary(uid, base_url)
            return 0
            
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
    
    def _print_banner(self):
        """Print startup banner."""
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
    
    def _get_chip_info(self) -> Ntag424VersionInfo:
        """Read chip version and UID."""
        log.info("Step 1: Get Chip Information")
        log.info("-" * 70)
        
        self.card.send(SelectPiccApplication())
        log.info("  Application selected")
        
        version_info = self.card.send(GetChipVersion())
        uid = version_info.uid
        asset_tag = uid_to_asset_tag(uid)
        
        log.info(f"  Chip UID: {format_uid_with_asset_tag(uid)}")
        log.info(f"  Asset Tag: {asset_tag} (write this on physical label)")
        log.info(f"  Chip Info: {version_info}")
        log.info("")
        
        return version_info
    
    def _get_current_keys(self, uid: bytes, decision: TagStateDecision) -> TagKeys:
        """Load current keys from database or use factory keys."""
        log.info("Step 2: Load Current Keys")
        log.info("-" * 70)
        
        if decision.was_reset or decision.use_factory_keys:
            reason = "just reset" if decision.was_reset else "factory assumed"
            log.info(f"  Using factory keys ({reason})")
            keys = TagKeys.from_factory_keys(uid.hex().upper())
        else:
            keys = self.key_mgr.get_tag_keys(uid)
            log.info("  Using saved keys for re-provision")
        
        log.info(f"  Current Status: {keys.status}")
        log.info("")
        return keys
    
    def _build_url_template(self, base_url: str) -> str:
        """Build URL template with SDM placeholders."""
        log.info("Step 3: Build SDM URL Template")
        log.info("-" * 70)
        
        url_template = (
            f"{base_url}?"
            f"uid=00000000000000&"
            f"ctr=000000&"
            f"cmac=0000000000000000"
        )
        
        log.info(f"  URL: {url_template}")
        log.info(f"  Length: {len(url_template)} characters")
        log.info("")
        
        return url_template
    
    def _execute_provisioning(self, uid: bytes, current_keys: TagKeys, 
                             url_template: str, base_url: str):
        """Execute the provisioning with two-phase commit."""
        log.info("Step 4: Change All Keys (Per charts.md sequence)")
        log.info("-" * 70)
        
        current_picc_key = current_keys.get_picc_master_key_bytes()
        log.info(f"  Authenticating with {'factory' if current_keys.status == 'factory' else 'saved'} PICC Master Key...")
        
        # Two-phase commit
        with self.key_mgr.provision_tag(uid, url=base_url) as new_keys:
            log.info("  [Phase 1] New keys generated and saved (status='pending')")
            log.info(f"    PICC Master: {new_keys.picc_master_key[:16]}...")
            log.info(f"    App Read:    {new_keys.app_read_key[:16]}...")
            log.info(f"    SDM MAC:     {new_keys.sdm_mac_key[:16]}...")
            log.info("")
            
            # Change all keys
            self.key_changer.change_all_keys(current_picc_key, new_keys)
            
            # Configure SDM and write NDEF (still in auth session)
            self.sdm_config.configure_and_write_ndef(url_template, base_url)
            
            log.info("  [Phase 2] Provisioning complete!")
            log.info("")
    
    def _verify_provisioning(self, uid: bytes, base_url: str):
        """Verify provisioning by simulating phone tap."""
        log.info("Step 6: Verify Provisioning (Simulate Phone Tap)")
        log.info("-" * 70)
        log.info("  Reading NDEF unauthenticated (like a phone would)...")
        
        tap_url = self.url_reader.read_url()
        if tap_url:
            log.info("")
            log.info(f"  Tap URL: {tap_url}")
            log.info("")
            
            if "00000000000000" in tap_url:
                log.info("  SDM Status: Placeholders present (SDM not fully active)")
                log.info("  URL will be static until SDM is properly configured")
            else:
                log.info("  SDM Status: ACTIVE! URL contains tap-unique values")
        else:
            log.warning("  Could not verify provisioning")
        
        log.info("")
    
    def _print_summary(self, uid: bytes, base_url: str):
        """Print provisioning summary."""
        asset_tag = uid_to_asset_tag(uid)
        
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


def main():
    """Main entry point."""
    key_mgr = CsvKeyManager()
    
    with CardManager(reader_index=0) as card:
        log.info("Please place your NTAG424 DNA tag on the reader...")
        log.info("")
        log.info("Connected to reader")
        log.info("")
        
        orchestrator = ProvisioningOrchestrator(card, key_mgr)
        return orchestrator.provision()


if __name__ == "__main__":
    sys.exit(main())
