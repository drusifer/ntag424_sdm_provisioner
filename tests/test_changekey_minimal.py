"""
Minimal ChangeKey test using raw pyscard API.

This bypasses our auth session implementation to isolate potential bugs.
Uses the verified crypto primitives from crypto_components.py.
"""

import os
import sys
from pathlib import Path

# Add tests directory to path
tests_dir = Path(__file__).parent
sys.path.insert(0, str(tests_dir))

from smartcard.System import readers
from Crypto.Cipher import AES
from ntag424_sdm_provisioner.crypto.crypto_primitives import build_changekey_apdu


def test_minimal_changekey_with_pyscard():
    """
    Execute ChangeKey using raw pyscard with verified crypto primitives.
    
    Sequence:
    1. Select PICC Application
    2. AuthenticateEV2First (using factory key 0x00*16)
    3. ChangeKey (using verified crypto from crypto_components)
    """
    
    # Get reader
    reader_list = readers()
    if not reader_list:
        print("No readers found!")
        return False
    
    r = reader_list[0]
    print(f"Using reader: {r}")
    
    connection = r.createConnection()
    connection.connect()
    
    print("\n=== MINIMAL CHANGEKEY SEQUENCE ===\n")
    
    # Step 1: Select PICC Application
    # For ACR122U, we need to use Control (escape) for native APDUs
    apdu = [0x90, 0x5A, 0x00, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00]
    print(f">>> SELECT PICC: {' '.join(f'{b:02X}' for b in apdu)}")
    
    # Try transmit first (direct)
    try:
        response, sw1, sw2 = connection.transmit(apdu)
        print(f"<<< Response: SW={sw1:02X}{sw2:02X}")
    except Exception as e:
        print(f"Transmit failed: {e}, trying Control...")
        # Use Control mode for ACR122U
        CONTROL_CODE = 0x42000000 + 3400  # IOCTL_CCID_ESCAPE
        wrapped_apdu = [0xFF, 0x00, 0x00, 0x00, len(apdu), *apdu]
        response_bytes = connection.control(CONTROL_CODE, wrapped_apdu)
        if len(response_bytes) >= 2:
            response = response_bytes[:-2]
            sw1, sw2 = response_bytes[-2], response_bytes[-1]
            print(f"<<< Response: SW={sw1:02X}{sw2:02X}")
        else:
            print(f"ERROR: Invalid response length: {len(response_bytes)}")
            return False
    
    if (sw1, sw2) != (0x90, 0x00):
        print(f"ERROR: Select failed with {sw1:02X}{sw2:02X}")
        return False
    
    # Step 2: AuthenticateEV2First
    factory_key = bytes(16)  # All zeros
    rnda = os.urandom(16)
    
    print(f"\nRndA: {rnda.hex()}")
    
    # Phase 1
    apdu = [0x90, 0x71, 0x00, 0x00, 0x11, 0x00, *list(rnda), 0x00]
    print(f"\n>>> AUTH PHASE 1: {' '.join(f'{b:02X}' for b in apdu[:7])}... (+ RndA)")
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"<<< Response: {len(response)} bytes, SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) != (0x91, 0xAF):
        print(f"ERROR: Auth Phase 1 failed with {sw1:02X}{sw2:02X}")
        return False
    
    # Decrypt response to get RndB
    rndb_enc = bytes(response[:16])
    print(f"RndB (encrypted): {rndb_enc.hex()}")
    
    cipher = AES.new(factory_key, AES.MODE_CBC, iv=b'\x00'*16)
    rndb = cipher.decrypt(rndb_enc)
    print(f"RndB (decrypted): {rndb.hex()}")
    
    # Rotate RndB
    rndb_rotated = rndb[1:] + rndb[:1]
    print(f"RndB (rotated):   {rndb_rotated.hex()}")
    
    # Encrypt RndB' || RndA
    plaintext = rndb_rotated + rnda
    cipher = AES.new(factory_key, AES.MODE_CBC, iv=rndb_enc)
    encrypted_part = cipher.encrypt(plaintext)
    
    # Phase 2
    apdu = [0x90, 0xAF, 0x00, 0x00, 0x20, *list(encrypted_part), 0x00]
    print(f"\n>>> AUTH PHASE 2: {' '.join(f'{b:02X}' for b in apdu[:5])}... (+ encrypted)")
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"<<< Response: {len(response)} bytes, SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) != (0x91, 0x00):
        print(f"ERROR: Auth Phase 2 failed with {sw1:02X}{sw2:02X}")
        return False
    
    # Parse response: Ti || RndA' || PDcap2 || PCDcap2
    response_enc = bytes(response)
    
    # Use last 16 bytes of encrypted_part as IV for decryption
    iv_for_response = encrypted_part[-16:]
    cipher = AES.new(factory_key, AES.MODE_CBC, iv=iv_for_response)
    response_dec = cipher.decrypt(response_enc)
    
    ti = response_dec[0:4]
    rnda_rotated_response = response_dec[4:20]
    
    print(f"\nTi: {ti.hex()}")
    print(f"RndA' (from card): {rnda_rotated_response.hex()}")
    
    # Verify RndA'
    rnda_rotated_expected = rnda[1:] + rnda[:1]
    print(f"RndA' (expected):  {rnda_rotated_expected.hex()}")
    
    if rnda_rotated_response != rnda_rotated_expected:
        print("ERROR: RndA' verification failed!")
        return False
    
    print("✓ Authentication successful!")
    
    # Derive session keys
    from Crypto.Hash import CMAC
    from Crypto.Cipher import AES as AES_cipher
    
    sv1 = b'\xA5\x5A\x00\x01\x00\x80' + rnda[0:2]
    cmac_enc = CMAC.new(factory_key, ciphermod=AES_cipher)
    cmac_enc.update(sv1 + b'\x00' * 8)
    session_enc_key = cmac_enc.digest()
    
    sv2 = b'\x5A\xA5\x00\x01\x00\x80' + rnda[0:2]
    cmac_mac = CMAC.new(factory_key, ciphermod=AES_cipher)
    cmac_mac.update(sv2 + b'\x00' * 8)
    session_mac_key = cmac_mac.digest()
    
    print(f"\nSession ENC key: {session_enc_key.hex()}")
    print(f"Session MAC key: {session_mac_key.hex()}")
    
    # Step 3: ChangeKey IMMEDIATELY after auth
    print("\n=== CHANGE KEY ===\n")
    
    new_key = bytes([1] + [0]*15)  # Simple test key
    key_version = 0x01
    cmd_ctr = 0  # First command after auth
    
    # Build ChangeKey APDU using our VERIFIED crypto primitives
    apdu = build_changekey_apdu(
        key_no=0,
        new_key=new_key,
        old_key=None,
        version=key_version,
        ti=ti,
        cmd_ctr=cmd_ctr,
        session_enc_key=session_enc_key,
        session_mac_key=session_mac_key
    )
    
    print(f">>> CHANGEKEY (Key 0): {' '.join(f'{b:02X}' for b in apdu[:10])}...")
    print(f"    Full length: {len(apdu)} bytes")
    print(f"    Full APDU: {' '.join(f'{b:02X}' for b in apdu)}")
    
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"<<< Response: SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) == (0x91, 0x00):
        print("\n" + "="*50)
        print("SUCCESS! CHANGEKEY WORKED!")
        print("="*50)
        return True
    else:
        print(f"\nERROR: ChangeKey failed with {sw1:02X}{sw2:02X}")
        error_names = {
            0x911E: "INTEGRITY_ERROR (CMAC wrong)",
            0x917E: "LENGTH_ERROR (wrong data length)",
            0x919E: "PARAMETER_ERROR (invalid parameter)",
            0x91AD: "AUTHENTICATION_DELAY (too many attempts)",
        }
        error_code = (sw1 << 8) | sw2
        if error_code in error_names:
            print(f"       ({error_names[error_code]})")
        return False


if __name__ == '__main__':
    success = test_minimal_changekey_with_pyscard()
    exit(0 if success else 1)

