"""
Test if our session keys match Arduino by using hardcoded RndA/RndB.

If we use the SAME RndA/RndB as Arduino and get DIFFERENT session keys,
that's the bug!
"""

from Crypto.Hash import CMAC
from Crypto.Cipher import AES


def test_session_key_derivation():
    """
    Derive session keys using same RndA/RndB as Arduino would use.
    
    This will help us verify if our key derivation matches Arduino.
    """
    
    print("\n=== SESSION KEY DERIVATION TEST ===\n")
    
    # From our last run
    # RndA: 66c0d4473d43ab5e57f0d59c2850795e
    # RndB (after decrypt): 58daf83bce2501f02b9cfc81a6dc41c5
    # Ti: 604ad58a
    # Session ENC key: 9c85e77d9463f16f624efbf931f93baa
    # Session MAC key: ed62527ca0e6b3521ebd3e30c85eda0a
    
    factory_key = bytes(16)  # All zeros
    rnda = bytes.fromhex("66c0d4473d43ab5e57f0d59c2850795e")
    rndb = bytes.fromhex("58daf83bce2501f02b9cfc81a6dc41c5")
    ti = bytes.fromhex("604ad58a")
    
    print(f"Factory Key: {factory_key.hex()}")
    print(f"RndA: {rnda.hex()}")
    print(f"RndB: {rndb.hex()}")
    print(f"Ti: {ti.hex()}")
    
    # Derive session keys using our production method
    sv1 = b'\xA5\x5A\x00\x01\x00\x80' + rnda[0:2]
    cmac_enc = CMAC.new(factory_key, ciphermod=AES)
    cmac_enc.update(sv1 + b'\x00' * 8)
    session_enc_key = cmac_enc.digest()
    
    sv2 = b'\x5A\xA5\x00\x01\x00\x80' + rnda[0:2]
    cmac_mac = CMAC.new(factory_key, ciphermod=AES)
    cmac_mac.update(sv2 + b'\x00' * 8)
    session_mac_key = cmac_mac.digest()
    
    print(f"\nDerived Session Keys:")
    print(f"  ENC: {session_enc_key.hex()}")
    print(f"  MAC: {session_mac_key.hex()}")
    
    # Compare with what we saw in log
    expected_enc = bytes.fromhex("9c85e77d9463f16f624efbf931f93baa")
    expected_mac = bytes.fromhex("ed62527ca0e6b3521ebd3e30c85eda0a")
    
    print(f"\nExpected from log:")
    print(f"  ENC: {expected_enc.hex()}")
    print(f"  MAC: {expected_mac.hex()}")
    
    if session_enc_key == expected_enc and session_mac_key == expected_mac:
        print("\n[OK] Session keys MATCH our log!")
        print("\nOur key derivation is consistent.")
        print("Now need to compare with Arduino...")
    else:
        print("\n[ERROR] Session keys DON'T MATCH!")
        print("This would be a serious bug in our derivation.")


if __name__ == '__main__':
    test_session_key_derivation()

