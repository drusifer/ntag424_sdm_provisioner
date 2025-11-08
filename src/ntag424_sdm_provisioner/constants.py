# file: ntag424_sdm_provisioner/constants.py

from dataclasses import dataclass
from enum import Enum, IntEnum, IntFlag
from typing import Final, Tuple, Optional

# ============================================================================
# Status Words (SW1 SW2)
# ============================================================================

class StatusWord(IntEnum):
    """
    ISO 7816-4 Status Words.
    Stored as 16-bit value: (SW1 << 8) | SW2
    """
    # Success
    OK = 0x9000                          # Operation successful
    OK_ALTERNATIVE = 0x9100              # Alternative success (some cards)
    
    # More data available (chaining)
    MORE_DATA_AVAILABLE = 0x91AF         # Additional frame available (DESFire)
    
    # Warnings
    NO_INFORMATION = 0x6300              # No information given
    FILE_FILLED = 0x6381                 # File filled up by last write
    
    # Execution errors
    AUTHENTICATION_ERROR = 0x6300        # Authentication failed
    WRONG_LENGTH = 0x6700                # Wrong length (Lc or Le)
    SECURITY_STATUS_NOT_SATISFIED = 0x6982  # Security condition not satisfied
    FILE_NOT_FOUND = 0x6A82              # File or application not found
    WRONG_PARAMETERS = 0x6A86            # Incorrect P1 P2
    WRONG_LE_FIELD = 0x6C00              # Wrong Le field
    INS_NOT_SUPPORTED = 0x6D00           # Instruction not supported
    CLA_NOT_SUPPORTED = 0x6E00           # Class not supported
    COMMAND_NOT_ALLOWED = 0x6986         # Command not allowed
    
    # DESFire specific
    PERMISSION_DENIED = 0x9D00           # Permission denied
    PARAMETER_ERROR = 0x9E00             # Parameter error
    APPLICATION_NOT_FOUND = 0x9DA0       # Application not found
    INTEGRITY_ERROR = 0x9E1E             # Integrity error
    NO_SUCH_KEY = 0x9E40                 # Key does not exist
    DUPLICATE_ERROR = 0x9EDE             # Duplicate entry
    
    # NTAG424 DNA specific (per NXP specification)
    NTAG_INTEGRITY_ERROR = 0x911E       # CRC or MAC does not match data
    NTAG_ILLEGAL_COMMAND_CODE = 0x911C  # Command code not supported
    NTAG_LENGTH_ERROR = 0x917E           # Length of command string invalid
    NTAG_NO_SUCH_KEY = 0x9140            # Invalid key number specified
    NTAG_PERMISSION_DENIED = 0x919D      # Current configuration/status does not allow command
    NTAG_PARAMETER_ERROR = 0x919E        # Value of parameter(s) invalid
    NTAG_AUTHENTICATION_DELAY = 0x91AD   # Currently not allowed to authenticate (delay not spent)
    NTAG_AUTHENTICATION_ERROR = 0x91AE   # Current authentication status does not allow command
    NTAG_BOUNDARY_ERROR = 0x91BE         # Attempt to read/write beyond file limits
    NTAG_COMMAND_ABORTED = 0x91CA        # Previous command was not fully completed (frames missing)
    NTAG_FILE_NOT_FOUND = 0x91F0         # Specified file number does not exist
    
    @classmethod
    def from_bytes(cls, sw1: int, sw2: int) -> 'StatusWord':
        """Create StatusWord from SW1 and SW2 bytes."""
        value = (sw1 << 8) | sw2
        try:
            return cls(value)
        except ValueError:
            # Return unknown status word as raw value
            return value
    
    def to_tuple(self) -> Tuple[int, int]:
        """Convert to (SW1, SW2) tuple."""
        return (self.value >> 8) & 0xFF, self.value & 0xFF
    
    def is_success(self) -> bool:
        """Check if status indicates success."""
        return self in [StatusWord.OK, StatusWord.OK_ALTERNATIVE]
    
    def is_error(self) -> bool:
        """Check if status indicates an error."""
        return not self.is_success() and self != StatusWord.MORE_DATA_AVAILABLE
    
    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:04X})"


