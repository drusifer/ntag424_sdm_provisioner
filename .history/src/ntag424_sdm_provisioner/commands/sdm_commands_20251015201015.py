
from ntag424_sdm_provisioner.commands.base import ( ApduCommand, 
                                                   ApduError, 
                                                   SuccessResponse,
                                                   AuthenticationChallengeResponse,
                                                   ReadDataResponse,
                                                   SW_OK, 
                                                   SW_ADDITIONAL_FRAME)
from ntag424_sdm_provisioner.hal import NTag424CardConnection, hexb


class SelectPiccApplication(ApduCommand):
    """Selects the main PICC-level application on the NTAG424 DNA tag."""
    PICC_AID = [0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01]

    def __str__(self) -> str:
        return f"SelectPiccApplication(AID={hexb(self.PICC_AID)})"

    def execute(self, connection: 'NTag424CardConnection') -> SuccessResponse:
        apdu = [0x00, 0xA4, 0x04, 0x00, len(self.PICC_AID), *self.PICC_AID, 0x00]
        _, sw1, sw2 = self.send_apdu(connection, apdu)
        if (sw1, sw2) != SW_OK:
            raise ApduError("Failed to select PICC application", sw1, sw2)
        return SuccessResponse("PICC Application selected.")

class AuthenticateEV2First(ApduCommand):
    """Begins the first phase of an EV2 authentication with an AES key."""
    def __init__(self, key_no: int, use_escape: bool = False):
        super().__init__(use_escape)
        self.key_no = key_no

    def __str__(self) -> str:
        return f"AuthenticateEV2First(key_no=0x{self.key_no:02X})"

    def execute(self, connection: 'NTag424CardConnection') -> AuthenticationChallengeResponse:
        apdu = [0x90, 0x71, 0x00, 0x00, 0x01, self.key_no, 0x00]
        data, sw1, sw2 = self.send_apdu(connection, apdu)
        if (sw1, sw2) != SW_ADDITIONAL_FRAME:
            raise ApduError("AuthenticateEV2First failed", sw1, sw2)
        return AuthenticationChallengeResponse(key_no_used=self.key_no, challenge=bytes(data))

class AuthenticateEV2Second(ApduCommand):
    """Completes the second phase of an EV2 authentication."""
    def __init__(self, data_to_card: bytes, use_escape: bool = False):
        super().__init__(use_escape)
        if len(data_to_card) != 32:
            raise ValueError("Authentication data for phase two must be 32 bytes.")
        self.data_to_card = data_to_card

    def __str__(self) -> str:
        return f"AuthenticateEV2Second(data=<{len(self.data_to_card)} bytes>)"

    def execute(self, connection: 'NTag424CardConnection') -> SuccessResponse:
        apdu = [0x90, 0xAF, 0x00, 0x00, len(self.data_to_card), *self.data_to_card, 0x00]
        _, sw1, sw2 = self.send_apdu(connection, apdu)
        if (sw1, sw2) != SW_OK:
            raise ApduError("AuthenticateEV2Second failed", sw1, sw2)
        return SuccessResponse("Secure session established.")

class ChangeKey(ApduCommand):
    """Changes a key on the card. Must be in an authenticated state."""
    def __init__(self, key_no_to_change: int, new_key: bytes, old_key: bytes, use_escape: bool = False):
        super().__init__(use_escape)
        # ... (constructor logic)
        self.key_no = key_no_to_change
        xored_key_data = bytes(a ^ b for a, b in zip(new_key, old_key))
        self.data_to_card = [key_no_to_change] + list(xored_key_data)
        
    def __str__(self) -> str:
        return f"ChangeKey(key_no=0x{self.key_no:02X})"

    def execute(self, connection: 'NTag424CardConnection') -> SuccessResponse:
        apdu = [0x90, 0xC4, 0x00, 0x00, len(self.data_to_card), *self.data_to_card]
        _, sw1, sw2 = self.send_apdu(connection, apdu)
        if (sw1, sw2) != SW_OK:
            raise ApduError(f"Failed to change key number {self.key_no}", sw1, sw2)
        return SuccessResponse(f"Key 0x{self.key_no:02X} changed successfully.")

class WriteData(ApduCommand):
    """Writes data to a standard file on the card."""
    def __init__(self, file_no: int, offset: int, data_to_write: bytes, use_escape: bool = False):
        super().__init__(use_escape)
        self.file_no = file_no
        self.offset = offset
        self.data = data_to_write

    def __str__(self) -> str:
        return f"WriteData(file_no=0x{self.file_no:02X}, offset={self.offset}, data=<{len(self.data)} bytes>)"

    def execute(self, connection: 'NTag424CardConnection') -> SuccessResponse:
        header = [
            self.file_no,
            self.offset & 0xFF, (self.offset >> 8) & 0xFF, 0x00,
            len(self.data) & 0xFF, (len(self.data) >> 8) & 0xFF, 0x00,
        ]
        apdu = [0x90, 0x3D, 0x00, 0x00, len(header) + len(self.data), *header, *self.data]
        _, sw1, sw2 = self.send_apdu(connection, apdu)
        if (sw1, sw2) != SW_OK:
            raise ApduError(f"Failed to write to file {self.file_no}", sw1, sw2)
        return SuccessResponse(f"Wrote {len(self.data)} bytes to file 0x{self.file_no:02X}.")

class ReadData(ApduCommand):
    """Reads data from a standard file on the card."""
    def __init__(self, file_no: int, offset: int, length: int, use_escape: bool = False):
        super().__init__(use_escape)
        self.file_no = file_no
        self.offset = offset
        self.length = length

    def __str__(self) -> str:
        return f"ReadData(file_no=0x{self.file_no:02X}, offset={self.offset}, length={self.length})"

    def execute(self, connection: 'NTag424CardConnection') -> ReadDataResponse:
        apdu = [
            0x90, 0xBD, 0x00, 0x00, 0x07,
            self.file_no,
            self.offset & 0xFF, (self.offset >> 8) & 0xFF, 0x00,
            self.length & 0xFF, (self.length >> 8) & 0xFF, 0x00,
            0x00
        ]
        data, sw1, sw2 = self.send_apdu(connection, apdu)
        if (sw1, sw2) != SW_OK:
            raise ApduError(f"Failed to read file {self.file_no}", sw1, sw2)
        return ReadDataResponse(file_no=self.file_no, offset=self.offset, data=bytes(data))