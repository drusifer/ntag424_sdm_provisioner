#!/usr/bin/env python3
"""
Example 25: Get Current File Settings

Check what the current NDEF file settings are before trying to change them.
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion, GetFileSettings


def get_current_settings():
    """Get current NDEF file settings."""
    
    with CardManager(reader_index=0) as card:
        SelectPiccApplication().execute(card)
        version = GetChipVersion().execute(card)
        print(f"UID: {version.uid.hex().upper()}")
        print()
        
        print("Current NDEF File Settings:")
        print("-" * 70)
        
        try:
            settings = GetFileSettings(file_no=0x02).execute(card)
            print(f"{settings}")
            print()
            print(f"Raw data: {settings}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    sys.exit(get_current_settings())

