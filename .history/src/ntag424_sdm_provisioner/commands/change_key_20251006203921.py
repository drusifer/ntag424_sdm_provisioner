"""
Implements the NTAG424 ChangeKey command.
"""
import zlib
from typing import cast
from smartcard.CardConnection import CardConnection
from Crypto.Cipher import AES

from .base import ApduCommand, ApduError, SW_OK
from ..session import Ntag424Session

# -- NTAG424 Constants for ChangeKey Command --

# The CLA byte for proprietary commands
CLA_PROPRIETARY = 0x90

# The INS byte for the ChangeKey command
INS_CHANGE_KEY = 0x54

# AES keys must be 16 bytes
AES_KEY_SIZE = 16

# NXP CRC32 uses a non-standard initial value of all 1s.
CRC32_INITIAL_VALUE = 0xFFFFFFFF

# The IV for encrypting the command payload is always all zeros.
ZERO_IV = b'\x00' * AES_KEY_SIZE

# Key range for application keys
MIN_KEY_NO = 0
MAX_KEY_NO = 4


def _xor_bytes(a: bytes, b: bytes) -> bytes:
    """Performs a byte-wise XOR operation."""
    return bytes(x ^ y for x, y in zip(a, b))


class ChangeKey(ApduCommand):
    """
    A command to change one of the five application-level keys on the NTAG424.
    This command must be sent over an authenticated and encrypted session.
    """

    def __init__(self, session: Ntag424Session, key_no: int,
                 new_key: bytes, old_key: bytes):
        """
        Args:
            session: An authenticated Ntag424Session.
            key_no: The number of the key to change (0-4).
            new_key: The new 16-byte AES key.
            old_key: The old 16-byte AES key.
        """
        if session.ses_enc_key is None:
            raise RuntimeError("Session is not authenticated")
        if not MIN_KEY_NO <= key_no <= MAX_KEY_NO:
            raise ValueError(f"Key number must be between {MIN_KEY_NO} and {MAX_KEY_NO}")
        if len(new_key) != AES_KEY_SIZE or len(old_key) != AES_KEY_SIZE:
            raise ValueError(f"Keys must be {AES_KEY_SIZE} bytes")

        self.session = session
        self._key_no = key_no
        self._new_key = new_key
        self._old_key = old_key

    def execute(self, connection: CardConnection) -> None:
        """
        Executes the ChangeKey command.

        Raises:
            ApduError: If the command fails.
        """
        # Data to be encrypted: NewKey || KeyDataCRC
        # For security, the new key is not sent in plaintext. Instead, the PICC
        # expects the new key to be XOR'd with the old key.
        xored_key = _xor_bytes(self._new_key, self._old_key)

        # The CRC is calculated over the *new* key, not the XOR'd one. This
        # acts as an integrity check.
        key_crc = zlib.crc32(self._new_key, CRC32_INITIAL_VALUE).to_bytes(4, 'little')

        # Construct the plaintext payload
        plaintext = xored_key + key_crc

        # Encrypt the payload using the session encryption key
        cipher = AES.new(self.session.ses_enc_key, AES.MODE_CBC, iv=ZERO_IV)
        encrypted_data = cipher.encrypt(plaintext)

        # The key number to change is specified in the P1 parameter.
        # P2 is unused for this command.
        response, sw1, sw2 = self._send_apdu(
            connection,
            cla=CLA_PROPRIETARY,
            ins=INS_CHANGE_KEY,
            p1=self._key_no,
            p2=0x00,
            data=encrypted_data
        )

        if (sw1, sw2) != SW_OK:
            raise ApduError("ChangeKey failed", sw1, sw2)

        print(f"INFO: Successfully changed Key No. {self._key_no}")

