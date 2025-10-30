# filename: ntag_communicator.py

from smartcard.System import readers
from smartcard.util import toHexString, toBytes
from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.chip_check import ChipCheck

# --- NTAG424 DNA APDU Commands ---
# CLA, INS, P1, P2, Le (for GetVersion, Le=00 means get max response)
GET_VERSION_APDU = [0x90, 0x60, 0x00, 0x00, 0x00]

def identify_ntag424():
    """
    Connects to the first available reader, selects the card,
    sends the GET_VERSION command, and checks the response.
    """
    try:
        with CardManager() as cardReader:
            print("--- Waiting for tap ---")
            atr = cardReader.wait_for_atr()
            print("INFO: Card detected. ATR:", atr)
            data = ChipCheck().execute(cardReader.connection)
            print(f'INFO: ChipCheck data: {toHexString(data)} ')

    except Exception as e:
        print(f"FATAL ERROR: An unexpected exception occurred: {e}")
    finally:
        if 'connection' in locals():
            try:
                connection.disconnect()
            except Exception:
                pass

if __name__ == "__main__":
    identify_ntag424()