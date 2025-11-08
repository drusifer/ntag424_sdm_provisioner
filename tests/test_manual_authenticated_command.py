"""
Manually build and send an authenticated GetKeyVersion command.

This bypasses our command classes to test if the session actually works.
"""

import sys
from pathlib import Path

tests_dir = Path(__file__).parent
sys.path.insert(0, str(tests_dir))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from Crypto.Hash import CMAC
from Crypto.Cipher import AES


def test_manual_authenticated_getkey():
    """
    Manually build GetKeyVersion with CMAC to test if session works.
    """
    
    print("\n=== MANUAL AUTHENTICATED COMMAND TEST ===\n")
    
    with CardManager() as card:
        # Step 1: Select and Authenticate
        print("Step 1: Selecting PICC...")
        SelectPiccApplication().execute(card)
        print("  [OK]\n")
        
        print("Step 2: Authenticating...")
        factory_key = bytes(16)
        session = Ntag424AuthSession(factory_key)
        session.authenticate(card, 0)
        
        print(f"  Ti: {session.session_keys.ti.hex()}")
        print(f"  Counter: {session.session_keys.cmd_counter}")
        print(f"  Session MAC key: {session.session_keys.session_mac_key.hex()}")
        print("  [OK]\n")
        
        # Step 3: Manually build authenticated GetKeyVersion
        print("Step 3: Building authenticated GetKeyVersion...")
        
        key_no_to_query = 0
        cmd_byte = 0x64  # GetKeyVersion
        
        # CMAC input: Cmd || CmdCtr || TI || KeyNo
        mac_input = bytearray()
        mac_input.append(cmd_byte)
        mac_input.extend(session.session_keys.cmd_counter.to_bytes(2, 'little'))
        mac_input.extend(session.session_keys.ti)
        mac_input.append(key_no_to_query)
        
        print(f"  CMAC input ({len(mac_input)} bytes): {bytes(mac_input).hex()}")
        
        # Calculate CMAC
        cmac_obj = CMAC.new(session.session_keys.session_mac_key, ciphermod=AES)
        cmac_obj.update(bytes(mac_input))
        cmac_full = cmac_obj.digest()
        
        # Truncate (even-numbered bytes)
        cmac_truncated = bytes([cmac_full[i] for i in range(1, 16, 2)])
        
        print(f"  CMAC (full): {cmac_full.hex()}")
        print(f"  CMAC (truncated): {cmac_truncated.hex()}")
        
        # Build APDU: CLA CMD P1 P2 Lc KeyNo CMAC Le
        apdu = [
            0x90,              # CLA
            cmd_byte,          # CMD (0x64)
            0x00,              # P1
            0x00,              # P2
            0x09,              # Lc (1 + 8 = KeyNo + CMAC)
            key_no_to_query,   # KeyNo
            *list(cmac_truncated),  # CMAC (8 bytes)
            0x00               # Le
        ]
        
        print(f"\n  Full APDU ({len(apdu)} bytes):")
        print(f"    {' '.join(f'{b:02X}' for b in apdu)}")
        
        # Step 4: Send it
        print("\nStep 4: Sending command...")
        response, sw1, sw2 = card.send_apdu(apdu, use_escape=False)
        
        print(f"  Response: {len(response)} bytes, SW={sw1:02X}{sw2:02X}")
        
        if (sw1, sw2) == (0x91, 0x00):
            print("\n" + "="*60)
            print("SUCCESS! AUTHENTICATED COMMAND WORKED!")
            print("="*60)
            print(f"\nKey version response: {bytes(response).hex()}")
            print("\nSession is VALID! Now we can try ChangeKey...")
            
            # Increment counter for next command
            session.session_keys.cmd_counter += 1
            
            # Now try ChangeKey
            from ntag424_sdm_provisioner.crypto.crypto_primitives import build_changekey_apdu
            
            print("\nStep 5: Trying ChangeKey with verified crypto...")
            new_key = bytes([1] + [0]*15)
            
            changekey_apdu = build_changekey_apdu(
                key_no=0,
                new_key=new_key,
                old_key=None,
                version=0x01,
                ti=session.session_keys.ti,
                cmd_ctr=session.session_keys.cmd_counter,
                session_enc_key=session.session_keys.session_enc_key,
                session_mac_key=session.session_keys.session_mac_key
            )
            
            print(f"  ChangeKey APDU ({len(changekey_apdu)} bytes)")
            
            response, sw1, sw2 = card.send_apdu(changekey_apdu, use_escape=False)
            print(f"  Response: SW={sw1:02X}{sw2:02X}")
            
            if (sw1, sw2) == (0x91, 0x00):
                print("\n" + "="*60)
                print("SUCCESS! CHANGEKEY WORKED!")
                print("="*60)
                return True
            else:
                print(f"\n[ERROR] ChangeKey failed: {sw1:02X}{sw2:02X}")
                return False
                
        else:
            print(f"\n[ERROR] GetKeyVersion failed with {sw1:02X}{sw2:02X}")
            
            error_names = {
                0x911E: "INTEGRITY_ERROR - CMAC wrong",
                0x917E: "LENGTH_ERROR - Wrong length",
                0x919E: "PARAMETER_ERROR - Invalid param",
            }
            error_code = (sw1 << 8) | sw2
            if error_code in error_names:
                print(f"       ({error_names[error_code]})")
            
            print("\nEven manually built authenticated command fails!")
            print("Session or CMAC is fundamentally broken.")
            return False


if __name__ == '__main__':
    try:
        success = test_manual_authenticated_getkey()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\nException: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

