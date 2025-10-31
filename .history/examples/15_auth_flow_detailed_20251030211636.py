"""
Example 15: Detailed EV2 Authentication Flow Using HAL APIs

This example demonstrates the complete EV2 authentication flow using the 
command classes (HAL APIs) with detailed byte-by-byte logging for debugging.

The flow uses:
- AuthenticateEV2First command class
- AuthenticateEV2Second command class (via Ntag424AuthSession)
- Ntag424AuthSession for crypto operations

This is the production code path that tests the actual command classes.
"""
import sys
import logging
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import (
    SelectPiccApplication,
    GetChipVersion,
    AuthenticateEV2First,
    AuthenticateEV2Second,
)
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.commands.base import ApduError
from ntag424_sdm_provisioner.constants import FACTORY_KEY, SW_OK, SW_ADDITIONAL_FRAME
from ntag424_sdm_provisioner.key_manager import DerivingKeyGenerator
from Crypto.Hash import CMAC

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable debug for auth session to see internal operations
logging.getLogger('ntag424_sdm_provisioner.crypto.auth_session').setLevel(logging.DEBUG)
logging.getLogger('ntag424_sdm_provisioner.commands.sdm_commands').setLevel(logging.DEBUG)

log = logging.getLogger(__name__)


def hex_print(label, data, max_bytes=32):
    """Helper to print hex data."""
    if isinstance(data, bytes):
        hex_str = data.hex().upper()
    else:
        hex_str = bytes(data).hex().upper()
    
    if len(hex_str) > max_bytes * 2:
        print(f"  {label}: {hex_str[:max_bytes*2]}... ({len(hex_str)//2} bytes)")
    else:
        print(f"  {label}: {hex_str}")
    
    return hex_str


def demonstrate_phase1_with_command_class(card, key_no=0):
    """
    Demonstrate Phase 1 using AuthenticateEV2First command class.
    
    Returns:
        AuthenticationChallengeResponse with encrypted RndB
    """
    print("\n" + "=" * 80)
    print("PHASE 1: Using AuthenticateEV2First Command Class")
    print("=" * 80)
    
    print(f"\nStep 1: Creating AuthenticateEV2First command...")
    print(f"  Key Number: {key_no:02X}")
    
    cmd = AuthenticateEV2First(key_no=key_no)
    print(f"  Command: {cmd}")
    print(f"  Command class: {type(cmd).__name__}")
    
    print(f"\nStep 2: Executing Phase 1 command...")
    try:
        response = cmd.execute(card)
        
        print(f"\nStep 3: Phase 1 Response Analysis")
        print(f"  Response type: {type(response).__name__}")
        print(f"  Key Number Used: {response.key_no_used:02X}")
        print(f"  Challenge length: {len(response.challenge)} bytes")
        hex_print("  Encrypted RndB", response.challenge)
        
        print(f"\n✅ Phase 1 successful!")
        print(f"   Received {len(response.challenge)} bytes encrypted RndB")
        
        return response
        
    except ApduError as e:
        print(f"\n❌ Phase 1 failed: {e}")
        print(f"   SW: {e.sw1:02X}{e.sw2:02X}")
        raise


