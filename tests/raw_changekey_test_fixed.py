"""
RAW PYSCARD - ChangeKey with CORRECT session key derivation.

Uses fixed 32-byte SV formula from datasheet.
"""

import os
from smartcard.System import readers
from smartcard.util import toHexString


import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)-8s [%(name)s] %(message)s'
)
log = logging.getLogger(__name__)

# All crypto from verified primitives module
from ntag424_sdm_provisioner.crypto.crypto_primitives import (
    build_key_data,
    calculate_iv_for_command,
    encrypt_key_data,
    calculate_cmac,
    derive_session_keys,
    decrypt_rndb,
    rotate_left,
    encrypt_auth_response,
    decrypt_auth_response
)

# Key manager for saved keys
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager


def test_changekey_with_correct_keys():
    """Test ChangeKey with CORRECT session keys."""
    
    log.info("="*70)
    log.info("RAW PYSCARD - CHANGEKEY WITH FIXED SESSION KEYS")
    log.info("="*70)
    
    connection = readers()[0].createConnection()
    connection.connect()
    
    # Select PICC
    log.info("Step 1: Select PICC Application")
    apdu = [0x00, 0xA4, 0x04, 0x00, 0x07, 0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01, 0x00]
    log.debug(f"  >>> {toHexString(apdu)}")
    response, sw1, sw2 = connection.transmit(apdu)
    log.debug(f"  <<< SW={sw1:02X}{sw2:02X}")
    if (sw1, sw2) != (0x90, 0x00):
        log.error("  [FAILED]")
        return False
    log.info("  [OK]")
    
    # Get UID
    log.info("Step 2: Get UID")
    apdu = [0x90, 0x60, 0x00, 0x00, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    all_data = list(response)
    
    while sw1 == 0x91 and sw2 == 0xAF:
        apdu = [0x90, 0xAF, 0x00, 0x00, 0x00]
        response, sw1, sw2 = connection.transmit(apdu)
        all_data.extend(response)
    
    if len(all_data) >= 14:
        uid = bytes(all_data[7:14])
        log.info(f"  UID: {uid.hex().upper()}")
    else:
        log.error("  [FAILED] Could not get UID")
        return False
    
    # Get key from manager
    log.info("Step 3: Get Key from Key Manager")
    key_mgr = CsvKeyManager()
    
    try:
        saved_keys = key_mgr.get_tag_keys(uid)
        auth_key = saved_keys.get_picc_master_key_bytes()
        log.info(f"  Using saved key (status: {saved_keys.status})")
        log.debug(f"  Key: {auth_key.hex()}")
    except Exception:
        auth_key = bytes(16)  # Factory default
        log.info("  Using factory key (tag not in database)")
        log.debug(f"  Key: {auth_key.hex()}")
    
    # Authenticate
    log.info("Step 4: Authenticate EV2")
    
    # Phase 1
    apdu = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
    log.debug(f"  >>> Phase 1: {toHexString(apdu)}")
    response, sw1, sw2 = connection.transmit(apdu)
    log.debug(f"  <<< {len(response)} bytes, SW={sw1:02X}{sw2:02X}")
    if (sw1, sw2) != (0x91, 0xAF):
        log.error("  [FAILED]")
        return False
    
    # Use crypto_primitives for all auth crypto
    encrypted_rndb = bytes(response[:16])
    log.debug(f"  RndB (encrypted): {encrypted_rndb.hex()}")
    
    rndb = decrypt_rndb(encrypted_rndb, auth_key)
    log.debug(f"  RndB (decrypted): {rndb.hex()}")
    
    rndb_rotated = rotate_left(rndb)
    log.debug(f"  RndB (rotated):   {rndb_rotated.hex()}")
    
    rnda = os.urandom(16)
    log.debug(f"  RndA (generated): {rnda.hex()}")
    
    # Phase 2
    log.debug(f"  Phase 2: Building encrypted response...")
    plaintext = rnda + rndb_rotated
    log.debug(f"  Plaintext: {plaintext.hex()}")
    
    encrypted = encrypt_auth_response(rnda, rndb_rotated, auth_key)
    log.debug(f"  Encrypted: {encrypted.hex()}")
    
    apdu = [0x90, 0xAF, 0x00, 0x00, 0x20, *list(encrypted), 0x00]
    log.debug(f"  >>> Phase 2: {toHexString(apdu[:10])}... (+ encrypted)")
    
    response, sw1, sw2 = connection.transmit(apdu)
    log.debug(f"  <<< {len(response)} bytes, SW={sw1:02X}{sw2:02X}")
    if (sw1, sw2) != (0x91, 0x00):
        log.error("  [FAILED]")
        return False
    
    # Decrypt card response
    log.debug(f"  Card response (encrypted): {bytes(response).hex()}")
    response_dec = decrypt_auth_response(bytes(response), auth_key)
    log.debug(f"  Card response (decrypted): {response_dec.hex()}")
    
    ti = response_dec[0:4]
    rnda_rotated_from_card = response_dec[4:20]
    rnda_rotated_expected = rotate_left(rnda)
    
    log.debug(f"  Ti: {ti.hex()}")
    log.debug(f"  RndA' (from card): {rnda_rotated_from_card.hex()}")
    log.debug(f"  RndA' (expected):  {rnda_rotated_expected.hex()}")
    
    if rnda_rotated_from_card != rnda_rotated_expected:
        log.error("  [FAILED] RndA' mismatch!")
        return False
    
    log.info("  [OK]")
    
    # Derive session keys
    log.info("Step 5: Derive Session Keys")
    session_enc_key, session_mac_key = derive_session_keys(auth_key, rnda, rndb)
    log.debug(f"  Session ENC: {session_enc_key.hex()}")
    log.debug(f"  Session MAC: {session_mac_key.hex()}")
    log.info("  [OK]")
    
    # ChangeKey
    log.info("Step 6: ChangeKey (change to same key for testing)")
    
    # New key - using same as current for testing
    new_key = auth_key
    key_data = build_key_data(0, new_key, None, 0x00)
    log.debug(f"  Key data (32 bytes): {key_data.hex()}")
    
    iv = calculate_iv_for_command(ti, 0, session_enc_key)
    log.debug(f"  IV (encrypted): {iv.hex()}")
    
    encrypted = encrypt_key_data(key_data, iv, session_enc_key)
    log.debug(f"  Encrypted (32 bytes): {encrypted.hex()}")
    
    cmac_truncated = calculate_cmac(
        cmd=0xC4,
        cmd_ctr=0,
        ti=ti,
        cmd_header=bytes([0]),
        encrypted_data=encrypted,
        session_mac_key=session_mac_key
    )
    log.debug(f"  CMAC (8 bytes): {cmac_truncated.hex()}")
    
    apdu = [
        0x90, 0xC4, 0x00, 0x00, 0x29,
        0x00,
        *list(encrypted),
        *list(cmac_truncated),
        0x00
    ]
    
    log.debug(f"  >>> ChangeKey APDU ({len(apdu)} bytes): {toHexString(apdu[:20])}...")
    
    response, sw1, sw2 = connection.transmit(apdu)
    log.debug(f"  <<< SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) == (0x91, 0x00):
        log.info("  [OK]")
        log.info("")
        log.info("="*70)
        log.info("SUCCESS! CHANGEKEY WORKED!")
        log.info("="*70)
        return True
    else:
        log.error(f"  [FAILED] SW={sw1:02X}{sw2:02X}")
        return False


if __name__ == '__main__':
    success = test_changekey_with_correct_keys()
    exit(0 if success else 1)

