"""
Test Phase 2 byte alignment issues.

This verifies:
1. Actual APDU structure being sent
2. Whether padding/alignment is needed
3. Compare escape vs no-escape packet sizes
"""
import os
import sys

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import (
    SelectPiccApplication,
    AuthenticateEV2First,
    AuthenticateEV2Second,
)
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession


FACTORY_KEY = bytes(16)


def test_alignment():
    """Test Phase 2 with different alignment scenarios."""
    
    print("=" * 60)
    print("Phase 2 Byte Alignment Test")
    print("=" * 60)
    
    try:
        with CardManager(0, timeout_seconds=15) as card:
            # Select PICC
            SelectPiccApplication().execute(card)
            
            # Phase 1
            ch = AuthenticateEV2First(0x00).execute(card)
            print(f"\nPhase 1 successful: {len(ch.challenge)} bytes challenge")
            
            # Check APDU structure
            sess = Ntag424AuthSession(key=FACTORY_KEY)
            
            # Decrypt and process
            rndb = sess._decrypt_rndb(ch.challenge)
            rndb_rotated = rndb[1:] + rndb[0:1]
            rnda = b'\x00' * 16  # Test with known data
            
            # Encrypt Phase 2 data
            response_data = sess._encrypt_response(rnda, rndb_rotated)
            
            # Build APDU
            apdu = [0x90, 0xAF, 0x00, 0x00, len(response_data), *response_data, 0x00]
            
            print(f"\nAPDU Structure Analysis:")
            print(f"  Total length: {len(apdu)} bytes")
            print(f"  Header: 5 bytes (CLA, INS, P1, P2, Lc)")
            print(f"  Data: {len(response_data)} bytes")
            print(f"  Le: 1 byte")
            print(f"  Alignment to 4 bytes: {len(apdu) % 4 == 0}")
            print(f"  Alignment to 8 bytes: {len(apdu) % 8 == 0}")
            print(f"  Alignment to 16 bytes: {len(apdu) % 16 == 0}")
            
            # Test with escape (control)
            print(f"\n" + "-" * 60)
            print("Test 1: Escape Mode (control)")
            print("-" * 60)
            os.environ['FORCE_ESCAPE'] = '1'
            os.environ.pop('FORCE_NO_ESCAPE', None)
            
            try:
                cmd = AuthenticateEV2Second(data_to_card=response_data)
                result = cmd.execute(card)
                print("[OK] Phase 2 successful in escape mode")
                print(f"Response: {len(result)} bytes")
            except Exception as e:
                print(f"[FAIL] Phase 2 failed in escape mode: {e}")
            
            # Phase 1 again (needed for Phase 2)
            try:
                ch2 = AuthenticateEV2First(0x00).execute(card)
                rndb2 = sess._decrypt_rndb(ch2.challenge)
                rndb2_rotated = rndb2[1:] + rndb2[0:1]
                response_data2 = sess._encrypt_response(rnda, rndb2_rotated)
            except Exception:
                print("[SKIP] Phase 1 retry failed")
                return
            
            # Test with no-escape (transmit)
            print(f"\n" + "-" * 60)
            print("Test 2: No-Escape Mode (transmit)")
            print("-" * 60)
            os.environ['FORCE_NO_ESCAPE'] = '1'
            os.environ.pop('FORCE_ESCAPE', None)
            
            try:
                cmd = AuthenticateEV2Second(data_to_card=response_data2)
                result = cmd.execute(card)
                print("[OK] Phase 2 successful in no-escape mode")
                print(f"Response: {len(result)} bytes")
            except Exception as e:
                print(f"[FAIL] Phase 2 failed in no-escape mode: {e}")
            
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
    
    finally:
        # Cleanup env vars
        os.environ.pop('FORCE_ESCAPE', None)
        os.environ.pop('FORCE_NO_ESCAPE', None)


if __name__ == "__main__":
    test_alignment()

