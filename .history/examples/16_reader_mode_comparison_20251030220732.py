#!/usr/bin/env python3
"""
Reader Mode Comparison Test

Compares escape mode (control) vs transmit mode for authentication.
Tests Phase 1 and Phase 2 separately with detailed logging of raw responses.
Tests timing delays to check for reader processing time issues.

This script helps diagnose if authentication issues are hardware/reader-related.
"""

import os
import sys
import time
from typing import List, Tuple, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import (
    SelectPiccApplication,
    GetChipVersion,
    AuthenticateEV2First,
    AuthenticateEV2Second,
)
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.constants import FACTORY_KEY
from Crypto.Cipher import AES

def format_bytes(data: bytes) -> str:
    """Format bytes as hex string with spaces every 2 bytes."""
    return ' '.join(f'{b:02X}' for b in data)

def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def test_phase1_with_mode(
    card, 
    key_no: int = 0, 
    use_escape: bool = True,
    description: str = ""
) -> Tuple[Optional[bytes], int, int]:
    """
    Test Phase 1 authentication with specified transmission mode.
    
    Returns:
        Tuple of (encrypted_rndb, sw1, sw2) or (None, sw1, sw2) on failure
    """
    mode_str = "ESCAPE (control)" if use_escape else "TRANSMIT"
    print(f"\n  Testing Phase 1 with {mode_str} mode{description}...")
    
    # Set environment variable to force mode
    old_escape = os.environ.get('FORCE_ESCAPE', '')
    old_no_escape = os.environ.get('FORCE_NO_ESCAPE', '')
    
    try:
        if use_escape:
            os.environ['FORCE_ESCAPE'] = '1'
            os.environ.pop('FORCE_NO_ESCAPE', None)
        else:
            os.environ['FORCE_NO_ESCAPE'] = '1'
            os.environ.pop('FORCE_ESCAPE', None)
        
        # Build APDU manually to see exact bytes
        apdu = [0x90, 0x71, 0x00, 0x00, 0x02, key_no, 0x00, 0x00]
        print(f"    APDU: {' '.join(f'{b:02X}' for b in apdu)}")
        
        # Send command
        data, sw1, sw2 = card.send_apdu(apdu, use_escape=use_escape)
        
        print(f"    Response length: {len(data)} bytes")
        print(f"    Response data: {format_bytes(bytes(data))}")
        print(f"    Status Word: {sw1:02X} {sw2:02X}")
        
        if (sw1, sw2) == (0x91, 0xAF):  # SW_ADDITIONAL_FRAME
            if len(data) == 16:
                print(f"    [OK] Phase 1 successful - received 16 bytes encrypted RndB")
                return bytes(data), sw1, sw2
            else:
                print(f"    [WARN] Phase 1 returned SW=91AF but {len(data)} bytes (expected 16)")
                return bytes(data) if data else None, sw1, sw2
        else:
            print(f"    [ERROR] Phase 1 failed with SW={sw1:02X}{sw2:02X}")
            return None, sw1, sw2
            
    except Exception as e:
        print(f"    [EXCEPTION] {type(e).__name__}: {e}")
        return None, 0, 0
    finally:
        # Restore environment
        if old_escape:
            os.environ['FORCE_ESCAPE'] = old_escape
        elif 'FORCE_ESCAPE' in os.environ:
            os.environ.pop('FORCE_ESCAPE')
            
        if old_no_escape:
            os.environ['FORCE_NO_ESCAPE'] = old_no_escape
        elif 'FORCE_NO_ESCAPE' in os.environ:
            os.environ.pop('FORCE_NO_ESCAPE')

