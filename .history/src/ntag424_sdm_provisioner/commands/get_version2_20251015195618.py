import sys
from abc import ABC, abstractmethod
from typing import List, Tuple
from dataclasses import dataclass
from ntag424_sdm_provisioner.hal import NTag424CardConnection, ApduError
from ntag424_sdm_provisioner.commands.base import ApduCommand, SW_OK


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

        
        
class GetVersion(ApduCommand):
    """
    Selects the NTAG PICC application and retrieves its version information.
    """

    
    def __init__(self, connection: NTag424CardConnection):
        super().__init__(connection, use_escape=True)
        
    # Standard APDU to SELECT application by its AID (DF Name)
    # AID for NXP NTAG is D2760000850101
    SELECT_APDU = [
        0x00,  # CLA: ISO/IEC 7816-4
        0xA4,  # INS: SELECT
        0x04,  # P1:  Select by DF Name (AID)
        0x00,  # P2:  First or only occurrence
        0x07,  # Lc:  Length of AID (7 bytes)
        0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01, # AID
        0x00   # Le:  Expected response length (00 means max available)
    ]

    # NTAG specific GetVersion command, wrapped in an ISO 7816-4 APDU
    # Native command code is 0x60
    GET_VERSION_APDU = [
        0x90,  # CLA: Proprietary class for wrapped native commands
        0x60,  # INS: GetVersion
        0x00,  # P1:  Not used
        0x00,  # P2:  Not used
        0x00   # Le:  Expected response length (00 means max available)
    ]

    def execute(self) -> VersionInfo:
        """
        Executes the command sequence to get the NTAG424 version.

        Args:
            ncc: An active card connection.

        Returns:
            A VersionInfo object containing the parsed data.

        Raises:
            ApduError: If the card returns a non-success status code (not 90 00).
            ValueError: If the version data response is not the expected length.
        """
        print("Step 1: Selecting NTAG Application...")
        _, sw1, sw2 = self.connection.send_apdu(self.SELECT_APDU, use_escape=True)
        if (sw1, sw2) != SW_OK:
            raise ApduError("Failed to select NTAG application", sw1, sw2)
        print("Success.")

        print("\nStep 2: Sending GetVersion command...")
        data, sw1, sw2 = self.connection.send_apdu(self.GET_VERSION_APDU, use_escape=True)
        if (sw1, sw2) != SW_OK:
            raise ApduError("GetVersion command failed", sw1, sw2)

        # The NTAG424 GetVersion command returns 28 bytes of data
        if len(data) < 28:
            raise ValueError(f"Received incomplete version data. "
                             f"Expected 28 bytes, got {len(data)}")

        print("Success.")
        # Parse the 28-byte response according to the NTAG424 datasheet
        version_info = VersionInfo(
            hw_vendor_id=data[0],
            hw_type=data[1],
            hw_subtype=data[2],
            hw_major_version=data[3],
            hw_minor_version=data[4],
            hw_storage_size=data[5],
            hw_protocol=data[6],
            sw_vendor_id=data[7],
            sw_type=data[8],
            sw_subtype=data[9],
            sw_major_version=data[10],
            sw_minor_version=data[11],
            sw_storage_size=data[12],
            sw_protocol=data[13],
            uid=bytes(data[14:21]),
            batch_no=bytes(data[21:26]),
            fab_week=data[26],
            fab_year=data[27]
        )
        return version_info