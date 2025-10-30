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
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication
from ntag424_sdm_provisioner.commands.change_file_settings import ChangeFileSettings
from ntag424_sdm_provisioner.constants import SDMConfiguration, CommMode, FileNo, AccessRightsPresets, SDMOption, FACTORY_KEY

def authenticate_example():
    """Example: Authenticate with factory key and demonstrate session usage."""
    
    print("🔐 NTAG424 Authentication Demo")
    print("=" * 50)
    
    with CardManager(0) as card:
        print("✅ Connected to NFC reader")
        
        # Select application
        SelectPiccApplication().execute(card)
        print("✅ Selected PICC application")
        
        # Create session and authenticate
        print("🔑 Authenticating with factory key...")
        session = Ntag424AuthSession(FACTORY_KEY)
        session_keys = session.authenticate(card, key_no=0)
        
        print(f"✅ Authentication successful!")
        print(f"   Session keys: {session_keys}")
        print(f"   Transaction ID: {session_keys.ti.hex().upper()}")
        
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
