"""
Implementation of the NTAG424's GetVersion command.
"""
import dataclasses
from typing import List, Tuple
from smartcard.CardConnection import CardConnection

from .base import ApduCommand, ApduError
from .. import hal

# NXP Proprietary APDU Constants
CLA_PROPRIETARY = 0x90
INS_GET_VERSION = 0x60
INS_GET_MORE = 0xAF

# ISO7816-4 Status Words
SW_OK: Tuple[int, int] = (0x91, 0x00)
SW_MORE_DATA: Tuple[int, int] = (0x91, 0xAF)


# Response field indices
_HW_VENDOR_ID = 0
_HW_TYPE = 1
_HW_SUBTYPE = 2
_HW_MAJOR_VERSION = 3
_HW_MINOR_VERSION = 4
_HW_STORAGE_SIZE = 5
_HW_PROTOCOL = 6
_SW_VENDOR_ID = 7
_SW_TYPE = 8
_SW_SUBTYPE = 9
_SW_MAJOR_VERSION = 10
_SW_MINOR_VERSION = 11
_SW_STORAGE_SIZE = 12
_SW_PROTOCOL = 13
_UID_START = 14
_UID_END = 21  # Exclusive
_BATCH_NO_START = 21
_BATCH_NO_END = 26  # Exclusive
_FAB_WEEK = 26
_FAB_YEAR = 27


@dataclasses.dataclass(frozen=True)
class Version:
    """Represents a major/minor version number."""
    major: int
    minor: int

    def __str__(self):
        return f"v{self.major}.{self.minor}"


@dataclasses.dataclass(frozen=True)
class Batch:
    """Represents manufacturing batch information."""
    number: str
    fab_week: int
    fab_year: int

    def __str__(self):
        return f"{self.number} (Fab: {self.fab_week:02}/{2000 + self.fab_year})"


@dataclasses.dataclass(frozen=True)
class HardwareInfo:
    """Represents hardware-specific version details."""
    vendor_id: int
    type: int
    subtype: int
    version: Version
    storage_size: int
    protocol: int


@dataclasses.dataclass(frozen=True)
class SoftwareInfo:
    """Represents software-specific version details."""
    vendor_id: int
    type: int
    subtype: int
    version: Version
    storage_size: int
    protocol: int


@dataclasses.dataclass
class NtagVersion:
    """Represents the parsed version information from the GetVersion command."""
    uid: str
    hardware: HardwareInfo
    software: SoftwareInfo
    batch: Batch

    def __str__(self):
        return (
            f"NTAG424 DNA Version:\n"
            f"  UID: {self.uid}\n"
            f"  Hardware: {self.hardware.version}\n"
            f"  Software: {self.software.version}\n"
            f"  Batch: {self.batch}"
        )


class GetVersion(ApduCommand):
    """
    Retrieves and parses the hardware and software version of the NTAG.
    """
    _EXPECTED_RESPONSE_LEN = 28

    def execute(self, connection: CardConnection) -> NtagVersion:
        """
        Executes the GetVersion command.

        Args:
            connection: An active CardConnection object.

        Raises:
            ApduError: If the command fails.
            ValueError: If the response data is malformed.

        Returns:
            An NtagVersion object containing the parsed version information.
        """
        print("INFO: Getting NTAG Version")
        apdu = [CLA_PROPRIETARY, INS_GET_VERSION, 0x00, 0x00, 0x00]
        data, sw1, sw2 = hal.send_apdu(connection, apdu)

        # Handle chained responses for complete version info
        while (sw1, sw2) == SW_MORE_DATA:
            more_apdu = [CLA_PROPRIETARY, INS_GET_MORE, 0x00, 0x00, 0x00]
            more_data, sw1, sw2 = hal.send_apdu(connection, more_apdu)
            data.extend(more_data)

        if (sw1, sw2) != SW_OK:
            raise ApduError("Get Version", sw1, sw2)

        if len(data) < self._EXPECTED_RESPONSE_LEN:
            raise ValueError(
                f"GetVersion response is shorter than the expected "
                f"{self._EXPECTED_RESPONSE_LEN} bytes."
            )

        return self._parse_version_data(data)

    def _parse_version_data(self, data: List[int]) -> NtagVersion:
        """Parses the raw byte list into an NtagVersion object."""
        hardware = HardwareInfo(
            vendor_id=data[_HW_VENDOR_ID],
            type=data[_HW_TYPE],
            subtype=data[_HW_SUBTYPE],
            version=Version(
                major=data[_HW_MAJOR_VERSION],
                minor=data[_HW_MINOR_VERSION]
            ),
            storage_size=data[_HW_STORAGE_SIZE],
            protocol=data[_HW_PROTOCOL],
        )

        software = SoftwareInfo(
            vendor_id=data[_SW_VENDOR_ID],
            type=data[_SW_TYPE],
            subtype=data[_SW_SUBTYPE],
            version=Version(
                major=data[_SW_MAJOR_VERSION],
                minor=data[_SW_MINOR_VERSION]
            ),
            storage_size=data[_SW_STORAGE_SIZE],
            protocol=data[_SW_PROTOCOL],
        )

        batch = Batch(
            number=''.join(f'{b:02X}' for b in data[_BATCH_NO_START:_BATCH_NO_END]),
            fab_week=data[_FAB_WEEK],
            fab_year=data[_FAB_YEAR]
        )

        return NtagVersion(
            uid=''.join(f'{b:02X}' for b in data[_UID_START:_UID_END]),
            hardware=hardware,
            software=software,
            batch=batch
        )

