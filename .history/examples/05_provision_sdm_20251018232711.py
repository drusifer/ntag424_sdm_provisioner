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
from ntag424_sdm_provisioner.session import Ntag424Session, KEY_DEFAULT_FACTORY
from ntag424_sdm_provisioner.commands.sdm_helpers import (
    calculate_sdm_offsets,
    build_ndef_uri_record

)
from ntag424_sdm_provisioner.commands.base import SDMUrlTemplate, SDMConfiguration, CommMode, 
from ntag424_sdm_provisioner.commands.sdm_commands import (
    SelectPiccApplication,
    ChangeFileSettings,
    WriteData
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


def provision_clean():
    """Clean provisioning with separated concerns."""
    
    with CardManager(0) as card:
        SelectPiccApplication().execute(card)
        
        # Auth (you implement this)
        session = authenticate_with_factory_key(card)
        
        # 1. Define URL template (dumb dataclass)
        template = SDMUrlTemplate(
            base_url="https://example.com/verify",
            uid_placeholder="00000000000000",
            cmac_placeholder="0000000000000000"
        )
        print(template)
        
        # 2. Calculate offsets (helper function)
        offsets = calculate_sdm_offsets(template)
        print(f"Calculated offsets: {offsets}")
        
        # 3. Build config (dumb dataclass)
        config = SDMConfiguration(
            file_no=0x02,
            comm_mode=CommMode.PLAIN,
            access_rights=b'\xE0\xEE',
            enable_sdm=True,
            **offsets
        )
        print(config)
        
        # 4. Apply settings (command does the work)
        ChangeFileSettings(config).execute(card, session=session)
        
        # 5. Build NDEF (helper function)
        ndef_data = build_ndef_uri_record(str(template))
        
        # 6. Write NDEF (command does the work)
        WriteData(file_no=0x02, data=ndef_data).execute(card, session=session)
        

def main():
    """Runs the full provisioning sequence."""
    print("--- NTAG424 SDM Provisioning Script ---")

    try:
        with CardManager() as connection:
            # 1. Get Tag UID - needed for key derivation

    except Exception as e:
        print(f"\n--- An error occurred: {e} ---")
        print("Provisioning failed.")


if __name__ == "__main__":
    main()