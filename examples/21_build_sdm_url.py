#!/usr/bin/env python3
"""
Example 21: Build SDM URL with Placeholders

This example demonstrates how to build an NDEF message with SDM (Secure Dynamic Messaging)
placeholders. These placeholders will be replaced by the tag with dynamic values when read.

SDM Placeholders:
- UID: Tag's unique identifier (14 hex chars = 7 bytes)
- Counter: Tap counter (6 hex chars = 3 bytes, 24-bit)
- CMAC: Authentication code (16 hex chars = 8 bytes)

Example URL:
  https://globalheadsandtails.com/tap?uid=00000000000000&ctr=000000&cmac=0000000000000000
  
When tapped, the tag fills in real values:
  https://globalheadsandtails.com/tap?uid=04B7664A2F7080&ctr=00002A&cmac=A1B2C3D4E5F67890
"""

import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from ntag424_sdm_provisioner.commands.sdm_helpers import build_ndef_uri_record, calculate_sdm_offsets
from ntag424_sdm_provisioner.constants import SDMUrlTemplate


def build_sdm_url_example():
    """Demonstrate building SDM URL with placeholders."""
    
    print("=" * 70)
    print("Example 21: Build SDM URL with Placeholders")
    print("=" * 70)
    print()
    print("This example shows how to create NDEF messages with SDM placeholders.")
    print()
    
    # Step 1: Define the base URL and placeholders
    print("Step 1: Define URL Template")
    print("-" * 70)
    
    base_url = "https://globalheadsandtails.com/tap"
    uid_placeholder = "00000000000000"      # 7 bytes = 14 hex chars
    counter_placeholder = "000000"           # 3 bytes = 6 hex chars
    cmac_placeholder = "0000000000000000"   # 8 bytes = 16 hex chars
    
    print(f"  Base URL: {base_url}")
    print(f"  UID Placeholder: {uid_placeholder} (14 hex chars)")
    print(f"  Counter Placeholder: {counter_placeholder} (6 hex chars)")
    print(f"  CMAC Placeholder: {cmac_placeholder} (16 hex chars)")
    print()
    
    # Step 2: Build complete URL with placeholders
    print("Step 2: Build Complete URL")
    print("-" * 70)
    
    url_with_placeholders = (
        f"{base_url}?"
        f"uid={uid_placeholder}&"
        f"ctr={counter_placeholder}&"
        f"cmac={cmac_placeholder}"
    )
    
    print(f"  URL: {url_with_placeholders}")
    print(f"  Length: {len(url_with_placeholders)} characters")
    print()
    
    # Step 3: Build NDEF message
    print("Step 3: Build NDEF Message")
    print("-" * 70)
    
    ndef_message = build_ndef_uri_record(url_with_placeholders)
    
    print(f"  NDEF Size: {len(ndef_message)} bytes")
    print(f"  NDEF Hex: {ndef_message.hex().upper()}")
    print()
    print("  Structure:")
    print(f"    TLV Type: 0x{ndef_message[0]:02X} (NDEF Message)")
    print(f"    TLV Length: {ndef_message[1]} bytes")
    print(f"    Record Header: 0x{ndef_message[2]:02X}")
    print(f"    Type: 'U' (URI)")
    print(f"    URI Prefix: 0x04 (https://)")
    print(f"    Terminator: 0x{ndef_message[-1]:02X}")
    print()
    
    # Step 4: Calculate SDM offsets
    print("Step 4: Calculate SDM Offsets")
    print("-" * 70)
    
    template = SDMUrlTemplate(
        base_url=base_url,
        uid_placeholder=uid_placeholder,
        cmac_placeholder=cmac_placeholder,
        read_ctr_placeholder=counter_placeholder,
        enc_placeholder=None  # No encryption for this example
    )
    
    offsets = calculate_sdm_offsets(template)
    
    print("  Calculated Offsets (byte positions in NDEF file):")
    for key, value in offsets.items():
        print(f"    {key}: {value}")
    print()
    
    # Step 5: Show how tag will fill placeholders
    print("Step 5: Example After Tag Fills Placeholders")
    print("-" * 70)
    
    example_uid = "04B7664A2F7080"
    example_counter = "00002A"
    example_cmac = "A1B2C3D4E5F67890"
    
    filled_url = (
        f"{base_url}?"
        f"uid={example_uid}&"
        f"ctr={example_counter}&"
        f"cmac={example_cmac}"
    )
    
    print(f"  Original: {url_with_placeholders}")
    print(f"  After Tap: {filled_url}")
    print()
    print("  What Changed:")
    print(f"    UID: {uid_placeholder} -> {example_uid}")
    print(f"    Counter: {counter_placeholder} -> {example_counter} (tap #42)")
    print(f"    CMAC: {cmac_placeholder} -> {example_cmac}")
    print()
    
    # Step 6: Explain server-side validation
    print("Step 6: Server-Side Validation")
    print("-" * 70)
    print()
    print("  When your server receives the tapped URL:")
    print()
    print("  1. Extract uid, ctr, cmac from query parameters")
    print("  2. Look up the coin's key using UID")
    print("  3. Calculate expected CMAC:")
    print("     CMAC(key, uid || counter || url_portion)")
    print("  4. Compare calculated CMAC with received CMAC")
    print("  5. Check counter hasn't been seen before (replay protection)")
    print("  6. If valid: Coin is authentic, deliver reward!")
    print()
    
    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print()
    print("You now have:")
    print("  [OK] NDEF message structure with placeholders")
    print("  [OK] SDM offset calculations")
    print("  [OK] Understanding of placeholder format")
    print()
    print("Next Steps:")
    print("  1. Authenticate with tag (get session keys)")
    print("  2. Configure SDM using ChangeFileSettings")
    print("  3. Write NDEF message to tag")
    print("  4. Enable SDM to activate dynamic URL generation")
    print("  5. Tap tag and see real values!")
    print()
    print(f"Ready to write {len(ndef_message)} bytes to tag")
    print()


if __name__ == "__main__":
    sys.exit(build_sdm_url_example())

