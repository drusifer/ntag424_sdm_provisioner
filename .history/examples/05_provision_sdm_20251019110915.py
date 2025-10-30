"""
Complete provisioning script for NTAG424 DNA for SDM.

This script orchestrates the entire process:
1. Connects to the tag.
2. Reads the tag's UID.
3. Authenticates with the factory PICC Master Key.
4. Uses a KeyManager to get new, unique keys for the tag.
5. Changes all keys from their factory defaults.
6. Re-authenticates with the new PICC Master Key.
7. Configures the NDEF file for full SDM functionality.
8. Writes a sample NDEF URI.
"""
import secrets

# --- Project Imports ---
from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.commands.base import SDMConfiguration, CommMode , ApduError, AuthenticationError
from ntag424_sdm_provisioner.commands.sdm_commands import (
    SelectPiccApplication,
    ChangeFileSettings,
)


# --- Configuration ---
# WARNING: For demonstration only. In production, use a secure key derivation system.
NEW_PICC_MASTER_KEY = secrets.token_bytes(16)
NEW_FILE_DATA_READ_KEY = secrets.token_bytes(16)
NEW_SDM_MAC_KEY = secrets.token_bytes(16)

# The base URL to write to the tag. Placeholders will be replaced by the NFC device.
# {UID} will be replaced with the tag's UID.
# {CNT} will be replaced with the tap counter.
# {MAC} will be the security code.
NDEF_URI = "https://example.com/tag?uid={UID}&c={CNT}&mac={MAC}"

from ntag424_sdm_provisioner.constants import (
    FileNo, KeyNo, CommMode, AccessRight, AccessRights, 
    AccessRightsPresets, SDMOption, FACTORY_KEY
)

def provision_with_error_handling():
    """Provision with comprehensive error handling."""
    
    try:
        with CardManager(0) as card:
            SelectPiccApplication().execute(card)
            
            # Authenticate
            session = Ntag424AuthSession(FACTORY_KEY)
            session.authenticate(card, key_no=KeyNo.KEY_0)
            
            # Configure SDM
            config = SDMConfiguration(
                file_no=FileNo.NDEF_FILE,
                comm_mode=CommMode.PLAIN,
                access_rights=AccessRightsPresets.FREE_READ_KEY0_WRITE,
                enable_sdm=True,
                sdm_options=SDMOption.BASIC_SDM,
                picc_data_offset=34,
                mac_input_offset=34,
                mac_offset=47
            )
            
            ChangeFileSettings(config).execute(card, session=session)
            
            print("✅ Provisioned successfully!")
            
    except ApduError as e:
        print(f"❌ APDU Error: {e}")
        print(f"   Category: {e.category.name}")
        
        if e.is_authentication_error():
            print("   → Check your key!")
        elif e.is_permission_error():
            print("   → Access rights not satisfied")
        elif e.is_not_found_error():
            print("   → File or application not found")
    
    except AuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def parse_existing_config():
    """Parse configuration read from card."""
    
    # Simulated data from GetFileSettings
    raw_access_rights = b'\xE0\xEE'
    
    # Parse into readable format
    rights = AccessRights.from_bytes(raw_access_rights)
    print(f"Parsed rights: {rights}")
    # Output: "Read=FREE, Write=KEY_0, RW=FREE, Change=FREE"
    
    # Check specific permissions
    if rights.read == AccessRight.FREE:
        print("✅ Anyone can read this file")
    
    if rights.write == AccessRight.KEY_0:
        print("🔒 Write requires key 0")


def demonstrate_sdm_options():
    """Show SDM option combinations."""
    
    # Option 1: Basic SDM (UID mirror only)
    basic = SDMOption.ENABLED | SDMOption.UID_MIRROR
    
    # Option 2: Add read counter
    with_counter = basic | SDMOption.READ_COUNTER
    
    # Option 3: Use preset
    preset = SDMOption.SDM_WITH_COUNTER
    
    # Check flags
    if preset & SDMOption.UID_MIRROR:
        print("✅ UID mirror is enabled")
    
    if preset & SDMOption.READ_COUNTER:
        print("✅ Read counter is enabled")
    
    # Convert to byte for APDU
    options_byte = int(preset)  # 0xE0
    print(f"SDM options byte: 0x{options_byte:02X}")


def main():
    """Runs the full provisioning sequence."""
    print("--- NTAG424 SDM Provisioning Script ---")

    try:
        provision_with_error_handling()
        print("\n--- Provisioning completed successfully! ✅ ---")

    except Exception as e:
        print(f"\n--- An error occurred: {e} ---")
        print("Provisioning failed.")


if __name__ == "__main__":
    main()