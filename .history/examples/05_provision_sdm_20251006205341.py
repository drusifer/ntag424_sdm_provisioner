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
from ntag424_sdm_provisioner.commands.get_version import GetVersion
from ntag424_sdm_provisioner.commands.change_key import ChangeKey
from ntag424_sdm_provisioner.commands.set_file_settings import FileSettingsBuilder, SetFileSettings
from ntag424_sdm_provisioner.commands.write_ndef_message import WriteNdefMessage
from ntag424_sdm_provisioner.key_manager import StaticKeyManager

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


def main():
    """Runs the full provisioning sequence."""
    print("--- NTAG424 SDM Provisioning Script ---")

    try:
        with CardManager() as connection:
            # 1. Get Tag UID - needed for key derivation
            print("\nStep 1: Reading Tag Version and UID...")
            get_version_cmd = GetVersion()
            version_info = get_version_cmd.execute(connection)
            uid = version_info.uid
            print(f"  Tag UID: {uid.hex().upper()}")

            # Initialize our key manager with the desired new keys.
            # In a real system, this would be a secure KDF-based manager.
            key_manager = StaticKeyManager({
                0: NEW_PICC_MASTER_KEY,
                1: NEW_FILE_DATA_READ_KEY,  # File Read/Write Key
                2: NEW_SDM_MAC_KEY,         # SDM MAC Calculation Key
                # Keys 3 and 4 are not used in this example, but should also be changed.
                3: secrets.token_bytes(16),
                4: secrets.token_bytes(16),
            })

            # 2. Authenticate with factory key
            print("\nStep 2: Authenticating with factory PICC Master Key...")
            session = Ntag424Session(connection, key_no=0, key=KEY_DEFAULT_FACTORY)
            session.authenticate()
            print("  Authentication successful.")

            # 3. Change all keys
            print("\nStep 3: Changing all keys from factory defaults...")
            for key_no in range(5):
                old_key = KEY_DEFAULT_FACTORY
                new_key = key_manager.get_key_for_uid(uid, key_no)
                change_key_cmd = ChangeKey(session, key_no_to_change=key_no, new_key=new_key, old_key=old_key)
                change_key_cmd.execute(connection)
            print("  All keys changed.")

            # 4. Re-authenticate with the NEW PICC Master Key
            print("\nStep 4: Re-authenticating with NEW PICC Master Key...")
            new_picc_master_key = key_manager.get_key_for_uid(uid, 0)
            session = Ntag424Session(connection, key_no=0, key=new_picc_master_key)
            session.authenticate()
            print("  Authentication successful.")

            # 5. Configure File 2 for SDM
            print("\nStep 5: Configuring NDEF File (File 2) for SDM...")
            settings = (FileSettingsBuilder()
                        .set_comms_mode('ENC')
                        .set_access_rights(read_key=2, write_key=1, rw_key=1, change_key=0)
                        .enable_sdm(uid_mirror=True, read_ctr_mirror=True, read_ctr_limit=0)
                        .build())
            set_settings_cmd = SetFileSettings(session, file_no=2, settings=settings)
            set_settings_cmd.execute(connection)
            print("  File settings configured.")

            # 6. Write the NDEF message
            print("\nStep 6: Writing NDEF message...")
            write_ndef_cmd = WriteNdefMessage(session, uri=NDEF_URI)
            write_ndef_cmd.execute(connection)
            print("  NDEF message written successfully.")

            print("\n--- Provisioning Complete ---")

    except Exception as e:
        print(f"\n--- An error occurred: {e} ---")
        print("Provisioning failed.")


if __name__ == "__main__":
    main()