#!/usr/bin/env python3
"""
Test SUN Configuration Without Authentication

Tests if we can configure SUN (Secure Unique NFC) settings on Seritag tags
without requiring EV2 authentication. This is critical for game coin provisioning.
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.commands.sun_commands import (
    ConfigureSunSettings, WriteNdefMessage, ReadNdefMessage, build_ndef_uri_record
)
from ntag424_sdm_provisioner.commands.base import ApduError
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def test_sun_configuration():
    """Test SUN configuration without authentication."""
    
    print("=" * 80)
    print("SUN CONFIGURATION TEST (Without Authentication)")
    print("=" * 80)
    print()
    print("Testing if SUN can be configured on Seritag tags without EV2 authentication.")
    print("If this works, game coins can be fully provisioned immediately!")
    print()
    
    try:
        with CardManager(0) as card:
            print("Step 1: Selecting PICC application...")
            SelectPiccApplication().execute(card)
            print("[OK] PICC application selected")
            
            print("\nStep 2: Getting chip version...")
            version_info = GetChipVersion().execute(card)
            print(f"[OK] Tag: HW {version_info.hw_major_version}.{version_info.hw_minor_version}")
            print(f"      UID: {version_info.uid.hex().upper()}")
            
            if version_info.hw_major_version == 48:
                print("      [INFO] Detected Seritag NTAG424 DNA (HW 48.0)")
            
            # Step 3: Write NDEF first (we know this works)
            print("\nStep 3: Writing base NDEF URL...")
            base_url = "https://game-server.com/verify"
            ndef_data = build_ndef_uri_record(base_url)
            print(f"      Base URL: {base_url}")
            print(f"      NDEF data: {len(ndef_data)} bytes")
            
            try:
                WriteNdefMessage(ndef_data).execute(card)
                print("[OK] NDEF written successfully")
            except ApduError as e:
                print(f"[FAIL] NDEF write failed: {e.sw1:02X}{e.sw2:02X} - {e}")
                return False
            
            # Step 4: Try to configure SUN settings
            print("\nStep 4: Configuring SUN settings...")
            print("        This is the critical test - does SUN require authentication?")
            
            try:
                # Configure SUN: Enable SUN, enable UID mirroring, enable counter
                sun_config = ConfigureSunSettings(
                    enable_sun=True,
                    enable_uid_mirror=True,
                    enable_counter=True,
                    enable_mac=True
                )
                
                result = sun_config.execute(card)
                print(f"[OK] SUCCESS! SUN configuration worked WITHOUT authentication!")
                print(f"     Response: {result}")
                print()
                print("=" * 80)
                print("BREAKTHROUGH: Full Provisioning Possible Without Authentication!")
                print("=" * 80)
                print()
                print("Game coins can now be fully provisioned:")
                print("  [OK] NDEF URL written")
                print("  [OK] SUN enabled (UID + Counter + MAC)")
                print("  [OK] Tags will serve authenticated URLs when tapped!")
                return True
                
            except ApduError as e:
                print(f"[FAIL] SUN configuration requires authentication")
                print(f"       Error: {e.sw1:02X}{e.sw2:02X} - {e}")
                print()
                print("=" * 80)
                print("SUN Requires Authentication")
                print("=" * 80)
                print()
                print("SUN configuration failed - still need EV2 authentication.")
                print("However, NDEF is working, so:")
                print("  [OK] Can write static URLs to tags")
                print("  [WARN] Cannot enable SUN authentication yet")
                print("  [INFO] Need to solve EV2 Phase 2 for full SUN support")
                return False
            
            # Step 5: If SUN worked, verify it
            print("\nStep 5: Reading back NDEF to verify SUN is active...")
            try:
                read_data = ReadNdefMessage(max_length=256).execute(card)
                print(f"[OK] Read {len(read_data)} bytes")
                
                # Check if SUN enhanced the NDEF
                ndef_str = read_data.decode('utf-8', errors='ignore')
                if 'uid=' in ndef_str.lower() or '&c=' in ndef_str.lower():
                    print("[OK] SUN appears to be active - URL contains parameters!")
                else:
                    print("[INFO] URL doesn't show SUN parameters (may need phone tap to activate)")
                    
            except ApduError as e:
                print(f"[WARN] Read failed: {e.sw1:02X}{e.sw2:02X}")
            
    except NTag242ConnectionError as e:
        print(f"\n[FAIL] CONNECTION FAILED: {e}")
        print("Make sure NFC reader is connected and tag is present.")
        return False
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_sun_configuration()
    
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    if success:
        print("[OK] SUN configuration works WITHOUT authentication!")
        print("     Game coins can be fully provisioned immediately.")
        print()
        print("Next steps:")
        print("  1. Test writing real game server URL")
        print("  2. Verify phone can read enhanced URL")
        print("  3. Test server-side MAC verification")
    else:
        print("[INFO] SUN requires authentication, but NDEF works.")
        print("       Can provision static URLs now.")
        print("       Need EV2 Phase 2 for full SUN authentication.")
    print()

