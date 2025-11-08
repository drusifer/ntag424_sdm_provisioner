"""
GetFileIds command for NTAG424 DNA.
"""

from typing import TYPE_CHECKING, List

from ntag424_sdm_provisioner.commands.base import ApduCommand

if TYPE_CHECKING:
    from ntag424_sdm_provisioner.hal import NTag424CardConnection


class GetFileIds(ApduCommand):
    """
    Get list of file IDs in the current application.
    
    Returns the list of files available in the selected PICC application.
    """
    
    def __init__(self):
        super().__init__(use_escape=True)
    
    def __str__(self) -> str:
        return "GetFileIds()"
    
    def build_apdu(self) -> list:
        """Build APDU for new connection.send(command) pattern."""
        return [0x90, 0x6F, 0x00, 0x00, 0x00]
    
    def parse_response(self, data: bytes, sw1: int, sw2: int) -> List[int]:
        """Parse response for new connection.send(command) pattern."""
        return list(data)

