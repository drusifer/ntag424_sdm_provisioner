"""
Read tag state using plain (unauthenticated) commands.

This shows what's on the tag without authentication.
"""

from smartcard.System import readers
from smartcard.util import toHexString


def read_tag_state():
    """Read tag state using plain commands."""
    
    print("\n" + "="*70)
    print("READ TAG STATE - PLAIN COMMANDS (No Auth)")
    print("="*70)
    print()
    
    connection = readers()[0].createConnection()
    connection.connect()
    
    # Select PICC
    print("Step 1: Select PICC")
    apdu = [0x00, 0xA4, 0x04, 0x00, 0x07, 0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    if (sw1, sw2) != (0x90, 0x00):
        print(f"  [FAILED] {sw1:02X}{sw2:02X}")
        return
    print("  [OK]\n")
    
    # Get Version (multi-frame)
    print("Step 2: Get Version")
    apdu = [0x90, 0x60, 0x00, 0x00, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    all_data = list(response)
    
    while sw1 == 0x91 and sw2 == 0xAF:
        apdu = [0x90, 0xAF, 0x00, 0x00, 0x00]
        response, sw1, sw2 = connection.transmit(apdu)
        all_data.extend(response)
    
    if len(all_data) >= 14:
        uid = bytes(all_data[7:14])
        hw_type = all_data[1]
        sw_type = all_data[8]
        print(f"  UID: {uid.hex().upper()}")
        print(f"  HW Type: {hw_type}")
        print(f"  SW Type: {sw_type}")
    print("  [OK]\n")
    
    # Get File IDs
    print("Step 3: Get File IDs")
    apdu = [0x90, 0x6F, 0x00, 0x00, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"  SW={sw1:02X}{sw2:02X}")
    if (sw1, sw2) == (0x91, 0x00):
        print(f"  File IDs: {bytes(response).hex().upper()}")
    print()
    
    # Get File Settings for each file
    for file_no in [0x01, 0x02, 0x03]:
        print(f"Step 4.{file_no}: Get File Settings for File 0x{file_no:02X}")
        apdu = [0x90, 0xF5, 0x00, 0x00, 0x01, file_no, 0x00]
        response, sw1, sw2 = connection.transmit(apdu)
        print(f"  SW={sw1:02X}{sw2:02X}")
        
        if (sw1, sw2) == (0x91, 0x00) and len(response) > 0:
            data = bytes(response)
            file_type = data[0]
            file_option = data[1] if len(data) > 1 else 0
            access_rights = data[2:4] if len(data) > 3 else b''
            file_size = data[4:7] if len(data) > 6 else b''
            
            print(f"  File Type: 0x{file_type:02X}")
            print(f"  File Option: 0x{file_option:02X} (CommMode: {file_option & 0x03})")
            if access_rights:
                print(f"  Access Rights: {access_rights.hex().upper()}")
            if file_size:
                size = int.from_bytes(file_size, 'little')
                print(f"  File Size: {size} bytes")
                
            # Decode CommMode
            comm_mode = file_option & 0x03
            comm_names = {0: "PLAIN", 1: "MAC", 3: "FULL"}
            print(f"  CommMode: {comm_names.get(comm_mode, 'Unknown')}")
            
        print()
    
    # Try to read NDEF file (if CommMode=PLAIN)
    print("Step 5: Try to read NDEF file data")
    
    # Select NDEF file (ISO SELECT)
    apdu = [0x00, 0xA4, 0x00, 0x00, 0x02, 0xE1, 0x04]
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"  ISO Select NDEF: SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) == (0x90, 0x00):
        # Try to read first 16 bytes
        apdu = [0x00, 0xB0, 0x00, 0x00, 0x10]  # READ BINARY
        response, sw1, sw2 = connection.transmit(apdu)
        print(f"  ISO Read Binary: SW={sw1:02X}{sw2:02X}")
        
        if (sw1, sw2) == (0x90, 0x00) and response:
            data = bytes(response)
            print(f"  Data (first 16 bytes): {data.hex().upper()}")
            if len(data) >= 2:
                cc_len = (data[0] << 8) | data[1]
                print(f"  CC Length: {cc_len}")
    
    print()
    print("="*70)
    print("TAG STATE ANALYSIS COMPLETE")
    print("="*70)


if __name__ == '__main__':
    try:
        read_tag_state()
    except Exception as e:
        print(f"\nException: {e}")
        import traceback
        traceback.print_exc()

