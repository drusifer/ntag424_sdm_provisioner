"""
Complete provisioning script for NTAG424 DNA for SDM.

This script orchestrates the entire process:
1. Connects to the tag.
2. Reads the tag's UID.
3. Authenticates with the factory PICC Master Key.
4. Uses a KeyManager to get new, unique keys for the tag.
5. Changes all keys from their factory defaults.
6. Re-authenticates with the new PICC Master Key.
7. Configures the NDEF file for full SDM functionality.
8. Writes a sample NDEF URI.
"""
import secrets

# --- Project Imports ---
from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.commands.base import ApduError, AuthenticationError
from ntag424_sdm_provisioner.constants import SDMConfiguration, CommMode
from ntag424_sdm_provisioner.commands.sdm_commands import (
    SelectPiccApplication, GetChipVersion, ChangeKey, WriteData, ReadData
)
from ntag424_sdm_provisioner.commands.change_file_settings import ChangeFileSettings
from ntag424_sdm_provisioner.key_manager import DerivingKeyGenerator, InMemoryKeyStorage, DerivedKeyManager
from ntag424_sdm_provisioner.commands.sdm_helpers import calculate_sdm_offsets, build_ndef_uri_record


# --- Configuration ---
# Use KeyManager for secure key derivation
MASTER_KEY = secrets.token_bytes(16)  # This should be stored securely in production

# The base URL to write to the tag. Placeholders will be replaced by the NFC device.
# {UID} will be replaced with the tag's UID.
# {CNT} will be replaced with the tap counter.
# {MAC} will be the security code.
NDEF_URI = "https://example.com/tag?uid={UID}&c={CNT}&mac={MAC}"

from ntag424_sdm_provisioner.constants import (
    FileNo, KeyNo, CommMode, AccessRight, AccessRights, 
    AccessRightsPresets, SDMOption, FACTORY_KEY
)

