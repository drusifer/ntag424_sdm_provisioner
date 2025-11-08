"""
Simple authentication demonstration for NTAG424 DNA.

This script demonstrates:
1. Connecting to an NTAG424 tag
2. Authenticating with factory key
3. Using the authenticated session for protected commands
"""
import logging
import sys

# Set up comprehensive logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Enable debug logging for specific modules
logging.getLogger('ntag424_sdm_provisioner.crypto.auth_session').setLevel(logging.DEBUG)
logging.getLogger('ntag424_sdm_provisioner.commands.sdm_commands').setLevel(logging.DEBUG)
logging.getLogger('ntag424_sdm_provisioner.hal').setLevel(logging.DEBUG)

from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.commands.change_file_settings import ChangeFileSettings
from ntag424_sdm_provisioner.constants import SDMConfiguration, CommMode, FileNo, AccessRightsPresets, SDMOption, FACTORY_KEY

def authenticate_example():
    """Example: Authenticate with factory key and demonstrate session usage."""
    
    print("🔐 NTAG424 Authentication Demo")
    print("=" * 50)
    
    # Debug: Show what key we're using
    print(f"🔑 Using factory key: {FACTORY_KEY.hex().upper()}")
    print(f"🔑 Key length: {len(FACTORY_KEY)} bytes")
    
    with CardManager(0) as card:
        print("✅ Connected to NFC reader")
        
        # Select application
        print("📱 Selecting PICC application...")
        SelectPiccApplication().execute(card)
        print("✅ Selected PICC application")
        
        # Get chip version to verify tag type
        print("🔍 Getting chip version information...")
        try:
            version_info = GetChipVersion().execute(card)
            print(f"✅ Chip identified: {version_info}")
            print(f"   UID: {version_info.uid.hex().upper()}")
            print(f"   Hardware: {version_info.hw_major_version}.{version_info.hw_minor_version}")
            print(f"   Software: {version_info.sw_major_version}.{version_info.sw_minor_version}")
            
            # Check if this is actually an NTAG424 DNA
            if version_info.hw_major_version != 0x04 or version_info.hw_minor_version != 0x02:
                print("⚠️  WARNING: This may not be an NTAG424 DNA tag!")
                print(f"   Expected HW version 4.2, got {version_info.hw_major_version}.{version_info.hw_minor_version}")
        except Exception as e:
            print(f"❌ Failed to get chip version: {e}")
            print("   This might not be an NTAG424 DNA tag")
            return
        
        # Authenticate using type-safe API
        print("🔑 Starting authentication process...")
        print(f"🔑 Using key: {FACTORY_KEY.hex().upper()}")
        
        # Try different keys
        keys_to_try = [
            (0, FACTORY_KEY, "Factory Key (all zeros)"),
            (1, FACTORY_KEY, "Factory Key (all zeros)"),
            (2, FACTORY_KEY, "Factory Key (all zeros)"),
            (3, FACTORY_KEY, "Factory Key (all zeros)"),
            (4, FACTORY_KEY, "Factory Key (all zeros)")
        ]
        
        auth_conn = None
        for key_no, key, description in keys_to_try:
            print(f"\n🔑 Trying {description} for key {key_no}...")
            try:
                from ntag424_sdm_provisioner.commands.sdm_commands import AuthenticateEV2
                auth_conn = AuthenticateEV2(key, key_no).execute(card)
                print(f"✅ Authentication successful with {description}!")
                break
            except Exception as e:
                print(f"❌ Failed with {description}: {e}")
                if hasattr(e, 'sw1') and hasattr(e, 'sw2'):
                    print(f"   Status Word: 0x{e.sw1:02X}{e.sw2:02X}")
                continue
        
        if auth_conn is None:
            print(f"❌ Authentication failed with all keys!")
            return
        
        # Authentication was successful
        print(f"\n✅ Authentication successful!")
        print(f"   Session keys: {auth_conn.session.session_keys}")
        print(f"   Transaction ID: {auth_conn.session.session_keys.ti.hex().upper()}")
        
        # Now use authenticated connection for commands
        print("\n📝 Testing authenticated command...")
        
        # Example: Change file settings with CMAC protection
        config = SDMConfiguration(
            file_no=FileNo.NDEF_FILE,
            comm_mode=CommMode.MAC,  # Requires CMAC
            access_rights=AccessRightsPresets.FREE_READ_KEY0_WRITE.to_bytes(),
            enable_sdm=False,
            sdm_options=int(SDMOption.NONE),
            picc_data_offset=0,
            mac_input_offset=0,
            mac_offset=0
        )
        
        try:
            from ntag424_sdm_provisioner.commands.change_file_settings import ChangeFileSettingsAuth
            ChangeFileSettingsAuth(config).execute(auth_conn)
            print("✅ Command executed with CMAC protection")
        except Exception as e:
            print(f"❌ Command failed: {e}")
        
        print("\n🎉 Authentication demo complete!")

if __name__ == "__main__":
    authenticate_example()
