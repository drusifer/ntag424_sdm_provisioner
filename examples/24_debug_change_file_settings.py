#!/usr/bin/env python3
"""
Example 24: Debug ChangeFileSettings - See Exact APDU Bytes

This script enables detailed logging to see exactly what bytes
are being sent in the ChangeFileSettings command.
"""

import sys
import os
import logging

# Enable DEBUG logging BEFORE imports
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s'
)

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.commands.change_file_settings import ChangeFileSettings
from ntag424_sdm_provisioner.constants import SDMConfiguration, CommMode, FileOption
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.key_manager_interface import KEY_DEFAULT_FACTORY


def debug_change_file_settings():
    """Debug ChangeFileSettings with full logging."""
    
    print("=" * 70)
    print("Example 24: Debug ChangeFileSettings")
    print("=" * 70)
    print()
    
    with CardManager(reader_index=0) as card:
        print("[OK] Connected")
        
        # Select and get version
        SelectPiccApplication().execute(card)
        version = GetChipVersion().execute(card)
        print(f"UID: {version.uid.hex().upper()}")
        print()
        
        # Authenticate
        print("Authenticating...")
        session = Ntag424AuthSession(KEY_DEFAULT_FACTORY)
        session.authenticate(card, key_no=0)
        print("[OK] Authenticated")
        print()
        
        # Build minimal SDM config
        print("Testing MINIMAL SDM config (just UID, no counter)...")
        print("-" * 70)
        
        config = SDMConfiguration(
            file_no=0x02,
            comm_mode=CommMode.PLAIN,  # Try PLAIN first (simplest)
            access_rights=b'\xE0\xEE',  # 2 bytes
            enable_sdm=True,
            sdm_options=FileOption.UID_MIRROR,  # Just UID, no extras
            picc_data_offset=47,  # UID position
            mac_input_offset=0,   # Not used
            mac_offset=0,         # Not used
            read_ctr_offset=None, # No counter (keep it simple)
        )
        
        print(f"Config: {config}")
        print()
        print("Sending ChangeFileSettings...")
        print("(Watch debug logs above for exact APDU bytes)")
        print()
        
        try:
            cmd = ChangeFileSettings(config)
            result = cmd.execute(card, session=session)
            print(f"[SUCCESS] {result}")
        except Exception as e:
            print(f"[ERROR] {e}")
            print()
            print("Analysis:")
            print("  - Check the debug log above for APDU bytes")
            print("  - Compare with NXP spec Section 10.7.1")
            print("  - Look for field count or order mismatch")


if __name__ == "__main__":
    sys.exit(debug_change_file_settings())