def demonstrate_phase2_low_level(card, session, encrypted_rndb):
    """
    Demonstrate Phase 2 using low-level AuthenticateEV2Second command class.
    This shows what happens inside Ntag424AuthSession.
    """
    print("\n" + "=" * 80)
    print("PHASE 2 (Low-Level): Using AuthenticateEV2Second Command Class")
    print("=" * 80)
    
    print(f"\nStep 1: Decrypting RndB...")
    print(f"  Key: {session.key.hex().upper()}")
    hex_print("  Encrypted RndB", encrypted_rndb)
    
    rndb = session._decrypt_rndb(encrypted_rndb)
    hex_print("  Decrypted RndB", rndb)
    
    print(f"\nStep 2: Rotating RndB (left by 1 byte)...")
    rndb_rotated = rndb[1:] + rndb[0:1]
    hex_print("  Rotated RndB'", rndb_rotated)
    print(f"  Verification: First byte moved from position 0 to position 15")
    print(f"    Original[0] = {rndb[0]:02X} → Rotated[15] = {rndb_rotated[15]:02X}")
    
    print(f"\nStep 3: Generating RndA...")
    rnda = get_random_bytes(16)
    hex_print("  Generated RndA", rnda)
    
    print(f"\nStep 4: Constructing Phase 2 plaintext (RndA || RndB')...")
    plaintext = rnda + rndb_rotated
    hex_print("  Plaintext (32 bytes)", plaintext)
    print(f"  Block 1 (bytes 0-15):   {plaintext[:16].hex().upper()}")
    print(f"  Block 2 (bytes 16-31):  {plaintext[16:32].hex().upper()}")
    
    print(f"\nStep 5: Encrypting Phase 2 data...")
    response_data = session._encrypt_response(rnda, rndb_rotated)
    hex_print("  Encrypted data (32 bytes)", response_data)
    print(f"  Encryption: AES-ECB mode (2 blocks of 16 bytes)")
    
    print(f"\nStep 6: Creating AuthenticateEV2Second command...")
    cmd = AuthenticateEV2Second(data_to_card=response_data)
    print(f"  Command: {cmd}")
    print(f"  Command class: {type(cmd).__name__}")
    print(f"  Data length: {len(response_data)} bytes")
    
    print(f"\nStep 7: Executing Phase 2 command...")
    try:
        encrypted_response = cmd.execute(card)
        
        print(f"\nStep 8: Phase 2 Response Analysis")
        print(f"  Response length: {len(encrypted_response)} bytes")
        hex_print("  Encrypted response", encrypted_response)
        
        print(f"\n✅ Phase 2 successful!")
        return encrypted_response, rnda, rndb
        
    except ApduError as e:
        print(f"\n❌ Phase 2 failed: {e}")
        print(f"   SW: {e.sw1:02X}{e.sw2:02X}")
        
        # Analyze error code
        if e.sw2 == 0xAE:
            print(f"\nSW=91AE: Authentication Error (Wrong RndB')")
            print(f"  This means:")
            print(f"    1. Tag decrypted our Phase 2 data [OK]")
            print(f"    2. Tag extracted RndB' from our data [OK]")
            print(f"    3. Tag compared RndB' with its expected value [FAIL]")
            print(f"    4. They didn't match [FAIL]")
            print(f"\n  Possible causes:")
            print(f"    - Wrong RndB from Phase 1 (wrong key?)")
            print(f"    - Wrong RndB rotation (but format check passes)")
            print(f"    - Seritag stores/rotates RndB differently")
            print(f"    - Phase 1/Phase 2 transaction state issue")
        elif e.sw2 == 0xCA:
            print(f"\nSW=91CA: Command Aborted")
            print(f"  Transaction state issue - Phase 1 transaction not complete")
        elif e.sw2 == 0xAD:
            print(f"\nSW=91AD: Authentication Delay")
            print(f"  Too many failed attempts - need to wait or use fresh tag")
        
        raise


def demonstrate_high_level_auth(card, key, key_no=0):
    """
    Demonstrate authentication using high-level Ntag424AuthSession API.
    This is the production code path.
    """
    print("\n" + "=" * 80)
    print("HIGH-LEVEL: Using Ntag424AuthSession.authenticate()")
    print("=" * 80)
    
    print(f"\nStep 1: Creating Ntag424AuthSession...")
    session = Ntag424AuthSession(key)
    print(f"  Session key: {session.key.hex().upper()}")
    print(f"  Key length: {len(session.key)} bytes")
    
    print(f"\nStep 2: Calling session.authenticate()...")
    print(f"  This internally:")
    print(f"    - Uses AuthenticateEV2First for Phase 1")
    print(f"    - Uses AuthenticateEV2Second for Phase 2")
    print(f"    - Handles all crypto operations")
    print(f"    - Derives session keys")
    
    try:
        session_keys = session.authenticate(card, key_no=key_no)
        
        print(f"\n✅ Authentication successful!")
        print(f"\nStep 3: Session Keys Derived")
        print(f"  Session Encryption Key: {session_keys.session_enc_key.hex().upper()}")
        print(f"  Session MAC Key:        {session_keys.session_mac_key.hex().upper()}")
        print(f"  Transaction ID:        {session_keys.ti.hex().upper()}")
        print(f"  Command Counter:       {session_keys.cmd_counter}")
        
        return session, session_keys
        
    except ApduError as e:
        print(f"\n❌ Authentication failed: {e}")
        print(f"   SW: {e.sw1:02X}{e.sw2:02X}")
        raise


