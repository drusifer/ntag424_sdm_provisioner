#!/usr/bin/env python3
"""
Test ChangeFileSettings without authentication (since Change=FREE)
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.commands.change_file_settings import ChangeFileSettings
from ntag424_sdm_provisioner.constants import (
    SDMUrlTemplate,
    SDMConfiguration,
    SDMOffsets,
    CommMode,
    FileOption,
    AccessRight,
    AccessRights,
)
from ntag424_sdm_provisioner.commands.sdm_helpers import calculate_sdm_offsets

# Build SDM config
base_url = "https://globalheadsandtails.com/tap"
uid_placeholder = "00000000000000"
counter_placeholder = "000000"
cmac_placeholder = "0000000000000000"

template = SDMUrlTemplate(
    base_url=base_url,
    uid_placeholder=uid_placeholder,
    cmac_placeholder=cmac_placeholder,
    read_ctr_placeholder=counter_placeholder,
    enc_placeholder=None
)

offsets = calculate_sdm_offsets(template)

access_rights = AccessRights(
    read=AccessRight.FREE,
    write=AccessRight.KEY_0,
    read_write=AccessRight.FREE,
    change=AccessRight.FREE
)

sdm_config = SDMConfiguration(
    file_no=0x02,
    comm_mode=CommMode.PLAIN,  # Keep it PLAIN
    access_rights=access_rights,
    enable_sdm=True,
    sdm_options=(
        FileOption.UID_MIRROR |
        FileOption.READ_COUNTER
    ),
    offsets=offsets
)

print("Testing ChangeFileSettings WITHOUT authentication")
print("=" * 70)
print()

with CardManager(reader_index=0) as card:
    SelectPiccApplication().execute(card)
    version = GetChipVersion().execute(card)
    print(f"Tag UID: {version.uid.hex().upper()}")
    print()
    
    print(f"SDM Config: {sdm_config}")
    print()
    
    print("Sending ChangeFileSettings (no auth, no CMAC)...")
    try:
        # Send WITHOUT session parameter (no CMAC)
        result = ChangeFileSettings(sdm_config).execute(card)
        print(f"[SUCCESS] {result}")
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

