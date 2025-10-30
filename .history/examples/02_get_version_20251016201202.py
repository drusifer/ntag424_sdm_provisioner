import sys
from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
# Import both necessary commands
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion

def main():
    """Main execution function."""
    try:
        print("--- Example 02: Get Chip Version ---")
        print("Please tap and hold the NTAG424 tag on the reader...")

        # The CardManager now handles waiting and connecting
        with CardManager(0) as card:
            # STEP 1: Select the main application on the card. This is required!
            print("\n1. Selecting the PICC application...")
            select_command = SelectPiccApplication(use_escape=True)
            print(f"   EXECUTING: {select_command}")
            select_response = select_command.execute(card)
            print(f"   RESPONSE: {select_response}")
            
            # STEP 2: Now that the application is selected, get the version.
            print("\n2. Getting the chip version...")
            get_version_command = GetChipVersion(use_escape=True)
            print(f"   EXECUTING: {get_version_command}")
            version_info = get_version_command.execute(card)
            
            # The dataclass response now handles the pretty printing
            print("\n--- RESULT ---")
            print(version_info)
            print("\nDone.")

    except NTag242ConnectionError as e:
        print(f"\n❌ CONNECTION FAILED: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}", file=sys.stderr)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())