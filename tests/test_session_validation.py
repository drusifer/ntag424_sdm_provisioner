"""
Test session validation by trying a simple authenticated command first.

If GetKeyVersion works but ChangeKey doesn't, the issue is specific to ChangeKey.
If GetKeyVersion also fails, the session itself is broken.
"""

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication
from ntag424_sdm_provisioner.commands.sdm_commands import GetKeyVersion
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.commands.base import AuthenticatedConnection


def test_session_with_simple_command():
    """
    1. Authenticate
    2. Try GetKeyVersion (simple MAC command)
    3. If that works, session is valid
    4. Then try ChangeKey
    """
    
    print("\n=== TESTING SESSION VALIDATION ===\n")
    
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
        print("  [OK]\n")
        
        # Step 3: Try GetKeyVersion (simple command)
        print("Step 3: Testing GetKeyVersion...")
        auth_conn = AuthenticatedConnection(card, session)
        
        try:
            version = GetKeyVersion(0).execute(auth_conn)
            print(f"  Key 0 version: {version}")
            print(f"  Counter after: {session.session_keys.cmd_counter}")
            print("  [OK] GetKeyVersion worked!")
            print("\nSession is VALID! Authenticated commands work.")
        except Exception as e:
            print(f"  [ERROR] GetKeyVersion failed: {e}")
            print("\nSession is BROKEN! Even simple commands fail.")
            return False
        
        # Step 4: Now try ChangeKey
        print("\nStep 4: Testing ChangeKey...")
        from ntag424_sdm_provisioner.commands.change_key import ChangeKey
        
        new_key = bytes([1] + [0]*15)
        
        try:
            result = ChangeKey(0, new_key, None, 0x01).execute(auth_conn)
            print(f"  [OK] ChangeKey worked! {result}")
            print("\n" + "="*60)
            print("SUCCESS! CHANGEKEY WORKED!")
            print("="*60)
            return True
        except Exception as e:
            print(f"  [ERROR] ChangeKey failed: {e}")
            print("\nGetKeyVersion works but ChangeKey doesn't!")
            print("The issue is specific to ChangeKey implementation.")
            return False


if __name__ == '__main__':
    try:
        success = test_session_with_simple_command()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\nException: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

