"""
Phase 2 Authentication Test with Detailed Logging

This script performs Phase 1 and Phase 2 authentication with extensive logging
to capture exactly what's happening at each step.
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


def test_phase2_with_logging(card):
    """Test Phase 2 with detailed logging."""
    
    print("=" * 80)
    print("PHASE 2 AUTHENTICATION TEST WITH DETAILED LOGGING")
    print("=" * 80)
    
    # Step 1: Phase 1
    print("\n" + "-" * 80)
    print("STEP 1: Phase 1 - AuthenticateEV2First")
    print("-" * 80)
    
    print("\nBuilding Phase 1 APDU:")
    apdu_phase1 = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
    print(f"  APDU: {' '.join(f'{b:02X}' for b in apdu_phase1)}")
    print(f"  Length: {len(apdu_phase1)} bytes")
    print(f"  CLA: 0x{apdu_phase1[0]:02X}")
    print(f"  INS: 0x{apdu_phase1[1]:02X}")
    print(f"  P1:  0x{apdu_phase1[2]:02X}")
    print(f"  P2:  0x{apdu_phase1[3]:02X}")
    print(f"  Lc:  0x{apdu_phase1[4]:02X} (2 bytes)")
    print(f"  Data: {apdu_phase1[5]:02X} {apdu_phase1[6]:02X} (KeyNo=0x{apdu_phase1[5]:02X}, LenCap=0x{apdu_phase1[6]:02X})")
    print(f"  Le:  0x{apdu_phase1[7]:02X}")
    
    print("\nSending Phase 1...")
    data1, sw1_1, sw2_1 = card.send_apdu(apdu_phase1, use_escape=True)
    print(f"\nPhase 1 Response:")
    print(f"  Data length: {len(data1)} bytes")
    print(f"  SW: {sw1_1:02X}{sw2_1:02X}")
    print(f"  Data: {bytes(data1).hex().upper()}")
    
    if (sw1_1, sw2_1) != SW_ADDITIONAL_FRAME:
        print(f"\n[ERROR] Phase 1 failed: Expected SW=91AF, got SW={sw1_1:02X}{sw2_1:02X}")
        return False
    
    if len(data1) != 16:
        print(f"\n[ERROR] Phase 1 returned {len(data1)} bytes, expected 16")
        return False
    
    encrypted_rndb = bytes(data1)
    print(f"\n[OK] Phase 1 successful: Received 16 bytes encrypted RndB")
    
    # Step 2: Decrypt RndB
    print("\n" + "-" * 80)
    print("STEP 2: Decrypt RndB")
    print("-" * 80)
    
    print(f"\nKey: {FACTORY_KEY.hex().upper()}")
    print(f"Encrypted RndB: {encrypted_rndb.hex().upper()}")
    
    cipher = AES.new(FACTORY_KEY, AES.MODE_ECB)
    rndb = cipher.decrypt(encrypted_rndb)
    print(f"Decrypted RndB: {rndb.hex().upper()}")
    
    # Step 3: Rotate RndB
    print("\n" + "-" * 80)
    print("STEP 3: Rotate RndB (left by 1 byte)")
    print("-" * 80)
    
    rndb_rotated = rndb[1:] + rndb[0:1]
    print(f"Original:  {rndb.hex().upper()}")
    print(f"Rotated:   {rndb_rotated.hex().upper()}")
    print(f"First byte moved to end: {rndb[0]:02X} -> position 15")
    
    # Step 4: Generate RndA
    print("\n" + "-" * 80)
    print("STEP 4: Generate RndA")
    print("-" * 80)
    
    rnda = get_random_bytes(16)
    print(f"Generated RndA: {rnda.hex().upper()}")
    
    # Step 5: Build Phase 2 plaintext
    print("\n" + "-" * 80)
    print("STEP 5: Build Phase 2 Plaintext")
    print("-" * 80)
    
    plaintext = rnda + rndb_rotated
    print(f"Plaintext (32 bytes):")
    print(f"  First 16 bytes (RndA):  {rnda.hex().upper()}")
    print(f"  Second 16 bytes (RndB'): {rndb_rotated.hex().upper()}")
    print(f"  Full plaintext:        {plaintext.hex().upper()}")
    print(f"  Total length: {len(plaintext)} bytes")
    
    # Step 6: Encrypt Phase 2 plaintext
    print("\n" + "-" * 80)
    print("STEP 6: Encrypt Phase 2 Plaintext")
    print("-" * 80)
    
    print(f"Encryption mode: AES-ECB (no padding)")
    print(f"Key: {FACTORY_KEY.hex().upper()}")
    
    encrypted_response = cipher.encrypt(plaintext)
    print(f"\nEncrypted response (32 bytes):")
    print(f"  {encrypted_response.hex().upper()}")
    print(f"  Length: {len(encrypted_response)} bytes")
    
    # Verify encryption - decrypt to check
    decrypted_check = cipher.decrypt(encrypted_response)
    if decrypted_check == plaintext:
        print(f"  [OK] Encryption/decryption round-trip verified")
    else:
        print(f"  [ERROR] Encryption mismatch!")
        print(f"    Original:  {plaintext.hex().upper()}")
        print(f"    Decrypted: {decrypted_check.hex().upper()}")
    
    # Step 7: Build Phase 2 APDU
    print("\n" + "-" * 80)
    print("STEP 7: Build Phase 2 APDU")
    print("-" * 80)
    
    apdu_phase2 = [0x90, 0xAF, 0x00, 0x00, len(encrypted_response), *encrypted_response, 0x00]
    print(f"\nPhase 2 APDU:")
    print(f"  Full APDU: {' '.join(f'{b:02X}' for b in apdu_phase2)}")
    print(f"  Total length: {len(apdu_phase2)} bytes")
    print(f"  CLA: 0x{apdu_phase2[0]:02X}")
    print(f"  INS: 0x{apdu_phase2[1]:02X}")
    print(f"  P1:  0x{apdu_phase2[2]:02X}")
    print(f"  P2:  0x{apdu_phase2[3]:02X}")
    print(f"  Lc:  0x{apdu_phase2[4]:02X} ({apdu_phase2[4]} bytes = 32 bytes)")
    print(f"  Data (first 16 bytes): {' '.join(f'{b:02X}' for b in encrypted_response[:16])}...")
    print(f"  Data (last 16 bytes): ...{' '.join(f'{b:02X}' for b in encrypted_response[16:])}")
    print(f"  Le:  0x{apdu_phase2[-1]:02X}")
    
    # Step 8: Send Phase 2
    print("\n" + "-" * 80)
    print("STEP 8: Send Phase 2")
    print("-" * 80)
    
    print("\nSending Phase 2 APDU...")
    print(f"  Using escape mode: True")
    print(f"  Time since Phase 1: immediate (same transaction)")
    
    data2, sw1_2, sw2_2 = card.send_apdu(apdu_phase2, use_escape=True)
    
    print(f"\nPhase 2 Response:")
    print(f"  SW: {sw1_2:02X}{sw2_2:02X}")
    print(f"  Data length: {len(data2)} bytes")
    if data2:
        print(f"  Data: {bytes(data2).hex().upper()}")
    
    # Analyze response
    print("\n" + "-" * 80)
    print("STEP 9: Analyze Response")
    print("-" * 80)
    
    if (sw1_2, sw2_2) == SW_OK:
        print("[SUCCESS] Phase 2 authentication successful!")
        if len(data2) >= 32:
            print(f"\nDecrypting card response:")
            decrypted_response = cipher.decrypt(bytes(data2[:32]))
            print(f"  Encrypted: {bytes(data2[:32]).hex().upper()}")
            print(f"  Decrypted: {decrypted_response.hex().upper()}")
            if len(decrypted_response) >= 32:
                ti = decrypted_response[0:4]
                rnda_prime = decrypted_response[4:20]
                print(f"  Ti (4 bytes):    {ti.hex().upper()}")
                print(f"  RndA' (16 bytes): {rnda_prime.hex().upper()}")
                expected_rnda_rotated = rnda[1:] + rnda[0:1]
                if rnda_prime == expected_rnda_rotated:
                    print(f"  [OK] RndA' matches expected rotation")
                else:
                    print(f"  [ERROR] RndA' mismatch!")
                    print(f"    Expected: {expected_rnda_rotated.hex().upper()}")
                    print(f"    Got:      {rnda_prime.hex().upper()}")
        return True
    else:
        print(f"[FAIL] Phase 2 failed: SW={sw1_2:02X}{sw2_2:02X}")
        
        # Status word analysis
        if sw2_2 == 0xAE:
            print("\nSW=91AE: Authentication Error")
            print("  Spec meaning: 'Wrong RndB''")
            print("  This means the tag decrypted our Phase 2 data but the RndB' doesn't match")
            print("  Possible causes:")
            print("    - Wrong key")
            print("    - Wrong RndB extraction/rotation")
            print("    - Wrong encryption format")
            print("    - Seritag protocol difference")
        elif sw2_2 == 0xCA:
            print("\nSW=91CA: Command Aborted")
            print("  Spec meaning: 'Previous command not fully completed'")
            print("  Phase 1 transaction might not be properly established")
        elif sw2_2 == 0xAD:
            print("\nSW=91AD: Authentication Delay")
            print("  Too many failed attempts - need to wait")
        elif sw2_2 == 0x7E:
            print("\nSW=917E: Length Error")
            print("  Command length invalid")
        elif sw2_2 == 0x1C:
            print("\nSW=911C: Illegal Command Code")
            print("  Command not recognized")
        else:
            print(f"\nUnknown SW={sw1_2:02X}{sw2_2:02X}")
        
        return False


def test_getfilesettings_after_phase1(card):
    """Test GetFileSettings after Phase 1 (before Phase 2)."""
    print("\n" + "=" * 80)
    print("TEST: GetFileSettings After Phase 1")
    print("=" * 80)
    print("\nHypothesis: Maybe GetFileSettings needs Phase 1 transaction active")
    
    # Phase 1
    print("\nStep 1: Phase 1 - AuthenticateEV2First")
    apdu_phase1 = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
    data1, sw1_1, sw2_1 = card.send_apdu(apdu_phase1, use_escape=True)
    
    if (sw1_1, sw2_1) != SW_ADDITIONAL_FRAME or len(data1) != 16:
        print(f"[FAIL] Phase 1 failed: SW={sw1_1:02X}{sw2_1:02X}")
        return False
    
    print(f"[OK] Phase 1 successful: {len(data1)} bytes challenge")
    
    # Try GetFileSettings immediately after Phase 1
    print("\nStep 2: GetFileSettings immediately after Phase 1")
    print("Note: GetFileSettings requires CommMode.MAC (per spec)")
    print("      But maybe Phase 1 transaction enables it?")
    
    for file_no in [0x02, 0x03]:
        print(f"\n  GetFileSettings for file 0x{file_no:02X}:")
        apdu_fs = [0x90, 0xF5, 0x00, 0x00, 0x01, file_no, 0x00]
        print(f"    APDU: {' '.join(f'{b:02X}' for b in apdu_fs)}")
        
        data_fs, sw1_fs, sw2_fs = card.send_apdu(apdu_fs, use_escape=True)
        print(f"    Response: SW={sw1_fs:02X}{sw2_fs:02X}, Data={len(data_fs)} bytes")
        
        if data_fs:
            print(f"    Data: {bytes(data_fs).hex().upper()}")
        
        if (sw1_fs, sw2_fs) == SW_OK:
            print(f"    [OK] GetFileSettings returned data!")
            return True
        elif sw2_fs == 0xCA:
            print(f"    [NOTE] SW=91CA (Command Aborted) - transaction still open")
        elif sw2_fs == 0xAE:
            print(f"    [NOTE] SW=91AE (Auth Error) - still needs full authentication")
        elif sw2_fs == 0x9D:
            print(f"    [NOTE] SW=919D (Permission Denied) - access rights")
    
    return False


def main():
    """Run Phase 2 test with detailed logging."""
    try:
        with CardManager(0, timeout_seconds=15) as card:
            SelectPiccApplication().execute(card)
            print("[OK] PICC selected\n")
            
            # Test GetFileSettings after Phase 1 first
            result1 = test_getfilesettings_after_phase1(card)
            
            print("\n" + "=" * 80)
            print("\n" + "=" * 80)
            
            # Main Phase 2 test
            result2 = test_phase2_with_logging(card)
            
            print("\n" + "=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print(f"GetFileSettings after Phase 1: {'[SUCCESS]' if result1 else '[FAIL]'}")
            print(f"Phase 2 authentication: {'[SUCCESS]' if result2 else '[FAIL]'}")
            print("\nReview the detailed log above to identify the issue")
            print("=" * 80)
            
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

