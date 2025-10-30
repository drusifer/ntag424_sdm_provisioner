#!/usr/bin/env python3
"""
Debug script for real hardware GetChipVersion command
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion

def debug_real_getversion():
    print("Debugging real hardware GetChipVersion...")
    
    try:
        with CardManager(0) as card:
            print("Card connected")
            
            # Step 1: Select application
            print("\nStep 1: SelectPICCApplication")
            result = SelectPiccApplication().execute(card)
            print(f"SelectPICCApplication: {result}")
            
            # Step 2: Get version with raw data inspection
            print("\nStep 2: GetChipVersion - inspecting raw data")
            
            # Create command and manually inspect the response
            cmd = GetChipVersion()
            
            # Send initial command
            print("Sending initial 0x90 0x60 command...")
            data, sw1, sw2 = cmd.send_apdu(card, cmd.GET_VERSION_APDU)
            print(f"Part 1: {len(data)} bytes, SW={sw1:02X}{sw2:02X}")
            print(f"Part 1 data: {bytes(data).hex()}")
            
            full_response = bytearray(data)
            
            # Handle additional frames
            frame_count = 1
            while (sw1, sw2) == (0x91, 0xAF):
                frame_count += 1
                print(f"Sending additional frame {frame_count}...")
                data, sw1, sw2 = cmd.send_apdu(card, cmd.GET_ADDITIONAL_FRAME_APDU)
                print(f"Part {frame_count}: {len(data)} bytes, SW={sw1:02X}{sw2:02X}")
                print(f"Part {frame_count} data: {bytes(data).hex()}")
                full_response.extend(data)
            
            print(f"\nFinal response: {len(full_response)} bytes")
            print(f"Full data: {bytes(full_response).hex()}")
            print(f"Final SW: {sw1:02X}{sw2:02X}")
            
            # Try to parse with current logic
            if len(full_response) == 29:
                print("✅ Data length matches expected 29 bytes")
            else:
                print(f"❌ Data length mismatch: expected 29, got {len(full_response)}")
                
                # Try to parse as 28 bytes
                if len(full_response) == 28:
                    print("Attempting to parse as 28-byte format...")
                    # Maybe the real hardware doesn't include the last byte?
                    # Let's see what the structure might be
                    print(f"Bytes 0-6 (HW): {bytes(full_response[0:7]).hex()}")
                    print(f"Bytes 7-13 (SW): {bytes(full_response[7:14]).hex()}")
                    print(f"Bytes 14-27 (Prod): {bytes(full_response[14:28]).hex()}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_real_getversion()
