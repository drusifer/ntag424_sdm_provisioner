#!/usr/bin/env python3
"""Debug ChangeKey to see exact bytes being sent"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion, AuthenticateEV2
from ntag424_sdm_provisioner.key_manager_interface import KEY_DEFAULT_FACTORY

with CardManager(reader_index=0) as card:
    SelectPiccApplication().execute(card)
    version = GetChipVersion().execute(card)
    print(f"UID: {version.uid.hex().upper()}")
    print()
    
    print("Authenticating...")
    with AuthenticateEV2(KEY_DEFAULT_FACTORY, key_no=0).execute(card) as auth_conn:
        print("[OK] Authenticated")
        print()
        
        session = auth_conn.session
        print(f"Session keys:")
        print(f"  TI: {session.session_keys.ti.hex().upper()} ({len(session.session_keys.ti)} bytes)")
        print(f"  CmdCounter: {session.session_keys.cmd_counter}")
        print(f"  Session ENC: {session.session_keys.session_enc_key.hex().upper()[:32]}...")
        print(f"  Session MAC: {session.session_keys.session_mac_key.hex().upper()[:32]}...")
        print()

