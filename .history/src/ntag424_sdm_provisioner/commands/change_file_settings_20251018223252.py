from typing import Optional
from enum import IntEnum
from ntag424_sdm_provisioner.commands.base import ApduCommand, ApduError, SW_OK, SuccessResponse

class CommMode(IntEnum):
    """Communication modes for file access."""
    PLAIN = 0x00      # No encryption/MAC
    MAC = 0x01        # MACed
    FULL = 0x03       # Fully encrypted + MACed

class FileOption(IntEnum):
    """SDM and mirroring options (bit flags)."""
    SDM_ENABLED = 0x40
    UID_MIRROR = 0x80
    SDM_READ_COUNTER_MIRROR = 0x20
    ASCII_ENCODING = 0x00  # vs binary encoding

class ChangeFileSettings(ApduCommand):
    """
    Change file settings including SDM configuration.
    Must be called within an authenticated session for CMAC protection.
    
    For NTAG424 DNA SDM provisioning on File 02 (NDEF file).
    """
    
    def __init__(
        self,
        file_no: int,
        comm_mode: CommMode,
        access_rights: bytes,
        enable_sdm: bool = False,
        sdm_options: Optional[int] = None,
        picc_data_offset: Optional[int] = None,
        mac_input_offset: Optional[int] = None,
        enc_data_offset: Optional[int] = None,
        enc_data_length: Optional[int] = None,
        mac_offset: Optional[int] = None,
        read_ctr_offset: Optional[int] = None,
        use_escape: bool = False
    ):
        """
        Args:
            file_no: File number (typically 0x02 for NDEF)
            comm_mode: Communication mode (PLAIN/MAC/FULL)
            access_rights: 2 bytes access control (e.g., b'\xE0\xEE' for free read)
            enable_sdm: Enable Secure Dynamic Messaging
            sdm_options: SDM option byte (UID mirror, ASCII encoding, etc.)
            picc_data_offset: Offset for UID mirror in NDEF (in bytes)
            mac_input_offset: Start of data to MAC
            enc_data_offset: Offset for encrypted data mirror
            enc_data_length: Length of encrypted data to mirror
            mac_offset: Offset for CMAC mirror
            read_ctr_offset: Offset for read counter mirror (optional)
        """
        super().__init__(use_escape)
        
        self.file_no = file_no
        self.comm_mode = comm_mode
        self.access_rights = access_rights
        
        # Build the file settings payload
        self.settings_data = self._build_settings_data(
            enable_sdm=enable_sdm,
            sdm_options=sdm_options,
            picc_data_offset=picc_data_offset,
            mac_input_offset=mac_input_offset,
            enc_data_offset=enc_data_offset,
            enc_data_length=enc_data_length,
            mac_offset=mac_offset,
            read_ctr_offset=read_ctr_offset
        )
    
    def _build_settings_data(
        self,
        enable_sdm: bool,
        sdm_options: Optional[int],
        picc_data_offset: Optional[int],
        mac_input_offset: Optional[int],
        enc_data_offset: Optional[int],
        enc_data_length: Optional[int],
        mac_offset: Optional[int],
        read_ctr_offset: Optional[int]
    ) -> bytes:
        """Build the file settings data payload."""
        
        # Start with comm mode and access rights
        data = bytearray([self.comm_mode])
        data.extend(self.access_rights)
        
        if not enable_sdm:
            # Simple case: no SDM, just comm mode + access rights
            return bytes(data)
        
        # SDM is enabled - build the SDM options
        if sdm_options is None:
            # Default: UID mirror + ASCII encoding
            sdm_options = FileOption.SDM_ENABLED | FileOption.UID_MIRROR
        
        data.append(sdm_options)
        
        # Add offsets (3 bytes each, little-endian)
        def add_offset(value: Optional[int], name: str):
            if value is None:
                raise ValueError(f"{name} required when SDM is enabled")
            if value > 0xFFFFFF:
                raise ValueError(f"{name} must fit in 3 bytes")
            # Little-endian 3-byte encoding
            data.extend([
                value & 0xFF,
                (value >> 8) & 0xFF,
                (value >> 16) & 0xFF
            ])
        
        # PICC Data Offset (UID mirror position)
        add_offset(picc_data_offset, "picc_data_offset")
        
        # SDMMACInputOffset (where MAC calculation starts)
        add_offset(mac_input_offset, "mac_input_offset")
        
        # EncOffset (encrypted data mirror position)
        if enc_data_offset is not None:
            add_offset(enc_data_offset, "enc_data_offset")
            
            # EncLength (how many bytes of encrypted data)
            if enc_data_length is None:
                raise ValueError("enc_data_length required when enc_data_offset set")
            if enc_data_length > 0xFFFFFF:
                raise ValueError("enc_data_length must fit in 3 bytes")
            data.extend([
                enc_data_length & 0xFF,
                (enc_data_length >> 8) & 0xFF,
                (enc_data_length >> 16) & 0xFF
            ])
        
        # MACOffset (CMAC mirror position)
        add_offset(mac_offset, "mac_offset")
        
        # Read Counter Offset (optional)
        if read_ctr_offset is not None:
            add_offset(read_ctr_offset, "read_ctr_offset")
        
        return bytes(data)
    
    def __str__(self) -> str:
        return (f"ChangeFileSettings(file={self.file_no:02X}, "
                f"comm_mode={self.comm_mode.name}, "
                f"data_len={len(self.settings_data)})")
    
    def execute(
        self, 
        connection: 'NTag424CardConnection',
        session: Optional['Ntag424AuthSession'] = None
    ) -> SuccessResponse:
        """
        Execute ChangeFileSettings.
        
        Args:
            connection: Card connection
            session: Authenticated session (required for CMAC calculation)
        
        Returns:
            SuccessResponse on success
        
        Raises:
            ApduError if command fails
            ValueError if session not provided when comm_mode requires it
        """
        
        # Build base APDU
        cmd_header = [0x90, 0x5F, 0x00, 0x00]
        cmd_data = [self.file_no] + list(self.settings_data)
        
        # Check if we need CMAC
        if self.comm_mode in [CommMode.MAC, CommMode.FULL]:
            if session is None:
                raise ValueError("Authenticated session required for MAC/FULL comm mode")
            
            # Calculate CMAC over command
            cmd_data_with_cmac = session.apply_cmac(
                cmd_header=bytes(cmd_header),
                cmd_data=bytes(cmd_data)
            )
            cmd_data = list(cmd_data_with_cmac)
        
        # Build final APDU
        apdu = cmd_header + [len(cmd_data)] + cmd_data + [0x00]
        
        log.debug(f"ChangeFileSettings APDU: {hexb(apdu)}")
        
        # Send command
        data, sw1, sw2 = self.send_apdu(connection, apdu)
        
        if (sw1, sw2) != SW_OK:
            raise ApduError(
                f"ChangeFileSettings failed for file {self.file_no:02X}",
                sw1, sw2
            )
        
        return SuccessResponse(f"File {self.file_no:02X} settings changed successfully")