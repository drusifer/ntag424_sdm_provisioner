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




