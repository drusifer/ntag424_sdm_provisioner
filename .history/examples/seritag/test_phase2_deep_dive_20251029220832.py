"""
Deep Dive Phase 2 Authentication Investigation

This test performs detailed byte-by-byte analysis of Phase 1 and Phase 2
authentication to identify why RndB' calculation fails.
"""
import sys
import os
import logging

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication
from ntag424_sdm_provisioner.constants import FACTORY_KEY, SW_OK, SW_ADDITIONAL_FRAME
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

# Enable verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

log = logging.getLogger(__name__)


def hex_print(label, data, max_bytes=32):
    """Helper to print hex data."""
    if isinstance(data, bytes):
        hex_str = data.hex().upper()
    else:
        hex_str = bytes(data).hex().upper()
    
    if len(hex_str) > max_bytes * 2:
        print(f"  {label}: {hex_str[:max_bytes*2]}... ({len(hex_str)//2} bytes)")
    else:
        print(f"  {label}: {hex_str}")
    
    return hex_str


def test_phase1_deep_analysis(card):
    """Test 1: Detailed Phase 1 response analysis."""
    print("\n" + "=" * 80)
    print("TEST 1: PHASE 1 RESPONSE BYTE-BY-BYTE ANALYSIS")
    print("=" * 80)
    
    # Phase 1
    print("\nStep 1: Sending Phase 1 APDU...")
    apdu_phase1 = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
    hex_print("Phase 1 APDU", apdu_phase1)
    
    print("\nStep 2: Receiving Phase 1 response...")
    data1, sw1_1, sw2_1 = card.send_apdu(apdu_phase1, use_escape=True)
    
    print(f"\nStep 3: Analyzing response...")
    print(f"  SW: {sw1_1:02X}{sw2_1:02X}")
    print(f"  Data length: {len(data1)} bytes")
    
    if (sw1_1, sw2_1) != SW_ADDITIONAL_FRAME:
        print(f"\n[ERROR] Phase 1 failed: Expected SW=91AF, got SW={sw1_1:02X}{sw2_1:02X}")
        return None
    
    if len(data1) != 16:
        print(f"\n[WARN] Phase 1 returned {len(data1)} bytes, expected 16")
        if len(data1) < 16:
            print(f"  [ERROR] Response too short!")
            return None
        elif len(data1) > 16:
            print(f"  [WARN] Response longer than expected - first 16 bytes are RndB")
    
    encrypted_rndb = bytes(data1[:16])
    
    print(f"\nStep 4: Encrypted RndB analysis...")
    hex_print("Encrypted RndB (16 bytes)", encrypted_rndb)
    print(f"  Bytes (hex): {' '.join(f'{b:02X}' for b in encrypted_rndb)}")
    print(f"  Bytes (dec): {' '.join(str(b) for b in encrypted_rndb)}")
    
    # Check for patterns
    unique_bytes = len(set(encrypted_rndb))
    print(f"  Unique bytes: {unique_bytes}/16 (expect high, ~14-16)")
    
    if unique_bytes < 10:
        print(f"  [WARN] Low entropy - might indicate decryption issue")
    
    return encrypted_rndb


