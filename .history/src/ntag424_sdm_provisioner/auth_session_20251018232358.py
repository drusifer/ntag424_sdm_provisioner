from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication
from ntag424_sdm_provisioner.commands.change_file_settings import ChangeFileSettings
from ntag424_sdm_provisioner.commands.base import SDMConfiguration, CommMode

def authenticate_example():
    """Example: Authenticate with factory key."""
    
    FACTORY_KEY = b'\x00' * 16  # Default factory key
    
    with CardManager(0) as card:
        # Select application
        SelectPiccApplication().execute(card)
        
        # Create session and authenticate
        session = Ntag424AuthSession(FACTORY_KEY)
        session_keys = session.authenticate(card, key_no=0)
        
        print(session_keys)
        
        # Now you can use the session for authenticated commands
        # Example: Change file settings with CMAC
        config = SDMConfiguration(
            file_no=0x02,
            comm_mode=CommMode.MAC,  # Requires CMAC
            access_rights=b'\xE0\xEE',
            enable_sdm=False
        )
        
        ChangeFileSettings(config).execute(card, session=session)
        
        print("✅ Command executed with CMAC protection")

if __name__ == "__main__":
    authenticate_example()
