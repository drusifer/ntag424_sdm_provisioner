"""
Test ChangeKey by changing Key 0 to the SAME value (factory to factory).

This eliminates any issues with key derivation - if this fails,
ChangeKey command itself has a problem.
"""

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.commands.base import AuthenticatedConnection
from ntag424_sdm_provisioner.crypto.crypto_primitives import build_changekey_apdu


def test_changekey_same_value():
    """
    Change Key 0 from factory (0x00*16) to factory (0x00*16).
    
    This should work if our crypto is correct.
    """
    
    print("\n=== TESTING CHANGEKEY TO SAME VALUE ===\n")
    
    with CardManager() as card:
        # Select and Auth
        print("Step 1: Select and Authenticate...")
        SelectPiccApplication().execute(card)
        
        factory_key = bytes(16)
        session = Ntag424AuthSession(factory_key)
        session.authenticate(card, 0)
        
        print(f"  Ti: {session.session_keys.ti.hex()}")
        print(f"  Counter: {session.session_keys.cmd_counter}")
        print("  [OK]\n")
        
        # Change Key 0 to itself
        print("Step 2: ChangeKey(0, factory_key -> factory_key)...")
        
        # Build APDU manually
        apdu = build_changekey_apdu(
            key_no=0,
            new_key=factory_key,  # Same as old!
            old_key=None,
            version=0x00,
            ti=session.session_keys.ti,
            cmd_ctr=session.session_keys.cmd_counter,
            session_enc_key=session.session_keys.session_enc_key,
            session_mac_key=session.session_keys.session_mac_key
        )
        
        print(f"  APDU: {' '.join(f'{b:02X}' for b in apdu[:20])}...")
        print()
        
        # Send it
        response, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
        print(f"  Response: SW={sw1:02X}{sw2:02X}")
        
        if (sw1, sw2) == (0x91, 0x00):
            print("\n" + "="*60)
            print("SUCCESS! CHANGEKEY WORKS!")
            print("="*60)
            print("\nThe tag is NOT corrupted!")
            print("The issue was something else...")
            return True
        else:
            print(f"\n[ERROR] Failed with {sw1:02X}{sw2:02X}")
            
            error_names = {
                0x911E: "INTEGRITY_ERROR - CMAC wrong",
                0x917E: "LENGTH_ERROR - Wrong length",
                0x919E: "PARAMETER_ERROR - Invalid param",
                0x91AE: "AUTHENTICATION_ERROR - Auth failed",
            }
            error_code = (sw1 << 8) | sw2
            if error_code in error_names:
                print(f"       ({error_names[error_code]})")
            
            print("\nEven changing to same value fails!")
            print("Either tag is corrupted OR our crypto is still wrong.")
            return False


if __name__ == '__main__':
    try:
        success = test_changekey_same_value()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\nException: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

