# filename: ntag_communicator.py

from smartcard.System import readers
from smartcard.util import toHexString, toBytes
from ntag424_sdm_provisioner.hal import CardManager

# --- NTAG424 DNA APDU Commands ---
# CLA, INS, P1, P2, Le (for GetVersion, Le=00 means get max response)
GET_VERSION_APDU = [0x90, 0x60, 0x00, 0x00, 0x00]

def identify_ntag424():
    """
    Connects to the first available reader, selects the card,
    sends the GET_VERSION command, and checks the response.
    """
    try:
        with CardManager() as cardReader:
                        print("--- Example 02: Get Version ---")
            print("INFO: Card detected. ATR:", cardReader.wait_for_atr())

        if not r:
            print("ERROR: No smart card readers found.")
            return

        print(f"INFO: Found reader: {r[0]}")
        connection = r[0].createConnection()
        connection.connect()
        print("INFO: Reader connected. Attempting to select card...")

        # 1. Send the GET_VERSION APDU
        print(f"DEBUG: Sending APDU: {toHexString(GET_VERSION_APDU)}")
        
        data, sw1, sw2 = connection.transmit(GET_VERSION_APDU)

        # 2. Check the Status Word (SW1, SW2)
        # 91 00 is the expected successful status word for NXP commands
        status_word = (sw1 << 8) | sw2
        if status_word == 0x9100:
            print(f"\nSUCCESS: GET_VERSION returned 91 00 (Success, more data follows).")
            
            # The full version response is 14 bytes long.
            # We must send one final APDU to get the rest of the data.
            # This is often done by sending a standard GET_RESPONSE command: [90 C0 00 00 00]
            # However, for NTAG/DESFire family, 91 00 means the data is in the 'data' variable.
            
            # 3. Parse the Version Response Data
            response_hex = toHexString(data)
            print(f"INFO: Version Response Data: {response_hex}")

            # For NTAG424 DNA, the response should have:
            # Major Product Version (byte 7): 0x01
            # Product Sub Type (byte 13): 0x01 (for NTAG 424 DNA)
            
            # Let's check the most critical byte: Product Family (Byte 4)
            # 0x05 or 0x06 usually indicates DESFire/NTAG family.
            product_family_code = data[4] if len(data) > 4 else None
            
            # This check is the most reliable:
            # For NTAG424 DNA, the response is often: 04 01 01 02 05 01 01 00 ...
            # Byte 4 (Product Family): 0x05 (DESFire/NTAG family)
            # Byte 5 (Product Major Version): 0x01
            # Byte 13 (Product Type): 0x01 (NTAG 424 DNA)

            if len(data) >= 14 and data[13] == 0x01 and data[4] == 0x05:
                print("\n✅ CHIP CONFIRMED: NTAG 424 DNA detected successfully.")
            else:
                print("\n⚠️ CHIP WARNING: Chip detected, but version check did not match NTAG 424 DNA profile.")
                print(f"   (Expected Product Family=0x05, Product Type=0x01. Got Family={hex(data[4]) if len(data)>4 else 'N/A'}, Type={hex(data[13]) if len(data)>13 else 'N/A'})")

        elif status_word == 0x6A81:
            print("ERROR: Command not supported or invalid parameter (6A 81). Not an NXP family chip or not in the right state.")
        else:
            print(f"ERROR: APDU failed. Status Word: {hex(sw1)} {hex(sw2)}")

    except Exception as e:
        print(f"FATAL ERROR: An unexpected exception occurred: {e}")
    finally:
        if 'connection' in locals():
            try:
                connection.disconnect()
            except Exception:
                pass

if __name__ == "__main__":
    identify_ntag424()