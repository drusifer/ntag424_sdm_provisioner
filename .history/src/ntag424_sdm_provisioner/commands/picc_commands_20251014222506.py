from typing import List
from ntag424_sdm_provisioner.hal import CardConnection, ApduError, hexb, SW_OK
from ntag424_sdm_provisioner.commands.base import ApduCommand

class GetData(ApduCommand):
    """
    Returns the serial number (UID) or Answer to Select (ATS) of the connected PICC. [cite: 180]
    """
    def __init__(self, get_ats: bool = False, use_escape: bool = False):
        """
        Args:
            get_ats: If True, gets the ATS[cite: 191]. If False, gets the UID[cite: 190].
        """
        super().__init__(use_escape)
        self._p1 = 0x01 if get_ats else 0x00 # [cite: 182]

    def execute(self, connection: CardConnection) -> List[int]:
        """
        Executes the Get Data command.

        Returns:
            A list of integers representing the UID or ATS.
        """
        apdu = [
            0xFF,  # Class [cite: 182]
            0xCA,  # INS [cite: 182]
            self._p1, # P1 [cite: 182]
            0x00,  # P2 [cite: 182]
            0x00   # Le (Full Length) [cite: 182]
        ]
        data, sw1, sw2 = self.send_apdu(connection, apdu)

        if (sw1, sw2) == SW_OK: # [cite: 188]
            return data
        else:
            raise ApduError("Get Data operation failed", sw1, sw2) # [cite: 188]

            
        # PICC Commands for MiFARE Classic
        