class StatusWordPair(Enum):
    """
    Status word pairs as Enum for better code readability and debugging.
    Each value is a (SW1, SW2) tuple that can be compared directly with tuples.
    """
    # Success codes
    SW_OK = (0x90, 0x00)
    SW_OK_ALTERNATIVE = (0x91, 0x00)
    
    # Chaining/continuation
    SW_ADDITIONAL_FRAME = (0x91, 0xAF)
    
    # Common errors
    SW_AUTH_FAILED = (0x91, 0x7E)
    SW_OPERATION_FAILED = (0x63, 0x00)
    SW_WRONG_LENGTH = (0x67, 0x00)
    SW_FUNC_NOT_SUPPORTED = (0x6A, 0x81)
    SW_FILE_NOT_FOUND = (0x6A, 0x82)
    
    def __eq__(self, other):
        """Allow comparison with tuples: if (sw1, sw2) == StatusWordPair.SW_OK"""
        if isinstance(other, tuple) and len(other) == 2:
            return self.value == other
        return super().__eq__(other)
    
    def __hash__(self):
        """Make hashable for use in sets/dicts"""
        return hash(self.value)
    
    def to_status_word(self) -> StatusWord:
        """Convert to StatusWord enum"""
        sw1, sw2 = self.value
        return StatusWord.from_bytes(sw1, sw2)
    
    def __str__(self) -> str:
        sw1, sw2 = self.value
        return f"{self.name} (0x{sw1:02X}{sw2:02X})"
    
    def __repr__(self) -> str:
        return f"StatusWordPair.{self.name}"


# Export enum members as module-level constants for backward compatibility
SW_OK = StatusWordPair.SW_OK
SW_OK_ALTERNATIVE = StatusWordPair.SW_OK_ALTERNATIVE
SW_ADDITIONAL_FRAME = StatusWordPair.SW_ADDITIONAL_FRAME
SW_AUTH_FAILED = StatusWordPair.SW_AUTH_FAILED
SW_OPERATION_FAILED = StatusWordPair.SW_OPERATION_FAILED
SW_WRONG_LENGTH = StatusWordPair.SW_WRONG_LENGTH
SW_FUNC_NOT_SUPPORTED = StatusWordPair.SW_FUNC_NOT_SUPPORTED
SW_FILE_NOT_FOUND = StatusWordPair.SW_FILE_NOT_FOUND


# ============================================================================
# APDU Command Codes
# ============================================================================

class APDUClass(IntEnum):
    """APDU Class bytes."""
    ISO7816 = 0x00           # Standard ISO 7816-4
    PROPRIETARY = 0x80       # Proprietary class
    DESFIRE = 0x90           # DESFire native
    PSEUDO = 0xFF            # PC/SC pseudo-APDU (reader control)
    
    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:02X})"


