#!/usr/bin/env python3
"""Check NDEF and CC file configuration."""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.commands.get_file_settings import GetFileSettings
from ntag424_sdm_provisioner.commands.iso_commands import ISOSelectFile, ISOReadBinary, ISOFileID
from ntag424_sdm_provisioner.constants import CCFileData

def check_config():
    """Check CC and NDEF file configuration."""
    
    with CardManager(reader_index=0) as card:
        print("\n" + "="*70)
        print("NDEF CONFIGURATION CHECK")
        print("="*70 + "\n")
        
        # Select PICC
        SelectPiccApplication().execute(card)
        print("[OK] PICC Application selected")
        
        # Check CC file
        print("\n1. Capability Container (CC) File:")
        print("-" * 70)
        try:
            ISOSelectFile(ISOFileID.CC_FILE).execute(card)
            cc_raw = ISOReadBinary(offset=0, length=32).execute(card)
            
            print(f"  Raw Data ({len(cc_raw)} bytes): {cc_raw.hex().upper()}")
            print()
            
            cc_data = CCFileData.from_bytes(cc_raw)
            print(cc_data)
            
            print("\n  [OK] CC file readable and valid")
        except Exception as e:
            print(f"  [ERROR] {e}")
        
        # Check NDEF file settings
        print("\n2. NDEF File (0x02) Settings:")
        print("-" * 70)
        try:
            SelectPiccApplication().execute(card)
            settings = GetFileSettings(file_no=0x02).execute(card)
            
            print(f"  File Type: 0x{settings.file_type:02X}")
            print(f"  File Option: 0x{settings.file_option:02X}")
            print(f"  Access Rights: {settings.access_rights.hex().upper()}")
            print(f"  File Size: {settings.file_size} bytes")
            
            # Decode access rights
            ar = settings.access_rights
            read = (ar[1] >> 4) & 0x0F
            write = ar[1] & 0x0F
            rw = (ar[0] >> 4) & 0x0F
            change = ar[0] & 0x0F
            
            print(f"    Read: 0x{read:X} {'(FREE)' if read == 0xE else f'(KEY {read})'}")
            print(f"    Write: 0x{write:X} {'(FREE)' if write == 0xE else f'(KEY {write})'}")
            print(f"    ReadWrite: 0x{rw:X} {'(FREE)' if rw == 0xE else f'(KEY {rw})'}")
            print(f"    Change: 0x{change:X} {'(FREE)' if change == 0xE else f'(KEY {change})'}")
            
            print("  [OK] NDEF file settings retrieved")
        except Exception as e:
            print(f"  [ERROR] {e}")
        
        # Check NDEF content
        print("\n3. NDEF Content:")
        print("-" * 70)
        try:
            ISOSelectFile(ISOFileID.NDEF_FILE).execute(card)
            ndef_data = ISOReadBinary(offset=0, length=200).execute(card)
            
            # Parse length field
            if len(ndef_data) >= 2:
                ndef_len = (ndef_data[0] << 8) | ndef_data[1]
                print(f"  NDEF Length: 0x{ndef_len:04X} ({ndef_len} bytes)")
                
                if ndef_len > 0 and ndef_len < 256:
                    # Parse TLV
                    if len(ndef_data) > 2:
                        tlv_tag = ndef_data[2]
                        if tlv_tag == 0x03:
                            tlv_len = ndef_data[3]
                            print(f"  NDEF Message TLV: T=0x03, L={tlv_len}")
                            
                            # Extract URL
                            if 0x55 in ndef_data:
                                pos = ndef_data.index(0x55)
                                prefix_code = ndef_data[pos + 1]
                                url_start = pos + 2
                                url_end = ndef_data.index(0xFE) if 0xFE in ndef_data else len(ndef_data)
                                
                                prefix_map = {0x04: "https://", 0x03: "http://", 0x00: ""}
                                prefix = prefix_map.get(prefix_code, "")
                                url = prefix + ndef_data[url_start:url_end].decode('utf-8', errors='ignore')
                                
                                print(f"  URL: {url[:80]}...")
                                print(f"  [OK] NDEF message valid")
                        else:
                            print(f"  [WARN] Unexpected TLV tag: 0x{tlv_tag:02X}")
                else:
                    print(f"  [WARN] NDEF length invalid or zero")
            else:
                print("  [ERROR] NDEF data too short")
        except Exception as e:
            print(f"  [ERROR] {e}")
        
        print("\n" + "="*70)
        print()

if __name__ == '__main__':
    try:
        check_config()
    except KeyboardInterrupt:
        print("\n[Interrupted]")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

