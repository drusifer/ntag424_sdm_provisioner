"""
Test authentication with a FRESH tag - READ ONLY (won't corrupt).

This script:
1. Authenticates with factory key
2. Prints session keys
3. Tries simple read command (GetKeyVersion)
4. DOES NOT change any keys or write anything

Safe to run on a fresh tag.
"""

from smartcard.System import readers
from smartcard.util import toHexString
from Crypto.Cipher import AES
from Crypto.Hash import CMAC
import os


def test_fresh_tag():
    """Test authentication and simple command with fresh tag."""
    
    print("\n" + "="*70)
    print("FRESH TAG TEST - READ ONLY")
    print("="*70)
    print("\nThis will NOT modify the tag - safe to run on fresh tag.")
    print()
    
    # Get reader
    reader_list = readers()
    if not reader_list:
        print("[ERROR] No readers found!")
        return False
    
    r = reader_list[0]
    print(f"Reader: {r}")
    print("\nPlace FRESH tag on reader...")
    print()
    
    connection = r.createConnection()
    connection.connect()
    
    # Step 1: Select PICC
    print("Step 1: Select PICC Application")
    apdu = [0x00, 0xA4, 0x04, 0x00, 0x07, 0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"  SW={sw1:02X}{sw2:02X}", end="")
    
    if (sw1, sw2) != (0x90, 0x00):
        print(f" [FAILED]")
        return False
    print(" [OK]")
    
    # Step 2: Get Version to confirm it's NTAG424
    print("\nStep 2: Get Chip Version")
    apdu = [0x90, 0x60, 0x00, 0x00, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    
    # Get all frames
    all_data = list(response)
    while sw1 == 0x91 and sw2 == 0xAF:
        apdu = [0x90, 0xAF, 0x00, 0x00, 0x00]
        response, sw1, sw2 = connection.transmit(apdu)
        all_data.extend(response)
    
    if len(all_data) >= 14:
        uid = bytes(all_data[7:14])
        print(f"  UID: {uid.hex().upper()}")
    print("  [OK]")
    
    # Step 3: Authenticate with factory key
    print("\nStep 3: Authenticate EV2 (factory key 0x00*16)")
    factory_key = bytes(16)
    key_no = 0
    
    # Phase 1
    apdu = [0x90, 0x71, 0x00, 0x00, 0x02, key_no, 0x00, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"  Phase 1: SW={sw1:02X}{sw2:02X}", end="")
    
    if (sw1, sw2) != (0x91, 0xAF):
        print(f" [FAILED]")
        return False
    print(" [OK]")
    
    # Decrypt RndB
    encrypted_rndb = bytes(response[:16])
    cipher = AES.new(factory_key, AES.MODE_CBC, iv=b'\x00'*16)
    rndb = cipher.decrypt(encrypted_rndb)
    rndb_rotated = rndb[1:] + rndb[:1]
    
    # Generate RndA
    rnda = os.urandom(16)
    print(f"    RndA: {rnda.hex()}")
    print(f"    RndB: {rndb.hex()}")
    
    # Phase 2
    plaintext = rnda + rndb_rotated
    cipher = AES.new(factory_key, AES.MODE_CBC, iv=b'\x00'*16)
    encrypted = cipher.encrypt(plaintext)
    
    apdu = [0x90, 0xAF, 0x00, 0x00, 0x20, *list(encrypted), 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"  Phase 2: SW={sw1:02X}{sw2:02X}", end="")
    
    if (sw1, sw2) != (0x91, 0x00):
        print(f" [FAILED]")
        return False
    print(" [OK]")
    
    # Verify response
    response_enc = bytes(response)
    cipher = AES.new(factory_key, AES.MODE_CBC, iv=b'\x00'*16)
    response_dec = cipher.decrypt(response_enc)
    
    ti = response_dec[0:4]
    rnda_rotated_card = response_dec[4:20]
    rnda_rotated_expected = rnda[1:] + rnda[:1]
    
    print(f"    Ti: {ti.hex()}")
    
    if rnda_rotated_card != rnda_rotated_expected:
        print("  [FAILED] RndA' mismatch!")
        return False
    print("  [OK] Authenticated!")
    
    # Derive session keys
    print("\nStep 4: Session Key Derivation")
    sv1 = b'\xA5\x5A\x00\x01\x00\x80' + rnda[0:2]
    cmac_obj = CMAC.new(factory_key, ciphermod=AES)
    cmac_obj.update(sv1 + b'\x00' * 8)
    session_enc_key = cmac_obj.digest()
    
    sv2 = b'\x5A\xA5\x00\x01\x00\x80' + rnda[0:2]
    cmac_obj = CMAC.new(factory_key, ciphermod=AES)
    cmac_obj.update(sv2 + b'\x00' * 8)
    session_mac_key = cmac_obj.digest()
    
    print(f"  Session ENC: {session_enc_key.hex()}")
    print(f"  Session MAC: {session_mac_key.hex()}")
    print("  [OK]")
    
    # Step 5: Try simple authenticated command (GetKeyVersion)
    print("\nStep 5: Test GetKeyVersion (simple MAC command)")
    
    cmd = 0x64  # GetKeyVersion
    cmd_ctr = 0
    key_no_to_query = 0
    
    # Build CMAC input: Cmd || CmdCtr || TI || KeyNo
    mac_input = (
        bytes([cmd]) +
        cmd_ctr.to_bytes(2, 'little') +
        ti +
        bytes([key_no_to_query])
    )
    
    print(f"  CMAC input: {mac_input.hex()}")
    
    # Calculate CMAC
    cmac_obj = CMAC.new(session_mac_key, ciphermod=AES)
    cmac_obj.update(mac_input)
    cmac_full = cmac_obj.digest()
    cmac_truncated = bytes([cmac_full[i * 2 + 1] for i in range(8)])
    
    print(f"  CMAC: {cmac_truncated.hex()}")
    
    # Build APDU
    apdu = [0x90, cmd, 0x00, 0x00, 0x09, key_no_to_query, *list(cmac_truncated), 0x00]
    print(f"  APDU: {toHexString(apdu)}")
    
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"  Response: SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) == (0x91, 0x00):
        print("\n" + "="*70)
        print("SUCCESS! AUTHENTICATED COMMAND WORKED!")
        print("="*70)
        print(f"\nKey version: {response[0] if response else 'N/A'}")
        print("\nSession is VALID on fresh tag!")
        print("Now safe to try ChangeKey...")
        return True
    else:
        print(f"\n[ERROR] GetKeyVersion failed: {sw1:02X}{sw2:02X}")
        
        error_names = {
            0x911E: "INTEGRITY_ERROR - CMAC wrong (session keys don't match card)",
            0x917E: "LENGTH_ERROR - Wrong data length",
            0x919E: "PARAMETER_ERROR - Invalid parameter",
        }
        error_code = (sw1 << 8) | sw2
        if error_code in error_names:
            print(f"       ({error_names[error_code]})")
        
        print("\nEven on FRESH tag, authenticated commands fail!")
        print("The bug is fundamental in our auth or session key derivation.")
        return False


if __name__ == '__main__':
    try:
        success = test_fresh_tag()
        
        if not success:
            print("\n" + "="*70)
            print("RECOMMENDATION")
            print("="*70)
            print("\nTo find the root cause:")
            print("1. Modify Arduino to print session keys after auth")
            print("2. Use SAME RndA in Arduino and Python (hardcode)")
            print("3. Compare session keys - that's where the bug is")
        
        exit(0 if success else 1)
    except Exception as e:
        print(f"\nException: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

