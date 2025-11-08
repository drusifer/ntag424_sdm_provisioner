"""
NTAG424 DNA Cryptographic Primitives.

Verified implementations of crypto operations per NXP specifications (AN12196, AN12343).
These functions have been tested against official NXP test vectors and match exactly.

All functions follow the NTAG424 DNA / MIFARE DESFire EV2 specifications.
"""

import zlib
from Crypto.Cipher import AES
from Crypto.Hash import CMAC


def calculate_iv_for_command(ti: bytes, cmd_ctr: int, session_enc_key: bytes) -> bytes:
    """
    Calculate IV for command encryption per NXP spec.
    
    IV = E(KSesAuthENC, zero_iv, A5 5A || TI || CmdCtr || 0x00*8)
    
    Args:
        ti: Transaction Identifier (4 bytes)
        cmd_ctr: Command counter (0-65535)
        session_enc_key: Session encryption key (16 bytes)
    
    Returns:
        Encrypted IV (16 bytes)
        
    Reference:
        AN12196 Table 26, Step 12
        AN12343 Table 40, Row 18
    """
    # Build plaintext IV: A5 5A || TI || CmdCtr || zeros
    plaintext_iv = bytearray(16)
    plaintext_iv[0] = 0xA5
    plaintext_iv[1] = 0x5A
    plaintext_iv[2:6] = ti
    plaintext_iv[6:8] = cmd_ctr.to_bytes(2, byteorder='little')
    # Rest is zeros
    
    # Encrypt with zero IV
    cipher = AES.new(session_enc_key, AES.MODE_CBC, iv=b'\x00' * 16)
    iv_encrypted = cipher.encrypt(bytes(plaintext_iv))
    
    return iv_encrypted


def encrypt_key_data(key_data: bytes, iv: bytes, session_enc_key: bytes) -> bytes:
    """
    Encrypt key data using AES-CBC.
    
    Args:
        key_data: Plaintext key data (must be multiple of 16 bytes)
        iv: Initialization vector (16 bytes)
        session_enc_key: Session encryption key (16 bytes)
    
    Returns:
        Encrypted data (same length as input)
        
    Reference:
        AN12196 Table 26, Step 13
        AN12343 Table 40, Row 20
    """
    if len(key_data) % 16 != 0:
        raise ValueError(f"key_data must be multiple of 16 bytes, got {len(key_data)}")
    
    cipher = AES.new(session_enc_key, AES.MODE_CBC, iv=iv)
    encrypted = cipher.encrypt(key_data)
    
    return encrypted


def calculate_cmac_full(mac_input: bytes, session_mac_key: bytes) -> bytes:
    """
    Calculate full 16-byte CMAC.
    
    Args:
        mac_input: Data to MAC
        session_mac_key: Session MAC key (16 bytes)
    
    Returns:
        Full CMAC (16 bytes)
        
    Reference:
        AN12196 Table 26, Step 15
    """
    cmac_obj = CMAC.new(session_mac_key, ciphermod=AES)
    cmac_obj.update(mac_input)
    return cmac_obj.digest()


def truncate_cmac(cmac_full: bytes) -> bytes:
    """
    Truncate CMAC to 8 bytes using even-numbered bytes (odd indices).
    
    Per AN12196: "truncated by using only the 8 even-numbered bytes"
    Indices: 1, 3, 5, 7, 9, 11, 13, 15 (0-indexed)
    
    CRITICAL: This is NOT taking the first 8 bytes, but every other byte starting at index 1.
    
    Args:
        cmac_full: Full 16-byte CMAC
    
    Returns:
        Truncated 8-byte CMAC
        
    Reference:
        AN12196 Table 26, Step 16
        NT4H2421Gx datasheet line 852
    """
    if len(cmac_full) != 16:
        raise ValueError(f"cmac_full must be 16 bytes, got {len(cmac_full)}")
    
    # Take odd indices (even-numbered bytes per NXP terminology)
    return bytes([cmac_full[i] for i in range(1, 16, 2)])


