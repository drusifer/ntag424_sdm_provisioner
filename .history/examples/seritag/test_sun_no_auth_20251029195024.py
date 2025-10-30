#!/usr/bin/env python3
"""
Test SUN (Secure Unique NFC) Without Authentication

This script tests if we can configure SUN or write NDEF messages
to Seritag tags WITHOUT requiring EV2 authentication.

Key hypothesis: SUN might work if NDEF file has FREE access rights,
even if we can't authenticate.
"""
import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.commands.sun_commands import (
    WriteNdefMessage, ReadNdefMessage, ConfigureSunSettings,
    build_ndef_uri_record, parse_sun_url
)
from ntag424_sdm_provisioner.commands.base import ApduError
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def test_sun_without_auth():
    """Test SUN functionality without EV2 authentication."""
    
    print("=" * 60)
    print("Testing SUN Without Authentication")
    print("=" * 60)
    print("Hypothesis: SUN may work if NDEF file has FREE access rights")
    print()
    
    try:
        with CardManager(0) as card:
            print("Step 1: Selecting PICC application...")
            try:
                SelectPiccApplication().execute(card)
                print("✅ PICC application selected")
            except ApduError as e:
                print(f"⚠️  Select failed: {e}")
            
            print("\nStep 2: Getting chip version...")
            version_info = GetChipVersion().execute(card)
            print(f"✅ Chip version: HW {version_info.hw_major_version}.{version_info.hw_minor_version}")
            print(f"   UID: {version_info.uid.hex().upper()}")
            
            if version_info.hw_major_version == 48:
                print("   🔍 Detected Seritag NTAG424 DNA (HW 48.0)")
            else:
                print(f"   ℹ️  Standard NXP tag (HW {version_info.hw_major_version}.{version_info.hw_minor_version})")
            
            # Test 1: Try reading NDEF without authentication
            print("\n" + "=" * 60)
            print("TEST 1: Reading NDEF without authentication")
            print("=" * 60)
            try:
                ndef_data = ReadNdefMessage(max_length=256).execute(card)
                print(f"✅ SUCCESS: NDEF readable without authentication!")
                print(f"   Length: {len(ndef_data)} bytes")
                print(f"   Hex: {ndef_data.hex().upper()[:64]}...")
                
                # Try to decode as text
                try:
                    text = ndef_data.decode('utf-8', errors='ignore')
                    print(f"   As text: {text[:100]}...")
                    
                    # Look for URLs
                    import re
                    urls = re.findall(r'https?://[^\s<>"]+', text)
                    if urls:
                        print(f"   Found URLs: {len(urls)}")
                        for url in urls:
                            print(f"     - {url}")
                            # Check if SUN already enhanced it
                            sun_params = parse_sun_url(url)
                            if sun_params:
                                print(f"       SUN parameters: {sun_params}")
                except:
                    pass
                    
            except ApduError as e:
                print(f"❌ FAILED: NDEF read requires authentication")
                print(f"   Error: {e.sw1:02X}{e.sw2:02X} - {e}")
            
            # Test 2: Try writing NDEF without authentication
            print("\n" + "=" * 60)
            print("TEST 2: Writing NDEF without authentication")
            print("=" * 60)
            base_url = "https://game-server.com/verify"
            print(f"Base URL to write: {base_url}")
            print("SUN will append: ?uid=XXXX&c=YYYY&mac=ZZZZ")
            
            try:
                ndef_data = build_ndef_uri_record(base_url)
                print(f"NDEF data prepared: {len(ndef_data)} bytes")
                
                write_response = WriteNdefMessage(ndef_data).execute(card)
                print(f"✅ SUCCESS: NDEF written without authentication!")
                print(f"   Response: {write_response}")
                
                # Read it back to verify
                print("\n   Verifying write by reading back...")
                ndef_readback = ReadNdefMessage(max_length=256).execute(card)
                print(f"   Read back: {len(ndef_readback)} bytes")
                
            except ApduError as e:
                print(f"❌ FAILED: NDEF write requires authentication")
                print(f"   Error: {e.sw1:02X}{e.sw2:02X} - {e}")
                print(f"   This means we need authentication to write NDEF")
            
            # Test 3: Try configuring SUN settings (likely requires auth)
            print("\n" + "=" * 60)
            print("TEST 3: Configuring SUN settings without authentication")
            print("=" * 60)
            print("Note: This likely requires authentication, but worth trying...")
            
            try:
                sun_config = ConfigureSunSettings(enable_sun=True)
                sun_response = sun_config.execute(card)
                print(f"✅ SUCCESS: SUN configuration without authentication!")
                print(f"   Response: {sun_response}")
            except ApduError as e:
                print(f"❌ Expected: SUN configuration requires authentication")
                print(f"   Error: {e.sw1:02X}{e.sw2:02X} - {e}")
                print(f"   This is expected - SUN config needs authenticated session")
            
            # Summary
            print("\n" + "=" * 60)
            print("SUMMARY")
            print("=" * 60)
            print("If TEST 2 (NDEF write) succeeded:")
            print("  ✅ We can provision tags WITHOUT authentication!")
            print("  ✅ SUN will automatically enhance URLs when scanned")
            print("  ✅ Game coin authentication can work immediately!")
            print()
            print("If TEST 2 failed but TEST 1 (NDEF read) succeeded:")
            print("  ⚠️  NDEF is readable but not writable without auth")
            print("  ⚠️  Need to continue EV2 investigation")
            print("  ⚠️  OR check if SUN is already pre-configured")
            print()
            print("If both failed:")
            print("  ❌ All operations require authentication")
            print("  ❌ Must solve EV2 Phase 2 to proceed")
            
    except NTag242ConnectionError as e:
        print(f"\n❌ CONNECTION FAILED: {e}")
        print("Make sure NFC reader is connected and tag is present.")
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_sun_without_auth()

