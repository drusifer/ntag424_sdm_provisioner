#!/usr/bin/env python3
"""
Example 07: SUN Server-Side Verification

This example demonstrates how to verify SUN (Secure Unique NFC) authentication
parameters on the server side when a Seritag tag is scanned.

SUN appends parameters like ?uid=XXXX&c=YYYY&mac=ZZZZ to URLs, which can be
verified server-side to ensure tag authenticity and detect replay attacks.
"""
import sys
import os
from typing import Dict, Optional
from Crypto.Cipher import AES
from Crypto.Hash import CMAC
import hashlib

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.commands.sun_commands import parse_sun_url


class SunVerifier:
    """
    Server-side SUN verification for Seritag NTAG424 DNA tags.
    
    SUN (Secure Unique NFC) provides dynamic authentication by appending
    encrypted parameters to URLs when tags are scanned.
    """
    
    def __init__(self, master_key: bytes):
        """
        Initialize SUN verifier with master key.
        
        Args:
            master_key: Master key for deriving tag-specific keys
        """
        self.master_key = master_key
    
    def derive_tag_key(self, uid: str) -> bytes:
        """
        Derive tag-specific key from UID using master key.
        
        Args:
            uid: Tag UID (hex string)
        
        Returns:
            Derived key for this specific tag
        """
        # Convert UID to bytes
        uid_bytes = bytes.fromhex(uid)
        
        # Use HMAC-SHA256 to derive key
        import hmac
        derived_key = hmac.new(
            self.master_key,
            uid_bytes,
            hashlib.sha256
        ).digest()[:16]  # Take first 16 bytes for AES-128
        
        return derived_key
    
    def verify_sun_parameters(self, url: str, expected_uid: Optional[str] = None) -> Dict[str, any]:
        """
        Verify SUN authentication parameters from URL.
        
        Args:
            url: SUN-enhanced URL with authentication parameters
            expected_uid: Expected UID for this tag (optional)
        
        Returns:
            Verification result dictionary
        """
        try:
            # Parse SUN parameters from URL
            sun_data = parse_sun_url(url)
            
            if not sun_data:
                return {
                    'valid': False,
                    'error': 'No SUN parameters found in URL',
                    'sun_data': None
                }
            
            uid = sun_data.get('uid')
            counter = sun_data.get('counter')
            mac = sun_data.get('mac')
            
            if not all([uid, counter is not None, mac]):
                return {
                    'valid': False,
                    'error': 'Missing required SUN parameters (uid, counter, mac)',
                    'sun_data': sun_data
                }
            
            # Verify UID if expected
            if expected_uid and uid != expected_uid:
                return {
                    'valid': False,
                    'error': f'UID mismatch: expected {expected_uid}, got {uid}',
                    'sun_data': sun_data
                }
            
            # Derive tag-specific key
            tag_key = self.derive_tag_key(uid)
            
            # Verify MAC
            mac_valid = self._verify_mac(tag_key, uid, counter, mac)
            
            if not mac_valid:
                return {
                    'valid': False,
                    'error': 'MAC verification failed',
                    'sun_data': sun_data
                }
            
            return {
                'valid': True,
                'error': None,
                'sun_data': sun_data,
                'tag_key': tag_key.hex().upper()
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Verification error: {str(e)}',
                'sun_data': None
            }
    
    def _verify_mac(self, tag_key: bytes, uid: str, counter: int, mac: str) -> bool:
        """
        Verify MAC using tag key, UID, and counter.
        
        Args:
            tag_key: Derived key for this tag
            uid: Tag UID
            counter: Scan counter
            mac: MAC to verify
        
        Returns:
            True if MAC is valid
        """
        try:
            # Convert inputs to bytes
            uid_bytes = bytes.fromhex(uid)
            counter_bytes = counter.to_bytes(4, 'big')
            mac_bytes = bytes.fromhex(mac)
            
            # Create message to verify: UID + Counter
            message = uid_bytes + counter_bytes
            
            # Calculate expected MAC using CMAC
            cmac = CMAC.new(tag_key, ciphermod=AES)
            cmac.update(message)
            expected_mac = cmac.digest()
            
            # Compare MACs
            return mac_bytes == expected_mac
            
        except Exception:
            return False


def sun_verification_example():
    """Demonstrate SUN server-side verification."""
    
    print("--- Example 07: SUN Server-Side Verification ---")
    
    # Initialize verifier with master key
    master_key = b'\x00' * 16  # In production, use a secure random key
    verifier = SunVerifier(master_key)
    
    print(f"Master key: {master_key.hex().upper()}")
    
    # Example SUN-enhanced URLs (simulated)
    test_urls = [
        "https://example.com/verify?uid=043F684A2F7080&c=00000001&mac=1234567890ABCDEF",
        "https://example.com/verify?uid=042A664A2F7080&c=00000002&mac=FEDCBA0987654321",
        "https://example.com/verify?uid=043F684A2F7080&c=00000001&mac=INVALIDMAC123456",
        "https://example.com/verify?uid=WRONGUID&c=00000001&mac=1234567890ABCDEF",
        "https://example.com/verify",  # No SUN parameters
    ]
    
    print("\nTesting SUN verification with sample URLs:")
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n--- Test {i} ---")
        print(f"URL: {url}")
        
        # Parse SUN parameters
        sun_data = parse_sun_url(url)
        print(f"SUN parameters: {sun_data}")
        
        # Verify SUN parameters
        result = verifier.verify_sun_parameters(url)
        
        if result['valid']:
            print("✅ VERIFICATION SUCCESS")
            print(f"   UID: {result['sun_data']['uid']}")
            print(f"   Counter: {result['sun_data']['counter']}")
            print(f"   MAC: {result['sun_data']['mac']}")
            print(f"   Tag key: {result['tag_key']}")
        else:
            print("❌ VERIFICATION FAILED")
            print(f"   Error: {result['error']}")
    
    print("\n" + "=" * 60)
    print("  SUN Verification Complete")
    print("=" * 60)
    print("Key points:")
    print("1. SUN provides dynamic authentication without complex protocols")
    print("2. Each scan generates unique parameters (uid, counter, mac)")
    print("3. Server can verify authenticity using derived keys")
    print("4. Counter prevents replay attacks")
    print("5. MAC ensures data integrity")
    
    print("\nProduction considerations:")
    print("- Use secure master key generation")
    print("- Store expected UIDs in database")
    print("- Implement counter tracking for replay detection")
    print("- Use HTTPS for secure parameter transmission")
    print("- Consider rate limiting for verification endpoints")


if __name__ == "__main__":
    sun_verification_example()