def calculate_cmac(cmd: int, cmd_ctr: int, ti: bytes, cmd_header: bytes, 
                   encrypted_data: bytes, session_mac_key: bytes) -> bytes:
    """
    Calculate truncated CMAC for authenticated command.
    
    CMAC input: Cmd || CmdCtr || TI || CmdHeader || EncryptedData
    
    Args:
        cmd: Command byte (e.g., 0xC4 for ChangeKey)
        cmd_ctr: Command counter (0-65535)
        ti: Transaction Identifier (4 bytes)
        cmd_header: Command header data (e.g., KeyNo for ChangeKey)
        encrypted_data: Encrypted command data
        session_mac_key: Session MAC key (16 bytes)
    
    Returns:
        Truncated CMAC (8 bytes)
        
    Reference:
        AN12196 Table 26, Steps 14-16
    """
    # Build CMAC input
    mac_input = bytearray()
    mac_input.append(cmd)
    mac_input.extend(cmd_ctr.to_bytes(2, byteorder='little'))
    mac_input.extend(ti)
    mac_input.extend(cmd_header)
    mac_input.extend(encrypted_data)
    
    # Calculate full CMAC
    cmac_full = calculate_cmac_full(bytes(mac_input), session_mac_key)
    
    # Truncate to 8 bytes
    return truncate_cmac(cmac_full)


def build_key_data(key_no: int, new_key: bytes, old_key: bytes, version: int) -> bytes:
    """
    Build 32-byte key data for ChangeKey command.
    
    Format per NXP spec:
    - Key 0: NewKey(16) + Version(1) + 0x80 + padding(14) = 32 bytes
    - Others: XOR(16) + Version(1) + CRC32(4) + 0x80 + padding(10) = 32 bytes
    
    Args:
        key_no: Key number (0-4)
        new_key: New key value (16 bytes)
        old_key: Old key value (16 bytes, or None for key 0)
        version: Key version (0-255)
    
    Returns:
        32-byte key data ready for encryption
        
    Reference:
        AN12196 Table 26, Step 11
        AN12343 Table 40, Row 16
        MFRC522_NTAG424DNA.cpp lines 1047-1064
    """
    if len(new_key) != 16:
        raise ValueError(f"new_key must be 16 bytes, got {len(new_key)}")
    
    key_data = bytearray(32)
    
    if key_no == 0:
        # Key 0 format: NewKey(16) + Version(1) + 0x80 + padding(14)
        key_data[0:16] = new_key
        key_data[16] = version
        key_data[17] = 0x80
        # Rest is already zeros (14 bytes)
    else:
        # Other keys format: XOR(16) + Version(1) + CRC32(4) + 0x80 + padding(10)
        if old_key is None:
            old_key = bytes(16)
        if len(old_key) != 16:
            raise ValueError(f"old_key must be 16 bytes, got {len(old_key)}")
        
        # XOR new and old keys
        xored = bytes(a ^ b for a, b in zip(new_key, old_key))
        
        # CRC32 of new key, inverted per Arduino
        crc = zlib.crc32(new_key) ^ 0xFFFFFFFF
        crc_bytes = crc.to_bytes(4, byteorder='little')
        
        key_data[0:16] = xored
        key_data[16] = version
        key_data[17:21] = crc_bytes
        key_data[21] = 0x80
        # Rest is already zeros (10 bytes)
    
    return bytes(key_data)


def build_changekey_apdu(key_no: int, new_key: bytes, old_key: bytes, version: int,
                        ti: bytes, cmd_ctr: int, session_enc_key: bytes, 
                        session_mac_key: bytes) -> list[int]:
    """
    Build complete ChangeKey APDU with encryption and CMAC.
    
    Args:
        key_no: Key number to change (0-4)
        new_key: New key value (16 bytes)
        old_key: Old key value (16 bytes, or None for key 0)
        version: New key version (0-255)
        ti: Transaction Identifier (4 bytes)
        cmd_ctr: Command counter (0-65535)
        session_enc_key: Session encryption key (16 bytes)
        session_mac_key: Session MAC key (16 bytes)
    
    Returns:
        Complete APDU as list of integers
        
    Reference:
        AN12196 Table 26 (complete example)
    """
    # Build 32-byte key data
    key_data = build_key_data(key_no, new_key, old_key, version)
    
    # Calculate IV
    iv = calculate_iv_for_command(ti, cmd_ctr, session_enc_key)
    
    # Encrypt key data
    encrypted = encrypt_key_data(key_data, iv, session_enc_key)
    
    # Calculate CMAC
    cmd_header = bytes([key_no])
    cmac = calculate_cmac(0xC4, cmd_ctr, ti, cmd_header, encrypted, session_mac_key)
    
    # Build APDU: CLA CMD P1 P2 Lc KeyNo Encrypted(32) CMAC(8) Le
    apdu = [
        0x90,           # CLA
        0xC4,           # CMD (ChangeKey)
        0x00,           # P1
        0x00,           # P2
        0x29,           # Lc (41 bytes: KeyNo + Encrypted + CMAC)
        key_no,         # KeyNo
        *list(encrypted),  # Encrypted data (32 bytes)
        *list(cmac),       # CMAC (8 bytes)
        0x00            # Le
    ]
    
    return apdu

