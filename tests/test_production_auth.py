#!/usr/bin/env python3
"""
Test production auth_session.py with verified crypto_primitives integration.

This verifies that auth_session.py correctly uses crypto_primitives for all operations.
"""

import logging
import sys
from pathlib import Path

# Add tests directory to path
tests_dir = Path(__file__).parent
sys.path.insert(0, str(tests_dir))

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)-8s [%(name)s] %(message)s'
)
log = logging.getLogger(__name__)

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.commands.sdm_commands import (
    SelectPiccApplication,
    GetChipVersion
)
from ntag424_sdm_provisioner.commands.change_key import ChangeKey


def test_production_auth():
    """Test production auth_session with verified crypto."""
    
    log.info("="*70)
    log.info("PRODUCTION AUTH SESSION TEST - With Verified Crypto Primitives")
    log.info("="*70)
    
    try:
        with CardManager(reader_index=0) as card:
            # Select PICC
            log.info("Step 1: Select PICC Application")
            SelectPiccApplication().execute(card)
            log.info("  [OK]")
            
            # Get UID from chip version response
            log.info("Step 2: Get Card UID")
            version_info = GetChipVersion().execute(card)
            uid = version_info.uid
            log.info(f"  UID: {uid.hex().upper()}")
            
            # Get key from manager
            log.info("Step 3: Get Key from Key Manager")
            key_mgr = CsvKeyManager()
            
            try:
                saved_keys = key_mgr.get_tag_keys(uid)
                auth_key = saved_keys.get_picc_master_key_bytes()
                log.info(f"  Using saved key (status: {saved_keys.status})")
            except Exception:
                auth_key = bytes(16)  # Factory default
                log.info("  Using factory key (tag not in database)")
            
            log.debug(f"  Key: {auth_key.hex()}")
            
            # Authenticate using production code
            log.info("Step 4: Authenticate EV2 (Production Code)")
            auth_session = Ntag424AuthSession(auth_key)
            session_keys = auth_session.authenticate(card, key_no=0)
            log.info("  [OK]")
            log.info(f"  Session ENC: {session_keys.session_enc_key.hex()}")
            log.info(f"  Session MAC: {session_keys.session_mac_key.hex()}")
            log.info(f"  Ti: {session_keys.ti.hex()}")
            log.info(f"  CmdCtr: {session_keys.cmd_counter}")
            
            # Try a ChangeKey command to verify session works
            log.info("Step 5: ChangeKey (same key, for testing)")
            
            # Build ChangeKey command
            change_key_cmd = ChangeKey(
                key_no=0,
                new_key=auth_key,  # Change to same key
                old_key=None,
                key_version=0x00
            )
            
            # Get the raw APDU data
            key_data = change_key_cmd.build_key_data()
            log.debug(f"  Key data: {key_data.hex()}")
            
            # Encrypt and MAC using auth_session
            encrypted = auth_session.encrypt_data(key_data)
            log.debug(f"  Encrypted ({len(encrypted)} bytes): {encrypted.hex()}")
            
            # Apply CMAC
            cmd_header = bytes([0x90, 0xC4, 0x00, 0x00])
            maced_data = auth_session.apply_cmac(cmd_header, bytes([0x00]) + encrypted)
            log.debug(f"  With CMAC ({len(maced_data)} bytes): {maced_data.hex()}")
            
            # Send APDU
            apdu = list(cmd_header) + [len(maced_data)] + list(maced_data) + [0x00]
            log.debug(f"  Sending APDU ({len(apdu)} bytes)")
            
            response, sw1, sw2 = card.connection.transmit(apdu)
            log.debug(f"  Response: SW={sw1:02X}{sw2:02X}")
            
            if (sw1, sw2) == (0x91, 0x00):
                log.info("  [OK]")
                log.info("")
                log.info("="*70)
                log.info("SUCCESS! Production auth_session works with crypto_primitives!")
                log.info("="*70)
                return True
            else:
                log.error(f"  [FAILED] SW={sw1:02X}{sw2:02X}")
                return False
            
    except Exception as e:
        log.error(f"[FAILED] {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_production_auth()
    sys.exit(0 if success else 1)

