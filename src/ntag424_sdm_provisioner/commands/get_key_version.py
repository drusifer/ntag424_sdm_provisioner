"""
GetKeyVersion command for NTAG424 DNA.
"""

from typing import TYPE_CHECKING
from dataclasses import dataclass

from ntag424_sdm_provisioner.commands.base import ApduCommand

if TYPE_CHECKING:
    from ntag424_sdm_provisioner.hal import NTag424CardConnection


@dataclass
class KeyVersionResponse:
    """Response from GetKeyVersion command."""
    key_no: int
    version: int
    
    def __str__(self) -> str:
        return f"Key 0x{self.key_no:02X} Version: 0x{self.version:02X}"


class GetKeyVersion(ApduCommand):
    """
    Get version of a specific key.
    
    Typically requires authentication (CommMode.MAC), but works with
    both regular and authenticated connections.
    """
    
    def __init__(self, key_no: int):
        super().__init__(use_escape=True)
        self.key_no = key_no
    
    def __str__(self) -> str:
        return f"GetKeyVersion(key_no=0x{self.key_no:02X})"
    
    def build_apdu(self) -> list:
        """Build APDU for new connection.send(command) pattern."""
        return [0x90, 0x64, 0x00, 0x00, 0x01, self.key_no, 0x00]
    
    def parse_response(self, data: bytes, sw1: int, sw2: int) -> KeyVersionResponse:
        """Parse response for new connection.send(command) pattern."""
        if not data or len(data) < 1:
            raise ValueError(f"Key version data too short: {len(data)} bytes (minimum 1)")
        
        version = data[0]
        return KeyVersionResponse(key_no=self.key_no, version=version)

