"""
Test which key works for authentication.

Try to authenticate with various keys to determine the tag's current state.
"""

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager


def test_which_key_works():
    """Try to authenticate with different keys to find which one works."""
    
    print("\n=== TESTING WHICH KEY WORKS ===\n")
    
    with CardManager() as card:
        # Get UID
        SelectPiccApplication().execute(card)
        version_info = GetChipVersion().execute(card)
        uid = version_info.uid
        print(f"Tag UID: {uid.hex().upper()}\n")
        
        # Try factory key first
        factory_key = bytes(16)
        print(f"Test 1: Factory key (0x00*16)")
        print(f"  Key: {factory_key.hex()}")
        
        try:
            session = Ntag424AuthSession(factory_key)
            session.authenticate(card, 0)
            print("  [OK] FACTORY KEY WORKS!")
            print("\nTag has factory keys. Not corrupted.")
            return "factory"
        except Exception as e:
            print(f"  [FAILED] {e}")
        
        # Try saved keys
        key_mgr = CsvKeyManager()
        try:
            saved_keys = key_mgr.get_tag_keys(uid)
            
            print(f"\nTest 2: Saved key from database")
            print(f"  Status: {saved_keys.status}")
            saved_key = saved_keys.get_picc_master_key_bytes()
            print(f"  Key: {saved_key.hex()}")
            
            try:
                session = Ntag424AuthSession(saved_key)
                session.authenticate(card, 0)
                print("  [OK] SAVED KEY WORKS!")
                print(f"\nTag has keys from database (status={saved_keys.status}).")
                return saved_keys.status
            except Exception as e:
                print(f"  [FAILED] {e}")
                
        except Exception:
            print("\nNo saved keys in database")
        
        # Try some common test keys
        test_keys = [
            bytes([1] + [0]*15),  # 0x01 followed by zeros
            bytes([0xFF]*16),      # All 0xFF
        ]
        
        for i, test_key in enumerate(test_keys, 3):
            print(f"\nTest {i}: Test key")
            print(f"  Key: {test_key.hex()}")
            
            try:
                session = Ntag424AuthSession(test_key)
                session.authenticate(card, 0)
                print("  [OK] THIS KEY WORKS!")
                print(f"\nTag has unexpected key: {test_key.hex()}")
                return "unknown"
            except Exception as e:
                print(f"  [FAILED] {e}")
        
        print("\n" + "="*60)
        print("[CONCLUSION] No known key works!")
        print("="*60)
        print("\nTag may be:")
        print("  1. Rate-limited (0x91AD) - wait 60 seconds")
        print("  2. In unknown state - needs hardware reset")
        print("  3. Requires Master Application key, not PICC key")
        
        return None


if __name__ == '__main__':
    result = test_which_key_works()
    if result == "factory":
        print("\nTag is OK. Issue is in our ChangeKey implementation.")
    elif result:
        print(f"\nTag state: {result}")
    else:
        print("\nCannot determine tag state.")

