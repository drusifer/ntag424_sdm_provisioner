"""
RAW PYSCARD - FORMAT_PICC (0xFC)

Uses ONLY crypto_primitives.py, no other production code.
Sends FORMAT_PICC to reset tag to factory defaults.

WARNING: This ERASES all keys and data!
"""

import os
from smartcard.System import readers
from smartcard.util import toHexString
from Crypto.Cipher import AES
from Crypto.Hash import CMAC

# Import ONLY crypto_primitives
from ntag424_sdm_provisioner.crypto.crypto_primitives import calculate_cmac


def raw_format_picc():
    """
    Format PICC using raw pyscard + crypto_primitives only.
    
    Command sequence:
    1. Select PICC
    2. Authenticate with current key (factory or known key)
    3. Send FORMAT_PICC (0xFC)
    """
    
    print("\n" + "="*70)
    print("RAW PYSCARD - FORMAT_PICC")
    print("="*70)
    print("\nWARNING: This will ERASE all keys and data!")
    print()
    
    # Get reader
    reader_list = readers()
    if not reader_list:
        print("[ERROR] No readers found!")
        return False
    
    connection = reader_list[0].createConnection()
    connection.connect()
    
    # Step 1: Select PICC
    print("Step 1: Select PICC Application")
    apdu = [0x00, 0xA4, 0x04, 0x00, 0x07, 0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"  SW={sw1:02X}{sw2:02X}", end="")
    if (sw1, sw2) != (0x90, 0x00):
        print(" [FAILED]")
        return False
    print(" [OK]\n")
    
    # Step 2: Authenticate with factory key
    print("Step 2: Authenticate EV2 with factory key (0x00*16)")
    factory_key = bytes(16)
    
    # Phase 1
    apdu = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    if (sw1, sw2) != (0x91, 0xAF):
        print(f"  Phase 1: SW={sw1:02X}{sw2:02X} [FAILED]")
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
        print(f"  Phase 2: SW={sw1:02X}{sw2:02X} [FAILED]")
        return False
    
    # Parse response
    cipher = AES.new(factory_key, AES.MODE_CBC, iv=b'\x00'*16)
    response_dec = cipher.decrypt(bytes(response))
    ti = response_dec[0:4]
    rnda_rotated_card = response_dec[4:20]
    rnda_rotated_expected = rnda[1:] + rnda[:1]
    
    if rnda_rotated_card != rnda_rotated_expected:
        print("  RndA' mismatch [FAILED]")
        return False
    
    print(f"  Ti: {ti.hex()}")
    print("  Auth complete [OK]\n")
    
    # Derive session keys
    sv1 = b'\xA5\x5A\x00\x01\x00\x80' + rnda[0:2]
    cmac_obj = CMAC.new(factory_key, ciphermod=AES)
    cmac_obj.update(sv1 + b'\x00' * 8)
    session_enc_key = cmac_obj.digest()
    
    sv2 = b'\x5A\xA5\x00\x01\x00\x80' + rnda[0:2]
    cmac_obj = CMAC.new(factory_key, ciphermod=AES)
    cmac_obj.update(sv2 + b'\x00' * 8)
    session_mac_key = cmac_obj.digest()
    
    print(f"  Session ENC: {session_enc_key.hex()}")
    print(f"  Session MAC: {session_mac_key.hex()}\n")
    
    # Step 3: FORMAT_PICC (0xFC)
    print("Step 3: FORMAT_PICC (0xFC)")
    
    cmd = 0xFC
    cmd_ctr = 0
    
    # Use crypto_primitives.calculate_cmac
    cmac_truncated = calculate_cmac(
        cmd=cmd,
        cmd_ctr=cmd_ctr,
        ti=ti,
        cmd_header=b'',  # FORMAT_PICC has no header data
        encrypted_data=b'',  # No data
        session_mac_key=session_mac_key
    )
    
    print(f"  CMAC: {cmac_truncated.hex()}")
    
    # Build APDU: CLA CMD P1 P2 Lc CMAC Le
    apdu = [
        0x90,                   # CLA
        cmd,                    # CMD (0xFC)
        0x00,                   # P1
        0x00,                   # P2
        0x08,                   # Lc (8 bytes CMAC)
        *list(cmac_truncated),  # CMAC
        0x00                    # Le
    ]
    
    print(f"  APDU: {toHexString(apdu)}\n")
    
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"  Response: SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) == (0x91, 0x00):
        print("\n" + "="*70)
        print("SUCCESS! FORMAT_PICC WORKED!")
        print("="*70)
        print("\nTag has been reset to factory defaults:")
        print("  - All keys: 0x00*16")
        print("  - All files reset")
        print("  - SDM disabled")
        return True
    else:
        error_names = {
            0x911C: "ILLEGAL_COMMAND - Command not available",
            0x911E: "INTEGRITY_ERROR - CMAC wrong",
            0x917E: "LENGTH_ERROR - Wrong length",
            0x919E: "PARAMETER_ERROR - Invalid param",
            0x91AE: "AUTHENTICATION_ERROR - Auth expired",
        }
        error_code = (sw1 << 8) | sw2
        print(f"\n[FAILED] {error_names.get(error_code, 'Unknown error')}")
        
        if error_code == 0x911C:
            print("\nFORMAT_PICC might not be available or requires Master App key.")
        elif error_code == 0x911E:
            print("\nCMAC verification failed - session keys don't match card.")
        
        return False


if __name__ == '__main__':
    try:
        success = raw_format_picc()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\nException: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

