#!/usr/bin/env python3
"""
Example 20: Get File Counters (SDM Read Counter)

This example demonstrates the new GetFileCounters command which retrieves
the SDM read counter from an NTAG424 DNA tag.

The SDM read counter:
- Increments each time the file is read in unauthenticated mode
- Used for replay protection in SUN (Secure Unique NFC) URLs
- 24-bit counter (0 to 16,777,215)
- Stored LSB-first in 3 bytes

This is useful for:
- Verifying tap-unique URL generation
- Detecting replay attacks
- Monitoring tag usage
"""

import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands import (
    SelectPiccApplication,
    GetChipVersion,
    GetFileCounters,
)
from ntag424_sdm_provisioner.commands.base import ApduError


def get_file_counters_example():
    """Demonstrate GetFileCounters command on a real chip."""
    
    print("=" * 70)
    print("Example 20: Get File Counters (SDM Read Counter)")
    print("=" * 70)
    print()
    print("This example reads the SDM counter from an NTAG424 DNA tag.")
    print("The counter increments on each unauthenticated read when SDM is enabled.")
    print()
    print("Please place your NTAG424 DNA tag on the reader...")
    print()
    
    try:
        with CardManager(reader_index=0) as card:
            print("[OK] Connected to reader")
            print()
            
            # Step 1: Select PICC Application
            print("Step 1: Selecting PICC Application...")
            print("-" * 70)
            try:
                select_cmd = SelectPiccApplication()
                print(f"  Command: {select_cmd}")
                select_cmd.execute(card)
                print("  [OK] Application selected")
            except ApduError as e:
                if "6985" in str(e):
                    print("  [INFO] Application already selected")
                else:
                    raise
            print()
            
            # Step 2: Get chip version (to identify tag type)
            print("Step 2: Getting Chip Version...")
            print("-" * 70)
            version_cmd = GetChipVersion()
            print(f"  Command: {version_cmd}")
            version_info = version_cmd.execute(card)
            print(f"  [OK] {version_info}")
            print()
            
            # Identify tag type
            if version_info.hw_major_version == 48:
                tag_type = "Seritag NTAG424 DNA"
            else:
                tag_type = "Standard NXP NTAG424 DNA"
            
            print(f"  Tag Type: {tag_type}")
            print(f"  UID: {version_info.uid.hex().upper()}")
            print()
            
            # Step 3: Get file counters for different files
            print("Step 3: Getting File Counters...")
            print("-" * 70)
            
            files_to_check = [
                (0x01, "CC File (Capability Container)"),
                (0x02, "NDEF File (Main SDM file)"),
                (0x03, "Proprietary File"),
            ]
            
            for file_no, file_name in files_to_check:
                print(f"\n  File 0x{file_no:02X}: {file_name}")
                print(f"  {'-' * 60}")
                
                try:
                    counter_cmd = GetFileCounters(file_no=file_no)
                    print(f"    Command: {counter_cmd}")
                    
                    counter = counter_cmd.execute(card)
                    
                    print(f"    [OK] Counter Value: {counter:,}")
                    print(f"      (0x{counter:06X} in hex)")
                    
                    # Provide context
                    if counter == 0:
                        print(f"      -> Counter is at 0 (SDM may not be enabled or never read)")
                    elif counter < 100:
                        print(f"      -> Low usage ({counter} reads)")
                    elif counter < 1000:
                        print(f"      -> Moderate usage ({counter} reads)")
                    else:
                        print(f"      -> High usage ({counter:,} reads)")
                    
                except ApduError as e:
                    print(f"    [FAIL] {e}")
                    print(f"      (File may not support counters or SDM not enabled)")
            
            print()
            print("=" * 70)
            print("Summary")
            print("=" * 70)
            print()
            print("The GetFileCounters command successfully retrieved SDM read counters.")
            print()
            print("Key Points:")
            print("  - Counter increments on each unauthenticated read")
            print("  - Used for replay protection in SUN URLs")
            print("  - 24-bit value (max 16,777,215)")
            print("  - Typically only NDEF file (0x02) has an active counter")
            print()
            print("Next Steps:")
            print("  - Enable SDM on the NDEF file to start using counters")
            print("  - Configure SUN to generate tap-unique URLs")
            print("  - Monitor counter to detect tag usage patterns")
            print()
            
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Stopped by user")
        return 1
    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("\nPlease ensure:")
        print("  1. NFC reader is connected")
        print("  2. NTAG424 DNA tag is placed on reader")
        print("  3. Tag remains on reader during operation")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(get_file_counters_example())

