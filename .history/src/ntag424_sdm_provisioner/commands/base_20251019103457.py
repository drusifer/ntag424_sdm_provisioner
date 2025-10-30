"""
Base classes and constants for APDU commands.
"""
from dataclasses import dataclass
from typing import Tuple, List, Any, Union
from abc import ABC, abstractmethod
from ntag424_sdm_provisioner.hal import NTag424CardConnection

# --- Standard ISO/IEC 7816-4 Status Word Constants ---
# Success Codes
SW_OK: Tuple[int, int] = (0x90, 0x00)          # The operation completed successfully. [cite: 188, 208, 666]
SW_OK_ALTERNATIVE: Tuple[int, int] = (0x91, 0x00) # Alternative "OK" status
SW_ADDITIONAL_FRAME: Tuple[int, int] = (0x91, 0xAF) # Used by DESFire cards to indicate more data is available. [cite: 691]

# Error Codes
SW_OPERATION_FAILED: Tuple[int, int] = (0x63, 0x00) # The operation failed. [cite: 188, 208, 666]
SW_WRONG_LENGTH: Tuple[int, int] = (0x67, 0x00)     # Wrong length specified in Lc field.
SW_FUNC_NOT_SUPPORTED: Tuple[int, int] = (0x6A, 0x81) # The card does not support the requested function. [cite: 188]
SW_FILE_NOT_FOUND: Tuple[int, int] = (0x6A, 0x82)     # File or application not found.

class ApduError(Exception):
    """Raised when an APDU command returns a non-OK status word."""
    def __init__(self, message: str, sw1: int, sw2: int):
        super().__init__(f"{message} - SW: {sw1:02X}{sw2:02X}")
        self.sw1 = sw1
        self.sw2 = sw2

def hexb(data: Union[bytes, List[int]]) -> str:
    """Pretty-prints bytes or a list of ints as a space-separated hex string."""
    return ' '.join(f'{byte:02X}' for byte in data)

@dataclass
class SuccessResponse:
    """A generic response for operations that succeed without returning data."""
    message: str = "Operation successful."

    def __str__(self) -> str:
        return f"✅ SUCCESS: {self.message}"

@dataclass
class AuthenticationChallengeResponse:
    """Holds the encrypted challenge returned by the card during authentication."""
    key_no_used: int
    challenge: bytes

    def __str__(self) -> str:
        return (
            f"✅ AUTHENTICATION CHALLENGE\n"
            f"  ► Key Number Used: 0x{self.key_no_used:02X}\n"
            f"  ► Encrypted Challenge (RndB): {hexb(self.challenge)}"
        )

@dataclass
class ReadDataResponse:
    """Holds the data read from a file on the card."""
    file_no: int
    offset: int
    data: bytes

    def __str__(self) -> str:
        return (
            f"✅ READ DATA SUCCESS\n"
            f"  ► File: 0x{self.file_no:02X}\n"
            f"  ► Offset: {self.offset}\n"
            f"  ► Length Read: {len(self.data)} bytes\n"
            f"  ► Data: {hexb(self.data)}"
        )
# file: responses.py


@dataclass
class Ntag424VersionInfo:
    """Represents the parsed version info from an NTAG424 DNA chip."""
    hw_vendor_id: int
    hw_type: int
    hw_subtype: int
    hw_major_version: int
    hw_minor_version: int
    hw_storage_size: int
    hw_protocol: int
    sw_vendor_id: int
    sw_type: int
    sw_subtype: int
    sw_major_version: int
    sw_minor_version: int
    sw_storage_size: int
    sw_protocol: int
    uid: bytes
    batch_no: bytes
    fab_week: int
    fab_year: int

    def __str__(self) -> str:
        """Returns a human-readable string representation."""
        return (
            f"✅ NTAG 424 DNA CHIP VERSION\n"
            f"  ► Hardware:\n"
            f"    - Vendor: 0x{self.hw_vendor_id:02X} (NXP)\n"
            f"    - Version: v{self.hw_major_version}.{self.hw_minor_version}\n"
            f"    - Storage: {self.hw_storage_size} bytes\n"
            f"  ► Software:\n"
            f"    - Vendor: 0x{self.sw_vendor_id:02X} (NXP)\n"
            f"    - Version: v{self.sw_major_version}.{self.sw_minor_version}\n"
            f"  ► Manufacturing:\n"
            f"    - UID: {self.uid.hex().upper()}\n"
            f"    - Batch No: {self.batch_no.hex().upper()}\n"
            f"    - Fab Date: Week {self.fab_week}, 20{self.fab_year:02d}"
        )
