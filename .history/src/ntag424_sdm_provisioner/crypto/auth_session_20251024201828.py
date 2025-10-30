# file: ntag424_sdm_provisioner/crypto/auth_session.py

import logging
from Crypto.Cipher import AES
from Crypto.Hash import CMAC
from Crypto.Random import get_random_bytes
from typing import Tuple

from ntag424_sdm_provisioner.constants import AuthSessionKeys

from ntag424_sdm_provisioner.commands.sdm_commands import (
    AuthenticateEV2First,
    AuthenticateEV2Second
)
from ntag424_sdm_provisioner.hal import NTag424CardConnection

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class Ntag424AuthSession:
    """
    Handles EV2 authentication and session key management for NTAG424 DNA.
    
    Manages the two-phase authentication protocol and derives session keys
    for subsequent encrypted/MACed commands.
    """
    
    def __init__(self, key: bytes):
        """
        Initialize authentication session.
        
        Args:
            key: 16-byte AES-128 key (factory default = all zeros)
        
        Raises:
            ValueError: If key is not 16 bytes
        """
        if len(key) != 16:
            raise ValueError("Key must be 16 bytes (AES-128)")
        
        self.key = key
        self.session_keys: AuthSessionKeys = None
        self.authenticated = False
    
    def authenticate(
        self, 
        connection: NTag424CardConnection, 
        key_no: int = 0
    ) -> AuthSessionKeys:
        """
        Perform complete EV2 authentication (both phases).
        
        Args:
            connection: Active card connection
            key_no: Key number to authenticate with (0-4)
        
        Returns:
            AuthSessionKeys with derived session keys
        
        Raises:
            ApduError: If authentication fails
        """
        log.info(f"Starting EV2 authentication with key {key_no:02X}")
        
        # Phase 1: Get encrypted RndB from card
        encrypted_rndb = self._phase1_get_challenge(connection, key_no)
        
        # Phase 2: Complete authentication and derive keys
        self.session_keys = self._phase2_authenticate(connection, encrypted_rndb)
        
        self.authenticated = True
        log.info("✅ Authentication successful")
        log.debug(f"{self.session_keys}")
        
        return self.session_keys
    
    def _phase1_get_challenge(
        self, 
        connection: NTag424CardConnection, 
        key_no: int
    ) -> bytes:
        """
        Phase 1: Send authentication request and get encrypted RndB.
        
        Args:
            connection: Card connection
            key_no: Key number to use
        
        Returns:
            Encrypted RndB (16 bytes)
        """
        log.debug(f"Phase 1: Requesting challenge for key {key_no:02X}")
        
        cmd = AuthenticateEV2First(key_no=key_no)
        response = cmd.execute(connection)
        
        log.debug(f"Received encrypted RndB: {response.challenge.hex()}")
        return response.challenge
    
    def _phase2_authenticate(
        self, 
        connection: NTag424CardConnection,
        encrypted_rndb: bytes
    ) -> AuthSessionKeys:
        """
        Phase 2: Decrypt RndB, generate RndA, authenticate, derive keys.
        
        Args:
            connection: Card connection
            encrypted_rndb: 16-byte encrypted challenge from card
        
        Returns:
            Derived session keys
        """
        log.debug("Phase 2: Processing challenge and deriving keys")
        
        # 1. Decrypt RndB from card
        rndb = self._decrypt_rndb(encrypted_rndb)
        log.debug(f"Decrypted RndB: {rndb.hex()}")
        
        # 2. Rotate RndB (left shift 1 byte)
        rndb_rotated = rndb[1:] + rndb[0:1]
        
        # 3. Generate random RndA
        rnda = get_random_bytes(16)
        log.debug(f"Generated RndA: {rnda.hex()}")
        
        # 4. Encrypt RndA + RndB_rotated and send to card
        response_data = self._encrypt_response(rnda, rndb_rotated)
        
        cmd = AuthenticateEV2Second(data_to_card=response_data)
        cmd.execute(connection)
        
        # Note: Card responds with encrypted(Ti || RndA' || PDcap || PCDcap)
        # For basic implementation, we derive keys from RndA and RndB only
        # Full implementation would parse the response and verify RndA'
        
        # 5. Derive session keys
        session_keys = self._derive_session_keys(rnda, rndb)
        
        return session_keys
    
    def _decrypt_rndb(self, encrypted_rndb: bytes) -> bytes:
        """
        Decrypt RndB received from card.
        
        Args:
            encrypted_rndb: 16 bytes encrypted challenge
        
        Returns:
            Decrypted RndB (16 bytes)
        """
        cipher = AES.new(self.key, AES.MODE_CBC, iv=b'\x00' * 16)
        return cipher.decrypt(encrypted_rndb)
    
    def _encrypt_response(self, rnda: bytes, rndb_rotated: bytes) -> bytes:
        """
        Encrypt authentication response (RndA + RndB').
        
        Args:
            rnda: 16-byte random A generated by reader
            rndb_rotated: 16-byte rotated RndB
        
        Returns:
            Encrypted 32-byte response
        """
        plaintext = rnda + rndb_rotated
        cipher = AES.new(self.key, AES.MODE_CBC, iv=b'\x00' * 16)
        return cipher.encrypt(plaintext)
    
    def _derive_session_keys(self, rnda: bytes, rndb: bytes) -> AuthSessionKeys:
        """
        Derive session encryption and MAC keys from RndA and RndB.
        
        Uses NTAG424 DNA key derivation as per NXP spec:
        - SV1 = 0xA5 5A 00 01 00 80 || RndA[0:2]
        - SV2 = 0x5A A5 00 01 00 80 || RndA[0:2]
        
        Args:
            rnda: Random A (16 bytes)
            rndb: Random B (16 bytes)
        
        Returns:
            AuthSessionKeys dataclass with derived keys
        """
        # Session Encryption Key derivation
        sv1 = b'\xA5\x5A\x00\x01\x00\x80' + rnda[0:2]
        cmac_enc = CMAC.new(self.key, cipher_mode=AES)
        cmac_enc.update(sv1 + b'\x00' * 8)
        session_enc_key = cmac_enc.digest()
        
        # Session MAC Key derivation
        sv2 = b'\x5A\xA5\x00\x01\x00\x80' + rnda[0:2]
        cmac_mac = CMAC.new(self.key, cipher_mode=AES)
        cmac_mac.update(sv2 + b'\x00' * 8)
        session_mac_key = cmac_mac.digest()
        
        # Transaction Identifier (TI) - simplified version
        # Full implementation would get this from card response
        ti = rnda[0:4]
        
        log.debug(f"Session ENC key: {session_enc_key.hex()}")
        log.debug(f"Session MAC key: {session_mac_key.hex()}")
        
        return AuthSessionKeys(
            session_enc_key=session_enc_key,
            session_mac_key=session_mac_key,
            ti=ti,
            cmd_counter=0
        )
    
    def apply_cmac(self, cmd_header: bytes, cmd_data: bytes) -> bytes:
        """
        Apply CMAC to command data for authenticated commands.
        
        CMAC is calculated over: CmdCounter || CmdHeader || CmdData
        and appended as 8 bytes to the command data.
        
        Args:
            cmd_header: 4-byte command header [CLA INS P1 P2]
            cmd_data: Command data payload (without CMAC)
        
        Returns:
            cmd_data + CMAC (8 bytes appended)
        
        Raises:
            RuntimeError: If not authenticated
        """
        if not self.authenticated or self.session_keys is None:
            raise RuntimeError("Must authenticate before applying CMAC")
        
        # Increment command counter
        self.session_keys.cmd_counter += 1
        
        # Build data to MAC: CmdCounter || CmdHeader || CmdData
        cmd_ctr_bytes = self.session_keys.cmd_counter.to_bytes(2, 'little')
        data_to_mac = cmd_ctr_bytes + cmd_header + cmd_data
        
        log.debug(f"CMAC input (counter={self.session_keys.cmd_counter}): {data_to_mac.hex()}")
        
        # Calculate CMAC using session MAC key
        cmac = CMAC.new(self.session_keys.session_mac_key, cipher_mode=AES)
        cmac.update(data_to_mac)
        mac_full = cmac.digest()  # 16 bytes
        
        # Truncate to 8 bytes (EV2 specification)
        mac_truncated = mac_full[:8]
        
        log.debug(f"CMAC (truncated): {mac_truncated.hex()}")
        
        return cmd_data + mac_truncated
    
    def encrypt_data(self, plaintext: bytes) -> bytes:
        """
        Encrypt data using session encryption key.
        
        Uses AES-128 CBC mode with IV derived from command counter.
        
        Args:
            plaintext: Data to encrypt (will be PKCS7 padded)
        
        Returns:
            Encrypted data
        
        Raises:
            RuntimeError: If not authenticated
        """
        if not self.authenticated or self.session_keys is None:
            raise RuntimeError("Must authenticate before encrypting")
        
        # Derive IV from command counter and TI
        iv = self._derive_iv()
        
        # PKCS7 padding
        padded = self._pkcs7_pad(plaintext)
        
        # Encrypt
        cipher = AES.new(self.session_keys.session_enc_key, AES.MODE_CBC, iv=iv)
        cipher_text = cipher.encrypt(padded)
        
        log.debug(f"Encrypted {len(plaintext)} bytes -> {len(cipher_text)} bytes")
        
        return cipher_text
    
    def decrypt_data(self, cipher_text: bytes) -> bytes:
        """
        Decrypt data using session encryption key.
        
        Args:
            cipher_text: Encrypted data
        
        Returns:
            Decrypted and unpadded plaintext
        
        Raises:
            RuntimeError: If not authenticated
        """
        if not self.authenticated or self.session_keys is None:
            raise RuntimeError("Must authenticate before decrypting")
        
        # Derive IV
        iv = self._derive_iv()
        
        # Decrypt
        cipher = AES.new(self.session_keys.session_enc_key, AES.MODE_CBC, iv=iv)
        padded = cipher.decrypt(cipher_text)
        
        # Remove PKCS7 padding
        plaintext = self._pkcs7_unpad(padded)
        
        log.debug(f"Decrypted {len(cipher_text)} bytes -> {len(plaintext)} bytes")
        
        return plaintext
    
    def _derive_iv(self) -> bytes:
        """
        Derive IV for encryption/decryption from TI and command counter.
        
        Returns:
            16-byte IV
        """
        # Simplified IV derivation
        # Full spec: IV = TI || CmdCounter || 0x00...
        cmd_ctr_bytes = self.session_keys.cmd_counter.to_bytes(2, 'little')
        iv = self.session_keys.ti + cmd_ctr_bytes + b'\x00' * 10
        return iv[:16]
    
    @staticmethod
    def _pkcs7_pad(data: bytes) -> bytes:
        """
        Apply PKCS7 padding to data.
        
        Args:
            data: Data to pad
        
        Returns:
            Padded data (multiple of 16 bytes)
        """
        padding_len = 16 - (len(data) % 16)
        padding = bytes([padding_len] * padding_len)
        return data + padding
    
    @staticmethod
    def _pkcs7_unpad(padded_data: bytes) -> bytes:
        """
        Remove PKCS7 padding from data.
        
        Args:
            padded_data: Padded data
        
        Returns:
            Original data without padding
        
        Raises:
            ValueError: If padding is invalid
        """
        padding_len = padded_data[-1]
        
        # Validate padding
        if padding_len > 16 or padding_len == 0:
            raise ValueError("Invalid PKCS7 padding")
        
        if padded_data[-padding_len:] != bytes([padding_len] * padding_len):
            raise ValueError("Invalid PKCS7 padding bytes")
        
        return padded_data[:-padding_len]