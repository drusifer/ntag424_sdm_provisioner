"""
Test LRP Authentication and Alternative Authentication Methods

Tests:
1. LRP Authentication (PCDcap2.1 bit 1 = 1)
2. AuthenticateEV2NonFirst (0x77)
3. Command 0x51 with Phase 1 response data
"""
import sys
import os
import time

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication
from ntag424_sdm_provisioner.commands.base import ApduError
from ntag424_sdm_provisioner.constants import FACTORY_KEY, SW_OK, SW_ADDITIONAL_FRAME
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import logging

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)


def test_lrp_authentication(card):
    """Test LRP authentication (PCDcap2.1 bit 1 = 1)."""
    print("\n" + "=" * 80)
    print("TEST: LRP Authentication")
    print("=" * 80)
    print("\nLRP uses same 0x71 command but with PCDcap2.1 bit 1 = 1 (0x02)")
    print("Expected: AuthMode=0x01 (LRP) + 16 bytes RndB if LRP-enabled")
    
    try:
        # Phase 1 with LRP mode: LenCap=0x01, PCDcap2=[0x02]
        apdu = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x01, 0x02, 0x00]
        data, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
        
        if (sw1, sw2) == SW_ADDITIONAL_FRAME:
            print(f"[OK] Phase 1 returned SW=91AF with {len(data)} bytes")
            
            if len(data) == 17:
                auth_mode = data[0]
                rndb_data = bytes(data[1:17])
                print(f"  AuthMode: 0x{auth_mode:02X}")
                print(f"  RndB (16 bytes): {rndb_data.hex().upper()}")
                
                if auth_mode == 0x01:
                    print("[SUCCESS] LRP authentication mode detected!")
                    # TODO: Continue with LRP Phase 2
                    return True
                else:
                    print(f"[NOTE] AuthMode is 0x{auth_mode:02X}, not LRP (0x01)")
            elif len(data) == 16:
                print("[NOTE] Received 16 bytes (like EV2) - might not be LRP")
            else:
                print(f"[NOTE] Unexpected data length: {len(data)} bytes")
        else:
            print(f"[FAIL] SW={sw1:02X}{sw2:02X}")
            
    except Exception as e:
        print(f"[FAIL] Error: {e}")
    
    return False


def test_ev2_nonfirst(card):
    """Test AuthenticateEV2NonFirst (0x77)."""
    print("\n" + "=" * 80)
    print("TEST: AuthenticateEV2NonFirst (0x77)")
    print("=" * 80)
    print("\nUses 0x77 instead of 0x71 for Phase 1")
    print("Expected: Similar to EV2First but maybe different sequence")
    
    try:
        # Phase 1 with 0x77: KeyNo only, no LenCap/PCDcap2
        apdu = [0x90, 0x77, 0x00, 0x00, 0x01, 0x00, 0x00]
        data, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
        
        if (sw1, sw2) == SW_ADDITIONAL_FRAME:
            print(f"[OK] Phase 1 returned SW=91AF with {len(data)} bytes")
            print(f"  Data: {bytes(data).hex().upper()}")
            
            if len(data) == 16:
                print("[NOTE] 16 bytes like EV2First - might be same protocol")
                # Try Phase 2
                encrypted_rndb = bytes(data)
                cipher = AES.new(FACTORY_KEY, AES.MODE_ECB)
                rndb = cipher.decrypt(encrypted_rndb)
                rnda = get_random_bytes(16)
                rndb_rotated = rndb[1:] + rndb[0:1]
                plaintext = rnda + rndb_rotated
                encrypted_response = cipher.encrypt(plaintext)
                
                # Phase 2
                apdu2 = [0x90, 0xAF, 0x00, 0x00, 0x20] + list(encrypted_response) + [0x00]
                data2, sw1_2, sw2_2 = card.send_apdu(apdu2, use_escape=True)
                
                if (sw1_2, sw2_2) == SW_OK:
                    print("[SUCCESS] AuthenticateEV2NonFirst works!")
                    return True
                else:
                    print(f"[FAIL] Phase 2 SW={sw1_2:02X}{sw2_2:02X}")
            else:
                print(f"[NOTE] Unexpected data length: {len(data)} bytes")
        else:
            print(f"[FAIL] SW={sw1:02X}{sw2:02X}")
            
    except Exception as e:
        print(f"[FAIL] Error: {e}")
    
    return False


