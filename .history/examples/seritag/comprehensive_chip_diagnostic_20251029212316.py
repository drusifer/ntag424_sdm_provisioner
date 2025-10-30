"""
Comprehensive Chip Diagnostic

This script queries as much information as possible from the chip to understand
its state, configuration, and capabilities. Useful for understanding why Phase 2
authentication might be failing.
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.constants import SW_OK
from ntag424_sdm_provisioner.commands.base import ApduError
import logging

logging.basicConfig(level=logging.WARNING)


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def try_command(card, name, apdu, description=""):
    """Try a command and return result."""
    try:
        data, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
        status = f"SW={sw1:02X}{sw2:02X}"
        if (sw1, sw2) == SW_OK:
            status = "[OK] " + status
            return True, data, sw1, sw2, status
        else:
            return False, data, sw1, sw2, f"[FAIL] {status}"
    except Exception as e:
        return False, None, None, None, f"[ERROR] {str(e)}"


def diagnostic_scan(card):
    """Run comprehensive diagnostic scan."""
    
    print_section("COMPREHENSIVE CHIP DIAGNOSTIC")
    
    # 1. Basic Information
    print_section("1. CHIP VERSION INFORMATION")
    try:
        version = GetChipVersion().execute(card)
        print(f"Hardware Version: {version.hw_major_version}.{version.hw_minor_version}")
        print(f"Software Version: {version.sw_major_version}.{version.sw_minor_version}")
        print(f"UID: {version.uid.hex().upper()}")
        print(f"Hardware Type: 0x{version.hw_type:02X}")
        print(f"Software Type: 0x{version.sw_type:02X}")
        print(f"Hardware Protocol: {version.hw_protocol}")
        print(f"Software Protocol: {version.sw_protocol}")
        print(f"Storage Size (HW): {version.hw_storage_size} bytes")
        print(f"Storage Size (SW): {version.sw_storage_size} bytes")
        print(f"Batch Number: {version.batch_no.hex().upper()}")
        print(f"Fabrication: Week {version.fab_week}, Year {version.fab_year}")
    except Exception as e:
        print(f"[FAIL] GetVersion: {e}")
    
    # 2. File System Information
    print_section("2. FILE SYSTEM INFORMATION")
    
    # GetFileSettings command (0x90 0xF5)
    files_to_check = [0x01, 0x02, 0x03, 0x04, 0x05]  # CC, NDEF, Proprietary, etc.
    for file_no in files_to_check:
        print(f"\nFile 0x{file_no:02X} Settings:")
        # GetFileSettings: 90 F5 00 00 01 [FileNo] 00
        apdu = [0x90, 0xF5, 0x00, 0x00, 0x01, file_no, 0x00]
        success, data, sw1, sw2, status = try_command(card, f"GetFileSettings(0x{file_no:02X})", apdu)
        print(f"  {status}")
        if success and data:
            print(f"  Data ({len(data)} bytes): {bytes(data).hex().upper()}")
            if len(data) >= 16:
                print(f"  File Type: 0x{data[0]:02X}")
                print(f"  File Option: 0x{data[1]:02X}")
                print(f"  Access Rights: {''.join(f'{b:02X}' for b in data[2:6])}")
    
    # 3. Get File List
    print_section("3. FILE LIST")
    # GetFileIDs: 90 6F 00 00 00
    apdu = [0x90, 0x6F, 0x00, 0x00, 0x00]
    success, data, sw1, sw2, status = try_command(card, "GetFileIDs", apdu)
    print(f"{status}")
    if success and data:
        print(f"  File IDs: {bytes(data).hex().upper()}")
        if len(data) > 0:
            file_ids = [b for b in data]
            print(f"  Files found: {', '.join(f'0x{b:02X}' for b in file_ids)}")
    
    # 4. Try Reading Files Without Authentication
    print_section("4. READ FILES (NO AUTHENTICATION)")
    
    for file_no in [0x01, 0x02, 0x03]:
        print(f"\nReading File 0x{file_no:02X}:")
        # ISOReadBinary: 00 B0 00 00 20 (read 32 bytes from offset 0)
        apdu = [0x00, 0xB0, 0x00, 0x00, 0x20]
        # First select the file
        # ISOSelectFile: 00 A4 00 00 02 [FileID_H] [FileID_L]
        file_id_high = (file_no << 8) | 0x04
        file_id_low = file_no
        select_apdu = [0x00, 0xA4, 0x00, 0x02, 0x02, (file_id_high >> 8) & 0xFF, file_id_high & 0xFF]
        sel_success, _, _, _, sel_status = try_command(card, f"SelectFile(0x{file_no:02X})", select_apdu)
        if sel_success:
            success, data, sw1, sw2, status = try_command(card, f"ReadBinary(0x{file_no:02X})", apdu)
            print(f"  Select: {sel_status}")
            print(f"  Read: {status}")
            if success and data:
                print(f"  Data (first 64 bytes): {bytes(data[:64]).hex().upper()}")
        else:
            print(f"  Select: {sel_status}")
    
    # 5. ISO GET DATA Commands
    print_section("5. ISO GET DATA COMMANDS")
    
    # ISO GET DATA for various tags (per ISO 7816-4)
    data_tags = [
        (0x00, 0x66, "Application identifier"),
        (0x00, 0x67, "Card production life cycle"),
        (0x00, 0x68, "Card issuer data"),
        (0x00, 0x6A, "Card service data"),
        (0x00, 0x6B, "Card capabilities"),
    ]
    
    for p1, p2, desc in data_tags:
        apdu = [0x00, 0xCA, p1, p2, 0x00]
        success, data, sw1, sw2, status = try_command(card, f"GetData({desc})", apdu)
        if success and data:
            print(f"\n{desc}:")
            print(f"  {status}")
            print(f"  Data ({len(data)} bytes): {bytes(data).hex().upper()}")
    
    # 6. Try Proprietary Commands
    print_section("6. PROPRIETARY COMMANDS")
    
    proprietary_commands = [
        (0x64, "GetKeyVersion"),
        (0x6C, "GetValue"),
        (0x70, "AuthenticateEV1First"),
        (0x72, "AuthenticateEV2NonFirst"),
        (0x73, "AuthenticateLRPFirst"),
        (0x74, "AuthenticateLRPNonFirst"),
        (0x77, "AuthenticateEV2NonFirst"),
        (0x51, "Command 0x51 (Seritag-specific)"),
        (0x52, "Command 0x52"),
        (0x53, "Command 0x53"),
    ]
    
    for ins, name in proprietary_commands:
        # Try with minimal parameters
        apdu = [0x90, ins, 0x00, 0x00, 0x00]
        success, data, sw1, sw2, status = try_command(card, name, apdu)
        if success or (sw1, sw2) != (0x6D, 0x00):  # Only print if not "command not supported"
            print(f"{name}: {status}")
            if success and data:
                print(f"  Response ({len(data)} bytes): {bytes(data).hex().upper()}")
    
    # 7. Read File Counters
    print_section("7. FILE COUNTERS")
    
    for file_no in [0x02, 0x03]:
        # GetFileCounters: 90 68 00 [FileNo] 00
        apdu = [0x90, 0x68, 0x00, file_no, 0x00]
        success, data, sw1, sw2, status = try_command(card, f"GetFileCounters(0x{file_no:02X})", apdu)
        if success and data:
            print(f"File 0x{file_no:02X} Counters: {status}")
            print(f"  Data: {bytes(data).hex().upper()}")
        elif sw2 != 0x40:  # Don't print if "wrong key" (expected without auth)
            print(f"File 0x{file_no:02X} Counters: {status}")
    
    # 8. Authentication State Check
    print_section("8. AUTHENTICATION STATE")
    
    # Try Phase 1 to see current state
    print("Attempting Phase 1 authentication:")
    apdu = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
    success, data, sw1, sw2, status = try_command(card, "AuthenticateEV2First", apdu)
    print(f"  {status}")
    if success and data:
        print(f"  Challenge ({len(data)} bytes): {bytes(data).hex().upper()}")
    
    # 9. Configuration Query
    print_section("9. CONFIGURATION QUERIES")
    
    # Try SetConfiguration query (might be read-only)
    # GetConfiguration: 90 5C 00 [ConfigPage] 00
    for page in [0x00, 0x01, 0x02]:
        apdu = [0x90, 0x5C, 0x00, page, 0x00]
        success, data, sw1, sw2, status = try_command(card, f"GetConfiguration(Page {page})", apdu)
        if success and data:
            print(f"\nConfiguration Page {page}:")
            print(f"  {status}")
            print(f"  Data ({len(data)} bytes): {bytes(data).hex().upper()}")
    
    # 10. Connection Information
    print_section("10. CONNECTION INFORMATION")
    print(f"Reader: {card}")
    print(f"Card Connection Type: {type(card.connection).__name__}")
    
    # Summary
    print_section("DIAGNOSTIC SUMMARY")
    print("Diagnostic scan complete!")
    print("Review the information above to understand chip state and configuration.")


def main():
    """Run comprehensive diagnostic."""
    try:
        with CardManager(0, timeout_seconds=15) as card:
            # Select PICC
            SelectPiccApplication().execute(card)
            print("[OK] PICC selected")
            
            # Run diagnostic
            diagnostic_scan(card)
            
    except Exception as e:
        print(f"\n[ERROR] Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

