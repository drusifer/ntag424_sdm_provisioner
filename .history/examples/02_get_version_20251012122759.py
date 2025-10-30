"""
Example 02: Connect to an NTAG424, select the PICC, and get its version.
"""
from __future__ import print_function
import sys
from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.base import ApduError
from ntag424_sdm_provisioner.commands.get_version import GetVersion
from ntag424_sdm_provisioner.commands.iso_select_file import IsoSelectFile

# NTAG424 uses 0x3F3F as the PICC master application ID
PICC_APPLICATION_ID = 0x3F3F


def main():
    """Main execution function."""
    try:
        # Use the first available reader
        with CardManager(0) as card:
            print("INFO: Card detected. ATR:", card.wait_for_atr())

            # 1. Select the PICC application
            select_picc_command = IsoSelectFile(file_id=PICC_APPLICATION_ID)
            select_picc_command.execute(card)

            # 2. Get the card version
            get_version_command = GetVersion()
            version_info = get_version_command.execute(card.connection)
            print("\n" + str(version_info))

    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        raise e
    return 0


if __name__ == "__main__":
    sys.exit(main())