from dataclasses import dataclass
from typing import Optional
from enum import IntEnum

# --- Enums (not dataclasses, just type definitions) ---

class CommMode(IntEnum):
    """Communication modes for file access."""
    PLAIN = 0x00
    MAC = 0x01
    FULL = 0x03
    
    def __str__(self) -> str:
        return self.name


class FileOption(IntEnum):
    """SDM and mirroring options (bit flags)."""
    SDM_ENABLED = 0x40
    UID_MIRROR = 0x80
    SDM_READ_COUNTER_MIRROR = 0x20
    ASCII_ENCODING = 0x00


# --- Dumb Dataclasses (Data + Validation Only) ---
# file: ntag424_sdm_provisioner/commands/base.py

from dataclasses import dataclass
from typing import Optional
from ntag424_sdm_provisioner.constants import (
    FileNo, CommMode, AccessRights, SDMOption, hexb
)


@dataclass
class SDMConfiguration:
    """
    Configuration for Secure Dynamic Messaging on a file.
    Uses type-safe enums/dataclasses instead of raw bytes.
    """
    file_no: FileNo
    comm_mode: CommMode
    access_rights: AccessRights  # Now a dataclass!
    
    # SDM options
    enable_sdm: bool = False
    sdm_options: SDMOption = SDMOption.NONE  # Now IntFlag!
    
    # Mirror offsets (in bytes within NDEF message)
    picc_data_offset: Optional[int] = None
    mac_input_offset: Optional[int] = None
    enc_data_offset: Optional[int] = None
    enc_data_length: Optional[int] = None
    mac_offset: Optional[int] = None
    read_ctr_offset: Optional[int] = None
    
    def __post_init__(self):
        """Validate configuration."""
        # Convert to proper types if needed
        if not isinstance(self.file_no, FileNo):
            self.file_no = FileNo(self.file_no)
        
        if not isinstance(self.comm_mode, CommMode):
            self.comm_mode = CommMode(self.comm_mode)
        
        if not isinstance(self.access_rights, AccessRights):
            if isinstance(self.access_rights, bytes):
                self.access_rights = AccessRights.from_bytes(self.access_rights)
            else:
                raise ValueError("access_rights must be AccessRights or bytes")
        
        if not isinstance(self.sdm_options, SDMOption):
            self.sdm_options = SDMOption(self.sdm_options)
        
        # Validate SDM requirements
        if self.enable_sdm:
            required = ['picc_data_offset', 'mac_input_offset', 'mac_offset']
            for field in required:
                if getattr(self, field) is None:
                    raise ValueError(f"{field} required when SDM is enabled")
            
            if self.enc_data_offset is not None and self.enc_data_length is None:
                raise ValueError("enc_data_length required when enc_data_offset is set")
            
            # Ensure SDM is actually enabled in options
            if not (self.sdm_options & SDMOption.ENABLED):
                self.sdm_options |= SDMOption.ENABLED
    
    def __str__(self) -> str:
        sdm_status = "ENABLED" if self.enable_sdm else "DISABLED"
        result = (
            f"📋 SDM CONFIGURATION\n"
            f"  ► File: {self.file_no.name} (0x{self.file_no:02X})\n"
            f"  ► Comm Mode: {self.comm_mode.name}\n"
            f"  ► Access Rights: {self.access_rights}\n"
            f"  ► Access Bytes: {hexb(self.access_rights.to_bytes())}\n"
            f"  ► SDM: {sdm_status}"
        )
        
        if self.enable_sdm:
            # Format SDM options nicely
            opts = []
            if self.sdm_options & SDMOption.ENABLED:
                opts.append("ENABLED")
            if self.sdm_options & SDMOption.UID_MIRROR:
                opts.append("UID_MIRROR")
            if self.sdm_options & SDMOption.READ_COUNTER:
                opts.append("READ_COUNTER")
            
            result += (
                f"\n  ► SDM Options: {' | '.join(opts)} (0x{self.sdm_options:02X})\n"
                f"  ► Offsets:\n"
                f"    - PICC Data (UID): {self.picc_data_offset}\n"
                f"    - MAC Input: {self.mac_input_offset}\n"
                f"    - MAC Mirror: {self.mac_offset}"
            )
            
            if self.enc_data_offset is not None:
                result += (
                    f"\n    - Encrypted Data: {self.enc_data_offset} "
                    f"({self.enc_data_length} bytes)"
                )
            
            if self.read_ctr_offset is not None:
                result += f"\n    - Read Counter: {self.read_ctr_offset}"
        
        return result


