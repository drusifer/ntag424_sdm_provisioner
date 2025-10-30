# file: ntag424_sdm_provisioner/constants.py

from dataclasses import dataclass
from enum import IntEnum, IntFlag

class AccessRight(IntEnum):
    """Access right nibble values."""
    KEY_0 = 0x0
    KEY_1 = 0x1
    KEY_2 = 0x2
    KEY_3 = 0x3
    KEY_4 = 0x4
    FREE = 0xE
    NEVER = 0xF


class SDMOption(IntFlag):
    """SDM options (combinable with | operator)."""
    NONE = 0x00
    READ_COUNTER = 0x20
    ENABLED = 0x40
    UID_MIRROR = 0x80


@dataclass
class AccessRights:
    """Type-safe access rights with validation."""
    read: AccessRight = AccessRight.FREE
    write: AccessRight = AccessRight.KEY_0
    read_write: AccessRight = AccessRight.FREE
    change: AccessRight = AccessRight.KEY_0
    
    def __post_init__(self):
        """Validate all fields are AccessRight enums."""
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
        """Parse from 2 bytes."""
        if len(data) != 2:
            raise ValueError("Must be 2 bytes")
        
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