#!/usr/bin/env python3
"""
Test if key encoding is consistent between authentication and ChangeKey
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ntag424_sdm_provisioner.csv_key_manager import TagKeys

# Create test keys
test_uid = "04C3664A2F7080"
keys = TagKeys.from_factory_keys(test_uid)

print("Factory Keys Test")
print("=" * 70)
print()

# Get keys as bytes
picc_key_bytes = keys.get_picc_master_key_bytes()
print(f"PICC Master Key (hex string): {keys.picc_master_key}")
print(f"PICC Master Key (bytes):      {picc_key_bytes.hex()}")
print(f"PICC Master Key (repr):       {picc_key_bytes}")
print(f"Length: {len(picc_key_bytes)} bytes")
print()

# Compare with direct factory key
from ntag424_sdm_provisioner.key_manager_interface import KEY_DEFAULT_FACTORY
print(f"KEY_DEFAULT_FACTORY:          {KEY_DEFAULT_FACTORY.hex()}")
print(f"Match: {picc_key_bytes == KEY_DEFAULT_FACTORY}")
print()

# Test custom key
print("Custom Key Test")
print("=" * 70)
print()

custom_key_hex = "0123456789ABCDEF0123456789ABCDEF"
keys2 = TagKeys(
    uid=test_uid,
    picc_master_key=custom_key_hex,
    app_read_key="FEDCBA9876543210FEDCBA9876543210",
    sdm_mac_key="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    provisioned_date="2025-11-02",
    status="test",
    notes=""
)

custom_bytes = keys2.get_picc_master_key_bytes()
print(f"Custom key (hex string): {keys2.picc_master_key}")
print(f"Custom key (bytes):      {custom_bytes.hex()}")
print(f"Uppercase match:         {custom_bytes.hex().upper() == custom_key_hex}")
print(f"Lowercase match:         {custom_bytes.hex() == custom_key_hex.lower()}")
print()

# Check byte order
print("Byte Order Check")
print("=" * 70)
print()
print("First 4 bytes:")
print(f"  Hex string: {keys2.picc_master_key[:8]}")
print(f"  As bytes:   {custom_bytes[:4].hex().upper()}")
print(f"  Match:      {custom_bytes[:4].hex().upper() == keys2.picc_master_key[:8]}")
print()

