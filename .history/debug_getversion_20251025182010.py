#!/usr/bin/env python3
"""
Debug script for GetChipVersion command
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ntag424_sdm_provisioner.seritag_simulator import SeritagCardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion

def debug_getversion():
    print("Debugging GetChipVersion command...")
    
    with SeritagCardManager(0) as card:
        print("Card connected")
        
        # Step 1: Select application
        print("\nStep 1: SelectPICCApplication")
        try:
            result = SelectPiccApplication().execute(card)
            print(f"SelectPICCApplication: {result}")
        except Exception as e:
            print(f"SelectPICCApplication failed: {e}")
            return
        
        # Step 2: Get version
        print("\nStep 2: GetChipVersion")
        try:
            version_info = GetChipVersion().execute(card)
            print(f"GetChipVersion success: {version_info}")
        except Exception as e:
            print(f"GetChipVersion failed: {e}")
            
            # Debug the simulator state
            print(f"\nSimulator state:")
            print(f"  get_version_part: {card.simulator.state.get_version_part}")
            print(f"  connected: {card.simulator.connected}")

if __name__ == "__main__":
    debug_getversion()
