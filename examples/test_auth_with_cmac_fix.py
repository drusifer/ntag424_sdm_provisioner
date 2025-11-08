#!/usr/bin/env python3
"""Test if even-numbered CMAC truncation works with real hardware"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion, AuthenticateEV2, GetKeyVersion
from ntag424_sdm_provisioner.key_manager_interface import KEY_DEFAULT_FACTORY

with CardManager(reader_index=0) as card:
    SelectPiccApplication().execute(card)
    version = GetChipVersion().execute(card)
    print(f"UID: {version.uid.hex().upper()}")
    print()
    
    print("Testing full authentication...")
    try:
        with AuthenticateEV2(KEY_DEFAULT_FACTORY, key_no=0).execute(card) as auth_conn:
            print("[OK] Full authentication successful!")
            print(f"  TI: {auth_conn.session.session_keys.ti.hex().upper()}")
            print(f"  Counter: {auth_conn.session.session_keys.cmd_counter}")
            print()
            
            print("Testing authenticated command (GetKeyVersion)...")
            try:
                # GetKeyVersion requires CommMode.MAC
                key_ver = GetKeyVersion(key_no=0).execute(auth_conn)
                print(f"[OK] GetKeyVersion succeeded: {key_ver}")
                print("[SUCCESS] CMAC truncation fix works!")
            except Exception as e:
                print(f"[FAIL] GetKeyVersion failed: {e}")
                print("[ERROR] CMAC truncation might have broken authenticated commands")
                
    except Exception as e:
        print(f"[FAIL] Authentication failed: {e}")

