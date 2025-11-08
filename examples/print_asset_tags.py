#!/usr/bin/env python3
"""Print asset tag labels for all tags in CSV."""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from ntag424_sdm_provisioner.uid_utils import uid_to_asset_tag

def print_asset_tags():
    """Print asset tags from tag_keys.csv."""
    csv_path = Path(__file__).parent / "tag_keys.csv"
    
    if not csv_path.exists():
        print("No tag_keys.csv found")
        return
    
    print("\n" + "="*60)
    print("ASSET TAG LABELS")
    print("="*60)
    print()
    
    with open(csv_path) as f:
        lines = f.readlines()
    
    # Skip header
    for line in lines[1:]:
        parts = line.strip().split(',')
        if len(parts) >= 6:
            uid = parts[0]
            status = parts[5]
            
            # Convert to asset tag
            asset_tag = uid_to_asset_tag(bytes.fromhex(uid))
            
            status_emoji = {
                'provisioned': '✓',
                'failed': '✗',
                'pending': '⧖',
                'factory': '○'
            }.get(status, '?')
            
            print(f"  [{status_emoji}] {asset_tag}  (UID: {uid}, Status: {status})")
    
    print()
    print("Legend: ✓=provisioned ✗=failed ⧖=pending ○=factory")
    print()
    print("Write asset tag on physical label (e.g., 'Tag: 4A2F-7080')")
    print("="*60)
    print()

if __name__ == '__main__':
    try:
        print_asset_tags()
    except Exception as e:
        # Fallback for encoding issues
        print(f"\nAsset Tags (fallback mode due to encoding):\n")
        csv_path = Path(__file__).parent / "tag_keys.csv"
        with open(csv_path) as f:
            lines = f.readlines()
        for line in lines[1:]:
            parts = line.strip().split(',')
            if len(parts) >= 6:
                uid = parts[0]
                status = parts[5]
                asset_tag = uid_to_asset_tag(bytes.fromhex(uid))
                marker = '[OK]' if status == 'provisioned' else '[ ]'
                print(f"  {marker} {asset_tag}  (UID: {uid})")
        print()

