"""
Implementation of the ISO7816-4 SELECT FILE command.
"""
from typing import Tuple
from smartcard.CardConnection import CardConnection

from .base import ApduCommand, ApduError
from .. import hal

# ISO7816-4 APDU Constants
CLA_ISO7816 = 0x00
INS_SELECT = 0xA4
P1_SELECT_BY_ID = 0x00
P2_FIRST_OR_ONLY = 0x0C

# ISO7816-4 Status Words
SW_OK: Tuple[int, int] = (0x91, 0x00)


class IsoSelectFile(ApduCommand):
    """
    Selects an application or file on the PICC by its ID.
    """

    def __init__(self, file_id: int):
        """
        Args:
            file_id: The 2-byte identifier of the file or application to select.
        """
        if not 0x0000 <= file_id <= 0xFFFF:
            raise ValueError("File ID must be a 2-byte integer (0x0000-0xFFFF)")
        self.file_id = file_id

    def execute(self, connection: CardConnection) -> None:
        """
        Executes the IsoSelectFile command.

        Args:
            connection: An active CardConnection object.

        Raises:
            ApduError: If the command fails.
        """
        print(f"INFO: Selecting File ID {self.file_id:04X}")
        # Lc is the length of the data field
        lc = 2
        # Data field contains the 2-byte file ID
        data = [(self.file_id >> 8) & 0xFF, self.file_id & 0xFF]

        apdu = [
            CLA_ISO7816,
            INS_SELECT,
            P1_SELECT_BY_ID,
            P2_FIRST_OR_ONLY,
            lc,
            *data
        ]
        _, sw1, sw2 = hal.send_apdu(connection, apdu)

        if (sw1, sw2) != SW_OK:
            raise ApduError(f"IsoSelectFile ({self.file_id:04X})", sw1, sw2)

        print(f"INFO: Successfully selected File ID {self.file_id:04X}")