class APDUInstruction(IntEnum):
    """APDU Instruction bytes (INS)."""
    # ISO 7816-4 standard
    SELECT_FILE = 0xA4
    GET_DATA = 0xCA
    READ_BINARY = 0xB0
    UPDATE_BINARY = 0xD6
    GET_CHALLENGE = 0x84
    
    # DESFire/NTAG424 specific
    AUTHENTICATE_EV2_FIRST = 0x71
    AUTHENTICATE_EV2_SECOND = 0xAF   # Also "Additional Frame"
    GET_VERSION = 0x60
    CHANGE_KEY = 0xC4
    GET_KEY_VERSION = 0x64
    CREATE_APPLICATION = 0xCA
    DELETE_APPLICATION = 0xDA
    GET_APPLICATION_IDS = 0x6A
    SELECT_APPLICATION = 0x5A
    FORMAT_PICC = 0xFC
    GET_FILE_IDS = 0x6F
    GET_FILE_SETTINGS = 0xF5
    CHANGE_FILE_SETTINGS = 0x5F
    GET_FILE_COUNTERS = 0xC1
    CREATE_STD_DATA_FILE = 0xCD
    CREATE_BACKUP_DATA_FILE = 0xCB
    DELETE_FILE = 0xDF
    READ_DATA = 0xBD
    WRITE_DATA = 0x3D
    GET_VALUE = 0x6C
    CREDIT = 0x0C
    DEBIT = 0xDC
    LIMITED_CREDIT = 0x1C
    
    # PC/SC Pseudo-APDUs
    DIRECT_TRANSMIT = 0x00
    LED_BUZZER_CONTROL = 0x00
    GET_FIRMWARE_VERSION = 0x00
    GET_PICC_OPERATING_PARAMETER = 0x00
    SET_PICC_OPERATING_PARAMETER = 0x00
    
    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:02X})"


# ============================================================================
# File Numbers
# ============================================================================

class FileNo(IntEnum):
    """Standard file numbers on NTAG424 DNA."""
    CC_FILE = 0x01          # Capability Container (read-only)
    NDEF_FILE = 0x02        # NDEF data file (main file for NFC)
    PROPRIETARY_FILE = 0x03 # Proprietary data file (optional)
    
    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:02X})"


# ============================================================================
# Key Numbers
# ============================================================================

class KeyNo(IntEnum):
    """Key numbers for authentication."""
    KEY_0 = 0x00  # Master application key
    KEY_1 = 0x01  # Key 1
    KEY_2 = 0x02  # Key 2
    KEY_3 = 0x03  # Key 3
    KEY_4 = 0x04  # Key 4
    
    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:02X})"


# Factory default
FACTORY_KEY: Final[bytes] = b'\x00' * 16


# ============================================================================
# Communication Modes
# ============================================================================

class CommMode(IntEnum):
    """Communication modes for file access."""
    PLAIN = 0x00      # No encryption/MAC
    MAC = 0x01        # MACed
    FULL = 0x03       # Fully encrypted + MACed
    
    # Mask for extracting CommMode from FileOption byte (bits [1:0])
    COMM_MODE_MASK = 0x03
    
    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:02X})"
    
    def requires_auth(self) -> bool:
        """Check if this mode requires authentication."""
        return self in [CommMode.MAC, CommMode.FULL]
    
    @classmethod
    def from_file_option(cls, file_option: int) -> 'CommMode':
        """
        Extract CommMode from FileOption byte.
        
        FileOption byte structure:
        - Bit 6: SDM enabled
        - Bits 1-0: CommMode
        
        Args:
            file_option: FileOption byte value
        
        Returns:
            CommMode enum value
        """
        return cls(file_option & cls.COMM_MODE_MASK)


# ============================================================================
# File Types
# ============================================================================

class FileType(IntEnum):
    """File types on NTAG424 DNA."""
    STANDARD_DATA = 0x00
    BACKUP_DATA = 0x01
    VALUE_FILE = 0x02
    LINEAR_RECORD = 0x03
    CYCLIC_RECORD = 0x04
    
    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:02X})"


# ============================================================================
# Access Rights
# ============================================================================

class AccessRight(IntEnum):
    """Individual access right values (nibble values 0-F)."""
    KEY_0 = 0x0
    KEY_1 = 0x1
    KEY_2 = 0x2
    KEY_3 = 0x3
    KEY_4 = 0x4
    # Reserved: 0x5-0xD
    FREE = 0xE    # Free access without authentication
    NEVER = 0xF   # Access denied
    
    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:01X})"


