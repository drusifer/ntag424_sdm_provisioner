#!/usr/bin/env python3
"""
Comprehensive SDM/SUN Configuration Test

Tests multiple approaches to configure SDM/SUN with our fixed protocol:
1. Try SDM with proper ChangeFileSettings format
2. Try SUN with different command variants
3. Try with CommMode.Plain (current file access rights)
4. Try partial configurations
5. Check current file settings first

With our protocol fixes:
- File selection works (P1=0x02)
- Command formats are correct (CLA=00 for ISO, FileNo in payload)
- Maybe we can find a way that works!
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.commands.sun_commands import WriteNdefMessage, ReadNdefMessage, build_ndef_uri_record
from ntag424_sdm_provisioner.commands.change_file_settings import ChangeFileSettings
from ntag424_sdm_provisioner.commands.base import ApduError
from ntag424_sdm_provisioner.constants import (
    SDMConfiguration, AccessRight, AccessRights, CommMode, FileOption,
    SDMOption, SDMUrlTemplate
)
from ntag424_sdm_provisioner.commands.sdm_helpers import calculate_sdm_offsets
from ntag424_sdm_provisioner.constants import SW_OK
import logging

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


def test_get_file_settings(card):
    """Try to read current file settings."""
    print("\nAttempting to read current file settings...")
    
    # GetFileSettings: 90 F5 00 00 01 [FileNo] 00
    file_no = 0x02  # NDEF file
    get_settings_apdu = [
        0x90, 0xF5,  # GetFileSettings
        0x00, 0x00,  # P1, P2
        0x01,        # Lc = 1 byte
        file_no,     # FileNo
        0x00         # Le
    ]
    
    try:
        data, sw1, sw2 = card.send_apdu(get_settings_apdu, use_escape=True)
        if (sw1, sw2) == SW_OK:
            print(f"[OK] Got file settings: {len(data)} bytes")
            print(f"     Hex: {data.hex().upper()[:64]}...")
            
            # Parse basic info
            if len(data) >= 1:
                file_type = data[0]
                print(f"     File Type: 0x{file_type:02X}")
            
            if len(data) >= 2:
                file_option = data[1]
                print(f"     File Option: 0x{file_option:02X}")
                if file_option & 0x40:
                    print(f"     [INFO] SDM is already enabled!")
                else:
                    print(f"     [INFO] SDM is disabled")
            
            if len(data) >= 6:
                access_rights = data[2:6]
                print(f"     Access Rights: {[hex(x) for x in access_rights]}")
            
            return data
        else:
            print(f"[FAIL] GetFileSettings: SW={sw1:02X}{sw2:02X}")
            return None
    except Exception as e:
        print(f"[FAIL] GetFileSettings error: {e}")
        return None


def test_sdm_with_calculated_offsets(card):
    """Test SDM configuration with properly calculated offsets."""
    print("\n" + "=" * 80)
    print("TEST 1: SDM Configuration with Proper Offsets")
    print("=" * 80)
    
    # Build URL template for offset calculation
    base_url = "https://game-server.com/verify"
    url_template = f"{base_url}?uid=XXXXXXXXXXXXXX&c=YYYYYYYY&mac=ZZZZZZZZZZZZZZZZ"
    
    print(f"URL Template: {url_template}")
    
    # Calculate offsets
    from ntag424_sdm_provisioner.constants import SDMUrlTemplate
    template = SDMUrlTemplate(
        base_url=base_url,
        uid_placeholder="XXXXXXXXXXXXXX",
        read_ctr_placeholder="YYYYYYYY",
        cmac_placeholder="ZZZZZZZZZZZZZZZZ"
    )
    
    offsets = calculate_sdm_offsets(template)
    print(f"Calculated Offsets: {offsets}")
    
    # Build NDEF with placeholders
    ndef_data = build_ndef_uri_record(url_template)
    print(f"NDEF with placeholders: {len(ndef_data)} bytes")
    
    # Write NDEF first
    print("\nWriting NDEF with placeholders...")
    try:
        WriteNdefMessage(ndef_data).execute(card)
        print("[OK] NDEF written with placeholders")
    except ApduError as e:
        print(f"[FAIL] NDEF write failed: {e.sw1:02X}{e.sw2:02X}")
        return False
    
    # Build SDM configuration
    config = SDMConfiguration(
        file_no=0x02,
        comm_mode=CommMode.PLAIN,  # Try Plain mode
        access_rights=AccessRights(
            read=AccessRight.FREE,
            write=AccessRight.FREE,
            read_write=AccessRight.FREE,
            change=AccessRight.FREE
        ),
        enable_sdm=True,
        sdm_options=SDMOption.ENABLED | SDMOption.UID_MIRROR | SDMOption.READ_COUNTER,
        picc_data_offset=offsets.get('picc_data_offset', 20),
        mac_input_offset=offsets.get('mac_input_offset', 20),
        mac_offset=offsets.get('mac_offset', 40),
        read_ctr_offset=offsets.get('read_ctr_offset', 35),
        enc_data_offset=None,
        enc_data_length=None
    )
    
    print("\nAttempting SDM configuration...")
    print(f"  CommMode: {config.comm_mode}")
    print(f"  SDMOptions: 0x{config.sdm_options:02X}")
    print(f"  PICCDataOffset: {config.picc_data_offset}")
    print(f"  MACOffset: {config.mac_offset}")
    
    try:
        change_cmd = ChangeFileSettings(config)
        result = change_cmd.execute(card)  # No session (no authentication)
        print(f"[OK] SUCCESS! SDM configured without authentication!")
        print(f"     {result}")
        return True
    except ApduError as e:
        print(f"[FAIL] SDM configuration failed: {e.sw1:02X}{e.sw2:02X} - {e}")
        return False


def test_sdm_minimal_format(card):
    """Test SDM with minimal configuration (just enable SDM, no offsets)."""
    print("\n" + "=" * 80)
    print("TEST 2: Minimal SDM Configuration")
    print("=" * 80)
    print("Trying minimal format - just enable SDM without offsets")
    
    file_no = 0x02
    
    # Minimal ChangeFileSettings: [FileNo] [FileOption] [AccessRights] [SDMOptions] [SDMAccessRights]
    # Without offsets - maybe offsets are optional?
    config_data = [
        file_no,     # FileNo
        0x00,        # FileOption (Plain)
        0x0E, 0x0E, 0x0E, 0x0E,  # Access Rights (FREE)
        0xC0,        # SDMOptions: 0xC0 = 0x40 (SDM_ENABLED) | 0x80 (UID_MIRROR)
        0x00,        # SDMAccessRights
    ]
    
    apdu = [
        0x90, 0x5F,  # ChangeFileSettings
        0x00, 0x00,  # P1, P2
        len(config_data),  # Lc
    ] + config_data + [0x00]  # Data + Le
    
    print(f"APDU: {' '.join([f'{b:02X}' for b in apdu])}")
    
    try:
        _, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
        if (sw1, sw2) == SW_OK:
            print(f"[OK] Minimal SDM configuration worked!")
            return True
        else:
            print(f"[FAIL] SW={sw1:02X}{sw2:02X}")
            return False
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


def test_sun_alternative_format(card):
    """Test SUN with alternative command format."""
    print("\n" + "=" * 80)
    print("TEST 3: SUN Alternative Format")
    print("=" * 80)
    
    # Check spec - maybe SUN uses SetConfiguration (90 5C) instead?
    # SetConfiguration: 90 5C [Option] [Data]
    # Option 05h = Capability data (might be for SUN?)
    
    test_configs = [
        # Test 1: SetConfiguration with Option 05h (Capability)
        {
            "name": "SetConfiguration Option 05h (Capability)",
            "apdu": [0x90, 0x5C, 0x00, 0x00, 0x01, 0x05, 0x00]
        },
        # Test 2: SetConfiguration with Option 04h (Secure Messaging)
        {
            "name": "SetConfiguration Option 04h (Secure Messaging)",
            "apdu": [0x90, 0x5C, 0x00, 0x00, 0x01, 0x04, 0x00]
        },
    ]
    
    for test in test_configs:
        print(f"\n  Trying: {test['name']}")
        try:
            _, sw1, sw2 = card.send_apdu(test['apdu'], use_escape=True)
            print(f"  Result: SW={sw1:02X}{sw2:02X}")
            if (sw1, sw2) == SW_OK:
                print(f"  [OK] Success!")
                return True
        except Exception as e:
            print(f"  [FAIL] Error: {e}")
    
    return False


def run_comprehensive_test():
    """Run all SDM/SUN configuration tests."""
    
    print("=" * 80)
    print("COMPREHENSIVE SDM/SUN CONFIGURATION TEST")
    print("=" * 80)
    print()
    print("Testing multiple approaches with our fixed protocol:")
    print("  - File selection working (P1=0x02)")
    print("  - Command formats correct")
    print("  - Maybe we can find a way that works without auth!")
    print()
    
    results = {}
    
    try:
        with CardManager(0) as card:
            print("Step 1: Selecting PICC application...")
            SelectPiccApplication().execute(card)
            print("[OK] PICC application selected")
            
            print("\nStep 2: Getting chip version...")
            version_info = GetChipVersion().execute(card)
            print(f"[OK] Tag: HW {version_info.hw_major_version}.{version_info.hw_minor_version}")
            print(f"      UID: {version_info.uid.hex().upper()}")
            
            # Select NDEF file
            print("\nStep 3: Selecting NDEF file...")
            select_apdu = [0x00, 0xA4, 0x02, 0x00, 0x02, 0xE1, 0x04, 0x00]
            _, sw1, sw2 = card.send_apdu(select_apdu, use_escape=True)
            if (sw1, sw2) == SW_OK:
                print("[OK] NDEF file selected")
            else:
                print(f"[WARN] File select: SW={sw1:02X}{sw2:02X}")
            
            # Get current file settings
            current_settings = test_get_file_settings(card)
            
            # Test 1: SDM with proper format
            results['sdm_proper'] = test_sdm_with_calculated_offsets(card)
            
            # Test 2: Minimal SDM
            results['sdm_minimal'] = test_sdm_minimal_format(card)
            
            # Test 3: SUN alternatives
            results['sun_alternative'] = test_sun_alternative_format(card)
            
            # Summary
            print("\n" + "=" * 80)
            print("TEST SUMMARY")
            print("=" * 80)
            
            success_count = sum(1 for v in results.values() if v)
            total_count = len(results)
            
            print(f"Total tests: {total_count}")
            print(f"Successful: {success_count}")
            
            if success_count > 0:
                print("\n[OK] Found working configuration!")
                for name, success in results.items():
                    if success:
                        print(f"  [OK] {name}")
            else:
                print("\n[INFO] All tests required authentication")
                print("       Current file settings:")
                if current_settings:
                    print(f"         {current_settings.hex().upper()[:64]}...")
            
    except NTag242ConnectionError as e:
        print(f"\n[FAIL] CONNECTION FAILED: {e}")
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_comprehensive_test()

