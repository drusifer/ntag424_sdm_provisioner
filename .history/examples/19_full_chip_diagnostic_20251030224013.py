#!/usr/bin/env python3
"""
Full Chip Diagnostic - Canonical Example

Demonstrates clean usage of HAL API and command classes to read all available
information from an NTAG424 DNA chip, both before and after authentication.

This is a canonical example showing proper API usage patterns.
"""

import os
import sys
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import (
    SelectPiccApplication,
    GetChipVersion,
    GetFileIds,
    GetFileSettings,
    GetKeyVersion,
    ReadData,
)
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.constants import (
    FACTORY_KEY,
    FileNo,
    KeyNo,
)
from ntag424_sdm_provisioner.commands.base import ApduError


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_subsection(title: str):
    """Print a formatted subsection header."""
    print(f"\n--- {title} ---")


def format_bytes(data: bytes, max_len: int = 32) -> str:
    """Format bytes as hex string with truncation."""
    hex_str = data.hex().upper()
    if len(hex_str) > max_len * 2:
        return hex_str[:max_len*2] + f"... ({len(data)} bytes total)"
    return hex_str


def read_chip_basic_info(card):
    """Read basic chip information (no authentication required)."""
    print_section("1. CHIP VERSION INFORMATION")
    
    try:
        version = GetChipVersion().execute(card)
        
        print(f"Hardware Version: {version.hw_major_version}.{version.hw_minor_version}")
        print(f"Software Version: {version.sw_major_version}.{version.sw_minor_version}")
        print(f"UID: {format_bytes(version.uid)}")
        print(f"Hardware Type: 0x{version.hw_type:02X}")
        print(f"Software Type: 0x{version.sw_type:02X}")
        print(f"Hardware Protocol: {version.hw_protocol}")
        print(f"Software Protocol: {version.sw_protocol}")
        print(f"Storage Size (HW): {version.hw_storage_size} bytes")
        print(f"Storage Size (SW): {version.sw_storage_size} bytes")
        
        if version.batch_no:
            print(f"Batch Number: {format_bytes(version.batch_no)}")
        if version.fab_week and version.fab_year:
            print(f"Fabrication: Week {version.fab_week}, Year {version.fab_year}")
        
        return version
    except Exception as e:
        print(f"[ERROR] Failed to read chip version: {e}")
        return None


def read_file_list(card):
    """Try to read file list, fallback to known file numbers."""
    print_section("2. FILE LIST")
    
    # Try GetFileIds first (may not be supported on NTAG424 DNA)
    try:
        cmd = GetFileIds()
        file_ids = cmd.execute(card)
        
        if not file_ids:
            print("[INFO] GetFileIds returned empty list")
        else:
            print(f"Found {len(file_ids)} file(s):")
            for file_id in file_ids:
                file_name = {
                    FileNo.CC_FILE: "CC_FILE (Capability Container)",
                    FileNo.NDEF_FILE: "NDEF_FILE",
                    FileNo.PROPRIETARY_FILE: "PROPRIETARY_FILE",
                }.get(file_id, "UNKNOWN")
                print(f"  File 0x{file_id:02X}: {file_name}")
            return file_ids
    except ApduError as e:
        if e.sw2 == 0x1C:  # Illegal Command Code
            print("[INFO] GetFileIds not supported (DESFire-only command)")
            print("[INFO] Will try known file numbers instead")
        else:
            print(f"[WARN] GetFileIds failed: {e} (SW={e.sw1:02X}{e.sw2:02X})")
            print("[INFO] Will try known file numbers instead")
    except Exception as e:
        print(f"[WARN] GetFileIds failed: {e}")
        print("[INFO] Will try known file numbers instead")
    
    # Fallback: try known file numbers
    print("\n[INFO] Trying known NTAG424 file numbers:")
    known_files = [FileNo.CC_FILE, FileNo.NDEF_FILE, FileNo.PROPRIETARY_FILE]
    existing_files = []
    
    for file_id in known_files:
        try:
            # Try GetFileSettings to see if file exists (might require auth, but we'll catch that)
            cmd = GetFileSettings(file_no=file_id, session=None)
            cmd.execute(card)
            existing_files.append(file_id)
            file_name = {
                FileNo.CC_FILE: "CC_FILE (Capability Container)",
                FileNo.NDEF_FILE: "NDEF_FILE",
                FileNo.PROPRIETARY_FILE: "PROPRIETARY_FILE",
            }.get(file_id, "UNKNOWN")
            print(f"  [OK] File 0x{file_id:02X}: {file_name} (exists)")
        except ApduError as e:
            if e.sw2 == 0xF0:  # File not found
                print(f"  [SKIP] File 0x{file_id:02X}: does not exist (SW={e.sw1:02X}{e.sw2:02X})")
            elif e.sw2 == 0xAE:  # Authentication required
                print(f"  [INFO] File 0x{file_id:02X}: exists but requires authentication")
                existing_files.append(file_id)  # Assume it exists if it needs auth
            else:
                # Unknown error - might mean file doesn't exist
                pass
    
    return existing_files


def read_file_settings(card, file_ids: List[int], session: Optional[Ntag424AuthSession] = None):
    """Read settings for each file."""
    print_section("3. FILE SETTINGS")
    
    if not file_ids:
        print("[INFO] No files to read settings for")
        return
    
    for file_id in file_ids:
        print_subsection(f"File 0x{file_id:02X} Settings")
        
        try:
            cmd = GetFileSettings(file_no=file_id, session=session)
            settings = cmd.execute(card)
            
            print("[OK] File settings retrieved")
            print(settings)  # Uses dataclass __str__ method
        except ApduError as e:
            if e.sw2 == 0xAE:  # Authentication required
                print(f"[SKIP] Authentication required (SW={e.sw1:02X}{e.sw2:02X})")
            elif e.sw2 == 0x40:  # No such key/file
                print(f"[SKIP] File does not exist (SW={e.sw1:02X}{e.sw2:02X})")
            else:
                print(f"[ERROR] {e} (SW={e.sw1:02X}{e.sw2:02X})")
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")