@dataclass
class AccessRights:
    """
    NTAG424 DNA access rights (2 bytes / 4 nibbles).
    
    Byte layout:
        Byte 1 [7:4]: Read access
        Byte 1 [3:0]: Write access
        Byte 0 [7:4]: ReadWrite access
        Byte 0 [3:0]: Change access (ChangeFileSettings)
    """
    read: AccessRight = AccessRight.FREE
    write: AccessRight = AccessRight.KEY_0
    read_write: AccessRight = AccessRight.FREE
    change: AccessRight = AccessRight.KEY_0
    
    def __post_init__(self):
        """Convert int values to AccessRight enums if needed."""
        for field in ['read', 'write', 'read_write', 'change']:
            val = getattr(self, field)
            if not isinstance(val, AccessRight):
                setattr(self, field, AccessRight(val))
    
    def to_bytes(self) -> bytes:
        """Convert to NTAG424 2-byte format."""
        byte1 = (self.read << 4) | self.write
        byte0 = (self.read_write << 4) | self.change
        return bytes([byte1, byte0])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'AccessRights':
        """Parse from 2-byte format."""
        if len(data) != 2:
            raise ValueError("Access rights must be 2 bytes")
        
        byte1, byte0 = data
        
        return cls(
            read=AccessRight((byte1 >> 4) & 0xF),
            write=AccessRight(byte1 & 0xF),
            read_write=AccessRight((byte0 >> 4) & 0xF),
            change=AccessRight(byte0 & 0xF)
        )
    
    def __str__(self) -> str:
        return (
            f"Read={self.read.name}, "
            f"Write={self.write.name}, "
            f"RW={self.read_write.name}, "
            f"Change={self.change.name}"
        )


# ============================================================================
# Access Rights Presets
# ============================================================================

class AccessRightsPresets:
    """Common access rights configurations."""
    
    FREE_READ_KEY0_WRITE = AccessRights(
        read=AccessRight.FREE,
        write=AccessRight.KEY_0,
        read_write=AccessRight.FREE,
        change=AccessRight.FREE
    )
    
    KEY0_ALL = AccessRights(
        read=AccessRight.KEY_0,
        write=AccessRight.KEY_0,
        read_write=AccessRight.KEY_0,
        change=AccessRight.KEY_0
    )
    
    FREE_ALL = AccessRights(
        read=AccessRight.FREE,
        write=AccessRight.FREE,
        read_write=AccessRight.FREE,
        change=AccessRight.FREE
    )
    
    READ_ONLY_FREE = AccessRights(
        read=AccessRight.FREE,
        write=AccessRight.NEVER,
        read_write=AccessRight.NEVER,
        change=AccessRight.NEVER
    )


# ============================================================================
# SDM Options
# ============================================================================

class SDMOption(IntFlag):
    """
    SDM configuration options (bit flags).
    Can be combined using bitwise OR: SDMOption.ENABLED | SDMOption.UID_MIRROR
    """
    NONE = 0x00
    ENCODING_ASCII = 0x01    # Bit 0: ASCII encoding
    ENC_FILE_DATA = 0x10     # Bit 4: Encrypt file data  
    READ_COUNTER_LIMIT = 0x20  # Bit 5: Enable counter limit
    READ_COUNTER = 0x40      # Bit 6: Mirror read counter (FIXED!)
    UID_MIRROR = 0x80        # Bit 7: Mirror UID in NDEF
    
    # Common combinations (Note: ENABLED goes in FileOption, not SDMOption!)
    BASIC_SDM = UID_MIRROR
    SDM_WITH_COUNTER = UID_MIRROR | READ_COUNTER


# ============================================================================
# NDEF Constants
# ============================================================================

class NdefUriPrefix(IntEnum):
    """NDEF URI identifier codes."""
    NONE = 0x00
    HTTP_WWW = 0x01        # http://www.
    HTTPS_WWW = 0x02       # https://www.
    HTTP = 0x03            # http://
    HTTPS = 0x04           # https://
    TEL = 0x05             # tel:
    MAILTO = 0x06          # mailto:
    FTP_ANON = 0x0D        # ftp://anonymous:anonymous@
    FTP = 0x0E             # ftp://
    FTPS = 0x0F            # ftps://
    SFTP = 0x10            # sftp://
    
    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:02X})"


