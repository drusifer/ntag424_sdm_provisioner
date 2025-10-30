from ntag424_sdm_provisioner.commands.base import (
    SW_OK, ApduCommand, ApduError, SuccessResponse, SDMConfiguration, CommMode)
from ntag424_sdm_provisioner.commands.sdm_helpers import build_sdm_settings_payload
from ntag424_sdm_provisioner.hal import NTag424CardConnection, hexb
from ntag424_sdm_provisioner.crypto.se import Ntag424AuthSession
from typing import Optional 

from logging import getLogger
log = getLogger(__name__)

class ChangeFileSettings(ApduCommand):
    """Change file settings including SDM configuration."""
    
    def __init__(self, config: SDMConfiguration, use_escape: bool = False):
        super().__init__(use_escape)
        self.config = config
    
    def __str__(self) -> str:
        return f"ChangeFileSettings(file=0x{self.config.file_no:02X})"
    
    def execute(
        self, 
        connection: 'NTag424CardConnection',
        session: Optional['Ntag424AuthSession'] = None
    ) -> SuccessResponse:
        """Execute the command with optional CMAC protection."""
        
        # Use helper to build payload
        settings_payload = build_sdm_settings_payload(self.config)
        
        # Build base APDU
        cmd_header = bytes([0x90, 0x5F, 0x00, 0x00])
        cmd_data = bytes([self.config.file_no]) + settings_payload
        
        # Apply CMAC if needed
        if self.config.comm_mode in [CommMode.MAC, CommMode.FULL]:
            if session is None:
                raise ValueError("Authenticated session required for MAC/FULL comm mode")
            cmd_data = session.apply_cmac(cmd_header, cmd_data)
        
        # Build final APDU
        apdu = list(cmd_header) + [len(cmd_data)] + list(cmd_data) + [0x00]
        
        log.debug(f"ChangeFileSettings APDU: {hexb(apdu)}")
        
        # Send command
        _, sw1, sw2 = self.send_apdu(connection, apdu)
        
        if (sw1, sw2) != SW_OK:
            raise ApduError(
                f"ChangeFileSettings failed for file {self.config.file_no:02X}",
                sw1, sw2
            )
        
        return SuccessResponse(f"File {self.config.file_no:02X} settings changed")