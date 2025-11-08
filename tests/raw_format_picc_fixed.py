"""
RAW PYSCARD - FORMAT_PICC with CORRECT session key derivation.
"""

import os
from smartcard.System import readers
from smartcard.util import toHexString

# All crypto from verified primitives module
from ntag424_sdm_provisioner.crypto.crypto_primitives import (
    calculate_cmac,
    derive_session_keys,
    decrypt_rndb,
    rotate_left,
    encrypt_auth_response,
    decrypt_auth_response
)


def test_format_picc():
    """Test FORMAT_PICC with corrected session keys."""
    
    print("\n" + "="*70)
    print("RAW PYSCARD - FORMAT_PICC (0xFC)")
    print("="*70)
    print("\nWARNING: This will ERASE all keys and data!\n")
    
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
    
    # Use crypto_primitives for auth
    encrypted_rndb = bytes(response[:16])
    rndb = decrypt_rndb(encrypted_rndb, factory_key)
    rndb_rotated = rotate_left(rndb)
    rnda = os.urandom(16)
    
    encrypted = encrypt_auth_response(rnda, rndb_rotated, factory_key)
    
    apdu = [0x90, 0xAF, 0x00, 0x00, 0x20, *list(encrypted), 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    if (sw1, sw2) != (0x91, 0x00):
        return False
    
    response_dec = decrypt_auth_response(bytes(response), factory_key)
    ti = response_dec[0:4]
    
    print(f"  Ti: {ti.hex()}")
    print("  [OK]\n")
    
    # Derive session keys
    session_enc_key, session_mac_key = derive_session_keys(factory_key, rnda, rndb)
    print(f"  Session MAC: {session_mac_key.hex()}\n")
    
    # FORMAT_PICC (0xFC)
    print("FORMAT_PICC (0xFC):")
    
    cmd = 0xFC
    cmd_ctr = 0
    
    # Calculate CMAC (no data for FORMAT_PICC)
    cmac_truncated = calculate_cmac(
        cmd=cmd,
        cmd_ctr=cmd_ctr,
        ti=ti,
        cmd_header=b'',
        encrypted_data=b'',
        session_mac_key=session_mac_key
    )
    
    print(f"  CMAC: {cmac_truncated.hex()}")
    
    apdu = [0x90, cmd, 0x00, 0x00, 0x08, *list(cmac_truncated), 0x00]
    print(f"  APDU: {toHexString(apdu)}\n")
    
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"  Response: SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) == (0x91, 0x00):
        print("\n" + "="*70)
        print("SUCCESS! FORMAT_PICC WORKED!")
        print("="*70)
        print("\nTag reset to factory defaults")
        return True
    else:
        error_names = {
            0x911C: "ILLEGAL_COMMAND - Not available",
            0x911E: "INTEGRITY_ERROR - CMAC wrong",
            0x917E: "LENGTH_ERROR",
            0x919E: "PARAMETER_ERROR",
        }
        error_code = (sw1 << 8) | sw2
        print(f"\n[FAILED] {error_names.get(error_code, 'Unknown')}")
        return False


if __name__ == '__main__':
    success = test_format_picc()
    exit(0 if success else 1)