class NdefRecordType(IntEnum):
    """NDEF Record Type Name Format (TNF)."""
    EMPTY = 0x00
    WELL_KNOWN = 0x01      # NFC Forum well-known type
    MIME_MEDIA = 0x02
    ABSOLUTE_URI = 0x03
    EXTERNAL = 0x04
    UNKNOWN = 0x05
    UNCHANGED = 0x06
    RESERVED = 0x07
    
    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:02X})"


class NdefTLV(IntEnum):
    """NDEF TLV types for Type 4 Tags."""
    NULL = 0x00
    LOCK_CONTROL = 0x01
    MEMORY_CONTROL = 0x02
    NDEF_MESSAGE = 0x03
    PROPRIETARY = 0xFD
    TERMINATOR = 0xFE
    
    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:02X})"


# ============================================================================
# Memory Sizes
# ============================================================================

class MemorySize:
    """Standard memory sizes for NTAG424 DNA variants."""
    NTAG424_DNA = 416      # 416 bytes user memory
    NTAG424_DNA_TT = 416   # TamperTag variant


# ============================================================================
# Application IDs
# ============================================================================

class ApplicationID:
    """Application IDs for NTAG424 DNA."""
    PICC_APP: Final[bytes] = b'\x00\x00\x00'  # Main PICC application


# ============================================================================
# Error Categories
# ============================================================================

class ErrorCategory(IntEnum):
    """Categories of errors for better error handling."""
    COMMUNICATION = 1      # Reader/card communication error
    AUTHENTICATION = 2     # Authentication failed
    PERMISSION = 3         # Permission denied
    PARAMETER = 4          # Invalid parameter
    STATE = 5              # Invalid state for operation
    INTEGRITY = 6          # Data integrity error
    NOT_FOUND = 7          # File/app not found
    HARDWARE = 8           # Hardware error
    
    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:02X})"


# Map status words to error categories
STATUS_WORD_CATEGORIES = {
    StatusWord.AUTHENTICATION_ERROR: ErrorCategory.AUTHENTICATION,
    StatusWord.PERMISSION_DENIED: ErrorCategory.PERMISSION,
    StatusWord.SECURITY_STATUS_NOT_SATISFIED: ErrorCategory.AUTHENTICATION,
    StatusWord.FILE_NOT_FOUND: ErrorCategory.NOT_FOUND,
    StatusWord.APPLICATION_NOT_FOUND: ErrorCategory.NOT_FOUND,
    StatusWord.WRONG_PARAMETERS: ErrorCategory.PARAMETER,
    StatusWord.PARAMETER_ERROR: ErrorCategory.PARAMETER,
    StatusWord.WRONG_LENGTH: ErrorCategory.PARAMETER,
    StatusWord.COMMAND_NOT_ALLOWED: ErrorCategory.STATE,
    StatusWord.INTEGRITY_ERROR: ErrorCategory.INTEGRITY,
    StatusWord.NO_SUCH_KEY: ErrorCategory.NOT_FOUND,
    
    # NTAG424 DNA specific mappings
    StatusWord.NTAG_INTEGRITY_ERROR: ErrorCategory.INTEGRITY,
    StatusWord.NTAG_ILLEGAL_COMMAND_CODE: ErrorCategory.COMMUNICATION,
    StatusWord.NTAG_LENGTH_ERROR: ErrorCategory.PARAMETER,
    StatusWord.NTAG_NO_SUCH_KEY: ErrorCategory.NOT_FOUND,
    StatusWord.NTAG_PERMISSION_DENIED: ErrorCategory.PERMISSION,
    StatusWord.NTAG_PARAMETER_ERROR: ErrorCategory.PARAMETER,
    StatusWord.NTAG_AUTHENTICATION_DELAY: ErrorCategory.STATE,
    StatusWord.NTAG_AUTHENTICATION_ERROR: ErrorCategory.AUTHENTICATION,
    StatusWord.NTAG_BOUNDARY_ERROR: ErrorCategory.PARAMETER,
    StatusWord.NTAG_COMMAND_ABORTED: ErrorCategory.STATE,
    StatusWord.NTAG_FILE_NOT_FOUND: ErrorCategory.NOT_FOUND,
}


