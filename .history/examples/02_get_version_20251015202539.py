"""
Example 02: Connect to an NTAG424, select the PICC, and get its version.
"""
from __future__ import print_function
import sys
from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.picc_commands import GetChipVersion


def main():
    """Main execution function."""
    try:
        # Use the first available reader
        with CardManager(0) as card:
            print("--- Example 02: Get Version ---")

            get_version_command = GetChipVersion()
            version_info = get_version_command.execute(card)
            print("\n" + str(version_info))

    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        raise e
    return 0

if __name__ == "__main__":
    sys.exit(main())

