#!/usr/bin/env python3
"""
Example 23: Debug SDM Configuration

This script helps debug the ChangeFileSettings length error by logging
every byte of the command payload.
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ntag424_sdm_provisioner.commands.sdm_helpers import build_sdm_settings_payload
from ntag424_sdm_provisioner.constants import SDMConfiguration, CommMode, FileOption


def debug_sdm_config():
    """Debug SDM configuration payload construction."""
    
    print("=" * 70)
    print("Example 23: Debug SDM Configuration")
    print("=" * 70)
    print()
    
    # Test 1: Minimal configuration (SDM disabled)
    print("Test 1: Minimal Config (SDM Disabled)")
    print("-" * 70)
    
    config1 = SDMConfiguration(
        file_no=0x02,
        comm_mode=CommMode.PLAIN,
        access_rights=b'\xEE\xEE',  # All free
        enable_sdm=False,
        sdm_options=0x00,
        picc_data_offset=0,
        mac_input_offset=0,
        mac_offset=0,
    )
    
    payload1 = build_sdm_settings_payload(config1)
    print(f"  Config: {config1}")
    print(f"  Payload bytes: {' '.join(f'{b:02X}' for b in payload1)}")
    print(f"  Payload length: {len(payload1)} bytes")
    print()
    
    # Test 2: SDM enabled with UID mirror only
    print("Test 2: SDM Enabled - UID Mirror Only")
    print("-" * 70)
    
    config2 = SDMConfiguration(
        file_no=0x02,
        comm_mode=CommMode.PLAIN,
        access_rights=b'\xE0\xEE',  # 2 bytes!
        enable_sdm=True,
        sdm_options=FileOption.SDM_ENABLED | FileOption.UID_MIRROR,
        picc_data_offset=47,
        mac_input_offset=47,
        mac_offset=67,
    )
    
    payload2 = build_sdm_settings_payload(config2)
    print(f"  Config: {config2}")
    print(f"  Payload bytes: {' '.join(f'{b:02X}' for b in payload2)}")
    print(f"  Payload length: {len(payload2)} bytes")
    print()
    
    # Test 3: Full SDM with UID + Counter + CMAC
    print("Test 3: Full SDM (UID + Counter + CMAC)")
    print("-" * 70)
    
    config3 = SDMConfiguration(
        file_no=0x02,
        comm_mode=CommMode.PLAIN,
        access_rights=b'\xE0\xEE',  # 2 bytes!
        enable_sdm=True,
        sdm_options=(FileOption.SDM_ENABLED | FileOption.UID_MIRROR | FileOption.READ_COUNTER),
        picc_data_offset=47,
        mac_input_offset=47,
        mac_offset=67,
        read_ctr_offset=47,
    )
    
    payload3 = build_sdm_settings_payload(config3)
    print(f"  Config: {config3}")
    print(f"  Payload bytes: {' '.join(f'{b:02X}' for b in payload3)}")
    print(f"  Payload length: {len(payload3)} bytes")
    print()
    
    # Build full APDU for comparison
    print("Full APDU Construction (Test 3)")
    print("-" * 70)
    
    cmd_header = bytes([0x90, 0x5F, 0x00, 0x00])
    cmd_data = bytes([config3.file_no]) + payload3
    
    # No CMAC for now (plain mode)
    apdu = list(cmd_header) + [len(cmd_data)] + list(cmd_data) + [0x00]
    
    print(f"  CLA INS P1 P2: {' '.join(f'{b:02X}' for b in apdu[:4])}")
    print(f"  Lc: {apdu[4]:02X} ({apdu[4]} bytes)")
    print(f"  Data: {' '.join(f'{b:02X}' for b in apdu[5:-1])}")
    print(f"  Le: {apdu[-1]:02X}")
    print(f"  Total APDU length: {len(apdu)} bytes")
    print()
    
    # Expected according to NXP spec
    print("NXP Spec Reference (Section 10.7.1)")
    print("-" * 70)
    print("  ChangeFileSettings: 90 5F 00 00 [Lc] [Data] 00")
    print("  Data format: [FileNo] [CommMode] [AccessRights] [SDM Options...]")
    print("  SDM Options (if enabled):")
    print("    - SDM Options byte")
    print("    - SDM Access Rights (2 bytes)")
    print("    - PICCDataOffset (3 bytes, LSB-first)")
    print("    - SDMMACInputOffset (3 bytes, LSB-first)")
    print("    - SDMMACOffset (3 bytes, LSB-first)")
    print("    - SDMReadCtrOffset (3 bytes, LSB-first if READ_COUNTER enabled)")
    print()
    
    print("Analysis:")
    print(f"  Expected minimum (SDM disabled): ~3 bytes (FileNo + CommMode + AccessRights)")
    print(f"  Expected with SDM: ~15+ bytes (depends on options)")
    print(f"  Actual payload length: {len(payload3)} bytes")
    print()


if __name__ == "__main__":
    sys.exit(debug_sdm_config())