def get_error_category(sw: StatusWord) -> ErrorCategory:
    """Get error category for a status word."""
    return STATUS_WORD_CATEGORIES.get(sw, ErrorCategory.COMMUNICATION)


# ============================================================================
# Response Dataclasses
# ============================================================================

@dataclass
class SuccessResponse:
    """Response for successful operations."""
    message: str
    
    def __str__(self) -> str:
        return f"SuccessResponse(message='{self.message}')"


@dataclass
class AuthenticationChallengeResponse:
    """Response from EV2 authentication first phase."""
    key_no_used: int
    challenge: bytes
    
    def __str__(self) -> str:
        return f"AuthenticationChallengeResponse(key_no={self.key_no_used}, challenge={self.challenge.hex().upper()})"


@dataclass
class AuthenticationResponse:
    """Response from EV2 authentication second phase."""
    ti: bytes  # Transaction Identifier (4 bytes)
    rnda_rotated: bytes  # RndA rotated by tag (16 bytes)
    pdcap: bytes  # PICC Data Capabilities (variable length)
    pcdcap: bytes  # PCD Capabilities (variable length)
    
    def __str__(self) -> str:
        return f"AuthenticationResponse(ti={self.ti.hex().upper()}, rnda_rotated={self.rnda_rotated.hex().upper()[:8]}..., pdcap_len={len(self.pdcap)}, pcdcap_len={len(self.pcdcap)})"


@dataclass
class Ntag424VersionInfo:
    """Version information from NTAG424 DNA chip."""
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
        return (
            f"Ntag424VersionInfo(\n"
            f"  UID: {self.uid.hex().upper()},\n"
            f"  Hardware: {self.hw_major_version}.{self.hw_minor_version} ({self.hw_storage_size}B),\n"
            f"  Software: {self.sw_major_version}.{self.sw_minor_version} ({self.sw_storage_size}B),\n"
            f"  Batch: {self.batch_no.hex().upper()},\n"
            f"  Fab: Week {self.fab_week}, Year {self.fab_year}\n"
            f"  {'=' * 60}\n"
            f"\n"
            f"CHIP INFORMATION:\n"
            f"  UID: {self.uid.hex().upper()}\n"
            f"  Hardware Protocol: {self.hw_protocol}\n"
            f"  Software Protocol: {self.sw_protocol}\n"
            f"  Hardware Type: {self.hw_type}\n"
            f"  Software Type: {self.sw_type}\n"
            f"\n"
            f")"
        )


@dataclass
class ReadDataResponse:
    """Response from file read operations."""
    file_no: int
    offset: int
    data: bytes
    
    def __str__(self) -> str:
        return f"ReadDataResponse(file_no={self.file_no}, offset={self.offset}, data_len={len(self.data)}, data={self.data.hex().upper()[:32]}{'...' if len(self.data) > 16 else ''})"


