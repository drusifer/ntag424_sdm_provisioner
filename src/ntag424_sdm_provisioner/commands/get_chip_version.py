"""
GetChipVersion command for NTAG424 DNA.
"""

from typing import TYPE_CHECKING
from dataclasses import dataclass

from ntag424_sdm_provisioner.commands.base import ApduCommand

if TYPE_CHECKING:
    from ntag424_sdm_provisioner.hal import NTag424CardConnection


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
        from ntag424_sdm_provisioner.uid_utils import uid_to_asset_tag
        asset_tag = uid_to_asset_tag(self.uid)
        return (
            f"Ntag424VersionInfo(\n"
            f"  UID: {self.uid.hex().upper()} [Tag: {asset_tag}],\n"
            f"  Hardware: {self.hw_major_version}.{self.hw_minor_version} ({self.hw_storage_size}B),\n"
            f"  Software: {self.sw_major_version}.{self.sw_minor_version} ({self.sw_storage_size}B),\n"
            f"  Batch: {self.batch_no.hex().upper()},\n"
            f"  Fab: Week {self.fab_week}, Year {self.fab_year}\n"
            f"  {'=' * 60}\n"
            f"\n"
            f"CHIP INFORMATION:\n"
            f"  UID: {self.uid.hex().upper()}\n"
            f"  Asset Tag: {asset_tag} <- Write on label\n"
            f"  Hardware Protocol: {self.hw_protocol}\n"
            f"  Software Protocol: {self.sw_protocol}\n"
            f"  Hardware Type: {self.hw_type}\n"
            f"  Software Type: {self.sw_type}\n"
            f"\n"
            f")"
        )


class GetChipVersion(ApduCommand):
    """
    Retrieves detailed version information from the NTAG424 DNA chip.
    
    Returns hardware info, software info, UID, batch number, and fabrication data.
    """
    
    GET_VERSION_APDU = [0x90, 0x60, 0x00, 0x00, 0x00]

    def __init__(self):
        super().__init__(use_escape=True)

    def __str__(self) -> str:
        return "GetChipVersion()"
    
    def build_apdu(self) -> list:
        """Build APDU for new connection.send(command) pattern."""
        return self.GET_VERSION_APDU.copy()
    
    def parse_response(self, data: bytes, sw1: int, sw2: int) -> Ntag424VersionInfo:
        """Parse response for new connection.send(command) pattern."""
        # NTAG424 DNA GetVersion returns 28 or 29 bytes total
        if len(data) not in [28, 29]:
            raise ValueError(f"Received incomplete version data. "
                             f"Expected 28 or 29 bytes, got {len(data)}")

        # Part 1: Hardware info (bytes 0-6)
        hw_vendor_id = data[0]
        hw_type = data[1] 
        hw_subtype = data[2]
        hw_major_version = data[3]
        hw_minor_version = data[4]
        hw_storage_size = data[5]
        hw_protocol = data[6]
        
        # Part 2: Software info (bytes 7-13)
        sw_vendor_id = data[7]
        sw_type = data[8]
        sw_subtype = data[9]
        sw_major_version = data[10]
        sw_minor_version = data[11]
        sw_storage_size = data[12]
        sw_protocol = data[13]
        
        # Part 3: Production info (bytes 14-27)
        uid = data[14:21]  # 7 bytes
        batch_no = data[21:25]  # 4 bytes
        cw_prod = data[26]  # Calendar week
        year_prod = data[27]  # Year
        
        return Ntag424VersionInfo(
            hw_vendor_id=hw_vendor_id,
            hw_type=hw_type,
            hw_subtype=hw_subtype,
            hw_major_version=hw_major_version,
            hw_minor_version=hw_minor_version,
            hw_storage_size=256 if hw_storage_size == 0x13 else 416,
            hw_protocol=hw_protocol,
            sw_vendor_id=sw_vendor_id,
            sw_type=sw_type,
            sw_subtype=sw_subtype,
            sw_major_version=sw_major_version,
            sw_minor_version=sw_minor_version,
            sw_storage_size=sw_storage_size,
            sw_protocol=sw_protocol,
            uid=uid,
            batch_no=batch_no,
            fab_week=cw_prod,
            fab_year=year_prod
        )