@dataclass
class FileSettingsResponse:
    """Response from GetFileSettings command."""
    file_no: int
    file_type: int
    comm_mode: CommMode
    access_rights: bytes
    file_size: int
    sdm_enabled: bool = False
    sdm_options: Optional[int] = None
    
    def __post_init__(self):
        if len(self.access_rights) != 2:
            raise ValueError("access_rights must be 2 bytes")
    
    def __str__(self) -> str:
        return (
            f"✅ FILE SETTINGS\n"
            f"  ► File: 0x{self.file_no:02X}\n"
            f"  ► Type: 0x{self.file_type:02X}\n"
            f"  ► Comm Mode: {self.comm_mode.name}\n"
            f"  ► Access Rights: {hexb(self.access_rights)}\n"
            f"  ► Size: {self.file_size} bytes\n"
            f"  ► SDM: {'ENABLED' if self.sdm_enabled else 'DISABLED'}"
        )


@dataclass
class AuthSessionKeys:
    """Holds derived session keys after successful EV2 authentication."""
    session_enc_key: bytes  # 16 bytes
    session_mac_key: bytes  # 16 bytes
    ti: bytes               # Transaction Identifier (4 bytes)
    cmd_counter: int = 0
    
    def __post_init__(self):
        if len(self.session_enc_key) != 16:
            raise ValueError("session_enc_key must be 16 bytes")
        if len(self.session_mac_key) != 16:
            raise ValueError("session_mac_key must be 16 bytes")
        if len(self.ti) != 4:
            raise ValueError("ti must be 4 bytes")
    
    def __str__(self) -> str:
        return (
            f"🔐 SESSION KEYS\n"
            f"  ► ENC Key: {hexb(self.session_enc_key)}\n"
            f"  ► MAC Key: {hexb(self.session_mac_key)}\n"
            f"  ► TI: {hexb(self.ti)}\n"
            f"  ► Cmd Counter: {self.cmd_counter}"
        )


@dataclass
class SDMUrlTemplate:
    """SDM URL template with mirror placeholders."""
    base_url: str
    uid_placeholder: str = "00000000000000"      # 7 bytes = 14 hex chars
    cmac_placeholder: str = "0000000000000000"   # 8 bytes = 16 hex chars
    enc_placeholder: Optional[str] = None         # 16 bytes = 32 hex chars
    read_ctr_placeholder: Optional[str] = None    # 3 bytes = 6 hex chars
    
    def __post_init__(self):
        # Validate placeholder lengths
        if len(self.uid_placeholder) != 14:
            raise ValueError("uid_placeholder must be 14 hex chars (7 bytes)")
        if len(self.cmac_placeholder) != 16:
            raise ValueError("cmac_placeholder must be 16 hex chars (8 bytes)")
        if self.enc_placeholder and len(self.enc_placeholder) != 32:
            raise ValueError("enc_placeholder must be 32 hex chars (16 bytes)")
        if self.read_ctr_placeholder and len(self.read_ctr_placeholder) != 6:
            raise ValueError("read_ctr_placeholder must be 6 hex chars (3 bytes)")
    
    def __str__(self) -> str:
        params = [f"uid={self.uid_placeholder}"]
        if self.cmac_placeholder:
            params.append(f"cmac={self.cmac_placeholder}")
        if self.enc_placeholder:
            params.append(f"enc={self.enc_placeholder}")
        if self.read_ctr_placeholder:
            params.append(f"ctr={self.read_ctr_placeholder}")
        
        url = f"{self.base_url}?{'&'.join(params)}"
        
        return (
            f"🔗 SDM URL TEMPLATE\n"
            f"  ► URL: {url}\n"
            f"  ► Length: {len(url)} chars"
        )


class ApduCommand(ABC):
    """
    Abstract base class for all APDU commands.

    This class holds the APDU structure and logic but delegates the actual
    sending of the command to the connection object.
    """
    def __init__(self, use_escape: bool = False) -> None:
        """
        Args:
            use_escape: Whether to wrap the APDU in a reader-specific escape
                        command (required for some readers like the ACR122U).
        """
        self.use_escape = use_escape

    @abstractmethod
    def execute(self, connection: 'NTag424CardConnection') -> Any: 
        """
        Executes the command against a card connection. This method must be
        implemented by all subclasses.
        """
        raise NotImplementedError

    def send_apdu(self, connection: 'NTag424CardConnection', apdu: List[int]) -> Tuple[List[int], int, int]:
        """
        A proxy method that calls the send_apdu method on the connection object.

        This keeps the pyscard dependency out of the command classes.
        """
        # This now calls the method on the connection object, fulfilling your design goal.
        return connection.send_apdu(apdu, use_escape=self.use_escape)