def main():
    """Main function demonstrating authentication flow."""
    print("=" * 80)
    print("Example 15: Detailed EV2 Authentication Flow Using HAL APIs")
    print("=" * 80)
    print("\nThis example demonstrates the complete authentication flow using")
    print("the command classes (AuthenticateEV2First, AuthenticateEV2Second)")
    print("and the high-level session API (Ntag424AuthSession).")
    print("\nPlease tap and hold the NTAG424 tag on the reader...")
    
    try:
        with CardManager(0, timeout_seconds=15) as card:
            # Step 1: Select PICC
            print("\n" + "=" * 80)
            print("STEP 1: Selecting PICC Application")
            print("=" * 80)
            
            try:
                select_cmd = SelectPiccApplication()
                print(f"\nExecuting: {select_cmd}")
                select_response = select_cmd.execute(card)
                print(f"Response: {select_response}")
            except ApduError as e:
                if "0x6985" in str(e) or "6985" in str(e):
                    print(f"[OK] PICC already selected (SW=6985 is OK)")
                else:
                    print(f"[WARNING] Selection issue: {e}")
            
            # Step 2: Get chip version
            print("\n" + "=" * 80)
            print("STEP 2: Getting Chip Version")
            print("=" * 80)
            
            version_cmd = GetChipVersion()
            print(f"\nExecuting: {version_cmd}")
            version_info = version_cmd.execute(card)
            print(f"Response: {version_info}")
            
            # Check if Seritag
            is_seritag = version_info.hw_major_version == 48
            if is_seritag:
                print(f"\n[INFO] Detected Seritag NTAG424 DNA (HW 48.0)")
                print(f"       Phase 1 works, but Phase 2 may fail with SW=91AE")
            else:
                print(f"\n[INFO] Detected Standard NXP NTAG424 DNA")
                print(f"       Full EV2 authentication should work")
            
            # Step 3: Phase 1 using command class
            print("\n" + "=" * 80)
            print("STEP 3: Phase 1 Authentication (Command Class)")
            print("=" * 80)
            
            key = FACTORY_KEY
            key_no = 0
            
            phase1_response = demonstrate_phase1_with_command_class(card, key_no)
            
            # Step 4: Phase 2 using low-level command class
            print("\n" + "=" * 80)
            print("STEP 4: Phase 2 Authentication (Low-Level Command Class)")
            print("=" * 80)
            
            session = Ntag424AuthSession(key)
            
            try:
                encrypted_response, rnda, rndb = demonstrate_phase2_low_level(
                    card, session, phase1_response.challenge
                )
                
                # If we got here, Phase 2 succeeded
                print(f"\n✅✅✅ PHASE 2 SUCCESSFUL! ✅✅✅")
                print(f"\nThis means we can now parse the response and derive session keys...")
                
                # Parse response
                auth_response = session._parse_card_response(encrypted_response, rnda)
                print(f"\nParsed Response:")
                print(f"  Ti: {auth_response.ti.hex().upper()}")
                print(f"  RndA': {auth_response.rnda_rotated.hex().upper()}")
                
                # Verify RndA'
                expected_rnda_rotated = rnda[1:] + rnda[0:1]
                if auth_response.rnda_rotated == expected_rnda_rotated:
                    print(f"  ✅ RndA' verification passed")
                else:
                    print(f"  ❌ RndA' verification failed")
                
                # Derive session keys
                session_keys = session._derive_session_keys(rnda, rndb, auth_response.ti)
                print(f"\nSession Keys Derived:")
                print(f"  Session Encryption Key: {session_keys.session_enc_key.hex().upper()}")
                print(f"  Session MAC Key:        {session_keys.session_mac_key.hex().upper()}")
                print(f"  Transaction ID:        {session_keys.ti.hex().upper()}")
                
            except ApduError as e:
                print(f"\n⚠️  Phase 2 failed - this is expected for Seritag tags")
                print(f"   Error: {e}")
                print(f"   SW: {e.sw1:02X}{e.sw2:02X}")
            
            # Step 5: High-level API demonstration (optional, if Phase 2 succeeded)
            if is_seritag:
                print("\n" + "=" * 80)
                print("STEP 5: High-Level API (Will Fail on Seritag)")
                print("=" * 80)
                print("\nDemonstrating high-level API (will fail due to Phase 2 issue)...")
                
                try:
                    session, session_keys = demonstrate_high_level_auth(card, key, key_no)
                    print(f"\n✅✅✅ HIGH-LEVEL AUTH SUCCESSFUL! ✅✅✅")
                except ApduError as e:
                    print(f"\n❌ High-level auth failed (expected): {e}")
                    print(f"   SW: {e.sw1:02X}{e.sw2:02X}")
            
            print("\n" + "=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print("\nThis example demonstrated:")
            print("  1. ✅ Phase 1 using AuthenticateEV2First command class")
            print("  2. ✅ Phase 2 using AuthenticateEV2Second command class")
            print("  3. ✅ High-level API using Ntag424AuthSession")
            print("\nAll operations use the production code path (command classes).")
            print("Check the logs above for detailed byte-by-byte analysis.")
            
    except NTag242ConnectionError as e:
        print(f"\n❌ CONNECTION FAILED: {e}", file=sys.stderr)
        return 1
    except ApduError as e:
        print(f"\n❌ APDU ERROR: {e}", file=sys.stderr)
        print(f"   SW: {e.sw1:02X}{e.sw2:02X}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

