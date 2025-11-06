#!/usr/bin/env python3
"""Test simple authenticated command with new CMAC format"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import (
    SelectPiccApplication,
    GetChipVersion,
    AuthenticateEV2,
    GetFileSettings
)
from ntag424_sdm_provisioner.key_manager_interface import KEY_DEFAULT_FACTORY

print("Testing authenticated command with new CMAC format")
print("=" * 70)
print()

with CardManager(reader_index=0) as card:
    SelectPiccApplication().execute(card)
    version = GetChipVersion().execute(card)
    print(f"UID: {version.uid.hex().upper()}")
    print()
    
    # Test GetFileSettings without auth first (baseline)
    print("Test 1: GetFileSettings (unauthenticated)...")
    try:
        settings = GetFileSettings(file_no=0x02).execute(card)
        print(f"[OK] {settings}")
    except Exception as e:
        print(f"[FAIL] {e}")
    print()
    
    # Now test with authentication
    print("Test 2: Authenticate and send continuation frame...")
    try:
        with AuthenticateEV2(KEY_DEFAULT_FACTORY, key_no=0).execute(card) as auth_conn:
            print("[OK] Authenticated")
            print(f"  Counter: {auth_conn.session.session_keys.cmd_counter}")
            print()
            
            # GetFileSettings has continuation frames that use CMAC
            # This will test if our new CMAC format works
            print("  Sending GetFileSettings (will use CMAC on continuation frames)...")
            settings = GetFileSettings(file_no=0x02).execute(card, session=auth_conn.session)
            print(f"  [OK] {settings}")
            print(f"  [SUCCESS] CMAC format works for authenticated commands!")
    except Exception as e:
        print(f"[FAIL] {e}")
        print("[ERROR] New CMAC format broke authenticated commands")