def provision_with_error_handling():
    """Provision with comprehensive error handling following the complete SDM flow."""
    
    try:
        with CardManager(0) as card:
            print("Step 1: Connecting to tag...")
            
            # Step 1: Select PICC Application
            SelectPiccApplication().execute(card)
            print("SUCCESS: PICC Application selected")
            
            # Step 2: Get Tag Information (UID and Version)
            print("Step 2: Getting tag information...")
            version_info = GetChipVersion().execute(card)
            tag_uid = version_info.uid
            print(f"SUCCESS: Tag UID: {tag_uid.hex().upper()}")
            print(f"SUCCESS: Hardware: {version_info.hw_major_version}.{version_info.hw_minor_version}")
            print(f"SUCCESS: Software: {version_info.sw_major_version}.{version_info.sw_minor_version}")
            
            # Step 2.5: Comprehensive Tag Diagnostics
            print("Step 2.5: Comprehensive tag diagnostics...")
            print("=" * 60)
            
            # Basic chip information
            print("CHIP INFORMATION:")
            print(f"  UID: {tag_uid.hex().upper()}")
            print(f"  Hardware Version: {version_info.hw_major_version}.{version_info.hw_minor_version}")
            print(f"  Software Version: {version_info.sw_major_version}.{version_info.sw_minor_version}")
            print(f"  Hardware Storage Size: {version_info.hw_storage_size} bytes")
            print(f"  Software Storage Size: {version_info.sw_storage_size} bytes")
            print(f"  Hardware Protocol: {version_info.hw_protocol}")
            print(f"  Software Protocol: {version_info.sw_protocol}")
            print(f"  Hardware Type: {version_info.hw_type}")
            print(f"  Software Type: {version_info.sw_type}")
            print()
            
            # Test all key numbers with factory key
            print("KEY AUTHENTICATION TEST:")
            factory_key_results = {}
            for key_no in [KeyNo.KEY_0, KeyNo.KEY_1, KeyNo.KEY_2, KeyNo.KEY_3, KeyNo.KEY_4]:
                try:
                    test_session = Ntag424AuthSession(FACTORY_KEY)
                    test_session.authenticate(card, key_no=key_no)
                    factory_key_results[key_no] = "SUCCESS"
                    print(f"  Key {key_no}: Factory key works")
                except ApduError as e:
                    factory_key_results[key_no] = f"FAILED ({e.sw1:02X}{e.sw2:02X})"
                    print(f"  Key {key_no}: Factory key failed - {e.sw1:02X}{e.sw2:02X}")
            
            print()
            
            # Test file access without authentication
            print("FILE ACCESS TEST (No Authentication):")
            file_tests = {}
            
            # Test NDEF file
            try:
                read_response = ReadData(FileNo.NDEF_FILE, 0, 16).execute(card)
                file_tests['NDEF'] = f"READABLE ({len(read_response.data)} bytes)"
                print(f"  NDEF File: Readable - {len(read_response.data)} bytes")
                if len(read_response.data) > 0:
                    print(f"    Data preview: {read_response.data[:16].hex().upper()}")
            except ApduError as e:
                file_tests['NDEF'] = f"ERROR ({e.sw1:02X}{e.sw2:02X})"
                print(f"  NDEF File: Error - {e.sw1:02X}{e.sw2:02X}")
            
            # Test other standard files
            for file_no in [FileNo.CC_FILE, FileNo.PROPRIETARY_FILE]:
                try:
                    read_response = ReadData(file_no, 0, 16).execute(card)
                    file_tests[f'File_{file_no}'] = f"READABLE ({len(read_response.data)} bytes)"
                    print(f"  File {file_no}: Readable - {len(read_response.data)} bytes")
                except ApduError as e:
                    file_tests[f'File_{file_no}'] = f"ERROR ({e.sw1:02X}{e.sw2:02X})"
                    print(f"  File {file_no}: Error - {e.sw1:02X}{e.sw2:02X}")
            
            print()
            
            # Test SDM capabilities
            print("SDM CAPABILITY TEST:")
            try:
                # Try to read file settings to see if SDM is configured
                read_response = ReadData(FileNo.NDEF_FILE, 0, 64).execute(card)
                print(f"  SDM Status: NDEF file accessible - {len(read_response.data)} bytes")
                if len(read_response.data) > 0:
                    # Look for NDEF TLV structure
                    if read_response.data[0] == 0x03:  # NDEF TLV
                        print("  SDM Status: NDEF TLV detected")
                        if len(read_response.data) > 1:
                            ndef_length = read_response.data[1]
                            print(f"  SDM Status: NDEF message length: {ndef_length} bytes")
            except ApduError as e:
                print(f"  SDM Status: Requires authentication - {e.sw1:02X}{e.sw2:02X}")
            
            print()
            
            # Memory layout analysis
            print("MEMORY LAYOUT ANALYSIS:")
            print(f"  Hardware Storage: {version_info.hw_storage_size} bytes")
            print(f"  Software Storage: {version_info.sw_storage_size} bytes")
            print(f"  NDEF File: File {FileNo.NDEF_FILE}")
            print(f"  Standard Data: File {FileNo.STANDARD_DATA_FILE}")
            print(f"  Value File: File {FileNo.VALUE_FILE}")
            
            print()
            
            # Security analysis
            print("SECURITY ANALYSIS:")
            auth_working_keys = [k for k, v in factory_key_results.items() if v == "SUCCESS"]
            if auth_working_keys:
                print(f"  Factory Key Works: Keys {auth_working_keys}")
                print("  Security Level: FACTORY STATE")
            else:
                print("  Factory Key: FAILED on all keys")
                print("  Security Level: CUSTOM KEYS CONFIGURED")
            
            readable_files = [f for f, v in file_tests.items() if "READABLE" in v]
            if readable_files:
                print(f"  Accessible Files: {readable_files}")
                print("  Access Level: SOME FILES OPEN")
            else:
                print("  Accessible Files: NONE")
                print("  Access Level: ALL FILES PROTECTED")
            
            print()
            
            # Configuration status
            print("CONFIGURATION STATUS:")
            if any("SUCCESS" in result for result in factory_key_results.values()):
                print("  Status: FACTORY STATE - Ready for provisioning")
                factory_auth_works = True
            else:
                print("  Status: CONFIGURED - Keys have been changed")
                factory_auth_works = False
                
            if any("READABLE" in result for result in file_tests.values()):
                print("  Files: SOME ACCESSIBLE - Partial configuration")
            else:
                print("  Files: ALL PROTECTED - Full security enabled")
            
            print("=" * 60)
            
            # Step 3: Initialize KeyManager
            print("Step 3: Initializing key management...")
            key_generator = DerivingKeyGenerator(MASTER_KEY)
            key_storage = InMemoryKeyStorage()
            key_manager = DerivedKeyManager(key_generator, key_storage)
            print("SUCCESS: KeyManager initialized")
            
            # Check if we should proceed with provisioning
            if not factory_auth_works:
                print("\nWARNING: Tag appears to be already configured!")
                print("WARNING: Factory key authentication failed - keys may have been changed.")
                print("WARNING: Continuing with provisioning may fail or overwrite existing configuration.")
                
                try:
                    response = input("Do you want to continue anyway? (y/N): ").strip().lower()
                    if response != 'y':
                        print("Provisioning cancelled by user.")
                        return
                except EOFError:
                    print("No interactive input available - continuing with provisioning...")
                print("Continuing with provisioning...")
            
            # Step 4: Authenticate with Factory Key
            print("Step 4: Authenticating with factory key...")
            print(f"   Using factory key: {FACTORY_KEY.hex().upper()}")
            print(f"   Trying key number: {KeyNo.KEY_0}")
            
            session = Ntag424AuthSession(FACTORY_KEY)
            session.authenticate(card, key_no=KeyNo.KEY_0)
            print("SUCCESS: Authenticated with factory key")
            
            # Step 5: Change Keys to Secure Values
            print("Step 5: Changing keys to secure values...")
            
            # Get new keys from KeyManager
            new_picc_key = key_manager.get_key_for_uid(tag_uid, KeyNo.KEY_0)
            new_file_key = key_manager.get_key_for_uid(tag_uid, KeyNo.KEY_1)
            new_sdm_key = key_manager.get_key_for_uid(tag_uid, KeyNo.KEY_2)
            
            # Change PICC Master Key (Key 0)
            ChangeKey(KeyNo.KEY_0, new_picc_key, FACTORY_KEY).execute(card)
            print("SUCCESS: PICC Master Key changed")
            
            # Change File Data Read Key (Key 1)
            ChangeKey(KeyNo.KEY_1, new_file_key, FACTORY_KEY).execute(card)
            print("SUCCESS: File Data Read Key changed")
            
            # Change SDM MAC Key (Key 2)
            ChangeKey(KeyNo.KEY_2, new_sdm_key, FACTORY_KEY).execute(card)
            print("SUCCESS: SDM MAC Key changed")
            
            # Step 6: Re-authenticate with New Keys
            print("Step 6: Re-authenticating with new keys...")
            new_session = Ntag424AuthSession(new_picc_key)
            new_session.authenticate(card, key_no=KeyNo.KEY_0)
            print("SUCCESS: Re-authenticated with new PICC Master Key")
            
            # Step 7: Calculate SDM Offsets from URL Template
            print("Step 7: Calculating SDM offsets...")
            from ntag424_sdm_provisioner.constants import SDMUrlTemplate
            url_template = SDMUrlTemplate(
                base_url=NDEF_URI,
                uid_placeholder="00000000000000",  # 14 hex chars
                cmac_placeholder="0000000000000000",  # 16 hex chars
                read_ctr_placeholder="00000000"  # 8 hex chars
            )
            offsets = calculate_sdm_offsets(url_template)
            print(f"SUCCESS: SDM offsets calculated: {offsets}")
            
            # Step 8: Configure SDM
            print("Step 8: Configuring SDM...")
            config = SDMConfiguration(
                file_no=FileNo.NDEF_FILE,
                comm_mode=CommMode.PLAIN,
                access_rights=AccessRightsPresets.FREE_READ_KEY0_WRITE.to_bytes(),
                enable_sdm=True,
                sdm_options=int(SDMOption.SDM_WITH_COUNTER),
                picc_data_offset=offsets['picc_data_offset'],
                mac_input_offset=offsets['mac_input_offset'],
                mac_offset=offsets['mac_offset'],
                read_ctr_offset=offsets.get('read_ctr_offset')
            )
            
            ChangeFileSettings(config).execute(card, session=new_session)
            print("SUCCESS: SDM configuration applied")
            
            # Step 9: Write NDEF Message
            print("Step 9: Writing NDEF message...")
            ndef_message = build_ndef_uri_record(NDEF_URI)
            WriteData(FileNo.NDEF_FILE, 0, ndef_message).execute(card)
            print("SUCCESS: NDEF message written")
            
            print("\n🎉 SDM Provisioning completed successfully!")
            print(f"Tag UID: {tag_uid.hex().upper()}")
            print(f"URL Template: {NDEF_URI}")
            print("The tag is now ready for SDM operation!")
            
    except ApduError as e:
        print(f"ERROR: APDU Error: {e}")
        print(f"   Category: {e.category.name}")
        
        if e.is_authentication_error():
            print("   -> Check your key!")
        elif e.is_permission_error():
            print("   -> Access rights not satisfied")
        elif e.is_not_found_error():
            print("   -> File or application not found")
    
    except AuthenticationError as e:
        print(f"ERROR: Authentication failed: {e}")
    
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()