@dataclass
class FileSettingsResponse:
    """Response from GetFileSettings command."""
    file_no: int
    file_type: int
    file_option: int
    access_rights: bytes
    file_size: int
    sdm_options: Optional[int] = None
    sdm_access_rights: Optional[bytes] = None
    uid_offset: Optional[int] = None
    read_ctr_offset: Optional[int] = None
    picc_data_offset: Optional[int] = None
    mac_input_offset: Optional[int] = None
    enc_offset: Optional[int] = None
    enc_length: Optional[int] = None
    mac_offset: Optional[int] = None
    read_ctr_limit: Optional[int] = None
    
    def get_comm_mode(self) -> 'CommMode':
        """
        Get the communication mode for this file.
        
        Extracts CommMode from file_option bits [1:0].
        
        Returns:
            CommMode enum value (PLAIN, MAC, or FULL)
        """
        return CommMode.from_file_option(self.file_option)
    
    def requires_authentication(self) -> bool:
        """
        Check if this file requires authentication for access.
        
        Returns:
            True if CommMode is MAC or FULL
        """
        return self.get_comm_mode().requires_auth()
    
    def __str__(self) -> str:
        lines = [
            f"File 0x{self.file_no:02X} Settings:",
            f"  File Type: 0x{self.file_type:02X}",
            f"  File Option: 0x{self.file_option:02X}",
            f"  Access Rights: {self.access_rights.hex().upper()}",
            f"  File Size: {self.file_size} bytes",
        ]
        
        if self.sdm_options is not None:
            lines.append(f"  SDM Options: 0x{self.sdm_options:02X}")
            if self.sdm_access_rights:
                lines.append(f"  SDM Access Rights: {self.sdm_access_rights.hex().upper()}")
            if self.uid_offset is not None:
                lines.append(f"  UID Offset: {self.uid_offset}")
            if self.read_ctr_offset is not None:
                lines.append(f"  Read Counter Offset: {self.read_ctr_offset}")
            if self.picc_data_offset is not None:
                lines.append(f"  PICC Data Offset: {self.picc_data_offset}")
            if self.mac_input_offset is not None:
                lines.append(f"  MAC Input Offset: {self.mac_input_offset}")
            if self.enc_offset is not None:
                lines.append(f"  Encryption Offset: {self.enc_offset}")
                if self.enc_length is not None:
                    lines.append(f"  Encryption Length: {self.enc_length}")
            if self.mac_offset is not None:
                lines.append(f"  MAC Offset: {self.mac_offset}")
            if self.read_ctr_limit is not None:
                lines.append(f"  Read Counter Limit: {self.read_ctr_limit}")
        
        return "\n".join(lines)


@dataclass
class KeyVersionResponse:
    """Response from GetKeyVersion command."""
    key_no: int
    version: int
    
    def __str__(self) -> str:
        return f"Key 0x{self.key_no:02X} Version: 0x{self.version:02X}"


# ============================================================================
# Configuration Dataclasses
# ============================================================================

@dataclass
class SDMOffsets:
    """SDM offset configuration with sane defaults."""
    uid_offset: int = 0
    read_ctr_offset: int = 0
    picc_data_offset: int = 0
    mac_input_offset: int = 0
    mac_offset: int = 0
    enc_offset: int = 0
    
    def __str__(self) -> str:
        parts = []
        if self.uid_offset:
            parts.append(f"UID@{self.uid_offset}")
        if self.read_ctr_offset:
            parts.append(f"CTR@{self.read_ctr_offset}")
        if self.mac_offset:
            parts.append(f"MAC@{self.mac_offset}")
        return ", ".join(parts) if parts else "No offsets"


@dataclass
class SDMConfiguration:
    """Configuration for Secure Dynamic Messaging."""
    file_no: int
    comm_mode: 'CommMode'
    access_rights: 'AccessRights'  # Type changed from bytes to AccessRights
    enable_sdm: bool
    sdm_options: int
    offsets: SDMOffsets = None  # Dataclass instead of individual fields
    
    def __post_init__(self):
        """Validate and normalize configuration."""
        # Convert bytes to AccessRights if needed (backward compatibility)
        if isinstance(self.access_rights, bytes):
            self.access_rights = AccessRights.from_bytes(self.access_rights)
        
        # Ensure offsets is SDMOffsets
        if self.offsets is None:
            self.offsets = SDMOffsets()
        elif isinstance(self.offsets, dict):
            # Backward compatibility: convert dict to SDMOffsets
            self.offsets = SDMOffsets(
                uid_offset=self.offsets.get('uid_offset', 0),
                read_ctr_offset=self.offsets.get('read_ctr_offset', 0),
                picc_data_offset=self.offsets.get('picc_data_offset', 0),
                mac_input_offset=self.offsets.get('mac_input_offset', 0),
                mac_offset=self.offsets.get('mac_offset', 0),
                enc_offset=self.offsets.get('enc_offset', 0),
            )
    
    def get_access_rights_bytes(self) -> bytes:
        """Get access rights as bytes (internal encoding)."""
        return self.access_rights.to_bytes()


