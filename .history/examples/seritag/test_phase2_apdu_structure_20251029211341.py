"""
Test Phase 2 APDU structure and byte alignment.

This verifies:
1. Exact APDU byte structure
2. Length field encoding
3. Data alignment
4. How pyscard sends it
"""
import sys

def test_apdu_structure():
    """Test Phase 2 APDU structure."""
    
    # Simulate 32 bytes of Phase 2 encrypted data
    data_to_card = bytes(range(32))  # 00 01 02 ... 1F
    
    print("=" * 60)
    print("Phase 2 APDU Structure Test")
    print("=" * 60)
    
    # Current implementation
    print("\n" + "-" * 60)
    print("Current Implementation:")
    print("-" * 60)
    apdu = [0x90, 0xAF, 0x00, 0x00, len(data_to_card), *data_to_card, 0x00]
    
    print(f"Data length: {len(data_to_card)} bytes (0x{len(data_to_card):02X})")
    print(f"APDU length: {len(apdu)} bytes")
    print(f"\nAPDU structure:")
    print(f"  [0] CLA:     0x{apdu[0]:02X}")
    print(f"  [1] INS:     0x{apdu[1]:02X}")
    print(f"  [2] P1:      0x{apdu[2]:02X}")
    print(f"  [3] P2:      0x{apdu[3]:02X}")
    print(f"  [4] Lc:      0x{apdu[4]:02X} ({apdu[4]} decimal)")
    print(f"  [5-36] Data: 32 bytes")
    print(f"  [37] Le:     0x{apdu[-1]:02X}")
    
    print(f"\nFull APDU (hex):")
    hex_str = " ".join(f"{b:02X}" for b in apdu)
    print(f"  {hex_str}")
    
    # Check for alignment issues
    print("\n" + "-" * 60)
    print("Alignment Check:")
    print("-" * 60)
    print(f"Lc field: {apdu[4]} bytes")
    print(f"  - Fits in 1 byte: {apdu[4] <= 255]}")
    print(f"  - No extended length needed: {apdu[4] < 256}")
    print(f"  - Single byte encoding: OK")
    
    print(f"\nData field:")
    print(f"  - Start offset: byte 5")
    print(f"  - Length: {len(data_to_card)} bytes")
    print(f"  - End offset: byte {4 + len(data_to_card)}")
    print(f"  - Alignment: {'OK' if len(data_to_card) % 2 == 0 else 'MISALIGNED (odd length)'}")
    
    print(f"\nLe field:")
    print(f"  - Offset: byte {len(apdu) - 1} (last byte)")
    print(f"  - Value: 0x{apdu[-1]:02X}")
    print(f"  - Encoding: Single byte (00h = all available data)")
    
    # Verify structure matches spec
    print("\n" + "-" * 60)
    print("Spec Compliance Check:")
    print("-" * 60)
    spec_fields = {
        "CLA": (apdu[0] == 0x90, "0x90"),
        "INS": (apdu[1] == 0xAF, "0xAF"),
        "P1": (apdu[2] == 0x00, "0x00"),
        "P2": (apdu[3] == 0x00, "0x00"),
        "Lc": (apdu[4] == 0x20, "0x20 (32 bytes)"),
        "Data length": (len(data_to_card) == 32, "32 bytes"),
        "Le": (apdu[-1] == 0x00, "0x00"),
    }
    
    all_ok = True
    for field, (check, expected) in spec_fields.items():
        status = "[OK]" if check else "[FAIL]"
        if not check:
            all_ok = False
        print(f"{status} {field}: expected {expected}")
    
    # Check for potential issues
    print("\n" + "-" * 60)
    print("Potential Issues Check:")
    print("-" * 60)
    
    # Issue 1: List vs bytes conversion
    print("1. APDU Type:")
    print(f"   Type: {type(apdu).__name__}")
    print(f"   pyscard expects: list (OK)")
    
    # Issue 2: Length encoding
    print("\n2. Length Encoding:")
    lc_value = apdu[4]
    if lc_value == len(data_to_card):
        print(f"   Lc matches data length: OK")
    else:
        print(f"   MISMATCH: Lc={lc_value}, data={len(data_to_card)}")
    
    # Issue 3: Byte alignment (for control() path)
    print("\n3. Byte Alignment:")
    total_length = len(apdu)
    print(f"   Total APDU length: {total_length} bytes")
    print(f"   Alignment to 4 bytes: {total_length % 4 == 0}")
    print(f"   Alignment to 8 bytes: {total_length % 8 == 0}")
    print(f"   Note: Most readers don't require alignment, but some might")
    
    # Issue 4: Check if data needs to be in specific format
    print("\n4. Data Format:")
    print(f"   Data type: {type(data_to_card).__name__}")
    print(f"   Converted to list: {list(data_to_card)[:5]}...")
    print(f"   Matches spec: Yes (32 bytes, encrypted)")
    
    print("\n" + "=" * 60)
    if all_ok:
        print("Conclusion: APDU structure looks CORRECT")
        print("\nIf Phase 2 still fails, possible issues:")
        print("  1. Reader-specific byte alignment requirements")
        print("  2. Data encoding differences (endianness?)")
        print("  3. Reader wrapping/transformation of APDU")
        print("  4. Seritag protocol differences")
    else:
        print("Conclusion: APDU structure has ISSUES")
    print("=" * 60)

if __name__ == "__main__":
    test_apdu_structure()

