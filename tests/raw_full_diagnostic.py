"""
RAW PYSCARD - Full Tag Diagnostic

Dumps all readable information about the tag state.
Uses crypto_primitives for authenticated commands.
"""

import os
from smartcard.System import readers
from smartcard.util import toHexString

import logging
# configure debug logging
logging.basicConfig(level=logging.DEBUG)

from ntag424_sdm_provisioner.crypto.crypto_primitives import (
    calculate_cmac,
    derive_session_keys,
    decrypt_rndb,
    rotate_left,
    encrypt_auth_response,
    decrypt_auth_response
)


def full_diagnostic():
    """Full tag diagnostic using raw pyscard."""
    
    print("\n" + "="*70)
    print("NTAG424 DNA - FULL DIAGNOSTIC")
    print("="*70)
    print()
    
    connection = readers()[0].createConnection()
    connection.connect()
    
    # ===== PART 1: UNAUTHENTICATED COMMANDS =====
    print("PART 1: UNAUTHENTICATED (PLAIN) COMMANDS")
    print("-" * 70)
    
    # Select PICC
    print("\n1. Select PICC Application")
    apdu = [0x00, 0xA4, 0x04, 0x00, 0x07, 0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"   SW={sw1:02X}{sw2:02X}", end="")
    if (sw1, sw2) != (0x90, 0x00):
        print(" [FAILED]")
        return
    print(" [OK]")
    
    # Get Version
    print("\n2. Get Version (multi-frame)")
    apdu = [0x90, 0x60, 0x00, 0x00, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    all_data = list(response)
    
    frame_count = 1
    while sw1 == 0x91 and sw2 == 0xAF:
        apdu = [0x90, 0xAF, 0x00, 0x00, 0x00]
        response, sw1, sw2 = connection.transmit(apdu)
        all_data.extend(response)
        frame_count += 1
    
    print(f"   Frames: {frame_count}")
    
    if len(all_data) >= 14:
        uid = bytes(all_data[7:14])
        hw_vendor = all_data[0]
        hw_type = all_data[1]
        hw_subtype = all_data[2]
        hw_major = all_data[3]
        hw_minor = all_data[4]
        hw_storage = all_data[5]
        hw_protocol = all_data[6]
        
        sw_vendor = all_data[7+7]
        sw_type = all_data[7+8]
        sw_subtype = all_data[7+9]
        sw_major = all_data[7+10]
        sw_minor = all_data[7+11]
        sw_storage = all_data[7+12]
        sw_protocol = all_data[7+13]
        
        print(f"   UID: {uid.hex().upper()}")
        print(f"   Hardware: {hw_type}.{hw_subtype} v{hw_major}.{hw_minor} (Protocol {hw_protocol})")
        print(f"   Software: {sw_type}.{sw_subtype} v{sw_major}.{sw_minor} (Protocol {sw_protocol})")
        
        if len(all_data) >= 28:
            batch = bytes(all_data[21:25])
            print(f"   Batch: {batch.hex().upper()}")
    
    # Get File IDs
    print("\n3. Get File IDs")
    apdu = [0x90, 0x6F, 0x00, 0x00, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"   SW={sw1:02X}{sw2:02X}", end="")
    
    file_ids = []
    if (sw1, sw2) == (0x91, 0x00):
        file_ids = list(response)
        print(f" Files: {[f'0x{f:02X}' for f in file_ids]}")
    else:
        print(" [FAILED - using defaults]")
        file_ids = [0x01, 0x02, 0x03]  # Standard files
    
    # Get File Settings for each
    print("\n4. File Settings (PLAIN)")
    for file_no in file_ids:
        apdu = [0x90, 0xF5, 0x00, 0x00, 0x01, file_no, 0x00]
        response, sw1, sw2 = connection.transmit(apdu)
        
        print(f"\n   File 0x{file_no:02X}: SW={sw1:02X}{sw2:02X}", end="")
        
        if (sw1, sw2) == (0x91, 0x00) and len(response) > 0:
            data = bytes(response)
            file_type = data[0]
            file_option = data[1] if len(data) > 1 else 0
            access_rights = data[2:4] if len(data) > 3 else b''
            file_size = data[4:7] if len(data) > 6 else b''
            
            comm_mode = file_option & 0x03
            comm_names = {0: "PLAIN", 1: "MAC", 3: "FULL"}
            
            print(f" [{comm_names.get(comm_mode, '?')}]")
            print(f"      Type: 0x{file_type:02X}, Option: 0x{file_option:02X}")
            if access_rights:
                print(f"      Access: {access_rights.hex().upper()}")
            if file_size:
                size = int.from_bytes(file_size, 'little')
                print(f"      Size: {size} bytes")
        else:
            print(" [FAILED]")
    
    # ===== PART 2: AUTHENTICATED COMMANDS =====
    print("\n\n" + "="*70)
    print("PART 2: AUTHENTICATED COMMANDS")
    print("-" * 70)
    
    # Authenticate again
    print("\n5. Authenticate with factory key")
    factory_key = bytes(16)  # All zeros
    
    apdu = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    
    if (sw1, sw2) != (0x91, 0xAF):
        print(f"   Phase 1: SW={sw1:02X}{sw2:02X} [FAILED - cannot auth]")
        print("\n   Tag may have non-factory keys or be rate-limited")
        return
    
    encrypted_rndb = bytes(response[:16])
    rndb = decrypt_rndb(encrypted_rndb, factory_key)
    rndb_rotated = rotate_left(rndb)
    rnda = os.urandom(16)
    
    encrypted = encrypt_auth_response(rnda, rndb_rotated, factory_key)
    
    apdu = [0x90, 0xAF, 0x00, 0x00, 0x20, *list(encrypted), 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    
    if (sw1, sw2) != (0x91, 0x00):
        print(f"   Phase 2: SW={sw1:02X}{sw2:02X} [FAILED]")
        return
    
    response_dec = decrypt_auth_response(bytes(response), factory_key)
    ti = response_dec[0:4]
    
    print(f"   Ti: {ti.hex()} [OK]")
    
    # Derive session keys
    session_enc_key, session_mac_key = derive_session_keys(factory_key, rnda, rndb)
    cmd_ctr = 0
    
    # Get Key Versions
    print("\n6. Get Key Versions")
    for key_no in range(5):
        cmd = 0x64
        
        cmac_truncated = calculate_cmac(
            cmd=cmd,
            cmd_ctr=cmd_ctr,
            ti=ti,
            cmd_header=bytes([key_no]),
            encrypted_data=b'',
            session_mac_key=session_mac_key
        )
        
        apdu = [0x90, cmd, 0x00, 0x00, 0x09, key_no, *list(cmac_truncated), 0x00]
        response, sw1, sw2 = connection.transmit(apdu)
        
        print(f"   Key {key_no}: SW={sw1:02X}{sw2:02X}", end="")
        
        if (sw1, sw2) == (0x91, 0x00) and response:
            version = response[0]
            print(f" Version=0x{version:02X}")
            cmd_ctr += 1  # Increment on success
        else:
            print(" [FAILED]")
            break
    
    print("\n" + "="*70)
    print("DIAGNOSTIC COMPLETE")
    print("="*70)


if __name__ == '__main__':
    try:
        full_diagnostic()
    except Exception as e:
        print(f"\nException: {e}")
        import traceback
        traceback.print_exc()