def test_phase2_with_mode(
    card,
    encrypted_rndb: bytes,
    key: bytes,
    use_escape: bool = True,
    delay_ms: int = 0,
    description: str = ""
) -> Tuple[Optional[bytes], int, int]:
    """
    Test Phase 2 authentication with specified transmission mode.
    
    Args:
        card: Card connection
        encrypted_rndb: Encrypted RndB from Phase 1
        key: Authentication key
        use_escape: Use escape mode (control) or transmit
        delay_ms: Delay in milliseconds before sending Phase 2
        description: Additional description for logging
    
    Returns:
        Tuple of (response_data, sw1, sw2) or (None, sw1, sw2) on failure
    """
    mode_str = "ESCAPE (control)" if use_escape else "TRANSMIT"
    print(f"\n  Testing Phase 2 with {mode_str} mode{description}...")
    
    if delay_ms > 0:
        print(f"    Adding {delay_ms}ms delay before Phase 2...")
        time.sleep(delay_ms / 1000.0)
    
    # Set environment variable to force mode
    old_escape = os.environ.get('FORCE_ESCAPE', '')
    old_no_escape = os.environ.get('FORCE_NO_ESCAPE', '')
    
    try:
        if use_escape:
            os.environ['FORCE_ESCAPE'] = '1'
            os.environ.pop('FORCE_NO_ESCAPE', None)
        else:
            os.environ['FORCE_NO_ESCAPE'] = '1'
            os.environ.pop('FORCE_ESCAPE', None)
        
        # Decrypt RndB
        cipher = AES.new(key, AES.MODE_ECB)
        rndb = cipher.decrypt(encrypted_rndb)
        print(f"    Decrypted RndB: {format_bytes(rndb)}")
        
        # Rotate RndB
        rndb_rotated = rndb[1:] + rndb[0:1]
        print(f"    Rotated RndB:   {format_bytes(rndb_rotated)}")
        
        # Generate RndA
        from Crypto.Random import get_random_bytes
        rnda = get_random_bytes(16)
        print(f"    Generated RndA: {format_bytes(rnda)}")
        
        # Encrypt response
        plaintext = rnda + rndb_rotated
        encrypted_data = cipher.encrypt(plaintext)
        print(f"    Encrypted data: {format_bytes(encrypted_data)}")
        print(f"    Plaintext len: {len(plaintext)} bytes, Encrypted len: {len(encrypted_data)} bytes")
        
        # Build APDU
        apdu = [0x90, 0xAF, 0x00, 0x00, len(encrypted_data)] + list(encrypted_data) + [0x00]
        print(f"    APDU length: {len(apdu)} bytes")
        print(f"    APDU header: {' '.join(f'{b:02X}' for b in apdu[:5])}...")
        print(f"    APDU tail: ...{format_bytes(encrypted_data[-8:])} {apdu[-1]:02X}")
        
        # Send command
        start_time = time.time()
        data, sw1, sw2 = card.send_apdu(apdu, use_escape=use_escape)
        elapsed = (time.time() - start_time) * 1000
        
        print(f"    Response time: {elapsed:.2f}ms")
        print(f"    Response length: {len(data)} bytes")
        if len(data) > 0:
            print(f"    Response data: {format_bytes(bytes(data))}")
        print(f"    Status Word: {sw1:02X} {sw2:02X}")
        
        if (sw1, sw2) == (0x91, 0x00):  # SW_OK
            print(f"    [OK] Phase 2 successful!")
            if len(data) == 32:
                print(f"    [OK] Received expected 32 bytes")
            else:
                print(f"    [WARN] Expected 32 bytes, got {len(data)}")
            return bytes(data), sw1, sw2
        elif (sw1, sw2) == (0x91, 0xAE):  # Wrong RndB'
            print(f"    [ERROR] Phase 2 failed: SW=91AE (Wrong RndB')")
            return None, sw1, sw2
        elif (sw1, sw2) == (0x91, 0xAF):  # Additional Frame
            print(f"    [INFO] Phase 2 returned SW=91AF (Additional Frame)")
            print(f"    Response length: {len(data)} bytes")
            # Try to get additional frame
            af_apdu = [0x90, 0xAF, 0x00, 0x00, 0x00]
            af_data, af_sw1, af_sw2 = card.send_apdu(af_apdu, use_escape=use_escape)
            print(f"    Additional frame response: {len(af_data)} bytes, SW={af_sw1:02X}{af_sw2:02X}")
            full_data = bytes(data) + bytes(af_data)
            if (af_sw1, af_sw2) == (0x91, 0x00) and len(full_data) == 32:
                print(f"    [OK] Phase 2 successful after additional frame!")
                return full_data, af_sw1, af_sw2
            return full_data if full_data else None, af_sw1, af_sw2
        else:
            print(f"    [ERROR] Phase 2 failed with SW={sw1:02X}{sw2:02X}")
            return None, sw1, sw2
            
    except Exception as e:
        print(f"    [EXCEPTION] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None, 0, 0
    finally:
        # Restore environment
        if old_escape:
            os.environ['FORCE_ESCAPE'] = old_escape
        elif 'FORCE_ESCAPE' in os.environ:
            os.environ.pop('FORCE_ESCAPE')
            
        if old_no_escape:
            os.environ['FORCE_NO_ESCAPE'] = old_no_escape
        elif 'FORCE_NO_ESCAPE' in os.environ:
            os.environ.pop('FORCE_NO_ESCAPE')

def main():
    """Main test function."""
    print_section("Reader Mode Comparison Test")
    print("\nThis script compares escape mode (control) vs transmit mode")
    print("to diagnose potential hardware/reader issues with authentication.")
    print("\nPress Ctrl+C to exit at any time.")
    
    try:
        with CardManager() as card:
            print_section("1. Initial Setup")
            
            # Select PICC application
            print("\n  Selecting PICC application...")
            SelectPiccApplication().execute(card)
            print("    [OK] PICC application selected")
            
            # Get chip version
            print("\n  Getting chip version...")
            version = GetChipVersion().execute(card)
            print(f"    Hardware: {version.hw_major_version}.{version.hw_minor_version}")
            print(f"    Software: {version.sw_major_version}.{version.sw_minor_version}")
            print(f"    UID: {format_bytes(version.uid)}")
            
            if version.hw_major_version == 48:
                print("    [INFO] Seritag tag detected (HW 48.0)")
            else:
                print(f"    [INFO] Standard NXP tag detected (HW {version.hw_major_version}.{version.hw_minor_version})")
            
            print_section("2. Phase 1 Comparison: Escape vs Transmit")
            
            # Test Phase 1 with escape mode
            encrypted_rndb_escape, sw1_esc, sw2_esc = test_phase1_with_mode(
                card, key_no=0, use_escape=True, description=" (ESCAPE)"
            )
            
            # Small delay between tests
            time.sleep(0.5)
            
            # Test Phase 1 with transmit mode
            encrypted_rndb_transmit, sw1_tx, sw2_tx = test_phase1_with_mode(
                card, key_no=0, use_escape=False, description=" (TRANSMIT)"
            )
            
            # Compare results
            print("\n  Phase 1 Comparison:")
            if encrypted_rndb_escape and encrypted_rndb_transmit:
                if encrypted_rndb_escape == encrypted_rndb_transmit:
                    print("    [OK] Both modes returned identical encrypted RndB")
                else:
                    print("    [WARN] Modes returned different encrypted RndB!")
                    print(f"      Escape:  {format_bytes(encrypted_rndb_escape)}")
                    print(f"      Transmit: {format_bytes(encrypted_rndb_transmit)}")
            
            # Use escape mode result for Phase 2 testing (or transmit if escape failed)
            encrypted_rndb = encrypted_rndb_escape or encrypted_rndb_transmit
            if not encrypted_rndb:
                print("\n  [ERROR] Phase 1 failed with both modes. Cannot continue.")
                return
            
            print_section("3. Phase 2 Comparison: Fresh Phase 1 + Phase 2 (Escape Mode)")
            print("\n  [INFO] Testing Phase 2 IMMEDIATELY after Phase 1 for each test")
            print("         (Each test starts fresh with new Phase 1)")
            
            # Test Phase 2 immediately after fresh Phase 1 (escape mode)
            print("\n  === TEST 1: Escape Mode (No Delay) ===")
            print("  Running fresh Phase 1 + Phase 2 sequence...")
            
            # Fresh Phase 1
            fresh_encrypted_rndb_1, p1_sw1, p1_sw2 = test_phase1_with_mode(
                card, key_no=0, use_escape=True, description=" (fresh, for Phase 2 test)"
            )
            
            if fresh_encrypted_rndb_1:
                # Phase 2 immediately after Phase 1
                result_escape, sw1_esc2, sw2_esc2 = test_phase2_with_mode(
                    card, fresh_encrypted_rndb_1, FACTORY_KEY,
                    use_escape=True, delay_ms=0, description=" (ESCAPE, immediately after Phase 1)"
                )
            else:
                print("    [SKIP] Phase 1 failed, cannot test Phase 2")
                result_escape, sw1_esc2, sw2_esc2 = None, 0, 0
            
            # Wait and try with transmit mode
            time.sleep(2.0)  # Give tag time to reset state
            
            print("\n  === TEST 2: Transmit Mode (No Delay) ===")
            print("  Running fresh Phase 1 + Phase 2 sequence...")
            
            # Fresh Phase 1 with transmit mode
            fresh_encrypted_rndb_2, p1_tx_sw1, p1_tx_sw2 = test_phase1_with_mode(
                card, key_no=0, use_escape=False, description=" (fresh, for Phase 2 test)"
            )
            
            if fresh_encrypted_rndb_2:
                # Phase 2 immediately after Phase 1
                result_transmit, sw1_tx2, sw2_tx2 = test_phase2_with_mode(
                    card, fresh_encrypted_rndb_2, FACTORY_KEY,
                    use_escape=False, delay_ms=0, description=" (TRANSMIT, immediately after Phase 1)"
                )
            else:
                print("    [SKIP] Phase 1 failed, cannot test Phase 2")
                result_transmit, sw1_tx2, sw2_tx2 = None, 0, 0
            
            print_section("4. Phase 2 with Timing Delays (Fresh Phase 1 each time)")
            
            # Test with delays - each test gets fresh Phase 1
            delays = [10, 50, 100]  # milliseconds
            
            for delay_ms in delays:
                time.sleep(2.0)  # Wait between tests
                print(f"\n  === Testing with {delay_ms}ms delay ===")
                print("  Running fresh Phase 1 + Phase 2 sequence...")
                
                # Fresh Phase 1
                fresh_encrypted_rndb_d, p1_d_sw1, p1_d_sw2 = test_phase1_with_mode(
                    card, key_no=0, use_escape=True, description=f" (fresh, for {delay_ms}ms delay test)"
                )
                
                if fresh_encrypted_rndb_d:
                    # Phase 2 with delay
                    result_delay, sw1_d, sw2_d = test_phase2_with_mode(
                        card, fresh_encrypted_rndb_d, FACTORY_KEY,
                        use_escape=True, delay_ms=delay_ms,
                        description=f" (ESCAPE, {delay_ms}ms delay)"
                    )
                    
                    if result_delay and (sw1_d, sw2_d) == (0x91, 0x00):
                        print(f"    [SUCCESS] Phase 2 succeeded with {delay_ms}ms delay!")
                        break
                else:
                    print(f"    [SKIP] Phase 1 failed, cannot test Phase 2 with {delay_ms}ms delay")
            
            print_section("5. Summary")
            
            print("\n  Phase 1 Results:")
            print(f"    Escape mode:  SW={sw1_esc:02X}{sw2_esc:02X}, Data={'OK' if encrypted_rndb_escape else 'FAIL'}")
            print(f"    Transmit mode: SW={sw1_tx:02X}{sw2_tx:02X}, Data={'OK' if encrypted_rndb_transmit else 'FAIL'}")
            
            print("\n  Phase 2 Results:")
            print(f"    Escape (no delay):  SW={sw1_esc2:02X}{sw2_esc2:02X}, Data={'OK' if result_escape else 'FAIL'}")
            print(f"    Transmit (no delay): SW={sw1_tx2:02X}{sw2_tx2:02X}, Data={'OK' if result_transmit else 'FAIL'}")
            
            if result_escape and (sw1_esc2, sw2_esc2) == (0x91, 0x00):
                print("\n  [SUCCESS] Phase 2 authentication successful with escape mode!")
            elif result_transmit and (sw1_tx2, sw2_tx2) == (0x91, 0x00):
                print("\n  [SUCCESS] Phase 2 authentication successful with transmit mode!")
            else:
                print("\n  [FAILURE] Phase 2 failed with both modes.")
                print("    This suggests the issue is NOT reader-specific.")
                print("    Possible causes:")
                print("      - Wrong key")
                print("      - Wrong RndB rotation")
                print("      - Tag-specific protocol difference")
            
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Test cancelled by user.")
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

