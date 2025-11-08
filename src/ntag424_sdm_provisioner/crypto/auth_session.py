# file: ntag424_sdm_provisioner/crypto/auth_session.py

import logging
from Crypto.Cipher import AES
from Crypto.Hash import CMAC
from Crypto.Random import get_random_bytes
from typing import Tuple

from ntag424_sdm_provisioner.constants import AuthSessionKeys, AuthenticationResponse

from ntag424_sdm_provisioner.commands.sdm_commands import (
    AuthenticateEV2First,
    AuthenticateEV2Second
)
from ntag424_sdm_provisioner.commands.base import AuthenticationError
from ntag424_sdm_provisioner.hal import NTag424CardConnection

# Import verified crypto primitives - ALL auth crypto now uses these verified functions
from ntag424_sdm_provisioner.crypto.crypto_primitives import (
    derive_session_keys,
    calculate_iv_for_command,
    decrypt_rndb,
    rotate_left,
    encrypt_auth_response,
    decrypt_auth_response
)

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
        log.info("="*70)
        log.info("[NEW SESSION CREATED]")
        log.info(f"  Ti: {self.session_keys.ti.hex()}")
        log.info(f"  Counter: {self.session_keys.cmd_counter}")
        log.info(f"  Session ENC: {self.session_keys.session_enc_key.hex()}")
        log.info(f"  Session MAC: {self.session_keys.session_mac_key.hex()}")
        log.info("="*70)
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
        log.debug(f"Using authentication key: {self.key.hex().upper()}")
        
        cmd = AuthenticateEV2First(key_no=key_no)
        log.debug(f"Sending AuthenticateEV2First command: {cmd}")
        
        try:
            response = cmd.execute(connection)
            log.debug(f"Received encrypted RndB: {response.challenge.hex()}")
            log.debug(f"Challenge length: {len(response.challenge)} bytes")
            return response.challenge
        except Exception as e:
            log.error(f"Phase 1 failed: {e}")
            log.error(f"Key used: {self.key.hex().upper()}")
            log.error(f"Key number: {key_no}")
            raise
    
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
        
        # 2. Rotate RndB using verified crypto_primitives
        rndb_rotated = rotate_left(rndb)
        log.debug(f"[crypto_primitives] rotate_left(RndB): {rndb_rotated.hex()}")
        
        # 3. Generate random RndA
        rnda = get_random_bytes(16)
        log.debug(f"Generated RndA: {rnda.hex()}")
        
        # 4. Encrypt RndA + RndB_rotated and send to card
        response_data = self._encrypt_response(rnda, rndb_rotated)
        
        cmd = AuthenticateEV2Second(data_to_card=response_data)
        encrypted_response = cmd.execute(connection)
        
        # 5. Parse and decrypt the card's response
        auth_response = self._parse_card_response(encrypted_response, rnda)
        
        # 6. Verify RndA' matches expected rotation
        expected_rnda_rotated = rotate_left(rnda)
        if auth_response.rnda_rotated != expected_rnda_rotated:
            raise AuthenticationError(f"RndA' verification failed. Expected: {expected_rnda_rotated.hex()}, Got: {auth_response.rnda_rotated.hex()}")
        
        log.debug(f"✅ RndA' verification successful")
        log.debug(f"Card response: {auth_response}")
        
        # 7. Derive session keys using actual Ti from card
        session_keys = self._derive_session_keys(rnda, rndb, auth_response.ti)
        
        return session_keys
    
    def _decrypt_rndb(self, encrypted_rndb: bytes) -> bytes:
        """
        Decrypt RndB received from card using verified crypto_primitives.
        
        Args:
            encrypted_rndb: 16 bytes encrypted challenge
        
        Returns:
            Decrypted RndB (16 bytes)
        """
        result = decrypt_rndb(encrypted_rndb, self.key)
        log.debug(f"[crypto_primitives] decrypt_rndb: {encrypted_rndb.hex()} -> {result.hex()}")
        return result
    
    def _encrypt_response(self, rnda: bytes, rndb_rotated: bytes) -> bytes:
        """
        Encrypt authentication response (RndA + RndB') using verified crypto_primitives.
        
        Args:
            rnda: 16-byte random A generated by reader
            rndb_rotated: 16-byte rotated RndB
        
        Returns:
            Encrypted 32-byte response
        """
        result = encrypt_auth_response(rnda, rndb_rotated, self.key)
        log.debug(f"[crypto_primitives] encrypt_auth_response: {len(result)} bytes")
        return result
    
    def _parse_card_response(self, encrypted_response: bytes, rnda: bytes) -> AuthenticationResponse:
        """
        Parse and decrypt the card's authentication response.
        
        The card responds with: E(Kx, Ti || RndA' || PDcap || PCDcap)
        
        Args:
            encrypted_response: Encrypted response from card
            rnda: Original RndA for verification
        
        Returns:
            Parsed authentication response
        
        Raises:
            AuthenticationError: If response parsing fails
        """
        log.debug(f"Parsing card response: {encrypted_response.hex()}")
        
        # Decrypt using verified crypto_primitives
        decrypted_response = decrypt_auth_response(encrypted_response, self.key)
        log.debug(f"[crypto_primitives] decrypt_auth_response: {decrypted_response.hex()}")
        
        # Parse the response structure
        # Format: Ti (4 bytes) || RndA' (16 bytes) || PDcap2 (6 bytes) || PCDcap2 (6 bytes)
        if len(decrypted_response) < 32:  # Expected: Ti(4) + RndA'(16) + PDcap2(6) + PCDcap2(6)
            raise AuthenticationError(f"Card response too short: {len(decrypted_response)} bytes")
        
        ti = decrypted_response[0:4]
        rnda_rotated = decrypted_response[4:20]
        pdcap2 = decrypted_response[20:26]
        pcdcap2 = decrypted_response[26:32]
        
        log.debug(f"Parsed - Ti: {ti.hex()}, RndA': {rnda_rotated.hex()}")
        log.debug(f"Parsed - PDcap2: {pdcap2.hex()}, PCDcap2: {pcdcap2.hex()}")
        
        return AuthenticationResponse(
            ti=ti,
            rnda_rotated=rnda_rotated,
            pdcap=pdcap2,
            pcdcap=pcdcap2
        )
    
    def _derive_session_keys(self, rnda: bytes, rndb: bytes, ti: bytes) -> AuthSessionKeys:
        """
        Derive session encryption and MAC keys from RndA, RndB, and Ti.
        
        Delegates to crypto_primitives.derive_session_keys() which implements
        the correct 32-byte SV formula per NXP datasheet Section 9.1.7.
        
        Args:
            rnda: Random A (16 bytes)
            rndb: Random B (16 bytes)
            ti: Transaction Identifier from card response (4 bytes)
        
        Returns:
            AuthSessionKeys dataclass with derived keys
        """
        # Use verified crypto_primitives implementation
        session_enc_key, session_mac_key = derive_session_keys(self.key, rnda, rndb)
        
        log.debug(f"[crypto_primitives] derive_session_keys:")
        log.debug(f"  Auth key: {self.key.hex()}")
        log.debug(f"  RndA: {rnda.hex()}")
        log.debug(f"  RndB: {rndb.hex()}")
        log.debug(f"  -> Session ENC: {session_enc_key.hex()}")
        log.debug(f"  -> Session MAC: {session_mac_key.hex()}")
        log.debug(f"  Using Ti from card: {ti.hex()}")
        
        return AuthSessionKeys(
            session_enc_key=session_enc_key,
            session_mac_key=session_mac_key,
            ti=ti,  # Use actual Ti from card response
            cmd_counter=0
        )
    
    def apply_cmac(self, cmd_header: bytes, cmd_data: bytes) -> bytes:
        """
        Apply CMAC to command data for authenticated commands.
        
        Per AN12196 and NXP datasheet:
        CMAC is calculated over: Cmd || CmdCounter || TI || CmdHeader || CmdData
        
        Args:
            cmd_header: 4-byte APDU command header [CLA INS P1 P2]
                       (INS byte will be extracted as native Cmd)
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
        
        # Build data to MAC: Cmd || CmdCtr || TI || CmdHeader || CmdData
        # Per AN12196: "Cmd" is the native command byte (INS), not full APDU header!
        native_cmd = cmd_header[1]  # Extract INS byte from [CLA, INS, P1, P2]
        cmd_ctr_bytes = self.session_keys.cmd_counter.to_bytes(2, 'little')
        ti = self.session_keys.ti
        
        # CmdHeader in CMAC is the command-specific header (e.g., FileNo, KeyNo)
        # which is already in cmd_data, so we don't include full APDU header
        data_to_mac = bytes([native_cmd]) + cmd_ctr_bytes + ti + cmd_data
        
        log.debug(f"CMAC input (counter={self.session_keys.cmd_counter}): {data_to_mac.hex()}")
        
        # Calculate CMAC using session MAC key
        cmac = CMAC.new(self.session_keys.session_mac_key, ciphermod=AES)
        cmac.update(data_to_mac)
        mac_full = cmac.digest()  # 16 bytes
        
        # Truncate to 8 bytes using EVEN-NUMBERED bytes (indices 1,3,5,7,9,11,13,15)
        # Per NXP NT4H2421Gx datasheet line 852:
        # "The MAC used in NT4H2421Gx is truncated by using only the 8 even-numbered bytes"
        # This applies to ALL CMAC calculations in NTAG424 DNA
        mac_truncated = bytes([mac_full[i] for i in range(1, 16, 2)])
        
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
        Derive IV for encryption/decryption using verified crypto_primitives.
        
        Per NXP spec: IV = Enc(K, A55A || Ti || CmdCtr || 0x00...)
        
        Returns:
            16-byte IV
        """
        iv = calculate_iv_for_command(
            self.session_keys.ti,
            self.session_keys.cmd_counter,
            self.session_keys.session_enc_key
        )
        log.debug(f"[crypto_primitives] calculate_iv (ctr={self.session_keys.cmd_counter}): {iv.hex()}")
        return iv
    
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