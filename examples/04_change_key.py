"""
Example script for changing a key on an NTAG424 DNA tag.

This script demonstrates:
1. Connecting to a reader.
2. Authenticating with a known key (the default factory key).
3. Changing Key 1 to a new, randomly generated key.
4. Re-authenticating with the NEW key to verify the change was successful.
5. Changing Key 1 BACK to the factory key so the script can be run again.
"""
import os
from ..hal import CardManager
from ..session import Ntag424Session
from .change_key import ChangeKey

# -- Configuration --
# The default factory key for NTAG424 DNA tags.
FACTORY_KEY = b'\x00' * 16

# We will demonstrate changing Application Key #1.
KEY_TO_CHANGE = 1


def main():
    """Main execution function."""
    print("NTAG424 DNA Key Change Example")
    print("------------------------------")

    # Generate a new random 16-byte key
    new_key = os.urandom(16)
    print(f"Generated new key: {new_key.hex().upper()}")

    try:
        with CardManager() as card:
            # --- Step 1: Authenticate with the OLD key (Factory Key) ---
            print("\nAttempting to authenticate with factory key...")
            session = Ntag424Session(card, key_no=KEY_TO_CHANGE, key=FACTORY_KEY)
            session.authenticate()
            print("Authentication successful.")

            # --- Step 2: Change the key to the NEW random value ---
            print(f"\nChanging Key {KEY_TO_CHANGE} to new random key...")
            change_to_new_cmd = ChangeKey(
                session=session,
                key_no=KEY_TO_CHANGE,
                new_key=new_key,
                old_key=FACTORY_KEY
            )
            change_to_new_cmd.execute(card)

            # --- Step 3: Verify the change by authenticating with the NEW key ---
            print("\nAttempting to authenticate with the NEW key to verify...")
            verify_session = Ntag424Session(card, key_no=KEY_TO_CHANGE, key=new_key)
            verify_session.authenticate()
            print("SUCCESS: Authentication with the new key was successful.")

            # --- Step 4: (Cleanup) Change the key BACK to the factory default ---
            print(f"\nChanging Key {KEY_TO_CHANGE} back to factory default...")
            change_back_cmd = ChangeKey(
                session=verify_session,  # Must use the currently active session
                key_no=KEY_TO_CHANGE,
                new_key=FACTORY_KEY,
                old_key=new_key
            )
            change_back_cmd.execute(card)
            print("Key has been reset to factory default.")

    except Exception as e:
        print(f"\nERROR: {e}")
        return


if __name__ == "__main__":
    main()
