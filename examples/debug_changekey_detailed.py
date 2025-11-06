#!/usr/bin/env python3
"""Debug ChangeKey step-by-step"""

import sys
import os
import zlib

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from Crypto.Cipher import AES
from Crypto.Hash import CMAC

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion, AuthenticateEV2
from ntag424_sdm_provisioner.key_manager_interface import KEY_DEFAULT_FACTORY

# Test key for Key 0
new_key = bytes([0x01] + [0x00] * 15)  # Simple test key
old_key = KEY_DEFAULT_FACTORY
key_version = 0x00
key_no = 0

print("=" * 70)
print("ChangeKey Debug - Step by Step")
print("=" * 70)
print()
print(f"Key Number: {key_no}")
print(f"Old Key: {old_key.hex()}")
print(f"New Key: {new_key.hex()}")
print(f"Version: 0x{key_version:02X}")
print()

# Step 1: Build 32-byte key data
print("Step 1: Build 32-byte Key Data")
print("-" * 70)
key_data = bytearray(32)

if key_no == 0:
    key_data[0:16] = new_key
    key_data[16] = key_version
    key_data[17] = 0x80
    print("  Format: newKey(16) + version(1) + 0x80 + padding(14)")
else:
    xored = bytes(a ^ b for a, b in zip(new_key, old_key))
    key_data[0:16] = xored
    key_data[16] = key_version
    crc = zlib.crc32(new_key) & 0xFFFFFFFF
    crc_inverted = crc ^ 0xFFFFFFFF
    key_data[17:21] = crc_inverted.to_bytes(4, byteorder='little')
    key_data[21] = 0x80
    print("  Format: XOR(16) + version(1) + CRC32(4) + 0x80 + padding(10)")
    print(f"  CRC32: 0x{crc:08X}")
    print(f"  CRC32 inverted: 0x{crc_inverted:08X}")

key_data = bytes(key_data)
print(f"  Key Data: {key_data.hex().upper()}")
print(f"  Length: {len(key_data)} bytes")
print()

with CardManager(reader_index=0) as card:
    SelectPiccApplication().execute(card)
    version = GetChipVersion().execute(card)
    print(f"Tag UID: {version.uid.hex().upper()}")
    print()
    
    with AuthenticateEV2(old_key, key_no=0).execute(card) as auth_conn:
        session = auth_conn.session
        
        print("Step 2: Calculate IV for Encryption")
        print("-" * 70)
        ti = session.session_keys.ti
        next_cmd_ctr = session.session_keys.cmd_counter + 1
        cmd_ctr_bytes = next_cmd_ctr.to_bytes(2, 'little')
        
        print(f"  TI: {ti.hex().upper()} ({len(ti)} bytes)")
        print(f"  Next CmdCtr: {next_cmd_ctr} = {cmd_ctr_bytes.hex().upper()}")
        print()
        
        # Build plaintext IV
        plaintext_iv = b'\xA5\x5A' + ti + cmd_ctr_bytes + b'\x00' * 8
        print(f"  Plaintext IV: {plaintext_iv.hex().upper()}")
        
        # Encrypt to get actual IV
        zero_iv = b'\x00' * 16
        cipher_iv = AES.new(session.session_keys.session_enc_key, AES.MODE_CBC, iv=zero_iv)
        actual_iv = cipher_iv.encrypt(plaintext_iv)
        print(f"  Encrypted IV: {actual_iv.hex().upper()}")
        print()
        
        print("Step 3: Encrypt Key Data")
        print("-" * 70)
        cipher = AES.new(session.session_keys.session_enc_key, AES.MODE_CBC, iv=actual_iv)
        encrypted_key_data = cipher.encrypt(key_data)
        print(f"  Encrypted: {encrypted_key_data.hex().upper()}")
        print(f"  Length: {len(encrypted_key_data)} bytes")
        print()
        
        print("Step 4: Calculate CMAC")
        print("-" * 70)
        cmd = 0xC4
        cmac_input = bytes([cmd]) + cmd_ctr_bytes + ti + bytes([key_no]) + encrypted_key_data
        print(f"  CMAC Input: {cmac_input.hex().upper()}")
        print(f"  Length: {len(cmac_input)} bytes")
        print(f"    Cmd:        {cmd:02X} (1 byte)")
        print(f"    CmdCtr:     {cmd_ctr_bytes.hex().upper()} (2 bytes)")
        print(f"    TI:         {ti.hex().upper()} (4 bytes)")
        print(f"    KeyNo:      {key_no:02X} (1 byte)")
        print(f"    Encrypted:  {encrypted_key_data.hex().upper()[:16]}... (32 bytes)")
        
        cmac_obj = CMAC.new(session.session_keys.session_mac_key, ciphermod=AES)
        cmac_obj.update(cmac_input)
        mac = cmac_obj.digest()[:8]
        print(f"  CMAC: {mac.hex().upper()}")
        print()
        
        print("Step 5: Final Command Data")
        print("-" * 70)
        cmd_data = bytes([key_no]) + encrypted_key_data + mac
        print(f"  KeyNo + Encrypted + CMAC: {cmd_data.hex().upper()}")
        print(f"  Total length: {len(cmd_data)} bytes (should be 1 + 32 + 8 = 41)")
        print()
        
        print("Step 6: Full APDU")
        print("-" * 70)
        cmd_header = bytes([0x90, 0xC4, 0x00, 0x00])
        apdu = list(cmd_header) + [len(cmd_data)] + list(cmd_data) + [0x00]
        apdu_hex = ' '.join(f'{b:02X}' for b in apdu)
        print(f"  APDU: {apdu_hex}")
        print(f"  Length: {len(apdu)} bytes")
        print()
        
        print("Arduino expects (line 1044): Lc = 0x29 (41 bytes)")
        print(f"We're sending: Lc = 0x{len(cmd_data):02X} ({len(cmd_data)} bytes)")
        print()

