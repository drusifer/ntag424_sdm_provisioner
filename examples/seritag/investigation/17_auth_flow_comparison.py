#!/usr/bin/env python3
"""
Authentication Flow Comparison

Detailed step-by-step comparison of our authentication flow vs. NXP spec
and Arduino implementation reference.

This script logs every single step, byte, and operation to identify differences.
"""

import os
import sys
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import (
    SelectPiccApplication,
    GetChipVersion,
    AuthenticateEV2First,
    AuthenticateEV2Second,
)
from ntag424_sdm_provisioner.constants import FACTORY_KEY

def format_bytes(data: bytes, label: str = "", max_bytes: int = 32) -> str:
    """Format bytes as hex string."""
    hex_str = data.hex().upper()
    if len(hex_str) > max_bytes * 2:
        hex_str = hex_str[:max_bytes*2] + f"... ({len(data)} bytes total)"
    return f"{label:20s}: {hex_str}"

def print_section(title: str):
    """Print section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def main():
    """Main comparison function."""
    print_section("Complete Authentication Flow Analysis")
    print("\nComparing our implementation step-by-step with NXP spec")
    print("and Arduino reference implementation.")
    
    key = FACTORY_KEY
    key_no = 0
    
    print(f"\nUsing:")
    print(f"  Key Number: {key_no:02X}")
    print(f"  Key: {format_bytes(key)}")
    
    try:
        with CardManager() as card:
            # Initial setup
            print_section("Step 1: Initial Setup")
            SelectPiccApplication().execute(card)
            print("[OK] PICC application selected")
            
            version = GetChipVersion().execute(card)
            print(f"[OK] Chip Version: HW {version.hw_major_version}.{version.hw_minor_version}, SW {version.sw_major_version}.{version.sw_minor_version}")
            print(f"[OK] UID: {format_bytes(version.uid)}")
            
            print_section("Step 2: Phase 1 - AuthenticateEV2First")
            print("\nAccording to NXP spec (NT4H2421Gx, Section 10.1):")
            print("  C-APDU: 90 71 00 00 02 [KeyNo] [LenCap] 00")
            print("    Where:")
            print("      CLA = 0x90 (DESFire native)")
            print("      CMD = 0x71 (AuthenticateEV2First)")
            print("      P1  = 0x00")
            print("      P2  = 0x00")
            print("      Lc  = 0x02 (2 bytes of data)")
            print("      Data = [KeyNo] [LenCap]")
            print("      Le  = 0x00")
            print("\n  Expected Response:")
            print("    R-APDU: E(Kx, RndB) || 91 AF")
            print("      - 16 bytes encrypted RndB")
            print("      - SW = 91AF (Additional Frame)")
            print("      - Note: SW=91AF here means 'data available', not 'need more frames'")
            
            cmd1 = AuthenticateEV2First(key_no=key_no)
            response1 = cmd1.execute(card)
            
            encrypted_rndb = response1.challenge
            print(f"\n[OK] Phase 1 Response:")
            print(f"  {format_bytes(encrypted_rndb, 'Encrypted RndB', 32)}")
            print(f"  Length: {len(encrypted_rndb)} bytes (expected 16)")
            print(f"  Status: 91 AF (Additional Frame)")
            
            if len(encrypted_rndb) != 16:
                print(f"\n[ERROR] Expected 16 bytes, got {len(encrypted_rndb)}")
                return
            
            print_section("Step 3: Phase 1 Analysis - Decrypt RndB")
            print("\nAccording to NXP spec:")
            print("  RndB is encrypted with key Kx (referenced by KeyNo)")
            print("  Encryption: AES-128-ECB (no padding)")
            print("  Decrypt: D(Kx, E(Kx, RndB)) = RndB")
            
            # Decrypt RndB
            cipher = AES.new(key, AES.MODE_ECB)
            rndb = cipher.decrypt(encrypted_rndb)
            
            print(f"\n[OK] Decryption:")
            print(f"  Key used: {format_bytes(key)}")
            print(f"  {format_bytes(encrypted_rndb, 'Encrypted RndB')}")
            print(f"  {format_bytes(rndb, 'Decrypted RndB')}")
            print(f"  Length: {len(rndb)} bytes (expected 16)")
            
            # Check if decrypted RndB looks random
            entropy_check = len(set(rndb)) / len(rndb)
            print(f"  Entropy check: {entropy_check:.2%} unique bytes (should be high for random)")
            
            print_section("Step 4: Phase 2 Preparation - Rotate RndB")
            print("\nAccording to NXP spec (NT4H2421Gx, Table 28):")
            print("  RndB' = RndB rotated left by 1 byte")
            print("  Format: RndB[1..15] || RndB[0]")
            
            # Rotate RndB
            rndb_rotated = rndb[1:] + rndb[0:1]
            
            print(f"\n[OK] Rotation:")
            print(f"  {format_bytes(rndb, 'Original RndB')}")
            print(f"  {format_bytes(rndb_rotated, 'Rotated RndB (RndB\')')}")
            print(f"  Verification: First byte {rndb[0]:02X} moved to position 15")
            print(f"                Last byte was {rndb[15]:02X}, now at position 14")
            
            print_section("Step 5: Phase 2 Preparation - Generate RndA")
            print("\nAccording to NXP spec:")
            print("  RndA: 16-byte random generated by PCD (reader)")
            print("  This is our challenge to the tag")
            
            # Generate RndA
            rnda = get_random_bytes(16)
            
            print(f"\n[OK] Generated RndA:")
            print(f"  {format_bytes(rnda)}")
            print(f"  Length: {len(rnda)} bytes (expected 16)")
            
            print_section("Step 6: Phase 2 Preparation - Encrypt Response")
            print("\nAccording to NXP spec (NT4H2421Gx, Table 28):")
            print("  Plaintext: RndA || RndB' (32 bytes total)")
            print("  Encryption: E(Kx, RndA || RndB')")
            print("    - AES-128-ECB (no padding)")
            print("    - Uses same key Kx as Phase 1")
            
            # Encrypt response
            plaintext = rnda + rndb_rotated
            encrypted_response = cipher.encrypt(plaintext)
            
            print(f"\n[OK] Encryption:")
            print(f"  Key used: {format_bytes(key)}")
            print(f"  {format_bytes(plaintext[:16], 'Plaintext (RndA)')}")
            print(f"  {format_bytes(plaintext[16:], 'Plaintext (RndB\')')}")
            print(f"  {format_bytes(encrypted_response, 'Encrypted (full 32 bytes)')}")
            print(f"  Length: {len(encrypted_response)} bytes (expected 32)")
            
            print_section("Step 7: Phase 2 - AuthenticateEV2Second")
            print("\nAccording to NXP spec (NT4H2421Gx, Section 10.1, Table 28):")
            print("  C-APDU: 90 AF 00 00 20 [E(Kx, RndA || RndB')] 00")
            print("    Where:")
            print("      CLA = 0x90 (DESFire native)")
            print("      CMD = 0xAF (AuthenticateEV2First - Part2 / Additional Frame)")
            print("      P1  = 0x00")
            print("      P2  = 0x00")
            print("      Lc  = 0x20 (32 bytes of data)")
            print("      Data = E(Kx, RndA || RndB') (32 bytes)")
            print("      Le  = 0x00")
            print("\n  Expected Response:")
            print("    R-APDU: E(Kx, Ti || RndA' || PDcap2 || PCDcap2) || 91 00")
            print("      - 32 bytes encrypted response")
            print("      - Ti: 4-byte Transaction Identifier")
            print("      - RndA': 16-byte RndA rotated left by 1 byte")
            print("      - PDcap2: 6-byte PD capabilities")
            print("      - PCDcap2: 6-byte PCD capabilities")
            print("      - SW = 9100 (Success)")
            
            # Build APDU manually to see exact format
            apdu_phase2 = [0x90, 0xAF, 0x00, 0x00, 0x20] + list(encrypted_response) + [0x00]
            
            print(f"\n[OK] Phase 2 APDU Construction:")
            print(f"  Header: {' '.join(f'{b:02X}' for b in apdu_phase2[:5])}")
            print(f"  Data length: {len(encrypted_response)} bytes")
            print(f"  Tail: {apdu_phase2[-1]:02X}")
            print(f"  Total APDU length: {len(apdu_phase2)} bytes")
            print(f"  Full APDU (first 10 bytes): {' '.join(f'{b:02X}' for b in apdu_phase2[:10])}...")
            print(f"  Full APDU (last 10 bytes): ...{' '.join(f'{b:02X}' for b in apdu_phase2[-10:])}")
            
            print(f"\n[OK] Phase 2 Command:")
            print(f"  CLA: {apdu_phase2[0]:02X} (0x90 = DESFire native)")
            print(f"  INS: {apdu_phase2[1]:02X} (0xAF = Additional Frame / Phase 2)")
            print(f"  P1:  {apdu_phase2[2]:02X} (0x00)")
            print(f"  P2:  {apdu_phase2[3]:02X} (0x00)")
            print(f"  Lc:  {apdu_phase2[4]:02X} (0x20 = 32 bytes)")
            print(f"  Data: {len(encrypted_response)} bytes")
            print(f"  Le:  {apdu_phase2[-1]:02X} (0x00)")
            
            # Send Phase 2
            cmd2 = AuthenticateEV2Second(data_to_card=encrypted_response)
            print(f"\n[SENDING] Phase 2 command...")
            
            try:
                encrypted_response_card = cmd2.execute(card)
                
                print(f"\n[SUCCESS] Phase 2 Response:")
                print(f"  {format_bytes(encrypted_response_card, 'Encrypted Response', 32)}")
                print(f"  Length: {len(encrypted_response_card)} bytes (expected 32)")
                
                print_section("Step 8: Phase 2 Analysis - Decrypt Response")
                
                # Decrypt response
                decrypted_response = cipher.decrypt(encrypted_response_card)
                
                print(f"\n[OK] Decryption:")
                print(f"  {format_bytes(encrypted_response_card, 'Encrypted Response')}")
                print(f"  {format_bytes(decrypted_response, 'Decrypted Response')}")
                print(f"  Length: {len(decrypted_response)} bytes (expected 32)")
                
                # Parse response
                ti = decrypted_response[0:4]
                rnda_rotated_received = decrypted_response[4:20]
                pdcap2 = decrypted_response[20:26]
                pcdcap2 = decrypted_response[26:32]
                
                print(f"\n[OK] Parsed Response:")
                print(f"  {format_bytes(ti, 'Ti (Transaction ID)')}")
                print(f"  {format_bytes(rnda_rotated_received, 'RndA\' (from tag)')}")
                print(f"  {format_bytes(pdcap2, 'PDcap2')}")
                print(f"  {format_bytes(pcdcap2, 'PCDcap2')}")
                
                print_section("Step 9: Phase 2 Verification - Check RndA'")
                
                # Verify RndA'
                expected_rnda_rotated = rnda[1:] + rnda[0:1]
                
                print(f"\n[OK] RndA' Verification:")
                print(f"  {format_bytes(rnda, 'Original RndA')}")
                print(f"  {format_bytes(expected_rnda_rotated, 'Expected RndA\'')}")
                print(f"  {format_bytes(rnda_rotated_received, 'Received RndA\'')}")
                
                if rnda_rotated_received == expected_rnda_rotated:
                    print(f"\n[SUCCESS] RndA' matches expected rotation!")
                    print(f"  Authentication successful!")
                else:
                    print(f"\n[ERROR] RndA' mismatch!")
                    print(f"  This indicates authentication failed despite SW=9100")
                    
            except Exception as e:
                print(f"\n[ERROR] Phase 2 failed: {e}")
                import traceback
                traceback.print_exc()
            
            print_section("Summary")
            print("\nAuthentication flow complete. Review above for any discrepancies.")
            print("\nKey points to verify:")
            print("  1. Phase 1 APDU format matches spec")
            print("  2. RndB decryption uses correct key")
            print("  3. RndB rotation is correct (left by 1 byte)")
            print("  4. Phase 2 APDU format matches spec")
            print("  5. Encryption uses same key as Phase 1")
            print("  6. Response parsing matches spec format")
            
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Test cancelled by user.")
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