def test_phase1_decryption(card, encrypted_rndb):
    """Test 2: Phase 1 decryption verification."""
    print("\n" + "=" * 80)
    print("TEST 2: PHASE 1 DECRYPTION VERIFICATION")
    print("=" * 80)
    
    print(f"\nStep 1: Testing decryption with Factory Key...")
    hex_print("Factory Key", FACTORY_KEY)
    
    # Try AES-ECB (current method)
    print("\nStep 2: AES-ECB decryption (current method)...")
    cipher_ecb = AES.new(FACTORY_KEY, AES.MODE_ECB)
    rndb_ecb = cipher_ecb.decrypt(encrypted_rndb)
    hex_print("Decrypted RndB (ECB)", rndb_ecb)
    
    # Verify randomness
    unique_bytes = len(set(rndb_ecb))
    print(f"  Unique bytes: {unique_bytes}/16")
    
    if unique_bytes < 10:
        print(f"  [WARN] Low entropy in decrypted RndB")
    
    # Try AES-CBC (alternative - unlikely but test)
    print("\nStep 3: Testing AES-CBC decryption (for comparison)...")
    try:
        from Crypto.Cipher import AES as AES_CBC
        from Crypto.Util.Padding import unpad
        
        # Try with zero IV
        iv_zero = b'\x00' * 16
        cipher_cbc = AES_CBC.new(FACTORY_KEY, AES_CBC.MODE_CBC, iv_zero)
        rndb_cbc = cipher_cbc.decrypt(encrypted_rndb)
        hex_print("Decrypted RndB (CBC, zero IV)", rndb_cbc)
        
        if rndb_cbc != rndb_ecb:
            print(f"  [NOTE] CBC decryption differs from ECB")
    except Exception as e:
        print(f"  [SKIP] CBC test failed: {e}")
    
    return rndb_ecb


def test_rndb_rotation(card, rndb):
    """Test 3: RndB rotation byte analysis."""
    print("\n" + "=" * 80)
    print("TEST 3: RNDB ROTATION BYTE-BY-BYTE ANALYSIS")
    print("=" * 80)
    
    print(f"\nStep 1: Original RndB...")
    hex_print("Original RndB", rndb)
    print(f"  Byte-by-byte:")
    for i, b in enumerate(rndb):
        print(f"    [{i:2d}]: 0x{b:02X} ({b:3d}) '{chr(b) if 32 <= b < 127 else '.'}'")
    
    print(f"\nStep 2: Rotating RndB left by 1 byte...")
    rndb_rotated = rndb[1:] + rndb[0:1]
    hex_print("Rotated RndB'", rndb_rotated)
    print(f"  Byte-by-byte:")
    for i, b in enumerate(rndb_rotated):
        original_idx = (i + 1) % 16
        original_byte = rndb[original_idx if original_idx < 16 else 0]
        print(f"    [{i:2d}]: 0x{b:02X} ({b:3d}) '{chr(b) if 32 <= b < 127 else '.'}' (from original[{original_idx}])")
    
    print(f"\nStep 3: Rotation verification...")
    print(f"  Original first byte: 0x{rndb[0]:02X} -> moved to position 15")
    print(f"  Original bytes [1-15] -> moved to positions [0-14]")
    
    if rndb_rotated[15] == rndb[0] and rndb_rotated[:15] == rndb[1:16]:
        print(f"  [OK] Rotation correct")
    else:
        print(f"  [ERROR] Rotation incorrect!")
        print(f"    Expected first byte at end: {rndb[0]:02X}, got {rndb_rotated[15]:02X}")
    
    return rndb_rotated


def test_phase2_plaintext(card, rndb_rotated):
    """Test 4: Phase 2 plaintext verification."""
    print("\n" + "=" * 80)
    print("TEST 4: PHASE 2 PLAINTEXT CONSTRUCTION")
    print("=" * 80)
    
    print(f"\nStep 1: Generating RndA...")
    rnda = get_random_bytes(16)
    hex_print("Generated RndA (16 bytes)", rnda)
    print(f"  Unique bytes: {len(set(rnda))}/16")
    
    print(f"\nStep 2: Constructing plaintext: RndA || RndB'...")
    plaintext = rnda + rndb_rotated
    hex_print("Plaintext (32 bytes)", plaintext)
    print(f"  Length: {len(plaintext)} bytes")
    print(f"  Block 1 (bytes 0-15):   {plaintext[:16].hex().upper()}")
    print(f"  Block 2 (bytes 16-31): {plaintext[16:32].hex().upper()}")
    
    # Verify block alignment
    if len(plaintext) % 16 == 0:
        print(f"  [OK] Block-aligned ({len(plaintext) // 16} blocks)")
    else:
        print(f"  [ERROR] Not block-aligned!")
    
    return plaintext, rnda


