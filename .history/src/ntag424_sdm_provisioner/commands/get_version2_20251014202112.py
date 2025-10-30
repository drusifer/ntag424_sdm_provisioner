import sys
from abc import ABC, abstractmethod
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class VersionInfo:
    """Represents the parsed version information from an NTAG424 chip."""
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

    def __str__(self):
        """Returns a human-readable string representation."""
        size_map = {0x15: "416 bytes", 0x13: "256 bytes"}
        hw_storage_str = size_map.get(self.hw_storage_size, f"Unknown (0x{self.hw_storage_size:02X})")
        
        return (
            f"--- NTAG 424 DNA Version Info ---\n"
            f"Hardware Information:\n"
            f"  Vendor ID:       0x{self.hw_vendor_id:02X} (NXP)\n"
            f"  Type:            0x{self.hw_type:02X} (NTAG)\n"
            f"  Subtype:         0x{self.hw_subtype:02X}\n"
            f"  Version:         v{self.hw_major_version}.{self.hw_minor_version}\n"
            f"  Storage Size:    {hw_storage_str}\n"
            f"  Protocol:        0x{self.hw_protocol:02X} (ISO/IEC 14443-4)\n"
            f"\nSoftware Information:\n"
            f"  Vendor ID:       0x{self.sw_vendor_id:02X} (NXP)\n"
            f"  Type:            0x{self.sw_type:02X} (NTAG)\n"
            f"  Subtype:         0x{self.sw_subtype:02X}\n"
            f"  Version:         v{self.sw_major_version}.{self.sw_minor_version}\n"
            f"  Protocol:        0x{self.sw_protocol:02X} (ISO/IEC 14443-4)\n"
            f"\nManufacturing Information:\n"
            f"  UID:             {self.uid.hex().upper()}\n"
            f"  Batch No:        {self.batch_no.hex().upper()}\n"
            f"  Fabrication:     Week {self.fab_week}, 20{self.fab_year:02d}"
        )