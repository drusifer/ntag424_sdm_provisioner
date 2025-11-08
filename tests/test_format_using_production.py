"""
Format PICC using production auth code.
"""

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from Crypto.Hash import CMAC
from Crypto.Cipher import AES


def format_picc():
    """Format PICC using production auth."""
    
    print("\n=== FORMAT PICC ===\n")
    
    with CardManager() as card:
        # Auth with factory key
        print("Authenticating with factory key...")
        SelectPiccApplication().execute(card)
        
        factory_key = bytes(16)
        session = Ntag424AuthSession(factory_key)
        session.authenticate(card, 0)
        
        print(f"  Ti: {session.session_keys.ti.hex()}")
        print(f"  Counter: {session.session_keys.cmd_counter}")
        print("  [OK]\n")
        
        # Build FORMAT_PICC command
        print("Sending FORMAT_PICC (0xFC)...")
        
        cmd_byte = 0xFC
        cmd_ctr = session.session_keys.cmd_counter
        
        # CMAC input: Cmd || CmdCtr || TI
        mac_input = bytearray()
        mac_input.append(cmd_byte)
        mac_input.extend(cmd_ctr.to_bytes(2, 'little'))
        mac_input.extend(session.session_keys.ti)
        
        print(f"  CMAC input: {bytes(mac_input).hex()}")
        
        # Calculate CMAC
        cmac_obj = CMAC.new(session.session_keys.session_mac_key, ciphermod=AES)
        cmac_obj.update(bytes(mac_input))
        cmac_full = cmac_obj.digest()
        
        # Truncate
        cmac_truncated = bytes([cmac_full[i] for i in range(1, 16, 2)])
        print(f"  CMAC: {cmac_truncated.hex()}")
        
        # Build APDU
        apdu = [0x90, cmd_byte, 0x00, 0x00, 0x08, *list(cmac_truncated), 0x00]
        
        print(f"  APDU: {' '.join(f'{b:02X}' for b in apdu)}")
        print()
        
        response, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
        print(f"  Response: SW={sw1:02X}{sw2:02X}")
        
        if (sw1, sw2) == (0x91, 0x00):
            print("\n" + "="*60)
            print("SUCCESS! TAG FORMATTED!")
            print("="*60)
            return True
        else:
            print(f"\n[ERROR] FORMAT failed: {sw1:02X}{sw2:02X}")
            return False


if __name__ == '__main__':
    try:
        format_picc()
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

