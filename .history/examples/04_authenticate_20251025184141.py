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
            
            print("\n2. Getting chip version...")
            version_command = GetChipVersion()
            print(f"   EXECUTING: {version_command}")
            version_info = version_command.execute(card)
            print(f"   RESPONSE: {version_info}")
            
            # Check if this is a Seritag tag
            if version_info.hw_major_version == 48:
                print("\nSUCCESS: Detected Seritag NTAG424 DNA (HW 48.0)")
                print("   Seritag uses SUN (Secure Unique NFC) instead of full EV2 authentication")
                print("   Phase 1 authentication works, but Phase 2 is not supported")
                
                print("\n3. Testing Phase 1 authentication...")
                try:
                    cmd1 = AuthenticateEV2First(key_no=KEY_NO)
                    print(f"   EXECUTING: {cmd1}")
                    response1 = cmd1.execute(card)
                    print(f"   RESPONSE: Phase 1 SUCCESS - Challenge: {response1.challenge.hex().upper()}")
                    
                    print("\n4. Configuring SUN for secure authentication...")
                    try:
                        sun_config = ConfigureSunSettings(enable_sun=True)
                        print(f"   EXECUTING: {sun_config}")
                        sun_response = sun_config.execute(card)
                        print(f"   RESPONSE: {sun_response}")
                        
                        print("\n5. Writing NDEF URL for SUN authentication...")
                        base_url = "https://example.com/verify"
                        ndef_data = build_ndef_uri_record(base_url)
                        
                        write_command = WriteNdefMessage(ndef_data)
                        print(f"   EXECUTING: {write_command}")
                        write_response = write_command.execute(card)
                        print(f"   RESPONSE: {write_response}")
                        
                        print("\n" + "=" * 60)
                        print("  SUCCESS: Seritag SUN Configuration Complete")
                        print("=" * 60)
                        print("SUN provides dynamic authentication without full EV2:")
                        print(f"- Base URL: {base_url}")
                        print("- SUN will append: ?uid={version_info.uid.hex().upper()}&c=XXXX&mac=YYYY")
                        print("- Each scan generates unique authentication parameters")
                        print("- Server-side verification required for full security")
                        print("\nSee examples/06_sun_authentication.py for SUN setup")
                        print("See examples/07_sun_server_verification.py for server verification")
                        
                    except ApduError as e:
                        print(f"   WARNING: SUN configuration failed: {e}")
                        print("   Phase 1 authentication successful, but SUN setup incomplete")
                        
                except ApduError as e:
                    print(f"   ERROR: Phase 1 authentication failed: {e}")
                    return 1
                    
            else:
                print(f"\n📱 Standard NXP NTAG424 DNA detected (HW {version_info.hw_major_version}.{version_info.hw_minor_version})")
                print("   Attempting full EV2 authentication...")
                
                print("\n3. Performing EV2 authentication...")
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
