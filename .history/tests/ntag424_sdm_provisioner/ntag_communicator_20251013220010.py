# filename: ntag_communicator.py

from smartcard.System import readers
from smartcard.util import toHexString, toBytes
from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.chip_check import ChipCheck
from ntag424_sdm_provisioner.commands.get_reader_settings import GetReaderSettings, SetBuzzer
from ntag424_sdm_provisioner.commands.mfc_list import MFC_ListSectors
from ntag424_sdm_provisioner.commands.base import ApduError

# --- NTAG424 DNA APDU Commands ---
# CLA, INS, P1, P2, Le (for GetVersion, Le=00 means get max response)
GET_VERSION_APDU = [0x90, 0x60, 0x00, 0x00, 0x00]

def try_mfc(cardReader):
    print("INFO: ChipCheck failed; Let's see if it's an older MIFARE Classic or non-ISO7816 card.")
    data = MFC_ListSectors().execute(cardReader.connection)
    print(f'INFO: MFC_ListSectors data: {toHexString(data)} ')


def identify_ntag424():
    """
    Connects to the first available reader, selects the card,
    sends the GET_VERSION command, and checks the response.
    """
    with CardManager() as cardReader:

        print(" set the buzzer off" )
        data = SetBuzzer(False).execute(cardReader.connection)
        print(f'INFO: Buzzer result: {toHexString(data)} ')
        
        print("Getting Reader Settings...")
        result = GetReaderSettings().execute(cardReader.connection)
        print("Got Reader Settings:", result)
        print("--- Waiting for tap ---")
        atr = cardReader.wait_for_atr()
        print("INFO: Card detected. ATR:", atr)
        try:
            data = ChipCheck().execute(cardReader.connection)
            print(f'INFO: ChipCheck data: {toHexString(data)} ')
        except ApduError as e:
            print(f"Error: {e}")
            try_mfc(cardReader)



if __name__ == "__main__":
    identify_ntag424()