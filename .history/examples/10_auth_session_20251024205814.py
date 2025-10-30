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
        
        # Create session and authenticate
        print("🔑 Creating authentication session...")
        session = Ntag424AuthSession(FACTORY_KEY)
        print(f"🔑 Session created with key: {session.key.hex().upper()}")
        
        print("🔑 Starting authentication process...")
        try:
            session_keys = session.authenticate(card, key_no=0)
            
            print(f"✅ Authentication successful!")
            print(f"   Session keys: {session_keys}")
            print(f"   Transaction ID: {session_keys.ti.hex().upper()}")
            print(f"   Session ENC key: {session_keys.session_enc_key.hex().upper()}")
            print(f"   Session MAC key: {session_keys.session_mac_key.hex().upper()}")
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            print(f"   Error type: {type(e).__name__}")
            
            # Try to get more details about the error
            if hasattr(e, 'sw1') and hasattr(e, 'sw2'):
                print(f"   Status Word: 0x{e.sw1:02X}{e.sw2:02X}")
                if hasattr(e, 'category'):
                    print(f"   Error Category: {e.category}")
            
            print("\n🔍 Debugging information:")
            print("   - Make sure you have a brand new NTAG424 DNA tag")
            print("   - Check that the tag is properly positioned on the reader")
            print("   - Verify the tag hasn't been previously configured")
            print("   - Try removing and re-tapping the tag")
            
            return  # Exit early on authentication failure
        
        # Now you can use the session for authenticated commands
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
            ChangeFileSettings(config).execute(card, session=session)
            print("✅ Command executed with CMAC protection")
        except Exception as e:
            print(f"❌ Command failed: {e}")
        
        print("\n🎉 Authentication demo complete!")

if __name__ == "__main__":
    authenticate_example()
