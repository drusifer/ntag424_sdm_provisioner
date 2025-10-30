#!/usr/bin/env python3
"""
Test ISO 7816-4 Commands (CLA=00) for NTAG424

The spec shows ISOReadBinary and ISOUpdateBinary use CLA=00, not CLA=90!
This might be the bug causing 917E and 911C errors.
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.commands.base import ApduError
from ntag424_sdm_provisioner.constants import SW_OK
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def test_iso_read_binary():
    """Test ISOReadBinary (CLA=00, INS=B0) - the correct format."""
    
    print("=" * 60)
    print("Testing ISOReadBinary with CLA=00 (ISO standard)")
    print("=" * 60)
    print("Spec: ISOReadBinary uses CLA=00 B0, not CLA=90 B0")
    print()
    
    try:
        with CardManager(0) as card:
            SelectPiccApplication().execute(card)
            version_info = GetChipVersion().execute(card)
            print(f"Tag: HW {version_info.hw_major_version}.{version_info.hw_minor_version}")
            print()
            
            # Test 1: ISOReadBinary with CLA=00 (CORRECT)
            print("Test 1: ISOReadBinary CLA=00 B0 (ISO standard)")
            print("APDU Format: 00 B0 <P1> <P2> <Le>")
            
            # P1[7]=0: P1-P2 is offset (15 bits, max 32767)
            # P1[7]=1: P1[4:0] is file ID, P2 is offset (0-255)
            # For file 2 (NDEF), we might need to select it first OR use file ID
            
            # Try direct offset approach (P1[7]=0)
            offset = 0
            length = 64  # Try reading 64 bytes
            p1 = (offset >> 8) & 0x7F  # Bit 7 must be 0 for offset mode
            p2 = offset & 0xFF
            
            apdu = [
                0x00,  # CLA = ISO 7816-4 standard
                0xB0,  # INS = ReadBinary
                p1,    # P1 = Offset high bits (bit 7=0 for offset mode)
                p2,    # P2 = Offset low bits
                length # Le = Length to read
            ]
            
            print(f"  APDU: {[hex(x) for x in apdu]}")
            
            try:
                data, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
                status = f"{sw1:02X}{sw2:02X}"
                print(f"  Response: SW={status}")
                if (sw1, sw2) == SW_OK:
                    print(f"  ✅ SUCCESS! Read {len(data)} bytes")
                    print(f"  Data: {bytes(data).hex().upper()[:64]}...")
                    return True
                else:
                    print(f"  ❌ Failed: {status}")
            except Exception as e:
                print(f"  ❌ Error: {e}")
            
            # Test 2: Try with file selection first (P1[7]=1, file ID in P1[4:0])
            print()
            print("Test 2: ISOReadBinary with file ID selection")
            print("P1[7]=1, P1[4:0]=file_id, P2=offset")
            
            file_id = 0x04  # NDEF file E104h = file 02 = 4 decimal?
            # Actually, check spec - file ID might be different
            
            # From spec: File 02 has File ID E104h
            # But ISOReadBinary uses "short ISO FileID" - need to check
            
            # Try P1 with file ID bit pattern
            # If P1[7]=1, then P1[4:0] is short file ID
            # But what's the mapping? Let's try a few values
            
            for file_id_bits in [0x02, 0x04, 0x10]:  # Try different file ID encodings
                p1_file = 0x80 | (file_id_bits & 0x1F)  # Set bit 7, use lower 5 bits
                p2_file = 0
                
                apdu_file = [
                    0x00,  # CLA
                    0xB0,  # INS
                    p1_file,
                    p2_file,
                    length
                ]
                
                print(f"  Trying file_id_bits={file_id_bits:02X}: {[hex(x) for x in apdu_file]}")
                try:
                    data, sw1, sw2 = card.send_apdu(apdu_file, use_escape=True)
                    if (sw1, sw2) == SW_OK:
                        print(f"  ✅ SUCCESS with file_id={file_id_bits:02X}!")
                        print(f"  Read {len(data)} bytes: {bytes(data).hex().upper()[:64]}...")
                        return True
                    else:
                        print(f"  SW={sw1:02X}{sw2:02X}")
                except:
                    pass
            
            # Test 3: Try selecting file first, then read
            print()
            print("Test 3: Select file first, then read")
            # ISOSelectFile: 00 A4
            select_apdu = [
                0x00, 0xA4, 0x00, 0x0C,  # Select by File ID
                0x02,  # Lc
                0xE1, 0x04,  # File ID E104h (NDEF file)
                0x00  # Le
            ]
            
            try:
                _, sw1, sw2 = card.send_apdu(select_apdu, use_escape=True)
                print(f"  File select: SW={sw1:02X}{sw2:02X}")
                if (sw1, sw2) == SW_OK:
                    # Now try read
                    read_apdu = [0x00, 0xB0, 0x00, 0x00, length]
                    data, sw1, sw2 = card.send_apdu(read_apdu, use_escape=True)
                    print(f"  Read after select: SW={sw1:02X}{sw2:02X}")
                    if (sw1, sw2) == SW_OK:
                        print(f"  ✅ SUCCESS after file selection!")
                        print(f"  Read {len(data)} bytes")
                        return True
            except Exception as e:
                print(f"  Error: {e}")
            
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_iso_update_binary():
    """Test ISOUpdateBinary (CLA=00, INS=D6) - the correct format."""
    
    print()
    print("=" * 60)
    print("Testing ISOUpdateBinary with CLA=00 (ISO standard)")
    print("=" * 60)
    print("Spec: ISOUpdateBinary uses CLA=00 D6, not CLA=90 D6")
    print()
    
    try:
        with CardManager(0) as card:
            SelectPiccApplication().execute(card)
            
            # Test write with CLA=00
            test_data = b'TEST'
            offset = 0
            
            # ISOUpdateBinary format: 00 D6 P1 P2 Lc Data
            # P1-P2 is offset (if P1[7]=0)
            p1 = (offset >> 8) & 0x7F  # Bit 7 = 0 for offset mode
            p2 = offset & 0xFF
            
            apdu = [
                0x00,  # CLA = ISO standard
                0xD6,  # INS = UpdateBinary
                p1,
                p2,
                len(test_data)  # Lc
            ] + list(test_data)
            
            print(f"APDU: {[hex(x) for x in apdu]}")
            
            try:
                _, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
                status = f"{sw1:02X}{sw2:02X}"
                print(f"Response: SW={status}")
                if (sw1, sw2) == SW_OK:
                    print("✅ SUCCESS! Write worked with CLA=00")
                    return True
                else:
                    print(f"❌ Failed: {status}")
                    return False
            except Exception as e:
                print(f"❌ Error: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    print("Testing ISO 7816-4 Commands (CLA=00)")
    print("Current bug: Using CLA=90 instead of CLA=00 for Read/UpdateBinary")
    print()
    
    read_success = test_iso_read_binary()
    write_success = test_iso_update_binary()
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    if read_success:
        print("✅ ISOReadBinary (CLA=00) WORKS!")
    else:
        print("❌ ISOReadBinary still failing - may need file selection or auth")
    
    if write_success:
        print("✅ ISOUpdateBinary (CLA=00) WORKS!")
    else:
        print("❌ ISOUpdateBinary still failing - may need file selection or auth")

