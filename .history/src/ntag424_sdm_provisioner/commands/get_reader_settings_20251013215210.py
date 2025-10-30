from ntag424_sdm_provisioner.commands.base import ApduCommand
from ntag424_sdm_provisioner.hal import NTag424CardConnection

class GetReaderSettings(ApduCommand):
    def __init__(self):
        super().__init__(use_escape=True)

    def execute(self, connection: NTag424CardConnection) -> bytes:
        print("GetReaderSettings: Not implemented yet.")
        get_status_apdu = [0xFF, 0x00, 0x00, 0x00, 0x02, 0xD4, 0x04]  # 
        data, sw1, sw2 = self.send_apdu(connection, get_status_apdu)
        status_word = (sw1 << 8) | sw2
        print (f"GetReaderSettings: SW={status_word:04X}, Data={data}")