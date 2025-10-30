"""
Example 05: Full SDM Provisioning

This script orchestrates the entire process of taking a factory-default
NTAG424 tag and provisioning it for Secure Dynamic Messaging (SDM).

WARNING: This script will permanently change the keys on your tag.
The new keys are printed to the console, but if you lose them, you will
no longer be able to administer the tag.

The process is as follows:
1. Connect to the tag.
2. Authenticate with the default PICC Master Key (Key 0).
3. Generate new, random keys for all 5 key slots.
4. Change each key from the factory default to the new random key.
5. Re-authenticate with the NEW PICC Master Key.
6. Configure the NDEF file (File 2) for SDM:
   - Enable UID and Read Counter mirroring.
   - Set file read access to be free (no key needed).
   - Set file write access to require the new Key 1.
   - Set file settings change access to require the new PICC Master Key.
7. Write a sample NDEF URI to the file with SDM placeholders.
"""
import os
from smartcard.System import readers

# --- Add parent directory to path to allow imports ---

from ntag424_sdm_provisioner.hal import list_readers, CardManager
from ntag424_sdm_provisioner.session import Ntag424Session
from ntag424_sdm_provisioner.commands.change_key import ChangeKey
from ntag424_sdm_provisioner.commands.set_file_settings import (
    FileSettingsBuilder, SetFileSettings, CommsMode, KEY_NO_FREE_ACCESS, NDEF_FILE_NO
)
from ntag424_sdm_provisioner.commands.write_ndef_message import WriteNdefMessage


def generate_random_key() -> bytes:
    """Generates a cryptographically secure 16-byte key."""
    return os.urandom(16)


def main():
    """Main provisioning function."""
    # --- Configuration ---
    # WARNING: The base_uri MUST contain placeholders for SDM parameters
    # that your server is expecting. The placeholders {UID} and {CNT}
    # are just examples. The NTAG424 hardware replaces these strings
    # in the URL with the actual UID and counter values *after* the MAC
    # is calculated.
    base_uri = "https://example.com/verify?uid={UID}&c={CNT}"

    # Factory default key (16 bytes of zeros)
    factory_key = b'\x00' * 16

    try:
        reader = list_readers()[0]
        print(f"INFO: Using reader: {reader}")
    except IndexError:
        print("ERROR: No readers found!")
        return

    with CardManager(reader) as card:
        # 1. Generate new keys
        print("INFO: Generating new keys...")
        new_keys = {i: generate_random_key() for i in range(5)}
        for i, key in new_keys.items():
            print(f"  - New Key {i}: {key.hex().upper()}")

        # 2. Authenticate with factory key and change all keys
        print("\nINFO: Authenticating with factory key to change keys...")
        session = Ntag424Session(card, key_no=0, key=factory_key)
        session.authenticate()
        print("INFO: Authentication successful.")

        for i in range(5):
            print(f"INFO: Changing Key {i}...")
            cmd = ChangeKey(session, key_no_to_change=i, new_key=new_keys[i], old_key=factory_key)
            cmd.execute(card)
        print("INFO: All keys changed successfully.")

        # 3. Re-authenticate with the NEW PICC Master Key
        print("\nINFO: Re-authenticating with new PICC Master Key (Key 0)...")
        session_new = Ntag424Session(card, key_no=0, key=new_keys[0])
        session_new.authenticate()
        print("INFO: Authentication successful.")

        # 4. Configure File 2 (NDEF File) for SDM
        print("\nINFO: Configuring NDEF file for SDM...")
        # We need read access to be "free" so that a phone can read the URL
        # without authentication. The security comes from the server verifying
        # the MAC. Write access and settings changes are protected by keys.
        settings_builder = (
            FileSettingsBuilder(file_no=NDEF_FILE_NO)
            .with_comms_mode(CommsMode.PLAIN)
            .with_access_keys(
                read=KEY_NO_FREE_ACCESS,  # Free read
                write=1,                 # Write needs Key 1
                read_write=0,            # Read/Write needs Key 0
                change=0                 # Change settings needs Key 0
            )
            .with_sdm(uid_mirror=True, read_ctr_mirror=True)
        )
        settings_payload = settings_builder.build()

        cmd_set_settings = SetFileSettings(session_new, settings_payload)
        cmd_set_settings.execute(card)
        print("INFO: NDEF file configured for SDM.")

        # 5. Write the NDEF message
        print(f"\nINFO: Writing NDEF URI: {base_uri}")
        # Writing may require authentication if the file settings were
        # different. We pass the authenticated session just in case.
        cmd_write_ndef = WriteNdefMessage(session_new, uri=base_uri)
        cmd_write_ndef.execute(card)
        print("INFO: NDEF URI written successfully.")

        print("\nSUCCESS: Tag provisioning complete.")


if __name__ == "__main__":
    main()
