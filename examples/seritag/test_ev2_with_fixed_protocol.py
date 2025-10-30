#!/usr/bin/env python3
"""
Test EV2 Authentication with Fixed Protocol

Now that we've fixed protocol issues:
- CLA byte correct (90 for proprietary commands)
- File selection working (P1=0x02)
- Command formats correct

Let's try EV2 authentication again - maybe with correct protocols it will work!
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.commands.base import ApduError, AuthenticationError
from ntag424_sdm_provisioner.constants import FACTORY_KEY
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def test_ev2_authentication():
    """Test EV2 authentication with fixed protocol."""
    
    print("=" * 80)
    print("EV2 AUTHENTICATION TEST (With Fixed Protocol)")
    print("=" * 80)
    print()
    print("Testing EV2 authentication with our protocol fixes:")
    print("  - Correct command formats")
    print("  - Proper CLA bytes")
    print("  - File selection working")
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
                print("      [INFO] Seritag NTAG424 DNA detected")
            
            print("\nStep 3: Attempting EV2 Authentication with Key 0 (factory key)...")
            print("        Factory key: 00" * 16 + " (all zeros)")
            
            try:
                session = Ntag424AuthSession(FACTORY_KEY)
                session.authenticate(card, key_no=0)
                
                print(f"[OK] SUCCESS! Authentication worked!")
                print(f"     Session keys derived:")
                print(f"       Encryption Key: {session.session_keys.session_enc_key.hex().upper()}")
                print(f"       MAC Key: {session.session_keys.session_mac_key.hex().upper()}")
                print(f"       Transaction ID: {session.session_keys.ti.hex().upper()}")
                print()
                print("=" * 80)
                print("BREAKTHROUGH: Authentication Works with Fixed Protocol!")
                print("=" * 80)
                print()
                print("We can now:")
                print("  [OK] Authenticate with Seritag tags")
                print("  [OK] Configure SDM/SUN settings")
                print("  [OK] Fully provision game coins!")
                return True
                
            except AuthenticationError as e:
                print(f"[FAIL] Authentication failed: {e}")
                if hasattr(e, 'sw1') and hasattr(e, 'sw2'):
                    print(f"       SW: {e.sw1:02X}{e.sw2:02X}")
                return False
            except ApduError as e:
                print(f"[FAIL] APDU error during authentication: {e.sw1:02X}{e.sw2:02X}")
                print(f"       {e}")
                return False
            
    except NTag242ConnectionError as e:
        print(f"\n[FAIL] CONNECTION FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_ev2_authentication()
    
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    if success:
        print("[OK] EV2 authentication works with fixed protocol!")
        print("     Next: Try configuring SDM/SUN with authenticated session")
    else:
        print("[INFO] EV2 authentication still requires investigation")
        print("       But NDEF read/write works without auth!")
    print()

