#!/usr/bin/env python3
"""
Debug ChangeFileSettings payload
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ntag424_sdm_provisioner.constants import (
    SDMUrlTemplate,
    SDMConfiguration,
    SDMOffsets,
    CommMode,
    FileOption,
    AccessRight,
    AccessRights,
)
from ntag424_sdm_provisioner.commands.sdm_helpers import build_sdm_settings_payload, calculate_sdm_offsets

# Build the same config as example 22
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

template = SDMUrlTemplate(
    base_url=base_url,
    uid_placeholder=uid_placeholder,
    cmac_placeholder=cmac_placeholder,
    read_ctr_placeholder=counter_placeholder,
    enc_placeholder=None
)

offsets = calculate_sdm_offsets(template)
print(f"Calculated offsets: {offsets}")
print()

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
    sdm_options=(
        FileOption.UID_MIRROR |
        FileOption.READ_COUNTER
    ),
    offsets=offsets
)

print(f"SDM Config: {sdm_config}")
print()

# Build payload
payload = build_sdm_settings_payload(sdm_config)

print("Payload breakdown:")
print(f"  Total length: {len(payload)} bytes")
print(f"  Hex: {payload.hex().upper()}")
print()

# Parse it byte by byte
idx = 0
print("Byte-by-byte analysis:")
print(f"  [{idx}] FileOption: 0x{payload[idx]:02X} (CommMode={payload[idx] & 0x03}, SDM={'enabled' if payload[idx] & 0x40 else 'disabled'})")
idx += 1

print(f"  [{idx}-{idx+1}] AccessRights: {payload[idx:idx+2].hex().upper()}")
idx += 2

if sdm_config.enable_sdm:
    print(f"  [{idx}] SDMOptions: 0x{payload[idx]:02X} (UID_MIRROR={bool(payload[idx] & 0x80)}, READ_COUNTER={bool(payload[idx] & 0x40)})")
    idx += 1
    
    print(f"  [{idx}-{idx+1}] SDMAccessRights: {payload[idx:idx+2].hex().upper()}")
    idx += 2
    
    # UIDOffset
    if len(payload) > idx:
        uid_off = payload[idx] | (payload[idx+1] << 8) | (payload[idx+2] << 16)
        print(f"  [{idx}-{idx+2}] UIDOffset: {uid_off} (0x{payload[idx:idx+3].hex().upper()})")
        idx += 3
    
    # ReadCtrOffset
    if len(payload) > idx:
        ctr_off = payload[idx] | (payload[idx+1] << 8) | (payload[idx+2] << 16)
        print(f"  [{idx}-{idx+2}] ReadCtrOffset: {ctr_off} (0x{payload[idx:idx+3].hex().upper()})")
        idx += 3
    
    # Any remaining bytes?
    if len(payload) > idx:
        print(f"  [{idx}-{len(payload)-1}] UNEXPECTED BYTES: {payload[idx:].hex().upper()}")

print()
print("Expected for minimal SDM (UID + Counter):")
print("  1 byte  - FileOption")
print("  2 bytes - AccessRights") 
print("  1 byte  - SDMOptions")
print("  2 bytes - SDMAccessRights")
print("  3 bytes - UIDOffset")
print("  3 bytes - ReadCtrOffset")
print("  = 12 bytes total")

