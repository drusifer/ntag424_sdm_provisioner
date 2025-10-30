"""
Example script to perform a full EV2 authentication handshake with an NTAG424 tag.
"""
import sys
from pathlib import Path

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion, AuthenticateEV2First
from ntag424_sdm_provisioner.commands.sun_commands import ConfigureSunSettings, build_ndef_uri_record, WriteNdefMessage
from ntag424_sdm_provisioner.commands.base import ApduError
from ntag424_sdm_provisioner.constants import FACTORY_KEY

# The default factory key for NTAG424 DNA tags is 16 zero bytes.
DEFAULT_KEY = FACTORY_KEY
KEY_NO = 0  # Authenticate with the PICC Master Key


def main():
    """Connects to a card, authenticates, and prints session keys."""
    try:
        print("--- Example 04: EV2 Authentication ---")
        print("Please tap and hold the NTAG424 tag on the reader...")
        
        with CardManager(0) as card:
            print("\n1. Selecting the PICC application...")
            try:
                select_command = SelectPiccApplication()
                print(f"   EXECUTING: {select_command}")
                select_response = select_command.execute(card)
                print(f"   RESPONSE: {select_response}")
            except ApduError as se:
                # Some cards might already be in the correct state
                if "0x6985" in str(se):
                    print(f"   INFO: Application already selected (SW=6985)")
                else:
                    print(f"   WARNING: {se}")
                    print("   Continuing anyway...")
            
            print("\n2. Performing EV2 authentication...")
            print(f"   Using factory key: {DEFAULT_KEY.hex().upper()}")
            print(f"   Key number: {KEY_NO}")
            
            session = Ntag424AuthSession(DEFAULT_KEY)
            session_keys = session.authenticate(card, key_no=KEY_NO)

            print("\n" + "=" * 50)
            print("  ✅ EV2 Authentication Successful")
            print("=" * 50)
            print(f"Session Encryption Key: {session_keys.session_enc_key.hex().upper()}")
            print(f"Session MAC Key:        {session_keys.session_mac_key.hex().upper()}")
            print(f"Transaction ID:        {session_keys.ti.hex().upper()}")
            print(f"Command Counter:       {session_keys.cmd_counter}")
            print("=" * 50)
            print("\nDone.")

    except NTag242ConnectionError as e:
        print(f"\n❌ CONNECTION FAILED: {e}", file=sys.stderr)
        return 1
    except ApduError as e:
        print(f"\n❌ APDU ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
