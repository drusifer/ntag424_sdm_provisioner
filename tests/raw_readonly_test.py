"""
RAW PYSCARD TEST A - READ ONLY

Uses ONLY crypto_primitives.py, no other production code.
Tests if authenticated commands work with fresh tag.
"""

import os
from smartcard.System import readers
from smartcard.util import toHexString
from Crypto.Cipher import AES
from Crypto.Hash import CMAC

# Import ONLY crypto_primitives
from ntag424_sdm_provisioner.crypto.crypto_primitives import calculate_cmac


def raw_readonly_test():
    """
    Authenticate and try GetKeyVersion using raw pyscard + crypto_primitives only.
    Safe - does NOT modify tag.
    """
    
    print("\n" + "="*70)
    print("RAW PYSCARD TEST A - READ ONLY")
    print("="*70)
    print("\nSAFE: Will NOT modify tag\n")
    
    # Get reader
    reader_list = readers()
    if not reader_list:
        print("[ERROR] No readers found!")
        return False
    
    connection = reader_list[0].createConnection()
    connection.connect()
    
    # Step 1: Select PICC
    print("Step 1: Select PICC")
    apdu = [0x00, 0xA4, 0x04, 0x00, 0x07, 0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"  SW={sw1:02X}{sw2:02X}", end="")
    if (sw1, sw2) != (0x90, 0x00):
        print(" [FAILED]")
        return False
    print(" [OK]\n")
    
    # Step 2: Authenticate
    print("Step 2: Authenticate with factory key")
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
    
    print(f"  RndA: {rnda.hex()}")
    print(f"  RndB: {rndb.hex()}")
    print(f"  Ti:   {ti.hex()}")
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
    
    # Step 3: GetKeyVersion using crypto_primitives
    print("Step 3: GetKeyVersion (using crypto_primitives.py)")
    
    cmd = 0x64
    cmd_ctr = 0
    key_no = 0
    
    # Use crypto_primitives.calculate_cmac
    cmac_truncated = calculate_cmac(
        cmd=cmd,
        cmd_ctr=cmd_ctr,
        ti=ti,
        cmd_header=bytes([key_no]),
        encrypted_data=b'',  # No encrypted data for MAC-only command
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
        print(f"\nKey version: {response[0] if response else 'N/A'}")
        print("\nAuthenticated commands work with raw pyscard + crypto_primitives!")
        return True
    else:
        print(f"\n[FAILED] {sw1:02X}{sw2:02X}")
        if (sw1, sw2) == (0x91, 0x1E):
            print("       INTEGRITY_ERROR - CMAC wrong")
            print("\nSession keys don't match card's expectations.")
        return False


if __name__ == '__main__':
    success = raw_readonly_test()
    exit(0 if success else 1)

