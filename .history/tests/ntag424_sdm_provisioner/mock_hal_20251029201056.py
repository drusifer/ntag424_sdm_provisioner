from __future__ import annotations

import os
from typing import Dict, List, Tuple, Optional

from Crypto.Cipher import AES
from Crypto.Hash import CMAC

# --- Constants copied from real modules for self-contained testing ---
KEY_DEFAULT_FACTORY = b"\x00" * 16
STATUS_SUCCESS = (0x90, 0x00)
STATUS_SUCCESS_MORE_DATA = (0x91, 0xAF)
SW_FILE_NOT_FOUND = (0x6A, 0x82)
SW_LENGTH_ERROR = (0x91, 0x7E)
SW_ILLEGAL_COMMAND = (0x91, 0x1C)
SW_CONDITIONS_NOT_SATISFIED = (0x69, 0x85)

# NDEF File ID
NDEF_FILE_ID = [0xE1, 0x04]  # E104h


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
    
    Updated to match real tag behavior from comprehensive_ndef_test.py results:
    - File selection works with ISOSelectFile (P1=0x02, file ID=E104h)
    - ISOReadBinary (00 B0) works without authentication
    - ISOUpdateBinary (00 D6) works without authentication
    - CLA=00 required for ISO commands, CLA=90 fails with SW=917E
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
        
        # File system state
        self.selected_file: Optional[int] = None  # None or file ID
        self.ndef_file_data: bytes = b'\x00' * 256  # 256 bytes for NDEF file
        self.picc_app_selected: bool = False  # Whether PICC app is selected
        
        # GetChipVersion state
        self.get_version_part: int = 0  # 0=not started, 1=part1, 2=part2, 3=part3

    def send_apdu(self, apdu: List[int], use_escape: bool = False) -> Tuple[List[int], int, int]:
        """
        Send APDU to mock card (matches real HAL interface).
        
        Args:
            apdu: APDU command bytes
            use_escape: Ignored for mock (matches real HAL signature)
            
        Returns:
            Tuple of (response_data, sw1, sw2)
        """
        if len(apdu) < 4:
            return [], 0x6D, 0x00  # Wrong length
        
        cla, ins = apdu[0], apdu[1]
        
        # Handle ISO commands (CLA=00) - work without authentication
        if cla == 0x00:
            return self._handle_iso_command(apdu)
        
        # Handle proprietary commands (CLA=90) - may require authentication
        if cla == 0x90:
            return self._handle_proprietary_command(apdu)
        
        # Unknown CLA
        return [], 0x6E, 0x00
    
    def transmit(self, apdu: List[int]) -> Tuple[List[int], int, int]:
        """Legacy pyscard interface - delegates to send_apdu."""
        return self.send_apdu(apdu, use_escape=False)
    
    def _handle_iso_command(self, apdu: List[int]) -> Tuple[List[int], int, int]:
        """Handle ISO 7816-4 commands (CLA=00)."""
        if len(apdu) < 4:
            return [], 0x6D, 0x00
        
        cla, ins, p1, p2 = apdu[0], apdu[1], apdu[2], apdu[3]
        
        # Parse Lc and data
        lc = apdu[4] if len(apdu) > 4 else 0
        data = bytes(apdu[5:5+lc]) if lc > 0 else b""
        
        # ISOSelectFile (00 A4)
        if ins == 0xA4:
            return self._handle_iso_select_file(p1, p2, data)
        
        # ISOReadBinary (00 B0)
        if ins == 0xB0:
            return self._handle_iso_read_binary(p1, p2, apdu)
        
        # ISOUpdateBinary (00 D6)
        if ins == 0xD6:
            return self._handle_iso_update_binary(p1, p2, data)
        
        # Unknown ISO command
        return [], 0x6D, 0x00
    
    def _handle_iso_select_file(self, p1: int, p2: int, data: bytes) -> Tuple[List[int], int, int]:
        """Handle ISOSelectFile (00 A4)."""
        # P1=0x02: Select EF under current DF, by file identifier
        # P1=0x04: Select by DF name
        # P1=0x00: Select by file identifier
        
        # First, check if selecting PICC application
        if p1 == 0x04 and len(data) >= 7:
            # Check if it's the PICC application DF name: D2760000850101h
            df_name = data[:7]
            if df_name == bytes([0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01]):
                self.picc_app_selected = True
                self.selected_file = None  # Clear file selection
                return [], *STATUS_SUCCESS
        
        # Select EF by file ID
        if p1 == 0x02 or p1 == 0x00:
            # Check if file ID matches NDEF file (E104h)
            if len(data) >= 2 and list(data[:2]) == NDEF_FILE_ID:
                if self.picc_app_selected:
                    self.selected_file = 0xE104  # NDEF file selected
                    return [], *STATUS_SUCCESS
                else:
                    # Application must be selected first
                    return [], *SW_CONDITIONS_NOT_SATISFIED
        
        # File not found
        return [], *SW_FILE_NOT_FOUND
    
    def _handle_iso_read_binary(self, p1: int, p2: int, apdu: List[int]) -> Tuple[List[int], int, int]:
        """Handle ISOReadBinary (00 B0)."""
        # Check if file is selected
        if self.selected_file != 0xE104:
            # No file selected - conditions not satisfied
            return [], *SW_CONDITIONS_NOT_SATISFIED
        
        # Parse offset and length
        if len(apdu) < 5:
            return [], *SW_LENGTH_ERROR
        
        # P1[7]=0: P1-P2 encodes 15-bit offset
        # P1[7]=1: P1[4:0] is file ID, P2 is offset
        if p1 & 0x80:
            # File ID mode - not supported for reading (matches real tag behavior)
            return [], *SW_FILE_NOT_FOUND
        
        # Offset mode
        offset = ((p1 & 0x7F) << 8) | p2
        le = apdu[4] if len(apdu) > 4 else 0
        
        if le == 0:
            le = 256  # Read all
        
        # Read from NDEF file
        read_length = min(le, len(self.ndef_file_data) - offset)
        if offset >= len(self.ndef_file_data):
            return [], 0x91, 0xBE  # BOUNDARY_ERROR
        
        read_data = self.ndef_file_data[offset:offset+read_length]
        return list(read_data), *STATUS_SUCCESS
    
    def _handle_iso_update_binary(self, p1: int, p2: int, data: bytes) -> Tuple[List[int], int, int]:
        """Handle ISOUpdateBinary (00 D6)."""
        # Check if file is selected
        if self.selected_file != 0xE104:
            # No file selected - conditions not satisfied
            return [], *SW_CONDITIONS_NOT_SATISFIED
        
        # Parse offset
        if p1 & 0x80:
            # File ID mode - not supported for writing (matches real tag behavior)
            return [], *SW_FILE_NOT_FOUND
        
        # Offset mode
        offset = ((p1 & 0x7F) << 8) | p2
        
        # Write to NDEF file
        if offset + len(data) > len(self.ndef_file_data):
            return [], 0x91, 0xBE  # BOUNDARY_ERROR
        
        # Update file data
        file_bytes = bytearray(self.ndef_file_data)
        file_bytes[offset:offset+len(data)] = data
        self.ndef_file_data = bytes(file_bytes)
        
        return [], *STATUS_SUCCESS
    
    def _handle_proprietary_command(self, apdu: List[int]) -> Tuple[List[int], int, int]:
        """Handle proprietary NTAG424 commands (CLA=90)."""
        if len(apdu) < 4:
            return [], 0x6D, 0x00
        
        cla, ins, p1, p2 = apdu[0], apdu[1], apdu[2], apdu[3]
        lc = apdu[4] if len(apdu) > 4 else 0
        data = bytes(apdu[5:5+lc]) if lc > 0 else b""
        
        # AuthenticateEV2First
        if ins == 0x71:
            key_no = data[0] if len(data) > 0 else 0
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

        # ReadBinary with CLA=90 - should fail with length error (matches real tag)
        if ins == 0xB0:
            return [], *SW_LENGTH_ERROR
        
        # UpdateBinary with CLA=90 - should fail with length error (matches real tag)
        if ins == 0xD6:
            return [], *SW_LENGTH_ERROR
        
        # ReadData (90 BD) - not implemented, returns illegal command
        if ins == 0xBD:
            return [], *SW_ILLEGAL_COMMAND

        # All other authenticated commands must be authenticated
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
