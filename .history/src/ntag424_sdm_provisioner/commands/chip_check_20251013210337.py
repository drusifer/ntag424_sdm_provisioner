# filename: ntag_communicator.py (Revised for Generic Test)

from ntag424_sdm_provisioner.commands.base import ApduCommand
from ntag424_sdm_provisioner.hal import NTag424CardConnection

from smartcard.System import readers
from smartcard.util import toHexString

# --- Generic ISO 7816-4 Command ---
# 1. SELECT MASTER FILE (MF ID: 3F 00)
# Command: 00 A4 00 00 02 3F 00 
SELECT_MF_APDU = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x3F, 0x00]


class ChipCheck(ApduCommand):
    """Sends a generic ISO 7816-4 command to check chip compatibility."""
    def execute(self, connection: NTag424CardConnection) -> bytes:
        data, sw1, sw2 = self.send_apdu(connection, SELECT_MF_APDU)
        status_word = (sw1 << 8) | sw2

        if status_word == 0x9000:
            print(f"\n✅ SUCCESS: SELECT_MF returned 90 00.")
            print("INFO: Chip supports ISO/IEC 7816-4. We may need to consult the chip's documentation for its specific AID/commands.")

        elif (sw1 & 0xF0) == 0x60:  # Check for any 6xxx error
            print(f"\nERROR: Standard 7816-4 command failed. Status Word: {hex(sw1)} {hex(sw2)}")
            print("INFO: This could be a non-7816-4 card (e.g., MIFARE Classic, Type 1/2 Tag) or a card that requires special initialization.")

        elif status_word == 0x0000:
            print(f"\nFATAL ERROR: APDU failed with 00 00 status. Still a LOW-LEVEL READER/PC/SC FAILURE.")
            print("ACTION: Ensure the card is stable on the reader. Try a different reader if possible.")

        else:
            print(f"\nERROR: APDU failed. Unknown Status Word: {hex(sw1)} {hex(sw2)}")
            print(f"INFO: Raw Response Data: {toHexString(data)}")

        return data
