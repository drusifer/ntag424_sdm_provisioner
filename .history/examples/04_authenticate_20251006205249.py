"""
Example script to perform a full authentication handshake with an NTAG424 tag.
"""
import sys
from pathlib import Path

from ntag424_sdm_provisioner import hal
from ntag424_sdm_provisioner.session import Ntag424Session
from ntag424_sdm_provisioner.commands.base import ApduError

# The default factory key for NTAG424 DNA tags is 16 zero bytes.
DEFAULT_KEY = b'\x00' * 16
KEY_NO = 0  # Authenticate with the PICC Master Key


def main():
    """Connects to a card, authenticates, and prints session keys."""
    try:
        with hal.CardManager() as card:
            print("INFO: Authenticating with default factory key...")

            session = Ntag424Session(card.connection, key_no=KEY_NO, key=DEFAULT_KEY)
            session.authenticate()

            print("\n" + "=" * 20)
            print("  Authentication Successful")
            print("=" * 20)
            print(f"SesAuthMACKey: {session.ses_auth_mac_key.hex()}")
            print(f"   SesEncKey: {session.ses_enc_key.hex()}")
            print("=" * 20)

    except hal.NoCardException:
        print("ERROR: No card detected.")
    except ApduError as e:
        print(f"ERROR: APDU command failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
