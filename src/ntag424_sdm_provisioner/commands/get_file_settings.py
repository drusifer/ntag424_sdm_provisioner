"""
GetFileSettings command for NTAG424 DNA.
"""

from typing import TYPE_CHECKING

from ntag424_sdm_provisioner.commands.base import ApduCommand
from ntag424_sdm_provisioner.constants import FileSettingsResponse
from ntag424_sdm_provisioner.commands.sdm_helpers import parse_file_settings

if TYPE_CHECKING:
    from ntag424_sdm_provisioner.hal import NTag424CardConnection


class GetFileSettings(ApduCommand):
    """
    Get settings for a specific file.
    
    Can be called with regular or authenticated connection.
    Most files allow reading settings without authentication (CommMode.PLAIN).
    """
    
    def __init__(self, file_no: int):
        super().__init__(use_escape=True)
        self.file_no = file_no
    
    def __str__(self) -> str:
        return f"GetFileSettings(file_no=0x{self.file_no:02X})"
    
    def build_apdu(self) -> list:
        """Build APDU for new connection.send(command) pattern."""
        return [0x90, 0xF5, 0x00, 0x00, 0x01, self.file_no, 0x00]
    
    def parse_response(self, data: bytes, sw1: int, sw2: int) -> FileSettingsResponse:
        """Parse response for new connection.send(command) pattern."""
        return parse_file_settings(self.file_no, data)

