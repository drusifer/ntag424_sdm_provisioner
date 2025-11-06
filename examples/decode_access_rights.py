#!/usr/bin/env python3
"""Decode current access rights"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ntag424_sdm_provisioner.constants import AccessRights, AccessRight

# Current file has: E0EE
current_bytes = bytes([0xE0, 0xEE])
print(f"Current AccessRights bytes: {current_bytes.hex().upper()}")
print()

# Decode using from_bytes
current_rights = AccessRights.from_bytes(current_bytes)
print(f"Decoded:")
print(f"  Read:      {current_rights.read.name} (0x{current_rights.read.value:X})")
print(f"  Write:     {current_rights.write.name} (0x{current_rights.write.value:X})")
print(f"  ReadWrite: {current_rights.read_write.name} (0x{current_rights.read_write.value:X})")
print(f"  Change:    {current_rights.change.name} (0x{current_rights.change.value:X})")
print()

# Encode back to verify
encoded = current_rights.to_bytes()
print(f"Re-encoded: {encoded.hex().upper()}")
print(f"Match: {encoded == current_bytes}")
print()

# What we want to set
our_rights = AccessRights(
    read=AccessRight.FREE,
    write=AccessRight.FREE,
    read_write=AccessRight.FREE,
    change=AccessRight.KEY_0
)
our_bytes = our_rights.to_bytes()
print(f"Our AccessRights: {our_bytes.hex().upper()}")
print(f"Match current: {our_bytes == current_bytes}")

