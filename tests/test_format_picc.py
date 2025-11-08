"""
Format PICC using raw pyscard API to reset the tag to factory defaults.

WARNING: This will erase ALL keys, files, and data on the tag!
"""

from smartcard.System import readers
from smartcard.util import toHexString
from Crypto.Cipher import AES
from Crypto.Hash import CMAC
import os


def format_picc():
    """
    Send FORMAT_PICC command to reset tag to factory defaults.
    
    This requires authentication with PICC Master Key (Key 0).
    """
    
    print("\n" + "="*70)
    print("FORMAT PICC - FACTORY RESET")
    print("="*70)
    print("\nWARNING: This will ERASE all data and reset keys to factory!")
    print()
    
    # Get reader
    reader_list = readers()
    if not reader_list:
        print("[ERROR] No readers found!")
        return False
    
    r = reader_list[0]
    print(f"Using reader: {r}")
    
    connection = r.createConnection()
    connection.connect()
    
    # Step 1: Select PICC Application
    print("\nStep 1: Selecting PICC Application...")
    apdu = [0x00, 0xA4, 0x04, 0x00, 0x07, 0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"  Response: SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) != (0x90, 0x00):
        print(f"  [ERROR] Select failed")
        return False
    print("  [OK]")
    
    # Step 2: Try factory key
    print("\nStep 2: Authenticating with factory key...")
    factory_key = bytes(16)
    rnda = os.urandom(16)
    
    print(f"  RndA: {rnda.hex()}")
    
    # Auth Phase 1 (plain mode - no encryption of RndA!)
    apdu = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
    print(f"  >>> Auth Phase 1: {toHexString(apdu)}")
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"  <<< Response: {len(response)} bytes, SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) != (0x91, 0xAF):
        print(f"  [ERROR] Auth Phase 1 failed")
        return False
    
    # Decrypt RndB
    rndb_enc = bytes(response[:16])
    cipher = AES.new(factory_key, AES.MODE_CBC, iv=b'\x00'*16)
    rndb = cipher.decrypt(rndb_enc)
    print(f"  RndB: {rndb.hex()}")
    
    # Rotate RndB
    rndb_rotated = rndb[1:] + rndb[:1]
    
    # Encrypt RndA || RndB' (per Arduino line 76-77)
    plaintext = rnda + rndb_rotated
    cipher = AES.new(factory_key, AES.MODE_CBC, iv=rndb_enc)
    encrypted_part = cipher.encrypt(plaintext)
    
    # Auth Phase 2
    apdu = [0x90, 0xAF, 0x00, 0x00, 0x20, *list(encrypted_part), 0x00]
    print(f"  >>> Auth Phase 2: (sending encrypted response)")
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"  <<< Response: {len(response)} bytes, SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) != (0x91, 0x00):
        print(f"  [ERROR] Auth Phase 2 failed")
        return False
    
    # Parse response
    response_enc = bytes(response)
    # Use zero IV for decrypting response (per Arduino line 96)
    cipher = AES.new(factory_key, AES.MODE_CBC, iv=b'\x00'*16)
    response_dec = cipher.decrypt(response_enc)
    
    print(f"  Response (encrypted): {response_enc.hex()}")
    print(f"  Response (decrypted): {response_dec.hex()}")
    
    ti = response_dec[0:4]
    rnda_rotated_response = response_dec[4:20]
    
    # Verify RndA'
    rnda_rotated_expected = rnda[1:] + rnda[:1]
    if rnda_rotated_response != rnda_rotated_expected:
        print("  [ERROR] RndA' verification failed!")
        return False
    
    print(f"  Ti: {ti.hex()}")
    print("  [OK] Authenticated!")
    
    # Derive session keys
    sv1 = b'\xA5\x5A\x00\x01\x00\x80' + rnda[0:2]
    cmac_enc = CMAC.new(factory_key, ciphermod=AES)
    cmac_enc.update(sv1 + b'\x00' * 8)
    session_enc_key = cmac_enc.digest()
    
    sv2 = b'\x5A\xA5\x00\x01\x00\x80' + rnda[0:2]
    cmac_mac = CMAC.new(factory_key, ciphermod=AES)
    cmac_mac.update(sv2 + b'\x00' * 8)
    session_mac_key = cmac_mac.digest()
    
    print(f"  Session ENC: {session_enc_key.hex()}")
    print(f"  Session MAC: {session_mac_key.hex()}")
    
    # Step 3: Send FORMAT_PICC
    print("\nStep 3: Sending FORMAT_PICC (0xFC)...")
    
    cmd_byte = 0xFC
    cmd_ctr = 0
    
    # Build CMAC input: Cmd || CmdCtr || TI
    mac_input = bytearray()
    mac_input.append(cmd_byte)
    mac_input.extend(cmd_ctr.to_bytes(2, 'little'))
    mac_input.extend(ti)
    
    print(f"  CMAC input: {bytes(mac_input).hex()}")
    
    # Calculate CMAC
    cmac_obj = CMAC.new(session_mac_key, ciphermod=AES)
    cmac_obj.update(bytes(mac_input))
    cmac_full = cmac_obj.digest()
    
    # Truncate to even-numbered bytes
    cmac_truncated = bytes([cmac_full[i] for i in range(1, 16, 2)])
    
    print(f"  CMAC: {cmac_truncated.hex()}")
    
    # Build APDU: CLA CMD P1 P2 Lc CMAC Le
    apdu = [
        0x90,                   # CLA
        cmd_byte,               # CMD (0xFC)
        0x00,                   # P1
        0x00,                   # P2
        0x08,                   # Lc (8 bytes CMAC)
        *list(cmac_truncated),  # CMAC
        0x00                    # Le
    ]
    
    print(f"  APDU: {toHexString(apdu)}")
    print()
    
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"  Response: SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) == (0x91, 0x00):
        print("\n" + "="*70)
        print("SUCCESS! TAG FORMATTED!")
        print("="*70)
        print("\nTag has been reset to factory defaults:")
        print("  - All keys: 0x00*16")
        print("  - All files reset")
        print("  - SDM disabled")
        return True
    else:
        print(f"\n[ERROR] FORMAT_PICC failed with {sw1:02X}{sw2:02X}")
        
        error_names = {
            0x911E: "INTEGRITY_ERROR - CMAC wrong",
            0x917E: "LENGTH_ERROR - Wrong length",
            0x919E: "PARAMETER_ERROR - Invalid param",
            0x91AE: "AUTHENTICATION_ERROR - Auth failed/expired",
        }
        error_code = (sw1 << 8) | sw2
        if error_code in error_names:
            print(f"       ({error_names[error_code]})")
        
        return False


if __name__ == '__main__':
    try:
        success = format_picc()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\nException: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

