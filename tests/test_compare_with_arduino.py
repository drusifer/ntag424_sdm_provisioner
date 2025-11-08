"""
Compare our ChangeKey APDU with Arduino-captured APDU using SAME session keys.

We'll hardcode session keys from a known good Arduino session and verify
our APDU construction matches byte-for-byte.
"""

from ntag424_sdm_provisioner.crypto.crypto_primitives import build_changekey_apdu


def test_compare_with_arduino_capture():
    """
    Use session keys from Arduino to build ChangeKey APDU and compare.
    
    This tests if our APDU construction matches Arduino when using IDENTICAL inputs.
    """
    
    print("\n=== COMPARING WITH ARDUINO WIRE CAPTURE ===\n")
    
    # These values should be captured from Arduino Serial.print()
    # Modify Full_ChangeKey.ino to print these after auth:
    ti = bytes.fromhex("604AD58A")  # From our Python log
    cmd_ctr = 0
    session_enc_key = bytes.fromhex("9C85E77D9463F16F624EFBF931F93BAA")  # From log
    session_mac_key = bytes.fromhex("ED62527CA0E6B3521EBD3E30C85EDA0A")  # From log
    
    new_key = bytes.fromhex("5BCAEE1B1C56784AC83373CF945DC428")  # From log
    key_version = 0x00
    
    # Build APDU
    apdu = build_changekey_apdu(
        key_no=0,
        new_key=new_key,
        old_key=None,
        version=key_version,
        ti=ti,
        cmd_ctr=cmd_ctr,
        session_enc_key=session_enc_key,
        session_mac_key=session_mac_key
    )
    
    print(f"Ti: {ti.hex()}")
    print(f"Counter: {cmd_ctr}")
    print(f"New Key: {new_key.hex()}")
    print(f"\nOur APDU ({len(apdu)} bytes):")
    print(' '.join(f'{b:02X}' for b in apdu))
    
    # Expected from our log (line 17):
    expected = bytes.fromhex("90C4000029007D39CB54283FE10E033931AD880EE0987DF0D398851409F2D0BED5A70CFCAD49FCD16DC06370808000")
    
    print(f"\nFrom log ({len(expected)} bytes):")
    print(' '.join(f'{b:02X}' for b in expected))
    
    if bytes(apdu) == expected:
        print("\n[OK] APDUs MATCH!")
        print("\nOur APDU construction is correct!")
        print("The issue must be something else...")
    else:
        print("\n[MISMATCH] APDUs differ!")
        for i, (ours, exp) in enumerate(zip(apdu, expected)):
            if ours != exp:
                print(f"  Byte {i}: Ours={ours:02X}, Expected={exp:02X}")


if __name__ == '__main__':
    test_compare_with_arduino_capture()

