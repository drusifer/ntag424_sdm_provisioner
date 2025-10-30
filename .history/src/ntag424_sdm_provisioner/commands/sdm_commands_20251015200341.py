from ntag424_sdm_provisioner.commands.base import ApduCommand, SW_OK, ApduError
from ntag424_sdm_provisioner.hal import NTag424CardConnection


class SelectPiccApplication(ApduCommand):
    """
    Selects the main PICC-level application on the NTAG424 DNA tag.
    This is the first step before performing any authenticated operations.
    """
    # The NTAG 424 DNA AID is F0 + NXP's RID + 0101 for the NDEF tag app
    PICC_AID = [0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01]

    def __init__(self, use_escape: bool = False):
        super().__init__(use_escape)

    def execute(self, connection: 'NTag424CardConnection') -> None:
        apdu = [
            0x00,  # CLA: ISO/IEC 7816-4
            0xA4,  # INS: SELECT
            0x04,  # P1: Select by DF Name (AID)
            0x00,  # P2: First or only occurrence
            len(self.PICC_AID),  # Lc
            *self.PICC_AID,  # Data: The AID
            0x00   # Le
        ]
        _, sw1, sw2 = self.send_apdu(connection, apdu)

        if (sw1, sw2) != SW_OK:
            raise ApduError("Failed to select PICC application", sw1, sw2)