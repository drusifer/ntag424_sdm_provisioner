"""
Analyze GetFileSettings response data.

File 0x03 returned: 00033023800000 (7 bytes)
Let's parse what this means.
"""
import sys

def parse_file_settings(data_hex):
    """Parse GetFileSettings response data."""
    
    data = bytes.fromhex(data_hex.replace(' ', ''))
    print("=" * 80)
    print(f"GetFileSettings Response Analysis")
    print("=" * 80)
    print(f"\nRaw data ({len(data)} bytes): {data.hex().upper()}")
    
    if len(data) >= 1:
        print(f"\nByte 0: File Type = 0x{data[0]:02X}")
        file_types = {
            0x00: "Standard Data File",
            0x01: "Backup Data File",
            0x02: "Value File",
            0x03: "Cyclic Record File",
        }
        print(f"  {file_types.get(data[0], 'Unknown')}")
    
    if len(data) >= 2:
        print(f"\nByte 1: File Option = 0x{data[1]:02X}")
        print(f"  Bit 7-4: RFU")
        print(f"  Bit 3: File access (0=Plain)")
        print(f"  Bit 2: File access (0=Plain)")
        print(f"  Bit 1: Communication settings")
        print(f"  Bit 0: Communication settings")
        print(f"  Binary: {data[1]:08b}")
    
    if len(data) >= 6:
        print(f"\nBytes 2-5: Access Rights = {data[2:6].hex().upper()}")
        print(f"  Byte 2 (Read):  0x{data[2]:02X}")
        print(f"  Byte 3 (Write): 0x{data[3]:02X}")
        print(f"  Byte 4 (Read&Write): 0x{data[4]:02X}")
        print(f"  Byte 5 (Change): 0x{data[5]:02X}")
        
        # Access rights interpretation
        access_keys = {
            0x00: "FREE",
            0x01: "KEY_0",
            0x02: "KEY_1",
            0x0E: "FREE or authenticated",
            0x0F: "Never",
        }
        
        print(f"\n  Access Rights Breakdown:")
        print(f"    Read:     {access_keys.get(data[2], f'KEY_{data[2]:02X}')}")
        print(f"    Write:    {access_keys.get(data[3], f'KEY_{data[3]:02X}')}")
        print(f"    Read&Write: {access_keys.get(data[4], f'KEY_{data[4]:02X}')}")
        print(f"    Change:   {access_keys.get(data[5], f'KEY_{data[5]:02X}')}")
    
    if len(data) >= 7:
        print(f"\nBytes 6+: File Size (if any): {data[6:].hex().upper() if len(data) > 6 else 'N/A'}")
    
    print("\n" + "=" * 80)
    print("Interpretation:")
    print("=" * 80)
    if len(data) >= 6:
        print(f"File Type: {file_types.get(data[0], 'Unknown')}")
        print(f"File Option: 0x{data[1]:02X}")
        print(f"Change Access: {access_keys.get(data[5], f'KEY_{data[5]:02X}')}")
        print(f"\nKey Finding: Change access right is {access_keys.get(data[5], f'KEY_{data[5]:02X}')}")
        print("  This determines what's needed to change file settings (including SDM/SUN)")
        if data[5] == 0x00:
            print("  -> FREE: No authentication needed!")
        elif data[5] in [0x01, 0x02, 0x03, 0x04]:
            print(f"  -> Requires authentication with KEY_{data[5]:02X}")
        elif data[5] == 0x0E:
            print("  -> FREE or authenticated - might work without auth?")
        elif data[5] == 0x0F:
            print("  -> NEVER: Cannot be changed")


if __name__ == "__main__":
    # Data from diagnostic: 00033023800000
    parse_file_settings("00033023800000")

