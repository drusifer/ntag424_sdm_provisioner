"""
RAW PYSCARD - ChangeKey with CORRECT session key derivation.

Uses fixed 32-byte SV formula from datasheet.
"""

import os
from smartcard.System import readers
from smartcard.util import toHexString
from Crypto.Cipher import AES
from Crypto.Hash import CMAC

from ntag424_sdm_provisioner.crypto.crypto_primitives import (
    build_key_data,
    calculate_iv_for_command,
    encrypt_key_data,
    calculate_cmac
)


def derive_session_keys_correct(key: bytes, rnda: bytes, rndb: bytes) -> tuple:
    """Derive session keys using CORRECT 32-byte SV formula."""
    
    # Build 32-byte SV1 per datasheet
    sv1 = bytearray(32)
    sv1[0] = 0xA5
    sv1[1] = 0x5A
    sv1[2:6] = b'\x00\x01\x00\x80'
    sv1[6:8] = rnda[0:2]           # RndA[15..14]
    sv1[8:14] = rndb[0:6]          # RndB[15..10]
    sv1[14:24] = rndb[6:16]        # RndB[9..0]
    sv1[24:32] = rnda[8:16]        # RndA[7..0]
    
    # XOR: RndA[13..8] with RndB[15..10]
    for i in range(6):
        sv1[8 + i] ^= rnda[2 + i]
    
    # Build SV2
    sv2 = bytearray(sv1)
    sv2[0] = 0x5A
    sv2[1] = 0xA5
    
    # Calculate session keys
    cmac_enc = CMAC.new(key, ciphermod=AES)
    cmac_enc.update(bytes(sv1))
    session_enc_key = cmac_enc.digest()
    
    cmac_mac = CMAC.new(key, ciphermod=AES)
    cmac_mac.update(bytes(sv2))
    session_mac_key = cmac_mac.digest()
    
    return session_enc_key, session_mac_key


def test_changekey_with_correct_keys():
    """Test ChangeKey with CORRECT session keys."""
    
    print("\n" + "="*70)
    print("RAW PYSCARD - CHANGEKEY WITH FIXED SESSION KEYS")
    print("="*70)
    print()
    
    connection = readers()[0].createConnection()
    connection.connect()
    
    # Select PICC
    apdu = [0x00, 0xA4, 0x04, 0x00, 0x07, 0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    if (sw1, sw2) != (0x90, 0x00):
        return False
    print("Select: [OK]\n")
    
    # Authenticate
    print("Authenticate:")
    factory_key = bytes(16)
    
    apdu = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    if (sw1, sw2) != (0x91, 0xAF):
        return False
    
    encrypted_rndb = bytes(response[:16])
    cipher = AES.new(factory_key, AES.MODE_CBC, iv=b'\x00'*16)
    rndb = cipher.decrypt(encrypted_rndb)
    rndb_rotated = rndb[1:] + rndb[:1]
    rnda = os.urandom(16)
    
    print(f"  RndA: {rnda.hex()}")
    print(f"  RndB: {rndb.hex()}")
    
    plaintext = rnda + rndb_rotated
    cipher = AES.new(factory_key, AES.MODE_CBC, iv=b'\x00'*16)
    encrypted = cipher.encrypt(plaintext)
    
    apdu = [0x90, 0xAF, 0x00, 0x00, 0x20, *list(encrypted), 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    if (sw1, sw2) != (0x91, 0x00):
        return False
    
    cipher = AES.new(factory_key, AES.MODE_CBC, iv=b'\x00'*16)
    response_dec = cipher.decrypt(bytes(response))
    ti = response_dec[0:4]
    
    print(f"  Ti: {ti.hex()}")
    print("  [OK]\n")
    
    # Derive with CORRECT formula
    print("Session Keys (CORRECT formula):")
    session_enc_key, session_mac_key = derive_session_keys_correct(factory_key, rnda, rndb)
    print(f"  ENC: {session_enc_key.hex()}")
    print(f"  MAC: {session_mac_key.hex()}\n")
    
    # ChangeKey(0, factory -> factory)
    print("ChangeKey(0, factory -> factory):")
    
    key_data = build_key_data(0, factory_key, None, 0x00)
    print(f"  Key data: {key_data.hex()}")
    
    iv = calculate_iv_for_command(ti, 0, session_enc_key)
    print(f"  IV: {iv.hex()}")
    
    encrypted = encrypt_key_data(key_data, iv, session_enc_key)
    print(f"  Encrypted: {encrypted.hex()}")
    
    cmac_truncated = calculate_cmac(
        cmd=0xC4,
        cmd_ctr=0,
        ti=ti,
        cmd_header=bytes([0]),
        encrypted_data=encrypted,
        session_mac_key=session_mac_key
    )
    print(f"  CMAC: {cmac_truncated.hex()}")
    
    apdu = [
        0x90, 0xC4, 0x00, 0x00, 0x29,
        0x00,
        *list(encrypted),
        *list(cmac_truncated),
        0x00
    ]
    
    print(f"\n  APDU: {toHexString(apdu[:20])}...\n")
    
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"  Response: SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) == (0x91, 0x00):
        print("\n" + "="*70)
        print("SUCCESS! CHANGEKEY WORKED!")
        print("="*70)
        print("\nKey 0 changed to factory (same value)")
        print("Tag is ready for provisioning!")
        return True
    else:
        print(f"\n[FAILED] {sw1:02X}{sw2:02X}")
        return False


if __name__ == '__main__':
    success = test_changekey_with_correct_keys()
    exit(0 if success else 1)

