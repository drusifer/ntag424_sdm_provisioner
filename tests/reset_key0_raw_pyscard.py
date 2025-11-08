"""
Reset Key 0 to factory defaults using raw pyscard - exact Arduino replication.

This script manually implements authentication and ChangeKey following
the Arduino MFRC522_NTAG424DNA library exactly.
"""

import os
from smartcard.System import readers
from smartcard.util import toHexString
from Crypto.Cipher import AES
from Crypto.Hash import CMAC


def reset_key0_raw():
    """Reset Key 0 to factory using raw pyscard, following Arduino exactly."""
    
    print("\n" + "="*70)
    print("RESET KEY 0 - RAW PYSCARD (Arduino Method)")
    print("="*70)
    print()
    
    # Get reader
    reader_list = readers()
    if not reader_list:
        print("[ERROR] No readers found!")
        return False
    
    r = reader_list[0]
    print(f"Using reader: {r}\n")
    
    connection = r.createConnection()
    connection.connect()
    
    # Step 1: Select PICC Application
    print("Step 1: Select PICC Application")
    apdu = [0x00, 0xA4, 0x04, 0x00, 0x07, 0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01, 0x00]
    print(f"  >>> {toHexString(apdu)}")
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"  <<< SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) != (0x90, 0x00):
        print(f"  [FAILED]")
        return False
    print("  [OK]\n")
    
    # Step 2: Authenticate EV2 (Arduino DNA_AuthenticateEV2First implementation)
    print("Step 2: Authenticate EV2 with factory key")
    factory_key = bytes(16)  # All zeros
    
    # Phase 1: Request challenge (Arduino line 1457-1468)
    print("  Phase 1: Request challenge...")
    key_no = 0
    apdu = [
        0x90,        # CLA
        0x71,        # CMD (AuthenticateEV2First)
        0x00,        # P1
        0x00,        # P2
        0x02,        # Lc
        key_no,      # KeyNo
        0x00,        # LenCap (0 = no PCDcap2)
        0x00         # Le
    ]
    print(f"    >>> {toHexString(apdu)}")
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"    <<< {len(response)} bytes, SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) != (0x91, 0xAF):
        print(f"    [FAILED] Expected 91AF")
        return False
    
    # Decrypt RndB (Arduino line 60-65)
    encrypted_rndb = bytes(response[:16])
    print(f"    RndB (encrypted): {encrypted_rndb.hex()}")
    
    cipher = AES.new(factory_key, AES.MODE_CBC, iv=b'\x00'*16)
    rndb = cipher.decrypt(encrypted_rndb)
    print(f"    RndB (decrypted): {rndb.hex()}")
    
    # Rotate RndB left (Arduino line 67-73)
    rndb_rotated = rndb[1:] + rndb[:1]
    print(f"    RndB (rotated):   {rndb_rotated.hex()}")
    
    # Generate RndA
    rnda = os.urandom(16)
    print(f"    RndA:             {rnda.hex()}")
    
    # Phase 2: Send RndA || RndB' (Arduino line 76-77, 80-81)
    print("\n  Phase 2: Send response...")
    plaintext = rnda + rndb_rotated  # Arduino line 76-77
    
    # Encrypt with zero IV (Arduino line 80)
    cipher = AES.new(factory_key, AES.MODE_CBC, iv=b'\x00'*16)
    encrypted = cipher.encrypt(plaintext)
    
    # Build APDU (Arduino line 1474-1483)
    apdu = [
        0x90,              # CLA
        0xAF,              # CMD (AuthenticateEV2Second)
        0x00,              # P1
        0x00,              # P2
        0x20,              # Lc (32 bytes)
        *list(encrypted),  # Encrypted RndA || RndB'
        0x00               # Le
    ]
    print(f"    >>> {toHexString(apdu[:10])}... (+ 32 encrypted bytes)")
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"    <<< {len(response)} bytes, SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) != (0x91, 0x00):
        print(f"    [FAILED] Expected 9100")
        return False
    
    # Decrypt response (Arduino line 95-97)
    response_enc = bytes(response)
    cipher = AES.new(factory_key, AES.MODE_CBC, iv=b'\x00'*16)
    response_dec = cipher.decrypt(response_enc)
    
    print(f"    Response (encrypted): {response_enc.hex()}")
    print(f"    Response (decrypted): {response_dec.hex()}")
    
    # Parse: Ti || RndA' || PDcap2 || PCDcap2 (Arduino line 109)
    ti = response_dec[0:4]
    rnda_rotated_from_card = response_dec[4:20]
    
    print(f"    Ti: {ti.hex()}")
    print(f"    RndA' (from card): {rnda_rotated_from_card.hex()}")
    
    # Verify RndA' (Arduino line 100-107)
    rnda_rotated_expected = rnda[1:] + rnda[:1]
    print(f"    RndA' (expected):  {rnda_rotated_expected.hex()}")
    
    if rnda_rotated_from_card != rnda_rotated_expected:
        print("    [FAILED] RndA' mismatch!")
        return False
    
    print("    [OK] RndA' verified!")
    
    # Derive session keys (Arduino DNA_GenerateSesAuthKeys)
    print("\n  Deriving session keys...")
    sv1 = b'\xA5\x5A\x00\x01\x00\x80' + rnda[0:2]
    cmac_obj = CMAC.new(factory_key, ciphermod=AES)
    cmac_obj.update(sv1 + b'\x00' * 8)
    session_enc_key = cmac_obj.digest()
    
    sv2 = b'\x5A\xA5\x00\x01\x00\x80' + rnda[0:2]
    cmac_obj = CMAC.new(factory_key, ciphermod=AES)
    cmac_obj.update(sv2 + b'\x00' * 8)
    session_mac_key = cmac_obj.digest()
    
    print(f"    Session ENC: {session_enc_key.hex()}")
    print(f"    Session MAC: {session_mac_key.hex()}")
    print("  [OK] Authenticated!\n")
    
    # Step 3: ChangeKey (Arduino DNA_Full_ChangeKey, line 1034-1095)
    print("Step 3: ChangeKey(0, factory -> factory)")
    
    cmd = 0xC4
    key_no = 0
    new_key = factory_key  # Reset to factory
    version = 0x00
    cmd_ctr = 0  # First command after auth (Arduino line 111-112)
    
    # Build 32-byte key data (Arduino line 1047-1053)
    key_data = bytearray(32)
    key_data[0:16] = new_key
    key_data[16] = version
    key_data[17] = 0x80
    # Rest is zeros
    
    print(f"  Key data (32 bytes): {bytes(key_data).hex()}")
    
    # Calculate IV (Arduino DNA_CalculateIVCmd)
    plaintext_iv = b'\xA5\x5A' + ti + cmd_ctr.to_bytes(2, 'little') + b'\x00' * 8
    cipher = AES.new(session_enc_key, AES.MODE_CBC, iv=b'\x00'*16)
    iv_encrypted = cipher.encrypt(plaintext_iv)
    
    print(f"  IV (encrypted): {iv_encrypted.hex()}")
    
    # Encrypt key data (Arduino line 1161-1163)
    cipher = AES.new(session_enc_key, AES.MODE_CBC, iv=iv_encrypted)
    encrypted = cipher.encrypt(bytes(key_data))
    
    print(f"  Encrypted (32 bytes): {encrypted.hex()}")
    
    # Calculate CMAC (Arduino DNA_CalculateDataEncAndCMACt, line 2153-2180)
    # CMAC input: Cmd || CmdCtr || TI || KeyNo || EncryptedData
    mac_input = (
        bytes([cmd]) +
        cmd_ctr.to_bytes(2, 'little') +
        ti +
        bytes([key_no]) +
        encrypted
    )
    
    print(f"  CMAC input ({len(mac_input)} bytes): {mac_input.hex()}")
    
    cmac_obj = CMAC.new(session_mac_key, ciphermod=AES)
    cmac_obj.update(mac_input)
    cmac_full = cmac_obj.digest()
    
    # Truncate (Arduino line 2122-2123)
    cmac_truncated = bytes([cmac_full[i * 2 + 1] for i in range(8)])
    
    print(f"  CMAC (full): {cmac_full.hex()}")
    print(f"  CMAC (truncated): {cmac_truncated.hex()}")
    
    # Build APDU (Arduino line 1040-1046, 1066)
    apdu = [
        0x90,                 # CLA
        cmd,                  # CMD (0xC4)
        0x00,                 # P1
        0x00,                 # P2
        0x29,                 # Lc (41 bytes)
        key_no,               # KeyNo
        *list(encrypted),     # Encrypted data (32 bytes)
        *list(cmac_truncated), # CMAC (8 bytes)
        0x00                  # Le
    ]
    
    print(f"\n  APDU ({len(apdu)} bytes):")
    print(f"    {toHexString(apdu)}")
    print()
    
    # Send it!
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"  Response: SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) == (0x91, 0x00):
        print("\n" + "="*70)
        print("SUCCESS! CHANGEKEY WORKED!")
        print("="*70)
        print("\nKey 0 reset to factory defaults!")
        print("Tag should now authenticate with 0x00*16")
        return True
    else:
        print(f"\n[ERROR] ChangeKey failed: {sw1:02X}{sw2:02X}")
        
        error_names = {
            0x911E: "INTEGRITY_ERROR - CMAC verification failed",
            0x917E: "LENGTH_ERROR - Wrong data length",
            0x919E: "PARAMETER_ERROR - Invalid parameter",
            0x91AE: "AUTHENTICATION_ERROR - Auth failed",
        }
        error_code = (sw1 << 8) | sw2
        if error_code in error_names:
            print(f"       ({error_names[error_code]})")
        
        return False


if __name__ == '__main__':
    try:
        success = reset_key0_raw()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\nException: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

