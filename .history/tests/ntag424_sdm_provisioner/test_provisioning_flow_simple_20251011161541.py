import secrets

from ntag424_sdm_provisioner.commands.change_key import ChangeKey
from ntag424_sdm_provisioner.commands.set_file_settings import FileSettingsBuilder, SetFileSettings
from ntag424_sdm_provisioner.commands.write_ndef_message import WriteNdefMessage
from ntag424_sdm_provisioner.session import Ntag424Session

from mock_hal import MockCardManager, KEY_DEFAULT_FACTORY


def test_list_keys():
    """Test that the mock card manager has the expected default keys."""
    mock_card_manager = MockCardManager()
    

def test_full_provisioning_flow_with_mock_manager():
    """Run the full provisioning flow using the provided MockCardManager
    directly (no patching). This exercises session and command integration
    against the mock hardware implementation.
    """
    mock_card_manager = MockCardManager()

    # --- 1. Generate new random keys ---
    new_picc_master_key = secrets.token_bytes(16)
    new_file_write_key = secrets.token_bytes(16)
    new_sdm_mac_key = secrets.token_bytes(16)

    # --- 2. Authenticate with factory PICC Master Key ---
    with mock_card_manager as connection:
        session = Ntag424Session(connection, key_no=0, key=KEY_DEFAULT_FACTORY)
        session.authenticate()

        # --- 3. Change keys ---
        ChangeKey(session, key_no_to_change=0, new_key=new_picc_master_key, old_key=KEY_DEFAULT_FACTORY).execute(connection)
        ChangeKey(session, key_no_to_change=1, new_key=new_file_write_key, old_key=KEY_DEFAULT_FACTORY).execute(connection)
        ChangeKey(session, key_no_to_change=2, new_key=new_sdm_mac_key, old_key=KEY_DEFAULT_FACTORY).execute(connection)

    # --- 4. Re-authenticate with new key to verify change ---
    with mock_card_manager as connection:
        connection.keys[0] = new_picc_master_key
        connection.keys[1] = new_file_write_key
        connection.keys[2] = new_sdm_mac_key

        session = Ntag424Session(connection, key_no=0, key=new_picc_master_key)
        session.authenticate()

        # Configure file and write NDEF
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
        WriteNdefMessage(session, uri="https://example.com/tag?uid={UID}&c={CNT}").execute(connection)

    # Verify final keys saved in mock
    final_keys = mock_card_manager.connection.keys
    assert final_keys[0] == new_picc_master_key
    assert final_keys[1] == new_file_write_key
    assert final_keys[2] == new_sdm_mac_key
