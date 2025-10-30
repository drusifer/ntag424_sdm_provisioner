from ntag424_sdm_provisioner.commands.base import ApduCommand
from ntag424_sdm_provisioner.hal import NTag424CardConnection

class GetReaderSettings(ApduCommand):
    def __init__(self):
        super().__init__(use_escape=False)

    def execute(self, connection: NTag424CardConnection) -> bytes:
        print("GetReaderSettings...")
        get_status_apdu = [0xFF, 0x00, 0x00, 0x00, 0x02, 0xD4, 0x04]   
        data, sw1, sw2 = self.send_apdu(connection, get_status_apdu)
        status_word = (sw1 << 8) | sw2
        print (f"GetReaderSettings: SW={status_word:04X}, Data={data}")


class SetBuzzer(ApduCommand):
    def __init__(self, enable: bool):
        super().__init__(use_escape=False)
        self.enable = enable

    def execute(self, connection: NTag424CardConnection) -> bytes:
        print(f"SetBuzzer: {'Enable' if self.enable else 'Disable'}")
        off = 0x00
        on = 0xFF
        if self.enable:
            status = on
        else:
            status = off

        buzzer_apdu = [0xFF, 0x00, 0x52, status, 0x00,]
        data, sw1, sw2 = self.send_apdu(connection, buzzer_apdu)
        status_word = (sw1 << 8) | sw2
        print (f"SetBuzzer: SW={status_word:04X}, Data={data}")