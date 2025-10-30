"""
Test Phase 2 command format to verify we're building the APDU correctly.

This script verifies that our Phase 2 command format matches the NXP spec exactly.
"""
import sys

def test_command_format():
    """Test Phase 2 command format."""
    
    # Simulate 32 bytes of encrypted data
    data_to_card = bytes(range(32))  # 00 01 02 ... 1F
    
    print("=" * 60)
    print("Phase 2 Command Format Test")
    print("=" * 60)
    print(f"\nData to card (32 bytes): {data_to_card.hex().upper()}")
    print(f"Data length: {len(data_to_card)} bytes = 0x{len(data_to_card):02X}")
    
    # Current implementation
    print("\n" + "-" * 60)
    print("Current Implementation:")
    print("-" * 60)
    apdu = [0x90, 0xAF, 0x00, 0x00, len(data_to_card), *data_to_card, 0x00]
    print(f"APDU: {', '.join(f'0x{b:02X}' for b in apdu[:10])}... ({len(apdu)} bytes total)")
    print(f"  CLA: 0x{apdu[0]:02X}")
    print(f"  CMD: 0x{apdu[1]:02X}")
    print(f"  P1:  0x{apdu[2]:02X}")
    print(f"  P2:  0x{apdu[3]:02X}")
    print(f"  Lc:  0x{apdu[4]:02X} ({apdu[4]} decimal)")
    print(f"  Data: {len(data_to_card)} bytes")
    print(f"  Le:  0x{apdu[-1]:02X}")
    print(f"Total length: {len(apdu)} bytes")
    
    # Expected format from spec
    print("\n" + "-" * 60)
    print("Expected Format (from NXP spec):")
    print("-" * 60)
    print("CLA: 0x90")
    print("CMD: 0xAF (Additional frame)")
    print("P1:  0x00")
    print("P2:  0x00")
    print("Lc:  0x20 (32 bytes)")
    print("Data: 32 bytes")
    print("Le:  0x00")
    
    # Verify each field
    print("\n" + "-" * 60)
    print("Verification:")
    print("-" * 60)
    checks = [
        ("CLA", apdu[0] == 0x90, f"0x{apdu[0]:02X}", "0x90"),
        ("CMD", apdu[1] == 0xAF, f"0x{apdu[1]:02X}", "0xAF"),
        ("P1", apdu[2] == 0x00, f"0x{apdu[2]:02X}", "0x00"),
        ("P2", apdu[3] == 0x00, f"0x{apdu[3]:02X}", "0x00"),
        ("Lc", apdu[4] == 0x20, f"0x{apdu[4]:02X}", "0x20"),
        ("Data length", len(data_to_card) == 32, f"{len(data_to_card)} bytes", "32 bytes"),
        ("Le", apdu[-1] == 0x00, f"0x{apdu[-1]:02X}", "0x00"),
    ]
    
    all_ok = True
    for field, check, actual, expected in checks:
        status = "[OK]" if check else "[FAIL]"
        if not check:
            all_ok = False
        print(f"{status} {field}: {actual} (expected {expected})")
    
    # Show full APDU hex
    print("\n" + "-" * 60)
    print("Full APDU (hex):")
    print("-" * 60)
    print(" ".join(f"{b:02X}" for b in apdu))
    
    # Show full APDU as expected by spec
    print("\n" + "-" * 60)
    print("Expected APDU (from spec):")
    print("-" * 60)
    expected_hex = "90 AF 00 00 20 " + " ".join(f"{b:02X}" for b in data_to_card) + " 00"
    print(expected_hex)
    
    # Compare
    actual_hex = " ".join(f"{b:02X}" for b in apdu)
    if actual_hex == expected_hex:
        print("\n[OK] Command format matches spec exactly!")
    else:
        print("\n[FAIL] Command format doesn't match spec!")
        print(f"Actual:   {actual_hex}")
        print(f"Expected: {expected_hex}")
        all_ok = False
    
    print("\n" + "=" * 60)
    if all_ok:
        print("Conclusion: Command format is CORRECT")
        print("If Phase 2 still fails, the issue is likely:")
        print("  1. Wrong encryption key")
        print("  2. Wrong RndB extraction/rotation")
        print("  3. Wrong RndA generation")
        print("  4. Seritag protocol difference")
    else:
        print("Conclusion: Command format has ISSUES - FIX NEEDED")
    print("=" * 60)

if __name__ == "__main__":
    test_command_format()

