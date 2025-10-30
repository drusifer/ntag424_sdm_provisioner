from __future__ import annotations

import os
from typing import Dict, List, Tuple

from Crypto.Cipher import AES
from Crypto.Hash import CMAC

# --- Constants copied from real modules for self-contained testing ---
KEY_DEFAULT_FACTORY = b"\x00" * 16
STATUS_SUCCESS = (0x91, 0x00)
STATUS_SUCCESS_MORE_DATA = (0x91, 0xAF)

# --- Crypto Helpers ---

def _decrypt_aes128_cbc(key: bytes, data: bytes) -> bytes:
    """Decrypts data using AES-128 in CBC mode with a zero IV."""
    cipher = AES.new(key, AES.MODE_CBC, iv=b"\x00" * 16)
    return cipher.decrypt(data)

def _encrypt_aes128_cbc(key: bytes, data: bytes) -> bytes:
    """Encrypts data using AES-128 in CBC mode with a zero IV."""
    cipher = AES.new(key, AES.MODE_CBC, iv=b"\x00" * 16)
    return cipher.encrypt(data)

def _left_rotate(data: bytes, shift_bytes: int) -> bytes:
    """Performs a left circular shift on a byte string."""
    return data[shift_bytes:] + data[:shift_bytes]


class MockCardConnection:
    """
    A mock implementation of a pyscard connection that simulates an NTAG424 chip.
    This class acts as a state machine, tracking authentication status and keys.
    """

    def __init__(self):
        self.keys: Dict[int, bytes] = {
            0: KEY_DEFAULT_FACTORY,
            1: KEY_DEFAULT_FACTORY,
            2: KEY_DEFAULT_FACTORY,
            3: KEY_DEFAULT_FACTORY,
            4: KEY_DEFAULT_FACTORY,
        }
        self.authenticated_key_no: int | None = None
        self.session_key: bytes | None = None
        self._rndB_prime: bytes | None = None  # The RndB' sent to the client

    def transmit(self, apdu: List[int]) -> Tuple[List[int], int, int]:
        """Receives an APDU, processes it based on state, and returns a response."""
        apdu_bytes = bytes(apdu)
        cla, ins, p1, p2, lc, *data_le = apdu
        data = apdu_bytes[5:-1] if lc > 0 else b""

        # AuthenticateEV2First
        if ins == 0x71:
            key_no = data[0]
            self.authenticated_key_no = key_no
            key = self.keys[key_no]
            self._rndB_prime = os.urandom(16)
            encrypted_rndB = _encrypt_aes128_cbc(key, self._rndB_prime)
            return list(encrypted_rndB), *STATUS_SUCCESS_MORE_DATA

        # AuthenticateEV2Part2 (or other commands using INS=AF for more data)
        if ins == 0xAF and self._rndB_prime is not None:
            key = self.keys[self.authenticated_key_no]
            decrypted_payload = _decrypt_aes128_cbc(key, data)
            rndA = decrypted_payload[:16]
            # In a real chip, we'd verify rotl(RndB'), but here we just proceed
            self.session_key = os.urandom(16) # Mock session key
            encrypted_rndA = _encrypt_aes128_cbc(key, _left_rotate(rndA, 1))
            self._rndB_prime = None # Clear state
            return list(encrypted_rndA), *STATUS_SUCCESS

        # All subsequent commands must be authenticated
        if self.session_key is None:
            # Return a permission denied error
            return [], 0x91, 0xDE

        # ChangeKey
        if ins == 0xC4:
            # We don't need to mock the full crypto, just acknowledge success
            return [], *STATUS_SUCCESS

        # SetFileSettings
        if ins == 0x5F:
            return [], *STATUS_SUCCESS

        # WriteData
        if ins == 0x8D:
            return [], *STATUS_SUCCESS

        # Default error for unknown commands
        return [], 0x6E, 0x00

    def getATR(self) -> List[int]:
        """Returns a mock ATR for an NTAG424."""
        return [
            0x3B, 0x88, 0x80, 0x01, 0x4E, 0x58, 0x50, 0x2D,
            0x4E, 0x54, 0x41, 0x47, 0x34, 0x32, 0x34, 0x90, 0x00
        ]

    def execute(self, command):
        """Proxy to command.execute, accepting command objects in tests."""
        return command.execute(self)


class MockCardManager:
    """
    A mock context manager that yields a MockCardConnection.
    """
    def __enter__(self) -> MockCardConnection:
        self.connection = MockCardConnection()
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

def list_readers() -> List[str]:
    """Returns a mock reader list."""
    return ["MockNFCReader 0"]
