"""
Implementation of the NTAG424's AuthenticateEV2First command.
"""
from typing import Tuple
from ntag424_sdm_provisioner.hal import NTag424CardConnection
from Crypto.Cipher import AES

from .base import ApduCommand, ApduError
from .. import hal

# NTAG424 DNA Command Constants
CLA_PROPRIETARY = 0x90
INS_AUTHENTICATE_EV2_FIRST = 0x71

# ISO7816-4 Status Words
SW_OK: Tuple[int, int] = (0x91, 0x00)
SW_MORE_DATA: Tuple[int, int] = (0x91, 0xAF)


class AuthenticateEV2First(ApduCommand):
    """
    Initiates EV2 authentication. The PICC is authenticated by the backend.
    """

    def __init__(self, key_no: int, key: bytes):
        """
        Args:
            key_no: The number of the key to be used (0x00 - 0x04).
            key: The 16-byte AES-128 key.
        """
        if not 0x00 <= key_no <= 0x04:
            raise ValueError("Key number must be between 0 and 4")
        if len(key) != 16:
            raise ValueError("Key must be 16 bytes for AES-128")
        self.key_no = key_no
        self.key = key
        self.cipher = AES.new(self.key, AES.MODE_CBC, iv=b'\x00' * 16)

    def execute(self, connection: NTag424CardConnection) -> bytes:
        """
        Executes the AuthenticateEV2First command.

        Args:
            connection: An active NTag424CardConnection object.

        Returns:
            The decrypted RndA' from the PICC.

        Raises:
            ApduError: If the command fails.
        """
        print(f"INFO: Authenticating with key number {self.key_no}")
        # Lc is 1 (length of data) + 1 (Le)
        lc = 1
        # Data is the key number
        data = [self.key_no]
        # Le specifies we expect a response
        le = 0x00

        apdu = [
            CLA_PROPRIETARY,
            INS_AUTHENTICATE_EV2_FIRST,
            0x00,  # P1
            0x00,  # P2
            lc,
            *data,
            le
        ]

        response, sw1, sw2 = connection.send_adpu(apdu)

        if (sw1, sw2) != SW_MORE_DATA:
            raise ApduError(f"AuthenticateEV2First (KeyNo {self.key_no})", sw1, sw2)

        # The response is the encrypted RndB from the card (enc_rndB)
        enc_rndb = bytes(response)
        if len(enc_rndb) != 16:
            raise ValueError("Expected a 16-byte encrypted RndB from the card")

        # Decrypt RndB to get RndA'
        # The card encrypts a random RndA, we send back a rotated RndA' and RndB
        # For this first step, we just need to get the challenge.
        # The PICC expects us to decrypt what it sends back, which is RndB.
        # However, the datasheet shows that the response to the first command
        # is actually an encrypted version of a random number from the card,
        # which we'll call RndB_enc. The backend decrypts this to get RndB.
        # The example in the datasheet is slightly confusing.
        # Let's follow AN12196: The PICC returns `ek(RndB)`.
        # We must decrypt it to get RndB.
        rndb = self.cipher.decrypt(enc_rndb)
        print("INFO: Received and decrypted RndB from PICC")

        return rndb
