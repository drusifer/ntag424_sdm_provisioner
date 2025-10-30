"""
Implementation of the NTAG424's AuthenticateEV2Part2 command.
"""
import os
from typing import Tuple
from smartcard.CardConnection import CardConnection
from Crypto.Cipher import AES

from .base import ApduCommand, ApduError
from .. import hal

# NTAG424 DNA Command Constants
CLA_PROPRIETARY = 0x90
INS_AUTHENTICATE_EV2_PART2 = 0xAF

# ISO7816-4 Status Words
SW_OK: Tuple[int, int] = (0x91, 0x00)


def _rotate_left(data: bytes, n: int = 1) -> bytes:
    """Rotates a byte string to the left."""
    return data[n:] + data[:n]


class AuthenticateEV2Part2(ApduCommand):
    """
    Completes the second half of the EV2 authentication.
    The backend authenticates itself to the PICC and verifies the PICC's
    response.
    """

    def __init__(self, key: bytes, rndB: bytes):
        """
        Args:
            key: The 16-byte AES-128 key.
            rndB: The 16-byte decrypted RndB from the PICC (from Part 1).
        """
        if len(rndB) != 16:
            raise ValueError("RndB must be 16 bytes")
        if len(key) != 16:
            raise ValueError("Key must be 16 bytes")
        self.key = key
        self.rndB = rndB
        self.rndA = os.urandom(16)

    def execute(self, connection: CardConnection) -> None:
        """
        Executes the AuthenticateEV2Part2 command.

        Args:
            connection: An active CardConnection object.

        Raises:
            ApduError: If the command fails or authentication is unsuccessful.
        """
    # Rotate RndA left by 8 bits (1 byte)
    rndA_prime = _rotate_left(self.rndA)

    # XOR RndA and RndB
    rndA_xor_rndB = bytes(a ^ b for a, b in zip(self.rndA, self.rndB))

    # Encrypt the XOR result using a fresh cipher instance
    cipher_enc = AES.new(self.key, AES.MODE_CBC, iv=b"\x00" * 16)
    enc_rndA_xor_rndB = cipher_enc.encrypt(rndA_xor_rndB)

        # Construct the payload: RndA' || enc(RndA xor RndB)
        payload = rndA_prime + enc_rndA_xor_rndB

        # Send the command
        lc = len(payload)
        le = 0x00
        apdu = [
            CLA_PROPRIETARY,
            INS_AUTHENTICATE_EV2_PART2,
            0x00,  # P1
            0x00,  # P2
            lc,
            *payload,
            le
        ]

        response, sw1, sw2 = hal.send_apdu(connection, apdu)

        if (sw1, sw2) != SW_OK:
            raise ApduError("AuthenticateEV2Part2", sw1, sw2)

        # The response from the PICC is ek(RndB')
        if len(response) != 16:
            msg = f"AuthenticateEV2Part2 expected 16-byte response, got {len(response)}"
            raise ApduError(msg, sw1, sw2)

    enc_rndB_prime = bytes(response)
    # Decrypt response using a fresh cipher instance
    cipher_dec = AES.new(self.key, AES.MODE_CBC, iv=b"\x00" * 16)
    rndB_prime_from_picc = cipher_dec.decrypt(enc_rndB_prime)

        # Verify the PICC's response
        rndB_prime_calculated = _rotate_left(self.rndB)

        if rndB_prime_from_picc != rndB_prime_calculated:
            raise ApduError(f"PICC authentication failed: RndB' mismatch picc: "
                            f"{rndB_prime_from_picc} calc: {rndB_prime_calculated}")

        print("INFO: PICC authenticated successfully")