@dataclass
class SDMUrlTemplate:
    """Template for SDM URL with placeholders."""
    base_url: str
    uid_placeholder: str = "00000000000000"
    cmac_placeholder: str = "0" * 16
    enc_placeholder: Optional[str] = None
    read_ctr_placeholder: Optional[str] = None


# ============================================================================
# Authentication Session Keys
# ============================================================================

@dataclass
class AuthSessionKeys:
    """Session keys derived from EV2 authentication."""
    session_enc_key: bytes
    session_mac_key: bytes
    ti: bytes
    cmd_counter: int = 0


# ============================================================================
# File Options
# ============================================================================

class FileOption(IntFlag):
    """
    File option flags for SDM configuration.
    
    Note: These combine FileOption byte (bits 1-0 = CommMode, bit 6 = SDM enable)
    with SDMOptions byte (bits for UID/counter mirroring).
    
    FileOption byte:
    - Bit 6: SDM enabled (0x40)
    - Bits 1-0: CommMode
    
    SDMOptions byte:
    - Bit 7: UID mirror (0x80)
    - Bit 6: Read counter (0x40)
    - Bit 5: Counter limit (0x20)
    - Bit 4: Encrypt file data (0x10)
    """
    SDM_ENABLED = 0x40       # FileOption bit 6
    UID_MIRROR = 0x80        # SDMOptions bit 7
    READ_COUNTER = 0x40      # SDMOptions bit 6 (FIXED from 0x20!)
    READ_COUNTER_LIMIT = 0x20  # SDMOptions bit 5
    ENC_FILE_DATA = 0x10     # SDMOptions bit 4


# ============================================================================
# Helper Functions
# ============================================================================


def describe_status_word(sw1: int, sw2: int) -> str:
    """Get human-readable description of status word."""
    sw = StatusWord.from_bytes(sw1, sw2)
    
    descriptions = {
        StatusWord.OK: "Operation successful",
        StatusWord.MORE_DATA_AVAILABLE: "More data available (send AF)",
        StatusWord.AUTHENTICATION_ERROR: "Authentication failed",
        StatusWord.PERMISSION_DENIED: "Permission denied",
        StatusWord.FILE_NOT_FOUND: "File or application not found",
        StatusWord.WRONG_LENGTH: "Wrong length in command",
        StatusWord.WRONG_PARAMETERS: "Incorrect parameters (P1/P2)",
        StatusWord.COMMAND_NOT_ALLOWED: "Command not allowed in current state",
        StatusWord.INTEGRITY_ERROR: "Data integrity check failed",
        StatusWord.NO_SUCH_KEY: "Specified key does not exist",
    }
    
    if isinstance(sw, StatusWord):
        desc = descriptions.get(sw, sw.name.replace('_', ' ').title())
        return f"{sw.name} (0x{sw1:02X}{sw2:02X}): {desc}"
    else:
        return f"Unknown status (0x{sw1:02X}{sw2:02X})"


GAME_COIN_BASE_URL = "https://script.google.com/a/macros/gutsteins.com/s/AKfycbz2gCQYl_OjEJB26jiUL8253I0bX4czxykkcmt-MnF41lIyX18SLkRgUcJ_VJRJbiwh/exec"