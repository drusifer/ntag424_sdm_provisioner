# file: ntag424_sdm_provisioner/constants.py

from dataclasses import dataclass
from enum import IntEnum, IntFlag
from typing import Final

# ============================================================================
# File Numbers
# ============================================================================

class FileNo(IntEnum):
    """Standard file numbers on NTAG424 DNA."""
    CC_FILE = 0x01          # Capability Container (read-only)
    NDEF_FILE = 0x02        # NDEF data file (main file for NFC)
    PROPRIETARY_FILE = 0x03 # Proprietary data file (optional)


# ============================================================================
# Key Numbers
# ============================================================================

class KeyNo(IntEnum):
    """Key numbers for authentication."""
    KEY_0 = 0x00  # Master application key
    KEY_1 = 0x01  # Read key
    KEY_2 = 0x02  # Write key
    KEY_3 = 0x03  # Read&Write key
    KEY_4 = 0x04  # Change key


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
    
    def __str__(self) -> str:
        return self.name


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
        """
        Convert to NTAG424 2-byte format.
        
        Returns:
            2 bytes [byte1, byte0]
        """
        byte1 = (self.read << 4) | self.write
        byte0 = (self.read_write << 4) | self.change
        return bytes([byte1, byte0])
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'AccessRights':
        """
        Parse from 2-byte format.
        
        Args:
            data: 2 bytes from card
        
        Returns:
            AccessRights instance
        """
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
        def fmt(val: AccessRight) -> str:
            return val.name
        
        return (
            f"Read={fmt(self.read)}, "
            f"Write={fmt(self.write)}, "
            f"RW={fmt(self.read_write)}, "
            f"Change={fmt(self.change)}"
        )


# ============================================================================
# Access Rights Presets
# ============================================================================

class AccessRightsPresets:
    """Common access rights configurations."""
    
    # Free read, key 0 for write (typical for NDEF)
    FREE_READ_KEY0_WRITE = AccessRights(
        read=AccessRight.FREE,
        write=AccessRight.KEY_0,
        read_write=AccessRight.FREE,
        change=AccessRight.FREE
    )
    
    # All operations require key 0
    KEY0_ALL = AccessRights(
        read=AccessRight.KEY_0,
        write=AccessRight.KEY_0,
        read_write=AccessRight.KEY_0,
        change=AccessRight.KEY_0
    )
    
    # Free read/write (not recommended for production!)
    FREE_ALL = AccessRights(
        read=AccessRight.FREE,
        write=AccessRight.FREE,
        read_write=AccessRight.FREE,
        change=AccessRight.FREE
    )
    
    # Read-only with free access
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
    READ_COUNTER = 0x20      # Mirror read counter in NDEF
    ENABLED = 0x40           # Enable SDM
    UID_MIRROR = 0x80        # Mirror UID in NDEF
    
    # Common combinations
    BASIC_SDM = ENABLED | UID_MIRROR
    SDM_WITH_COUNTER = ENABLED | UID_MIRROR | READ_COUNTER


# ============================================================================
# NDEF URI Prefixes
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