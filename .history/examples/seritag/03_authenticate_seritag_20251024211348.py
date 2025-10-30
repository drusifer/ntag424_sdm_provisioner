"""
Seritag NTAG424 DNA Authentication Diagnostic

This script tests various authentication methods to determine
the correct protocol for Seritag NTAG424 DNA tags.
"""
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

from ntag424_sdm_provisioner.seritag_simulator import SeritagCardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.constants import FACTORY_KEY

def test_seritag_authentication():
    """Test various authentication methods for Seritag NTAG424 DNA."""
    
    print("🔐 Seritag NTAG424 DNA Authentication Diagnostic")
    print("=" * 60)
    
    try:
        with SeritagCardManager(0) as card:
            print("✅ Connected to Seritag NTAG424 DNA tag")
            
            # Select PICC application
            print("\n📱 Selecting PICC application...")
            SelectPiccApplication().execute(card)
            print("✅ PICC application selected")
            
            # Get chip version
            print("\n🔍 Getting chip version information...")
            version_info = GetChipVersion().execute(card)
            print(f"   UID: {version_info.uid.hex().upper()}")
            print(f"   Hardware: {version_info.hw_major_version}.{version_info.hw_minor_version}")
            print(f"   Software: {version_info.sw_major_version}.{version_info.sw_minor_version}")
            
            # Test EV2 Authentication with factory key
            print(f"\n🔑 Testing EV2 Authentication with Factory Key...")
            print(f"   Factory Key: {FACTORY_KEY.hex().upper()}")
            
            # Try all 5 keys (0-4)
            keys_to_try = [
                (0, "PICC Master Key"),
                (1, "File Data Read Key"), 
                (2, "SDM MAC Key"),
                (3, "File Data Write Key"),
                (4, "File Configuration Key")
            ]
            
            ev2_success = False
            for key_no, key_name in keys_to_try:
                print(f"\n   Testing {key_name} (Key {key_no})...")
                try:
                    session = Ntag424AuthSession(FACTORY_KEY)
                    session_keys = session.authenticate(card, key_no=key_no)
                    print(f"   ✅ EV2 Authentication successful with {key_name}!")
                    print(f"      Transaction ID: {session_keys.ti.hex().upper()}")
                    ev2_success = True
                    break
                except Exception as e:
                    print(f"   ❌ EV2 Authentication failed: {e}")
                    if hasattr(e, 'sw1') and hasattr(e, 'sw2'):
                        print(f"      Status Word: 0x{e.sw1:02X}{e.sw2:02X}")
            
            if not ev2_success:
                print(f"\n⚠️  EV2 Authentication failed with all keys")
                print(f"   This confirms Seritag uses a different authentication protocol")
                
                # Test alternative authentication methods
                print(f"\n🔍 Testing Alternative Authentication Methods...")
                
                # Test 1: Try different factory keys
                print(f"\n   1. Testing different factory keys...")
                alternative_keys = [
                    (b'\xFF' * 16, "All ones"),
                    (b'\xAA' * 16, "Alternating pattern"),
                    (b'\x55' * 16, "Alternating pattern 2"),
                    (b'\x12\x34\x56\x78' * 4, "Sequential pattern"),
                ]
                
                for alt_key, key_desc in alternative_keys:
                    print(f"      Testing {key_desc}: {alt_key.hex().upper()}")
                    try:
                        session = Ntag424AuthSession(alt_key)
                        session_keys = session.authenticate(card, key_no=0)
                        print(f"      ✅ Authentication successful with {key_desc}!")
                        break
                    except Exception as e:
                        print(f"      ❌ Failed: {e}")
                
                # Test 2: Try EV1 authentication (if supported)
                print(f"\n   2. EV1 Authentication not implemented yet")
                
                # Test 3: Try custom Seritag protocol (if known)
                print(f"\n   3. Custom Seritag protocol not implemented yet")
                
                print(f"\n📋 Diagnostic Summary:")
                print(f"   - Standard EV2 authentication: ❌ FAILED")
                print(f"   - Alternative keys: ❌ FAILED") 
                print(f"   - EV1 authentication: ⏳ NOT TESTED")
                print(f"   - Custom Seritag protocol: ⏳ NOT IMPLEMENTED")
                print(f"\n💡 Next Steps:")
                print(f"   1. Research Seritag's official authentication documentation")
                print(f"   2. Contact Seritag support for technical specifications")
                print(f"   3. Implement EV1 authentication support")
                print(f"   4. Reverse engineer the authentication protocol")
                
            else:
                print(f"\n✅ EV2 Authentication successful!")
                print(f"   Seritag tag supports standard EV2 protocol")
                
    except Exception as e:
        print(f"❌ Authentication diagnostic failed: {e}")
        return False
        
    return True

if __name__ == "__main__":
    success = test_seritag_authentication()
    if success:
        print("\n🎉 Seritag authentication diagnostic completed!")
    else:
        print("\n💥 Seritag authentication diagnostic failed!")
        sys.exit(1)
