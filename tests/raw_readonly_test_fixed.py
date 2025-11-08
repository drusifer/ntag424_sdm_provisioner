"""
RAW PYSCARD TEST - with CORRECT session key derivation per datasheet.

Implements the CORRECT 32-byte SV formula from NXP datasheet Section 9.1.7:
SV1 = A5||5A||00||01||00||80||RndA[15..14]||(RndA[13..8] XOR RndB[15..10])||RndB[9..0]||RndA[7..0]
"""

import os
from smartcard.System import readers
from smartcard.util import toHexString
from Crypto.Cipher import AES
from Crypto.Hash import CMAC

# Import ONLY crypto_primitives for CMAC calculation
from ntag424_sdm_provisioner.crypto.crypto_primitives import calculate_cmac


def derive_session_keys_correct(key: bytes, rnda: bytes, rndb: bytes) -> tuple:
    """
    Derive session keys using CORRECT 32-byte SV formula from datasheet.
    
    Per NXP NT4H2421Gx Section 9.1.7:
    SV1 = A5||5A||00||01||00||80||RndA[15..14]||(RndA[13..8] XOR RndB[15..10])||RndB[9..0]||RndA[7..0]
    SV2 = 5A||A5||00||01||00||80||RndA[15..14]||(RndA[13..8] XOR RndB[15..10])||RndB[9..0]||RndA[7..0]
    
    Returns:
        (session_enc_key, session_mac_key)
    """
    # Build 32-byte SV1
    sv1 = bytearray(32)
    sv1[0] = 0xA5
    sv1[1] = 0x5A
    sv1[2] = 0x00
    sv1[3] = 0x01
    sv1[4] = 0x00
    sv1[5] = 0x80
    sv1[6:8] = rnda[0:2]           # RndA[15..14] (first 2 bytes)
    sv1[8:14] = rndb[0:6]          # RndB[15..10] (first 6 bytes)
    sv1[14:24] = rndb[6:16]        # RndB[9..0] (last 10 bytes)
    sv1[24:32] = rnda[8:16]        # RndA[7..0] (last 8 bytes)
    
    # XOR: RndA[13..8] with RndB[15..10]
    for i in range(6):
        sv1[8 + i] ^= rnda[2 + i]
    
    # Build 32-byte SV2 (same structure, different label)
    sv2 = bytearray(sv1)
    sv2[0] = 0x5A
    sv2[1] = 0xA5
    
    print(f"  SV1 (32 bytes): {bytes(sv1).hex()}")
    print(f"  SV2 (32 bytes): {bytes(sv2).hex()}")
    
    # Calculate session keys
    cmac_enc = CMAC.new(key, ciphermod=AES)
    cmac_enc.update(bytes(sv1))
    session_enc_key = cmac_enc.digest()
    
    cmac_mac = CMAC.new(key, ciphermod=AES)
    cmac_mac.update(bytes(sv2))
    session_mac_key = cmac_mac.digest()
    
    return session_enc_key, session_mac_key


def test_with_correct_derivation():
    """Test GetKeyVersion with CORRECT session key derivation."""
    
    print("\n" + "="*70)
    print("RAW PYSCARD - CORRECT SESSION KEY DERIVATION")
    print("="*70)
    print()
    
    connection = readers()[0].createConnection()
    connection.connect()
    
    # Select PICC
    apdu = [0x00, 0xA4, 0x04, 0x00, 0x07, 0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    if (sw1, sw2) != (0x90, 0x00):
        return False
    print("Select PICC: [OK]\n")
    
    # Authenticate
    print("Authenticate:")
    factory_key = bytes(16)
    
    # Phase 1
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
    
    # Phase 2
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
    print("  Auth: [OK]\n")
    
    # Derive session keys with CORRECT formula
    print("Session Key Derivation (CORRECT 32-byte SV):")
    session_enc_key, session_mac_key = derive_session_keys_correct(factory_key, rnda, rndb)
    
    print(f"  Session ENC: {session_enc_key.hex()}")
    print(f"  Session MAC: {session_mac_key.hex()}\n")
    
    # GetKeyVersion
    print("GetKeyVersion:")
    cmd = 0x64
    cmd_ctr = 0
    key_no = 0
    
    cmac_truncated = calculate_cmac(
        cmd=cmd,
        cmd_ctr=cmd_ctr,
        ti=ti,
        cmd_header=bytes([key_no]),
        encrypted_data=b'',
        session_mac_key=session_mac_key
    )
    
    print(f"  CMAC: {cmac_truncated.hex()}")
    
    apdu = [0x90, cmd, 0x00, 0x00, 0x09, key_no, *list(cmac_truncated), 0x00]
    print(f"  APDU: {toHexString(apdu)}\n")
    
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"  Response: SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) == (0x91, 0x00):
        print("\n" + "="*70)
        print("SUCCESS! GETKEYVERSION WORKED!")
        print("="*70)
        print("\nThe bug was in session key derivation!")
        print("We were using 8-byte SV, should be 32-byte SV with XOR.")
        return True
    else:
        print(f"\n[FAILED] {sw1:02X}{sw2:02X}")
        return False


if __name__ == '__main__':
    success = test_with_correct_derivation()
    exit(0 if success else 1)

