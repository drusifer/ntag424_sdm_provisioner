from ntag424_sdm_provisioner.commands.base import AuthApduCommand, AuthenticatedConnection
from ntag424_sdm_provisioner.constants import SuccessResponse

class ChangeKey(AuthApduCommand):
    """
    Changes a key on the card. Must be in an authenticated state.
    
    Per NXP spec: CommMode.Full is required (encryption + CMAC).
    
    Key format differs for Key 0 vs other keys:
    - Key 0: newKey + version + padding
    - Others: (newKey XOR oldKey) + version + CRC32 + padding
    
    Type-safe: execute() requires AuthenticatedConnection.
    """
    def __init__(self, key_no_to_change: int, new_key: bytes, old_key: bytes, key_version: int = 0x00):
        super().__init__(use_escape=True)  # Use Control mode (escape) for ACR122U
        self.key_no = key_no_to_change
        self.new_key = new_key
        self.old_key = old_key
        self.key_version = key_version
        
    def __str__(self) -> str:
        return f"ChangeKey(key_no=0x{self.key_no:02X})"
    
    def get_command_byte(self) -> int:
        """Get ChangeKey command byte."""
        return 0xC4
    
    def get_unencrypted_header(self) -> bytes:
        """Get KeyNo (not encrypted, but included in CMAC)."""
        return bytes([self.key_no])
    
    def build_command_data(self) -> bytes:
        """
        Build plaintext command data for ChangeKey.
        
        Returns 32-byte key data (pre-padded with 0x80).
        
        Returns:
            32 bytes: KeyData (block-aligned for no-padding encryption)
        """
        return self._build_key_data()
    
    def parse_response(self, data: bytes) -> SuccessResponse:
        """
        Parse ChangeKey response.
        
        Args:
            data: Decrypted response data (should be empty for success)
            
        Returns:
            SuccessResponse
        """
        return SuccessResponse(f"Key 0x{self.key_no:02X} changed successfully.")
    
    def _build_key_data(self) -> bytes:
        """
        Build 32-byte key data for encryption.
        
        Format per Arduino MFRC522 library and NXP spec:
        - Key 0: newKey(16) + version(1) + 0x80 + padding(14) = 32 bytes
        - Others: XOR(16) + version(1) + CRC32(4) + 0x80 + padding(10) = 32 bytes
        """
        import zlib
        
        key_data = bytearray(32)
        
        if self.key_no == 0:
            # Key 0 format: NewKey(16) + KeyVer(1) = 17 bytes
            key_data[0:16] = self.new_key
            key_data[16] = self.key_version
            key_data[17] = 0x80  # Padding start
            # Rest is already zeros (14 bytes of zeros)
        else:
            # Other keys format: XOR(16) + KeyVer(1) + CRC32(4) = 21 bytes
            if self.old_key is None:
                self.old_key = bytes(16)
            xored = bytes(a ^ b for a, b in zip(self.new_key, self.old_key))
            
            # CRC32 of new key, inverted per Arduino
            crc = zlib.crc32(self.new_key) & 0xFFFFFFFF
            crc_inverted = crc ^ 0xFFFFFFFF  # Invert all bits
            
            key_data[0:16] = xored
            key_data[16] = self.key_version
            key_data[17:21] = crc_inverted.to_bytes(4, byteorder='little')
            key_data[21] = 0x80  # Padding start
            # Rest is already zeros (10 bytes of zeros)
        
        return bytes(key_data)

    def execute(self, auth_conn: AuthenticatedConnection) -> SuccessResponse:
        """
        Execute ChangeKey command (OLD PATTERN - DEPRECATED).
        
        DEPRECATED: Use auth_conn.send(command) instead:
            auth_conn.send(ChangeKey(0, new_key, old_key))
        
        This method is kept for backwards compatibility but will be removed.
        
        Args:
            auth_conn: Authenticated connection
            
        Returns:
            SuccessResponse on success
        """
        # Use new pattern internally
        return auth_conn.send(self)