def test_phase2_encryption(card, plaintext):
    """Test 5: Phase 2 encryption verification."""
    print("\n" + "=" * 80)
    print("TEST 5: PHASE 2 ENCRYPTION VERIFICATION")
    print("=" * 80)
    
    print(f"\nStep 1: Encrypting plaintext with AES-ECB...")
    hex_print("Factory Key", FACTORY_KEY)
    
    cipher = AES.new(FACTORY_KEY, AES.MODE_ECB)
    encrypted_response = cipher.encrypt(plaintext)
    
    hex_print("Encrypted response (32 bytes)", encrypted_response)
    print(f"  Length: {len(encrypted_response)} bytes")
    print(f"  Block 1 (bytes 0-15):   {encrypted_response[:16].hex().upper()}")
    print(f"  Block 2 (bytes 16-31): {encrypted_response[16:32].hex().upper()}")
    
    # Verify encryption round-trip
    print(f"\nStep 2: Verifying encryption round-trip...")
    decrypted = cipher.decrypt(encrypted_response)
    if decrypted == plaintext:
        print(f"  [OK] Encryption round-trip verified")
    else:
        print(f"  [ERROR] Encryption mismatch!")
        print(f"    Original:  {plaintext.hex().upper()}")
        print(f"    Decrypted: {decrypted.hex().upper()}")
    
    # Test block-by-block encryption
    print(f"\nStep 3: Testing block-by-block encryption...")
    block1 = cipher.encrypt(plaintext[:16])
    block2 = cipher.encrypt(plaintext[16:32])
    blocks_combined = block1 + block2
    
    if encrypted_response == blocks_combined:
        print(f"  [OK] Block-by-block matches single encrypt (32 bytes)")
    else:
        print(f"  [WARN] Block-by-block differs (should be same for ECB)")
    
    return encrypted_response


def test_phase2_apdu(card, encrypted_response):
    """Test 6: Phase 2 APDU byte analysis."""
    print("\n" + "=" * 80)
    print("TEST 6: PHASE 2 APDU BYTE-BY-BYTE ANALYSIS")
    print("=" * 80)
    
    print(f"\nStep 1: Constructing Phase 2 APDU...")
    apdu_phase2 = [0x90, 0xAF, 0x00, 0x00, len(encrypted_response)] + list(encrypted_response) + [0x00]
    
    print(f"  APDU length: {len(apdu_phase2)} bytes")
    print(f"  Structure:")
    print(f"    [0]     CLA: 0x{apdu_phase2[0]:02X}")
    print(f"    [1]     INS: 0x{apdu_phase2[1]:02X} (AuthenticateEV2Second)")
    print(f"    [2]     P1:  0x{apdu_phase2[2]:02X}")
    print(f"    [3]     P2:  0x{apdu_phase2[3]:02X}")
    print(f"    [4]     Lc:  0x{apdu_phase2[4]:02X} ({apdu_phase2[4]} bytes)")
    print(f"    [5-36]  Data: {len(encrypted_response)} bytes encrypted")
    print(f"    [37]    Le:  0x{apdu_phase2[-1]:02X}")
    
    hex_print("Full APDU", apdu_phase2)
    
    # Verify Lc matches data length
    if apdu_phase2[4] == len(encrypted_response):
        print(f"  [OK] Lc matches data length")
    else:
        print(f"  [ERROR] Lc mismatch: {apdu_phase2[4]} vs {len(encrypted_response)}")
    
    return apdu_phase2


