"""
Example 02: Connect to an NTAG424, select the PICC, and get its version.
"""
from __future__ import print_function
import sys
from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import GetChipVersion, SelectPiccApplication


def main():
    """Main execution function."""
    try:
        # Use the first available reader
        with CardManager(0) as card:
            print("--- Example 02: Get Version ---")

            # STEP 1: Select the main application on the card. This is required!
            print("\n1. Selecting the PICC application...")
            select_command = SelectPiccApplication(use_escape=True)

            print(str(select_command))
            select_response = select_command.execute(card)
            print(str(select_response))
            get_version_command = GetChipVersion()
            version_info = get_version_command.execute(card)
            print("\n" + str(version_info))

    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        raise e
    return 0

if __name__ == "__main__":
    sys.exit(main())

