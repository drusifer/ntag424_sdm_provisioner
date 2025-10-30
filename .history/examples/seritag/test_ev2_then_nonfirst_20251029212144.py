"""
Test AuthenticateEV2NonFirst (0x77) AFTER successful EV2First authentication.

Since 0x77 returned SW=919D (Not Enabled), maybe it requires prior authentication.
"""
import sys
import os
import time

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication
from ntag424_sdm_provisioner.constants import FACTORY_KEY, SW_OK, SW_ADDITIONAL_FRAME
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import logging

logging.basicConfig(level=logging.WARNING)


def test_ev2_then_nonfirst(card):
    """Test 0x77 after Phase 1 succeeds (without complete Phase 2)."""
    print("\n" + "=" * 80)
    print("TEST: EV2First -> EV2NonFirst (0x77)")
    print("=" * 80)
    print("\nIdea: Maybe 0x77 works if we do Phase 1 first (establishing transaction)")
    
    try:
        # Phase 1: Standard EV2First
        apdu1 = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
        data1, sw1_1, sw2_1 = card.send_apdu(apdu1, use_escape=True)
        
        if (sw1_1, sw2_1) != SW_ADDITIONAL_FRAME or len(data1) != 16:
            print(f"[SKIP] Phase 1 failed: SW={sw1_1:02X}{sw2_1:02X}")
            return False
        
        print(f"[OK] Phase 1 successful: {len(data1)} bytes")
        
        # Now try 0x77 (EV2NonFirst) - should continue transaction
        print("\nTrying 0x77 after Phase 1...")
        apdu2 = [0x90, 0x77, 0x00, 0x00, 0x01, 0x00, 0x00]
        data2, sw1_2, sw2_2 = card.send_apdu(apdu2, use_escape=True)
        
        if (sw1_2, sw2_2) == SW_ADDITIONAL_FRAME:
            print(f"[OK] 0x77 Phase 1 returned SW=91AF with {len(data2)} bytes")
            print(f"  Data: {bytes(data2).hex().upper()}")
            
            # Try Phase 2 with 0x77 transaction
            if len(data2) == 16:
                encrypted_rndb = bytes(data2)
                cipher = AES.new(FACTORY_KEY, AES.MODE_ECB)
                rndb = cipher.decrypt(encrypted_rndb)
                rnda = get_random_bytes(16)
                rndb_rotated = rndb[1:] + rndb[0:1]
                plaintext = rnda + rndb_rotated
                encrypted_response = cipher.encrypt(plaintext)
                
                apdu3 = [0x90, 0xAF, 0x00, 0x00, 0x20] + list(encrypted_response) + [0x00]
                data3, sw1_3, sw2_3 = card.send_apdu(apdu3, use_escape=True)
                
                if (sw1_3, sw2_3) == SW_OK:
                    print("[SUCCESS] EV2NonFirst after EV2First works!")
                    return True
                else:
                    print(f"[FAIL] Phase 2 SW={sw1_3:02X}{sw2_3:02X}")
            
            return False
        else:
            print(f"[FAIL] SW={sw1_2:02X}{sw2_2:02X}")
    
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    
    return False


def main():
    print("=" * 80)
    print("Test: EV2First -> EV2NonFirst Sequence")
    print("=" * 80)
    
    try:
        with CardManager(0, timeout_seconds=15) as card:
            SelectPiccApplication().execute(card)
            print("[OK] PICC selected")
            
            result = test_ev2_then_nonfirst(card)
            print(f"\n{'[SUCCESS]' if result else '[FAIL]'} Test result: {result}")
            
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")


if __name__ == "__main__":
    main()

