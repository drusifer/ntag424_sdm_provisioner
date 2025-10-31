"""
Test Phase 2 encryption format to verify we're encrypting correctly.

This script tests different ways to encrypt the 32-byte Phase 2 payload
to see if our encryption method matches what Seritag expects.
"""
import sys
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

def test_encryption_formats():
    """Test different encryption formats for Phase 2."""
    
    # Use factory key (all zeros)
    key = bytes(16)  # 16 bytes of zeros
    
    # Generate test data
    rnda = get_random_bytes(16)
    rndb = get_random_bytes(16)
    rndb_rotated = rndb[1:] + rndb[0:1]  # Left rotate by 1 byte
    
    print("=" * 60)
    print("Phase 2 Encryption Format Test")
    print("=" * 60)
    print(f"\nKey: {key.hex().upper()}")
    print(f"RndA: {rnda.hex().upper()}")
    print(f"RndB: {rndb.hex().upper()}")
    print(f"RndB' (rotated): {rndb_rotated.hex().upper()}")
    
    # Method 1: Current implementation - single encrypt on 32 bytes
    print("\n" + "-" * 60)
    print("Method 1: Single encrypt(32 bytes) - Current Implementation")
    print("-" * 60)
    plaintext = rnda + rndb_rotated
    print(f"Plaintext (RndA || RndB'): {plaintext.hex().upper()}")
    cipher = AES.new(key, AES.MODE_ECB)
    encrypted = cipher.encrypt(plaintext)
    print(f"Encrypted (32 bytes): {encrypted.hex().upper()}")
    print(f"Length: {len(encrypted)} bytes")
    
    # Verify decryption
    decrypted = cipher.decrypt(encrypted)
    print(f"Decrypted: {decrypted.hex().upper()}")
    if decrypted == plaintext:
        print("[OK] Decryption matches plaintext")
    else:
        print("[FAIL] Decryption doesn't match plaintext!")
    
    # Method 2: Two separate encrypts (block 1, block 2)
    print("\n" + "-" * 60)
    print("Method 2: Two separate encrypts (block 1, block 2)")
    print("-" * 60)
    block1 = rnda  # First 16 bytes
    block2 = rndb_rotated  # Second 16 bytes
    print(f"Block 1 (RndA): {block1.hex().upper()}")
    print(f"Block 2 (RndB'): {block2.hex().upper()}")
    cipher = AES.new(key, AES.MODE_ECB)
    encrypted1 = cipher.encrypt(block1)
    encrypted2 = cipher.encrypt(block2)
    encrypted_combined = encrypted1 + encrypted2
    print(f"Encrypted Block 1: {encrypted1.hex().upper()}")
    print(f"Encrypted Block 2: {encrypted2.hex().upper()}")
    print(f"Combined (32 bytes): {encrypted_combined.hex().upper()}")
    print(f"Length: {len(encrypted_combined)} bytes")
    
    # Compare with Method 1
    if encrypted == encrypted_combined:
        print("[OK] Methods 1 and 2 produce same result")
    else:
        print("[DIFFERENT] Methods 1 and 2 produce different results!")
        print(f"Method 1: {encrypted.hex().upper()}")
        print(f"Method 2: {encrypted_combined.hex().upper()}")
    
    # Method 3: Check if padding is needed (should NOT be)
    print("\n" + "-" * 60)
    print("Method 3: Verify no padding is used")
    print("-" * 60)
    print("AES ECB with 32 bytes (2 blocks):")
    print("  - Block 1 (bytes 0-15): RndA")
    print("  - Block 2 (bytes 16-31): RndB'")
    print("  - Total: 32 bytes = exactly 2 blocks")
    print("  - No padding should be needed")
    
    # Verify encryption/decryption round-trip
    print("\n" + "-" * 60)
    print("Round-trip verification:")
    print("-" * 60)
    cipher_enc = AES.new(key, AES.MODE_ECB)
    cipher_dec = AES.new(key, AES.MODE_ECB)
    test_plaintext = rnda + rndb_rotated
    test_encrypted = cipher_enc.encrypt(test_plaintext)
    test_decrypted = cipher_dec.decrypt(test_encrypted)
    if test_plaintext == test_decrypted:
        print("[OK] Encryption/decryption round-trip successful")
    else:
        print("[FAIL] Encryption/decryption round-trip failed!")
        print(f"Original: {test_plaintext.hex().upper()}")
        print(f"Decrypted: {test_decrypted.hex().upper()}")
    
    print("\n" + "=" * 60)
    print("Conclusion:")
    print("=" * 60)
    print("AES ECB mode encrypts each 16-byte block independently.")
    print("Encrypting 32 bytes = encrypting 2 blocks sequentially.")
    print("Our current implementation (Method 1) should be correct.")
    print("\nIf Phase 2 still fails, the issue is likely:")
    print("  1. Wrong key")
    print("  2. Wrong RndB rotation")
    print("  3. Wrong RndB extraction from Phase 1")
    print("  4. Command format issue")
    print("=" * 60)

if __name__ == "__main__":
    test_encryption_formats()

