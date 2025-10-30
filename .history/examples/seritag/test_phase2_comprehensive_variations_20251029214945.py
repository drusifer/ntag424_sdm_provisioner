"""
Comprehensive Phase 2 Authentication Variations Test

Tests multiple variations of Phase 2 authentication to identify
the correct protocol for Seritag tags:
- Different factory keys
- Different RndB rotation methods
- Different encryption formats
- Different command formats
"""
import sys
import os
import logging

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication
from ntag424_sdm_provisioner.constants import FACTORY_KEY, SW_OK, SW_ADDITIONAL_FRAME
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

# Enable verbose logging
logging.basicConfig(
    level=logging.INFO,  # Set to INFO for cleaner output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

log = logging.getLogger(__name__)


def get_uid_from_card(card):
    """Get UID from card by trying GetCardUID after Phase 1."""
    try:
        # Try GetCardUID (0x51)
        apdu = [0x90, 0x51, 0x00, 0x00, 0x00]
        data, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
        if (sw1, sw2) == SW_OK and len(data) >= 4:
            return bytes(data[:4])  # UID is first 4 bytes
    except:
        pass
    
    # Try via GetVersion
    try:
        apdu = [0x90, 0x60, 0x00, 0x00, 0x00]
        data, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
        if (sw1, sw2) == SW_ADDITIONAL_FRAME and len(data) >= 4:
            # UID is typically in GetVersion response
            return bytes(data[:4])
    except:
        pass
    
    return None


def derive_uid_based_key(uid_bytes):
    """Derive a key from UID (simple method - pad or repeat)."""
    if uid_bytes is None or len(uid_bytes) < 4:
        return FACTORY_KEY
    
    # Simple derivation: pad UID to 16 bytes
    # Option 1: Repeat UID 4 times
    key1 = (uid_bytes * 4)[:16]
    
    # Option 2: Pad with zeros
    key2 = uid_bytes + b'\x00' * (16 - len(uid_bytes))
    
    # Option 3: Pad with 0xFF
    key3 = uid_bytes + b'\xFF' * (16 - len(uid_bytes))
    
    return [key1, key2, key3]


def rotate_rndb_left(data, shift_bytes=1):
    """Rotate RndB left by shift_bytes (standard NXP spec)."""
    return data[shift_bytes:] + data[:shift_bytes]


def rotate_rndb_right(data, shift_bytes=1):
    """Rotate RndB right by shift_bytes."""
    return data[-shift_bytes:] + data[:-shift_bytes]


def test_phase2_variation(card, key, rndb_encrypted, rotation_func, rotation_name, encryption_name=""):
    """Test a single Phase 2 variation."""
    try:
        # Decrypt RndB
        cipher = AES.new(key, AES.MODE_ECB)
        rndb = cipher.decrypt(rndb_encrypted)
        
        # Rotate RndB
        rndb_rotated = rotation_func(rndb)
        
        # Generate RndA
        rnda = get_random_bytes(16)
        
        # Build Phase 2 plaintext
        plaintext = rnda + rndb_rotated
        
        # Encrypt Phase 2 plaintext
        encrypted_response = cipher.encrypt(plaintext)
        
        # Build Phase 2 APDU
        apdu_phase2 = [0x90, 0xAF, 0x00, 0x00, len(encrypted_response)] + list(encrypted_response) + [0x00]
        
        # Send Phase 2
        data2, sw1_2, sw2_2 = card.send_apdu(apdu_phase2, use_escape=True)
        
        return {
            'success': (sw1_2, sw2_2) == SW_OK,
            'sw': (sw1_2, sw2_2),
            'data_length': len(data2) if data2 else 0,
            'encryption': encryption_name if encryption_name else 'AES-ECB',
            'rotation': rotation_name
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'sw': (0x00, 0x00),
            'encryption': encryption_name if encryption_name else 'AES-ECB',
            'rotation': rotation_name
        }


def run_comprehensive_test(card):
    """Run comprehensive Phase 2 variations test."""
    
    print("=" * 80)
    print("COMPREHENSIVE PHASE 2 AUTHENTICATION VARIATIONS TEST")
    print("=" * 80)
    print("\nTesting multiple combinations of:")
    print("  - Factory key variations")
    print("  - RndB rotation methods")
    print("  - Encryption formats")
    print("\nNOTE: Each test requires a fresh Phase 1")
    print("=" * 80)
    
    # Get UID first (need Phase 1 but we'll try without first)
    print("\nStep 1: Getting card UID...")
    uid = None
    try:
        apdu_uid = [0x90, 0x51, 0x00, 0x00, 0x00]
        data_uid, sw1_uid, sw2_uid = card.send_apdu(apdu_uid, use_escape=True)
        if (sw1_uid, sw2_uid) == SW_OK and len(data_uid) >= 4:
            uid = bytes(data_uid[:4])
            print(f"  [OK] UID: {uid.hex().upper()}")
        else:
            print(f"  [SKIP] GetCardUID returned SW={sw1_uid:02X}{sw2_uid:02X}")
    except Exception as e:
        print(f"  [SKIP] Could not get UID: {e}")
    
    # Define key variations
    key_variations = []
    
    # Standard factory key (all zeros)
    key_variations.append({
        'name': 'Factory Key (All Zeros)',
        'key': FACTORY_KEY,
        'description': 'Standard NXP factory key: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'
    })
    
    # All ones key
    key_variations.append({
        'name': 'All Ones Key',
        'key': b'\xFF' * 16,
        'description': 'All ones: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF'
    })
    
    # UID-based keys (if we got UID)
    if uid:
        uid_keys = derive_uid_based_key(uid)
        key_variations.append({
            'name': 'UID-Based Key (Repeat)',
            'key': uid_keys[0],
            'description': f'UID repeated 4 times: {uid_keys[0].hex().upper()}'
        })
        key_variations.append({
            'name': 'UID-Based Key (Zero-Padded)',
            'key': uid_keys[1],
            'description': f'UID zero-padded: {uid_keys[1].hex().upper()}'
        })
        key_variations.append({
            'name': 'UID-Based Key (FF-Padded)',
            'key': uid_keys[2],
            'description': f'UID FF-padded: {uid_keys[2].hex().upper()}'
        })
    
    # Common weak keys
    key_variations.append({
        'name': 'Weak Key (0123456789ABCDEF)',
        'key': bytes.fromhex('0123456789ABCDEF0123456789ABCDEF')[:16],
        'description': 'Common weak key pattern'
    })
    
    # Define rotation variations
    rotation_variations = [
        {
            'name': 'Standard Left Rotate (1 byte)',
            'func': lambda d: rotate_rndb_left(d, 1),
            'description': 'NXP spec: rotate left by 1 byte'
        },
        {
            'name': 'No Rotation',
            'func': lambda d: d,
            'description': 'No rotation (use RndB as-is)'
        },
        {
            'name': 'Right Rotate (1 byte)',
            'func': lambda d: rotate_rndb_right(d, 1),
            'description': 'Rotate right by 1 byte'
        },
        {
            'name': 'Left Rotate (2 bytes)',
            'func': lambda d: rotate_rndb_left(d, 2),
            'description': 'Rotate left by 2 bytes'
        },
        {
            'name': 'Left Rotate (4 bytes)',
            'func': lambda d: rotate_rndb_left(d, 4),
            'description': 'Rotate left by 4 bytes'
        },
    ]
    
    results = []
    test_number = 0
    
    # Run all combinations
    print("\n" + "=" * 80)
    print("RUNNING VARIATIONS...")
    print("=" * 80)
    
    for key_var in key_variations:
        print(f"\n--- Testing Key: {key_var['name']} ---")
        print(f"  {key_var['description']}")
        
        # Get fresh Phase 1 for each key variation
        try:
            apdu_phase1 = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
            data1, sw1_1, sw2_1 = card.send_apdu(apdu_phase1, use_escape=True)
            
            if (sw1_1, sw2_1) != SW_ADDITIONAL_FRAME or len(data1) != 16:
                print(f"  [SKIP] Phase 1 failed: SW={sw1_1:02X}{sw2_1:02X}")
                continue
            
            encrypted_rndb = bytes(data1)
            
            for rot_var in rotation_variations:
                test_number += 1
                print(f"\n  Test #{test_number}: {rot_var['name']}")
                
                result = test_phase2_variation(
                    card,
                    key_var['key'],
                    encrypted_rndb,
                    rot_var['func'],
                    rot_var['name'],
                    'AES-ECB'
                )
                
                result['key_name'] = key_var['name']
                result['test_number'] = test_number
                results.append(result)
                
                if result.get('success'):
                    print(f"    [SUCCESS] SW={result['sw'][0]:02X}{result['sw'][1]:02X}")
                    print(f"             Data length: {result.get('data_length', 0)} bytes")
                    print(f"             Key: {key_var['name']}")
                    print(f"             Rotation: {rot_var['name']}")
                    print(f"\n>>> BREAKTHROUGH: Phase 2 authentication successful! <<<")
                    return results
                else:
                    sw = result.get('sw', (0x00, 0x00))
                    print(f"    [FAIL] SW={sw[0]:02X}{sw[1]:02X}")
                    if result.get('error'):
                        print(f"             Error: {result['error']}")
                    
                    # If we get 91CA, need fresh Phase 1
                    if sw[1] == 0xCA:
                        print(f"    [WARN] Command Aborted - transaction state issue")
                        print(f"           Need fresh Phase 1, but continuing...")
                
                # Small delay to avoid overwhelming the tag
                import time
                time.sleep(0.1)
        
        except Exception as e:
            print(f"  [ERROR] Test failed: {e}")
            continue
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]
    
    print(f"\nTotal tests: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if successful:
        print("\n[SUCCESS] Working combinations found:")
        for r in successful:
            print(f"  Test #{r['test_number']}:")
            print(f"    Key: {r['key_name']}")
            print(f"    Rotation: {r['rotation']}")
            print(f"    SW: {r['sw'][0]:02X}{r['sw'][1]:02X}")
    else:
        print("\n[FAIL] No successful combinations found")
        print("\nMost common error codes:")
        error_counts = {}
        for r in failed:
            sw = r.get('sw', (0x00, 0x00))
            sw_str = f"{sw[0]:02X}{sw[1]:02X}"
            error_counts[sw_str] = error_counts.get(sw_str, 0) + 1
        
        for sw, count in sorted(error_counts.items(), key=lambda x: -x[1]):
            meanings = {
                '91AE': 'Authentication Error (Wrong RndB\')',
                '91CA': 'Command Aborted (Transaction state)',
                '91AD': 'Authentication Delay',
                '917E': 'Length Error',
                '911C': 'Illegal Command Code',
            }
            meaning = meanings.get(sw, 'Unknown')
            print(f"  SW={sw}: {count} times ({meaning})")
    
    return results


def main():
    """Run comprehensive Phase 2 variations test."""
    try:
        with CardManager(0, timeout_seconds=15) as card:
            SelectPiccApplication().execute(card)
            print("[OK] PICC selected\n")
            
            results = run_comprehensive_test(card)
            
            print("\n" + "=" * 80)
            if any(r.get('success') for r in results):
                print("[SUCCESS] Found working Phase 2 authentication combination!")
            else:
                print("[FAIL] No working Phase 2 authentication combination found")
                print("       All variations failed - likely Seritag-specific protocol")
            print("=" * 80)
            
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

