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
    
    def __str__(self) -> str:
        return f"ChangeFileSettings(file=0x{self.config.file_no:02X})"
    
    def execute(self, connection: NTag424CardConnection) -> SuccessResponse:
        """
        Execute ChangeFileSettings for PLAIN mode (no authentication).
        
        Type-safe: Only accepts NTag424CardConnection.
        For authenticated modes, use ChangeFileSettingsAuth instead.
        
        Args:
            connection: Raw card connection
            
        Returns:
            SuccessResponse on success
        """
        if self.config.comm_mode != CommMode.PLAIN:
            raise ValueError(
                f"ChangeFileSettings only supports CommMode.PLAIN. "
                f"For {self.config.comm_mode}, use ChangeFileSettingsAuth"
            )
        
        # Use helper to build payload
        settings_payload = build_sdm_settings_payload(self.config)
        
        # Build APDU (plain mode - no encryption/CMAC)
        cmd_header_apdu = bytes([0x90, 0x5F, 0x00, 0x00])
        file_no_byte = bytes([self.config.file_no])
        cmd_data = file_no_byte + settings_payload
        
        apdu = list(cmd_header_apdu) + [len(cmd_data)] + list(cmd_data) + [0x00]
        
        log.debug(f"ChangeFileSettings (PLAIN) APDU: {hexb(apdu)}")
        
        # Send command
        _, sw1, sw2 = self.send_command(
            connection,
            apdu,
            allow_alternative_ok=False
        )
        
        return SuccessResponse(f"File {self.config.file_no:02X} settings changed")


class ChangeFileSettingsAuth(AuthApduCommand):
    """
    Change file settings - Authenticated modes (CommMode.MAC, CommMode.FULL).
    
    Type-safe: Requires AuthenticatedConnection.
    For PLAIN mode, use ChangeFileSettings instead.
    """
    
    def __init__(self, config: SDMConfiguration):
        super().__init__(use_escape=False)
        self.config = config
    
    def __str__(self) -> str:
        return f"ChangeFileSettingsAuth(file=0x{self.config.file_no:02X}, mode={self.config.comm_mode})"
    
    def execute(self, auth_conn: AuthenticatedConnection) -> SuccessResponse:
        """
        Execute ChangeFileSettings with authentication.
        
        Type-safe: Only accepts AuthenticatedConnection.
        
        Args:
            auth_conn: Authenticated connection
            
        Returns:
            SuccessResponse on success
        """
        if self.config.comm_mode == CommMode.PLAIN:
            raise ValueError(
                "ChangeFileSettingsAuth is for authenticated modes. "
                "For CommMode.PLAIN, use ChangeFileSettings"
            )
        
        # Use helper to build payload
        settings_payload = build_sdm_settings_payload(self.config)
        
        cmd_header_apdu = bytes([0x90, 0x5F, 0x00, 0x00])
        file_no_byte = bytes([self.config.file_no])
        
        # CommMode.FULL - encryption + CMAC
        if self.config.comm_mode == CommMode.FULL:
            # Add CMAC padding: 0x80 + zeros to reach multiple of 16
            payload_with_padding = bytearray(settings_payload)
            payload_with_padding.append(0x80)
            while len(payload_with_padding) % 16 != 0:
                payload_with_padding.append(0x00)
            
            # Use auth_conn methods - no manual crypto!
            encrypted_with_mac = auth_conn.encrypt_and_mac(
                plaintext=bytes(payload_with_padding),
                cmd_header=cmd_header_apdu
            )
            
            cmd_data = file_no_byte + encrypted_with_mac
            
        else:  # CommMode.MAC
            # CMAC only, no encryption
            cmd_data = file_no_byte + settings_payload
            cmd_data = auth_conn.apply_cmac(cmd_header_apdu, cmd_data)
        
        # Build final APDU
        apdu = list(cmd_header_apdu) + [len(cmd_data)] + list(cmd_data) + [0x00]
        
        log.debug(f"ChangeFileSettingsAuth ({self.config.comm_mode}) APDU: {hexb(apdu)}")
        
        # Send command via underlying connection
        _, sw1, sw2 = self.send_command(
            auth_conn.connection,
            apdu,
            allow_alternative_ok=False
        )
        
        return SuccessResponse(f"File {self.config.file_no:02X} settings changed")