def read_file_data(card, file_ids: List[int], session: Optional[Ntag424AuthSession] = None):
    """Read data from each file."""
    print_section("4. FILE DATA")
    
    if not file_ids:
        print("[INFO] No files to read data from")
        return
    
    for file_id in file_ids:
        print_subsection(f"File 0x{file_id:02X} Data")
        
        try:
            # Try reading first 64 bytes
            cmd = ReadData(file_no=file_id, offset=0, length=64)
            response = cmd.execute(card)
            
            print(f"[OK] Read {len(response.data)} bytes from offset {response.offset}")
            print(f"  Data: {format_bytes(response.data, max_len=128)}")
            
            # Try reading more if file is larger
            if len(response.data) == 64:
                try:
                    cmd2 = ReadData(file_no=file_id, offset=64, length=64)
                    response2 = cmd2.execute(card)
                    print(f"  (offset 64, {len(response2.data)} bytes): {format_bytes(response2.data, max_len=128)}")
                except Exception:
                    pass  # File might not be that large
        except ApduError as e:
            if e.sw2 == 0xAE:  # Authentication required
                print(f"[SKIP] Authentication required (SW={e.sw1:02X}{e.sw2:02X})")
            elif e.sw2 == 0x82:  # File not found
                print(f"[SKIP] File does not exist (SW={e.sw1:02X}{e.sw2:02X})")
            else:
                print(f"[ERROR] {e} (SW={e.sw1:02X}{e.sw2:02X})")
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")


def read_key_versions(card, session: Optional[Ntag424AuthSession] = None):
    """Read version for each key (requires authentication)."""
    print_section("5. KEY VERSIONS")
    
    if not session:
        print("[INFO] Skipping key versions (authentication required)")
        return
    
    for key_no in range(5):  # Keys 0-4
        print(f"\nKey 0x{key_no:02X}: ", end="")
        
        try:
            cmd = GetKeyVersion(key_no=key_no, session=session)
            key_version = cmd.execute(card)
            print(f"[OK] {key_version}")  # Uses dataclass __str__ method
        except ApduError as e:
            if e.sw2 == 0x40:  # No such key
                print(f"[SKIP] Key does not exist (SW={e.sw1:02X}{e.sw2:02X})")
            else:
                print(f"[ERROR] {e} (SW={e.sw1:02X}{e.sw2:02X})")
        except Exception as e:
            print(f"[ERROR] {e}")


def main():
    """Main diagnostic function."""
    print("=" * 70)
    print("  NTAG424 DNA Full Chip Diagnostic")
    print("=" * 70)
    print("\nThis example demonstrates clean usage of HAL API and commands")
    print("to read all available information from the chip.\n")
    print("Please tap and hold the NTAG424 tag on the reader...\n")
    
    try:
        with CardManager() as card:
            # Initial setup
            print("[1/6] Selecting PICC application...")
            SelectPiccApplication().execute(card)
            print("[OK] PICC application selected")
            
            # Read basic info (no auth required)
            version = read_chip_basic_info(card)
            
            if not version:
                print("\n[ERROR] Cannot proceed without chip version information")
                return
            
            # Read file list (no auth required)
            file_ids = read_file_list(card)
            
            # Try reading file settings without authentication
            print("\n[INFO] Attempting to read file settings without authentication...")
            read_file_settings(card, file_ids, session=None)
            
            # Try reading file data without authentication
            print("\n[INFO] Attempting to read file data without authentication...")
            read_file_data(card, file_ids, session=None)
            
            # Now authenticate and try again
            print_section("AUTHENTICATION")
            print("\n[2/6] Authenticating with factory key...")
            
            try:
                session = Ntag424AuthSession(FACTORY_KEY)
                session_keys = session.authenticate(card, key_no=KeyNo.KEY_0)
                
                print("[OK] Authentication successful")
                print(f"  Transaction ID: {format_bytes(session_keys.ti)}")
                print(f"  Session ENC Key: {format_bytes(session_keys.session_enc_key)}")
                print(f"  Session MAC Key: {format_bytes(session_keys.session_mac_key)}")
                
                # Read file settings with authentication
                print("\n[3/6] Reading file settings with authentication...")
                read_file_settings(card, file_ids, session=session)
                
                # Read file data with authentication
                print("\n[4/6] Reading file data with authentication...")
                read_file_data(card, file_ids, session=session)
                
                # Read key versions (requires authentication)
                print("\n[5/6] Reading key versions...")
                read_key_versions(card, session=session)
                
                print_section("SUMMARY")
                print("\n[6/6] Diagnostic complete!")
                print(f"  - Chip UID: {format_bytes(version.uid)}")
                print(f"  - Files found: {len(file_ids)}")
                print(f"  - Authentication: SUCCESS")
                print(f"  - All readable data retrieved")
                
            except ApduError as e:
                print(f"[ERROR] Authentication failed: {e} (SW={e.sw1:02X}{e.sw2:02X})")
                print("\n[INFO] Some information requires authentication")
                print("       Non-authenticated data retrieved above")
            
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Diagnostic cancelled by user")
    except Exception as e:
        print(f"\n[ERROR] Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