def parse_existing_config():
    """Parse configuration read from card."""
    
    # Simulated data from GetFileSettings
    raw_access_rights = b'\xE0\xEE'
    
    # Parse into readable format
    rights = AccessRights.from_bytes(raw_access_rights)
    print(f"Parsed rights: {rights}")
    # Output: "Read=FREE, Write=KEY_0, RW=FREE, Change=FREE"
    
    # Check specific permissions
    if rights.read == AccessRight.FREE:
        print("SUCCESS: Anyone can read this file")
    
    if rights.write == AccessRight.KEY_0:
        print("SECURE: Write requires key 0")


def demonstrate_sdm_options():
    """Show SDM option combinations."""
    
    # Option 1: Basic SDM (UID mirror only)
    basic = SDMOption.ENABLED | SDMOption.UID_MIRROR
    
    # Option 2: Add read counter
    with_counter = basic | SDMOption.READ_COUNTER
    
    # Option 3: Use preset
    preset = SDMOption.SDM_WITH_COUNTER
    
    # Check flags
    if preset & SDMOption.UID_MIRROR:
        print("SUCCESS: UID mirror is enabled")
    
    if preset & SDMOption.READ_COUNTER:
        print("SUCCESS: Read counter is enabled")
    
    # Convert to byte for APDU
    options_byte = int(preset)  # 0xE0
    print(f"SDM options byte: 0x{options_byte:02X}")


def main():
    """Runs the full provisioning sequence."""
    print("--- NTAG424 SDM Provisioning Script ---")

    try:
        provision_with_error_handling()
        print("\n--- Provisioning completed successfully! SUCCESS ---")

    except Exception as e:
        print(f"\n--- An error occurred: {e} ---")
        print("Provisioning failed.")


if __name__ == "__main__":
    main()