def test_command_51_with_data(card):
    """Test Command 0x51 with Phase 2 data."""
    print("\n" + "=" * 80)
    print("TEST: Command 0x51 with Phase 2 Data")
    print("=" * 80)
    print("\nSeritag-specific command - might be alternative Phase 2")
    
    try:
        # First get Phase 1
        apdu1 = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
        data1, sw1_1, sw2_1 = card.send_apdu(apdu1, use_escape=True)
        
        if (sw1_1, sw2_1) != SW_ADDITIONAL_FRAME or len(data1) != 16:
            print(f"[SKIP] Phase 1 failed: SW={sw1_1:02X}{sw2_1:02X}")
            return False
        
        encrypted_rndb = bytes(data1)
        cipher = AES.new(FACTORY_KEY, AES.MODE_ECB)
        rndb = cipher.decrypt(encrypted_rndb)
        rnda = get_random_bytes(16)
        rndb_rotated = rndb[1:] + rndb[0:1]
        plaintext = rnda + rndb_rotated
        encrypted_response = cipher.encrypt(plaintext)
        
        # Try 0x51 as Phase 2 with data
        print("\nVariation 1: 0x51 with 32 bytes data (like Phase 2)")
        apdu2 = [0x90, 0x51, 0x00, 0x00, 0x20] + list(encrypted_response) + [0x00]
        data2, sw1_2, sw2_2 = card.send_apdu(apdu2, use_escape=True)
        print(f"  SW={sw1_2:02X}{sw2_2:02X}, data={len(data2)} bytes")
        
        # Try 0x51 with different P1/P2
        print("\nVariation 2: 0x51 with data, P1=0x01")
        apdu3 = [0x90, 0x51, 0x01, 0x00, 0x20] + list(encrypted_response) + [0x00]
        data3, sw1_3, sw2_3 = card.send_apdu(apdu3, use_escape=True)
        print(f"  SW={sw1_3:02X}{sw2_3:02X}, data={len(data3)} bytes")
        
        # Try 0x51 with no data
        print("\nVariation 3: 0x51 with no data (after Phase 1)")
        apdu4 = [0x90, 0x51, 0x00, 0x00, 0x00]
        data4, sw1_4, sw2_4 = card.send_apdu(apdu4, use_escape=True)
        print(f"  SW={sw1_4:02X}{sw2_4:02X}, data={len(data4)} bytes")
        
        if (sw1_2, sw2_2) == SW_OK or (sw1_3, sw2_3) == SW_OK or (sw1_4, sw2_4) == SW_OK:
            print("[SUCCESS] Command 0x51 worked!")
            return True
        
    except Exception as e:
        print(f"[FAIL] Error: {e}")
    
    return False


def main():
    """Run all alternative authentication tests."""
    print("=" * 80)
    print("Seritag Alternative Authentication Methods Test")
    print("=" * 80)
    
    try:
        with CardManager(0, timeout_seconds=15) as card:
            # Select PICC
            SelectPiccApplication().execute(card)
            print("[OK] PICC selected")
            
            results = {}
            results['lrp'] = test_lrp_authentication(card)
            time.sleep(1)  # Delay between tests
            
            results['ev2_nonfirst'] = test_ev2_nonfirst(card)
            time.sleep(1)
            
            results['command_51'] = test_command_51_with_data(card)
            
            print("\n" + "=" * 80)
            print("Test Results Summary")
            print("=" * 80)
            for name, result in results.items():
                status = "[OK]" if result else "[FAIL]"
                print(f"{status} {name}: {result}")
            
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

