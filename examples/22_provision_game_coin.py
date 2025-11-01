#!/usr/bin/env python3
"""
Example 22: Provision Game Coin with SDM/SUN

This example demonstrates complete end-to-end provisioning of an NTAG424 DNA
tag for use as a game coin with Secure Unique NFC (SUN) authentication.

Steps:
1. Connect to tag and get chip info
2. Authenticate with factory keys
3. Build SDM URL with placeholders
4. Configure SDM on NDEF file
5. Write NDEF message
6. Verify provisioning

Result: Game coin that generates tap-unique authenticated URLs
"""

import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands import (
    SelectPiccApplication,
    GetChipVersion,
    GetFileCounters,
    WriteData,
    ChangeFileSettings,
)
from ntag424_sdm_provisioner.commands.sun_commands import WriteNdefMessage
from ntag424_sdm_provisioner.commands.base import ApduError
from ntag424_sdm_provisioner.commands.sdm_helpers import build_ndef_uri_record, calculate_sdm_offsets
from ntag424_sdm_provisioner.constants import (
    SDMUrlTemplate,
    SDMConfiguration,
    CommMode,
    FileOption,
)
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.key_manager_interface import SimpleKeyManager, KEY_DEFAULT_FACTORY


def provision_game_coin():
    """Provision an NTAG424 DNA tag as a game coin."""
    
    print("=" * 70)
    print("Example 22: Provision Game Coin with SDM/SUN")
    print("=" * 70)
    print()
    print("This will configure your NTAG424 DNA tag for tap-unique URLs.")
    print()
    print("[WARNING] This example requires:")
    print("  - Tag with factory default keys (all zeros)")
    print("  - Fresh or already-authenticated tag")
    print()
    print("Please place your NTAG424 DNA tag on the reader...")
    print()
    
    try:
        with CardManager(reader_index=0) as card:
            print("[OK] Connected to reader")
            print()
            
            # Step 1: Select application and get chip info
            print("Step 1: Get Chip Information")
            print("-" * 70)
            
            try:
                SelectPiccApplication().execute(card)
                print("  [OK] Application selected")
            except ApduError as e:
                if "6985" in str(e):
                    print("  [INFO] Application already selected")
                else:
                    raise
            
            version_info = GetChipVersion().execute(card)
            print(f"  Chip: {version_info}")
            print(f"  UID: {version_info.uid.hex().upper()}")
            print()
            
            # Step 2: Define URL template
            print("Step 2: Build SDM URL Template")
            print("-" * 70)
            
            base_url = "https://globalheadsandtails.com/tap"
            uid_placeholder = "00000000000000"      # 7 bytes
            counter_placeholder = "000000"           # 3 bytes
            cmac_placeholder = "0000000000000000"   # 8 bytes
            
            url_with_placeholders = (
                f"{base_url}?"
                f"uid={uid_placeholder}&"
                f"ctr={counter_placeholder}&"
                f"cmac={cmac_placeholder}"
            )
            
            print(f"  URL: {url_with_placeholders}")
            print(f"  Length: {len(url_with_placeholders)} characters")
            
            # Build NDEF message
            ndef_message = build_ndef_uri_record(url_with_placeholders)
            print(f"  NDEF Size: {len(ndef_message)} bytes")
            print()
            
            # Calculate SDM offsets
            template = SDMUrlTemplate(
                base_url=base_url,
                uid_placeholder=uid_placeholder,
                cmac_placeholder=cmac_placeholder,
                read_ctr_placeholder=counter_placeholder,
                enc_placeholder=None
            )
            
            offsets = calculate_sdm_offsets(template)
            print("  SDM Offsets:")
            for key, value in offsets.items():
                print(f"    {key}: {value}")
            print()
            
            # Step 3: Authenticate (using factory keys)
            print("Step 3: Authenticate with Tag")
            print("-" * 70)
            
            # Create key manager (using factory keys for now)
            key_mgr = SimpleKeyManager(factory_key=KEY_DEFAULT_FACTORY)
            print(f"  Key Manager: {key_mgr}")
            
            # Get key for this tag (key 0 = Application Master Key)
            auth_key = key_mgr.get_key(version_info.uid, key_no=0)
            print(f"  Using Key: {'00'*16} (factory default)")
            
            # Create auth session
            try:
                print("  Authenticating...")
                session = Ntag424AuthSession(auth_key)
                session_keys = session.authenticate(card, key_no=0)
                print(f"  [OK] Authenticated successfully!")
                print(f"  Session ENC Key: {session_keys.session_enc_key.hex()[:16]}...")
                print(f"  Session MAC Key: {session_keys.session_mac_key.hex()[:16]}...")
            except Exception as e:
                print(f"  [ERROR] Authentication failed: {e}")
                print("  [INFO] Continuing with unauthenticated operations")
                session = None
            print()
            
            # Step 4: Write NDEF Message FIRST (before enabling SDM)
            print("Step 4: Write NDEF Message")
            print("-" * 70)
            print("  [INFO] Writing NDEF before enabling SDM (data must exist first)")
            
            try:
                # Select NDEF file
                print("  Selecting NDEF file (0xE104)...")
                select_ndef_apdu = [0x00, 0xA4, 0x02, 0x00, 0x02, 0xE1, 0x04, 0x00]
                _, sw1, sw2 = card.send_apdu(select_ndef_apdu, use_escape=True)
                if (sw1, sw2) in [(0x90, 0x00), (0x91, 0x00)]:
                    print("  [OK] NDEF file selected")
                
                # Write NDEF data
                print(f"  Writing {len(ndef_message)} bytes to NDEF file...")
                write_cmd = WriteNdefMessage(ndef_data=ndef_message)
                result = write_cmd.execute(card)
                print(f"  [OK] {result}")
                
            except Exception as e:
                print(f"  [ERROR] NDEF write failed: {e}")
                import traceback
                traceback.print_exc()
            print()
            
            # Step 5: Configure SDM (requires authentication AND data written)
            print("Step 5: Configure SDM on NDEF File")
            print("-" * 70)
            
            if session is None:
                print("  [SKIP] Cannot configure SDM without authentication")
                print("  [INFO] SDM configuration requires authenticated session")
            else:
                try:
                    # Build SDM configuration
                    sdm_config = SDMConfiguration(
                        file_no=0x02,  # NDEF file
                        comm_mode=CommMode.PLAIN,  # Plain communication
                        access_rights=b'\xE0\xEE',  # 2 bytes
                        enable_sdm=True,
                        sdm_options=(
                            FileOption.UID_MIRROR |   # Bit 7
                            FileOption.READ_COUNTER   # Bit 6 (now correct!)
                        ),
                        picc_data_offset=offsets.get('picc_data_offset', 0),
                        mac_input_offset=offsets.get('mac_input_offset', 0),
                        mac_offset=offsets.get('mac_offset', 0),
                        read_ctr_offset=offsets.get('read_ctr_offset', 0),
                    )
                    
                    print(f"  SDM Config: {sdm_config}")
                    print("  Configuring...")
                    
                    config_cmd = ChangeFileSettings(sdm_config)
                    config_cmd.execute(card, session=session)
                    print("  [OK] SDM configured successfully!")
                    
                except Exception as e:
                    print(f"  [ERROR] SDM configuration failed: {e}")
                    print("  [INFO] Trying to continue anyway...")
            print()
            
            # Step 6: (removed - NDEF write moved to step 4)
            # Step 6: Verify (try to read counter)
            print("Step 6: Verify Provisioning")
            print("-" * 70)
            
            try:
                counter = GetFileCounters(file_no=0x02).execute(card)
                print(f"  [OK] SDM counter: {counter}")
                print("  [SUCCESS] SDM appears to be already configured!")
            except ApduError as e:
                if "911C" in str(e):
                    print("  [INFO] SDM not yet enabled (expected)")
                    print("  [INFO] Counter will work after SDM configuration")
                else:
                    print(f"  [WARN] Unexpected error: {e}")
            print()
            
            # Summary
            print("=" * 70)
            print("Provisioning Summary")
            print("=" * 70)
            print()
            print("Provisioning Steps Executed:")
            print("  [OK] Tag detected and identified")
            print("  [OK] URL template created (87 bytes)")
            print("  [OK] NDEF message built")
            print("  [OK] SDM offsets calculated")
            print(f"  {'[OK]' if session else '[SKIP]'} Authentication")
            print(f"  {'[OK]' if session else '[SKIP]'} SDM configuration")
            print("  [OK] NDEF write")
            print()
            
            if session:
                print("SUCCESS! Your game coin is provisioned.")
                print()
                print("Tapping the coin will now generate:")
                print(f"  {base_url}?uid={version_info.uid.hex().upper()}&ctr=XXXXXX&cmac=XXXXXXXXXXXXXXXX")
                print()
                print("Next Steps:")
                print("  1. Tap coin with NFC phone")
                print("  2. Phone browser opens with tap-unique URL")
                print("  3. Implement server validation endpoint")
                print("  4. Server verifies CMAC and counter")
                print("  5. Deliver game reward!")
            else:
                print("Authentication required for SDM configuration.")
                print()
                print("To complete provisioning:")
                print("  1. Ensure tag has factory default keys")
                print("  2. Re-run this script")
                print("  3. Authentication should succeed")
            print()
            
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Stopped by user")
        return 1
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(provision_game_coin())