def test_phase2_send(card, apdu_phase2):
    """Test 7: Send Phase 2 and analyze response."""
    print("\n" + "=" * 80)
    print("TEST 7: SEND PHASE 2 AND ANALYZE RESPONSE")
    print("=" * 80)
    
    print(f"\nStep 1: Sending Phase 2 APDU...")
    print(f"  Using escape mode: True")
    print(f"  Time since Phase 1: immediate (same transaction)")
    
    data2, sw1_2, sw2_2 = card.send_apdu(apdu_phase2, use_escape=True)
    
    print(f"\nStep 2: Analyzing Phase 2 response...")
    print(f"  SW: {sw1_2:02X}{sw2_2:02X}")
    print(f"  Data length: {len(data2)} bytes")
    
    if data2:
        hex_print("Response data", bytes(data2))
    
    if (sw1_2, sw2_2) == SW_OK:
        print(f"\n  [SUCCESS] Phase 2 authentication successful!")
        return True
    else:
        print(f"\n  [FAIL] Phase 2 authentication failed")
        
        # Status word analysis
        if sw2_2 == 0xAE:
            print(f"\nSW=91AE: Authentication Error (Wrong RndB')")
            print(f"  This means:")
            print(f"    1. Tag decrypted our Phase 2 data ✓")
            print(f"    2. Tag extracted RndB' from our data ✓")
            print(f"    3. Tag compared RndB' with its expected value ✗")
            print(f"    4. They didn't match ✗")
            print(f"\n  Possible causes:")
            print(f"    - Wrong RndB from Phase 1 (wrong key?)")
            print(f"    - Wrong RndB rotation (but format check passes)")
            print(f"    - Seritag stores/rotates RndB differently")
            print(f"    - Phase 1/Phase 2 transaction state issue")
        elif sw2_2 == 0xCA:
            print(f"\nSW=91CA: Command Aborted")
            print(f"  Transaction state issue - Phase 1 transaction not complete")
        elif sw2_2 == 0xAD:
            print(f"\nSW=91AD: Authentication Delay")
            print(f"  Too many failed attempts - need to wait or use fresh tag")
        
        return False


def main():
    """Run deep dive Phase 2 investigation."""
    print("=" * 80)
    print("DEEP DIVE PHASE 2 AUTHENTICATION INVESTIGATION")
    print("=" * 80)
    print("\nThis test performs detailed byte-by-byte analysis to identify")
    print("why Phase 2 authentication fails on Seritag tags.")
    print("\nPlease place a FRESH Seritag NTAG424 DNA tag on the reader...")
    
    try:
        with CardManager(0, timeout_seconds=15) as card:
            SelectPiccApplication().execute(card)
            print("[OK] PICC selected\n")
            
            # Test 1: Phase 1 deep analysis
            encrypted_rndb = test_phase1_deep_analysis(card)
            if not encrypted_rndb:
                print("\n[ERROR] Phase 1 failed - cannot continue")
                return
            
            # Test 2: Phase 1 decryption
            rndb = test_phase1_decryption(card, encrypted_rndb)
            
            # Test 3: RndB rotation
            rndb_rotated = test_rndb_rotation(card, rndb)
            
            # Test 4: Phase 2 plaintext
            plaintext, rnda = test_phase2_plaintext(card, rndb_rotated)
            
            # Test 5: Phase 2 encryption
            encrypted_response = test_phase2_encryption(card, plaintext)
            
            # Test 6: Phase 2 APDU
            apdu_phase2 = test_phase2_apdu(card, encrypted_response)
            
            # Test 7: Send Phase 2
            success = test_phase2_send(card, apdu_phase2)
            
            print("\n" + "=" * 80)
            print("SUMMARY")
            print("=" * 80)
            if success:
                print("\n[SUCCESS] Phase 2 authentication successful!")
                print("Root cause identified: Check the detailed logs above")
            else:
                print("\n[FAIL] Phase 2 authentication failed")
                print("\nDetailed analysis complete. Review logs above to identify issue.")
                print("\nKey areas to investigate:")
                print("  1. Phase 1 RndB extraction/decryption")
                print("  2. RndB rotation calculation")
                print("  3. Phase 2 plaintext construction")
                print("  4. Phase 2 encryption")
                print("  5. Phase 2 APDU format")
            print("=" * 80)
            
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

