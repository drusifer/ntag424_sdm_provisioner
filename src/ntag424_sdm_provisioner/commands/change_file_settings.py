from typing import Optional 
from ntag424_sdm_provisioner.constants import CommMode, SuccessResponse, SDMConfiguration
from ntag424_sdm_provisioner.commands.base import ApduCommand, ApduError
from ntag424_sdm_provisioner.commands.sdm_helpers import build_sdm_settings_payload
from ntag424_sdm_provisioner.hal import NTag424CardConnection, hexb
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession

from logging import getLogger
log = getLogger(__name__)

class ChangeFileSettings(ApduCommand):
    """Change file settings including SDM configuration."""
    
    def __init__(self, config: SDMConfiguration):
        super().__init__(use_escape=False)  # Use transmit for authenticated commands
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
        # Per AN12196: CmdHeader (FileNo) is NOT encrypted, only CmdData (settings) is encrypted
        cmd_header_apdu = bytes([0x90, 0x5F, 0x00, 0x00])
        file_no_byte = bytes([self.config.file_no])
        
        # Apply encryption and CMAC for CommMode.FULL
        if self.config.comm_mode == CommMode.FULL:
            from Crypto.Hash import CMAC
            from Crypto.Cipher import AES
            
            if session is None:
                raise ValueError("Authenticated session required for FULL comm mode")
            
            # Do EVERYTHING manually like ChangeKey (to match AN12196 exactly)
            # Don't mix manual encryption with apply_cmac - it causes double-increment
            
            # Add CMAC padding: 0x80 + zeros to reach multiple of 16
            payload_with_padding = bytearray(settings_payload)
            payload_with_padding.append(0x80)
            while len(payload_with_padding) % 16 != 0:
                payload_with_padding.append(0x00)
            
            # Calculate IV: E(KSesAuthENC, zero_iv, A5 5A || TI || CmdCtr || zeros)
            ti = session.session_keys.ti
            current_cmd_ctr = session.session_keys.cmd_counter
            cmd_ctr_bytes = current_cmd_ctr.to_bytes(2, 'little')
            
            plaintext_iv = b'\xA5\x5A' + ti + cmd_ctr_bytes + b'\x00' * 8
            zero_iv = b'\x00' * 16
            cipher_iv = AES.new(session.session_keys.session_enc_key, AES.MODE_CBC, iv=zero_iv)
            actual_iv = cipher_iv.encrypt(plaintext_iv)
            
            # Encrypt settings
            cipher = AES.new(session.session_keys.session_enc_key, AES.MODE_CBC, iv=actual_iv)
            encrypted_settings = cipher.encrypt(bytes(payload_with_padding))
            
            # Manual CMAC: Cmd || CmdCtr || TI || FileNo || EncryptedSettings
            cmd = 0x5F
            cmac_input = bytes([cmd]) + cmd_ctr_bytes + ti + file_no_byte + encrypted_settings
            
            cmac_obj = CMAC.new(session.session_keys.session_mac_key, ciphermod=AES)
            cmac_obj.update(cmac_input)
            mac_full = cmac_obj.digest()
            # Even-numbered bytes truncation
            mac = bytes([mac_full[i] for i in range(1, 16, 2)])
            
            # Increment counter AFTER building command
            session.session_keys.cmd_counter = current_cmd_ctr + 1
            
            cmd_data = file_no_byte + encrypted_settings + mac
        elif self.config.comm_mode == CommMode.MAC:
            if session is None:
                raise ValueError("Authenticated session required for MAC comm mode")
            # Just CMAC, no encryption
            cmd_data = file_no_byte + settings_payload
            cmd_data = session.apply_cmac(cmd_header_apdu, cmd_data)
        else:
            # Plain mode - no protection
            cmd_data = file_no_byte + settings_payload
        
        # Build final APDU
        apdu = list(cmd_header_apdu) + [len(cmd_data)] + list(cmd_data) + [0x00]
        
        log.debug(f"ChangeFileSettings APDU: {hexb(apdu)}")
        
        # Send command
        _, sw1, sw2 = self.send_command(
            connection,
            apdu,
            allow_alternative_ok=False  # Only accept 0x9000 for file settings
        )
        
        return SuccessResponse(f"File {self.config.file_no:02X} settings changed")