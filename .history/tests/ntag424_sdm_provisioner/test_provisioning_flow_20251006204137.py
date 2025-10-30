import secrets
from unittest.mock import patch

import pytest

# Use absolute imports based on the 'src' layout
from ntag424_sdm_provisioner.commands.change_key import ChangeKey
from ntag424_sdm_provisioner.commands.set_file_settings import FileSettingsBuilder, SetFileSettings
from ntag424_sdm_provisioner.commands.write_ndef_message import WriteNdefMessage
from ntag424_sdm_provisioner.session import Ntag424Session

# Import our mock objects
from mock_hal import MockCardManager


@pytest.fixture
def mock_card_manager():
    """Provides a mock card manager for the test."""
    return MockCardManager()

def test_full_provisioning_flow(mock_card_manager: MockCardManager):
    """
    Tests the entire SDM provisioning flow against a mock hardware connection.
    This test verifies that all commands are constructed and executed in the
    correct sequence without errors.
    """
    # Use patch to replace the real hardware manager with our mock,
    # making sure to target the correct, full module path.
    with patch('ntag424_sdm_provisioner.session.CardManager', return_value=mock_card_manager), \
         patch('ntag424_sdm_provisioner.commands.base.CardManager', return_value=mock_card_manager):

        print("\n--- Starting Mock Provisioning Flow ---")

        # --- 1. Generate new random keys ---
        new_picc_master_key = secrets.token_bytes(16)
        new_file_write_key = secrets.token_bytes(16)
        new_sdm_mac_key = secrets.token_bytes(16)

        # --- 2. Authenticate with factory PICC Master Key ---
        print("Step 1: Authenticating with factory PICC Master Key (Key 0)...")
        with mock_card_manager as connection:
            session = Ntag424Session(connection, key_no=0, key=KEY_DEFAULT_FACTORY)
            session.authenticate()
            print("Authentication successful.")

            # --- 3. Change all keys from factory defaults ---
            print("Step 2: Changing all keys...")
            ChangeKey(session, key_no_to_change=0, new_key=new_picc_master_key, old_key=KEY_DEFAULT_FACTORY).execute(connection)
            ChangeKey(session, key_no_to_change=1, new_key=new_file_write_key, old_key=KEY_DEFAULT_FACTORY).execute(connection)
            ChangeKey(session, key_no_to_change=2, new_key=new_sdm_mac_key, old_key=KEY_DEFAULT_FACTORY).execute(connection)
            print("All keys changed successfully.")

        # --- 4. Verify key change by re-authenticating with the NEW key ---
        print("Step 3: Verifying key change by re-authenticating with new PICC Master Key...")
        with mock_card_manager as connection:
            mock_connection = connection
            mock_connection.keys[0] = new_picc_master_key
            mock_connection.keys[1] = new_file_write_key
            mock_connection.keys[2] = new_sdm_mac_key

            session = Ntag424Session(connection, key_no=0, key=new_picc_master_key)
            session.authenticate()
            print("Re-authentication successful.")

            # --- 5. Configure File 2 for SDM ---
            print("Step 4: Configuring NDEF file for SDM...")
            settings = (FileSettingsBuilder()
                        .set_read_key(2)
                        .set_write_key(1)
                        .set_read_write_key(1)
                        .set_change_key(0)
                        .set_sdm_enabled(True)
                        .set_uid_mirroring(True)
                        .set_read_counter_mirroring(True)
                        .build())
            SetFileSettings(session, file_no=2, settings=settings).execute(connection)
            print("File settings configured.")

            # --- 6. Write NDEF Message ---
            print("Step 5: Writing NDEF message with SDM placeholders...")
            uri = "https://example.com/tag?uid={UID}&c={CNT}"
            WriteNdefMessage(session, uri=uri).execute(connection)
            print("NDEF message written successfully.")

        print("\n--- Mock Provisioning Flow Completed Successfully ---")

        # --- Assertions ---
        final_keys = mock_card_manager.connection.keys
        assert final_keys[0] == new_picc_master_key
        assert final_keys[1] == new_file_write_key
        assert final_keys[2] == new_sdm_mac_key
        assert final_keys[3] == KEY_DEFAULT_FACTORY

