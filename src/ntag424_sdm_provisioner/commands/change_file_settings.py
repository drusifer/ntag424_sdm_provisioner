from typing import Optional
from ntag424_sdm_provisioner.constants import CommMode, SuccessResponse, SDMConfiguration
from ntag424_sdm_provisioner.commands.base import ApduCommand, AuthApduCommand, ApduError, AuthenticatedConnection
from ntag424_sdm_provisioner.commands.sdm_helpers import build_sdm_settings_payload
from ntag424_sdm_provisioner.hal import NTag424CardConnection, hexb
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession

from logging import getLogger
log = getLogger(__name__)


class ChangeFileSettings(ApduCommand):
    """
    Change file settings - PLAIN mode only (no authentication).
    
    For authenticated modes (CommMode.MAC, CommMode.FULL), use ChangeFileSettingsAuth.
    """
    
    def __init__(self, config: SDMConfiguration):
        super().__init__(use_escape=False)  # Use transmit for authenticated commands
        self.config = config
        
        if self.config.comm_mode != CommMode.PLAIN:
            raise ValueError(
                f"ChangeFileSettings only supports CommMode.PLAIN. "
                f"For {self.config.comm_mode}, use ChangeFileSettingsAuth"
            )
    
    def __str__(self) -> str:
        return f"ChangeFileSettings(file=0x{self.config.file_no:02X})"
    
    def build_apdu(self) -> list:
        """Build APDU for connection.send(command) pattern."""
        # Use helper to build payload
        settings_payload = build_sdm_settings_payload(self.config)
        
        # Build APDU (plain mode - no encryption/CMAC)
        cmd_header_apdu = bytes([0x90, 0x5F, 0x00, 0x00])
        file_no_byte = bytes([self.config.file_no])
        cmd_data = file_no_byte + settings_payload
        
        apdu = list(cmd_header_apdu) + [len(cmd_data)] + list(cmd_data) + [0x00]
        
        log.debug(f"ChangeFileSettings (PLAIN) APDU: {hexb(apdu)}")
        return apdu
    
    def parse_response(self, data: bytes, sw1: int, sw2: int) -> SuccessResponse:
        """Parse response for connection.send(command) pattern."""
        return SuccessResponse(f"File {self.config.file_no:02X} settings changed")


class ChangeFileSettingsAuth(AuthApduCommand):
    """
    Change file settings - Authenticated modes (CommMode.MAC, CommMode.FULL).
    
    Type-safe: Requires AuthenticatedConnection via connection.send(command).
    For PLAIN mode, use ChangeFileSettings instead.
    """
    
    def __init__(self, config: SDMConfiguration):
        super().__init__(use_escape=False)
        self.config = config
        
        if self.config.comm_mode == CommMode.PLAIN:
            raise ValueError(
                "ChangeFileSettingsAuth is for authenticated modes. "
                "For CommMode.PLAIN, use ChangeFileSettings"
            )
    
    def __str__(self) -> str:
        return f"ChangeFileSettingsAuth(file=0x{self.config.file_no:02X}, mode={self.config.comm_mode})"
    
    def build_command_data(self, auth_conn: AuthenticatedConnection) -> tuple[bytes, bytes]:
        """
        Build command for auth_conn.send() - returns (header, plaintext).
        auth_conn.send() handles encryption/CMAC automatically.
        
        Returns:
            (cmd_header, unencrypted_data) for CommMode.MAC
            (cmd_header, plaintext_with_padding) for CommMode.FULL
        """
        # Use helper to build payload
        settings_payload = build_sdm_settings_payload(self.config)
        
        cmd_header = bytes([0x90, 0x5F, 0x00, 0x00])
        file_no_byte = bytes([self.config.file_no])
        
        # For FULL mode, add padding (auth_conn will encrypt+MAC)
        if self.config.comm_mode == CommMode.FULL:
            payload_with_padding = bytearray(settings_payload)
            payload_with_padding.append(0x80)
            while len(payload_with_padding) % 16 != 0:
                payload_with_padding.append(0x00)
            plaintext = file_no_byte + bytes(payload_with_padding)
        else:  # CommMode.MAC
            plaintext = file_no_byte + settings_payload
        
        return cmd_header, plaintext
    
    def parse_response(self, data: bytes, sw1: int, sw2: int) -> SuccessResponse:
        """Parse response - no data expected on success."""
        return SuccessResponse(f"File {self.config.file_no:02X} settings changed")