"""
Test GetKeyVersion CMAC against AN12343 exact test vector.

This verifies our crypto_primitives.calculate_cmac() produces
the exact CMAC from AN12343 Table 39 (GetKeyVersion example).
"""

from ntag424_sdm_provisioner.crypto.crypto_primitives import calculate_cmac


def test_an12343_getkeyversion_cmac():
    """Test against AN12343 Table 39, Row 13-14."""
    
    print("\n=== AN12343 GetKeyVersion CMAC Test ===\n")
    
    # From AN12343 Table 39
    ti = bytes.fromhex("5084A1A3")
    cmd_ctr = 0
    session_mac_key = bytes.fromhex("AAB799EBB2B22AC79D7F3EB0E1CFD49E")
    cmd = 0x64  # GetKeyVersion
    key_no = 0x00
    
    print(f"Ti: {ti.hex()}")
    print(f"Counter: {cmd_ctr}")
    print(f"Session MAC: {session_mac_key.hex()}")
    print(f"Cmd: 0x{cmd:02X}")
    print(f"KeyNo: 0x{key_no:02X}\n")
    
    # Calculate CMAC using our crypto_primitives
    cmac_truncated = calculate_cmac(
        cmd=cmd,
        cmd_ctr=cmd_ctr,
        ti=ti,
        cmd_header=bytes([key_no]),
        encrypted_data=b'',  # No encrypted data
        session_mac_key=session_mac_key
    )
    
    # Expected from AN12343 Row 14
    expected = bytes.fromhex("7F0A6EABC174B6DF")
    
    print(f"Our CMAC:      {cmac_truncated.hex().upper()}")
    print(f"Expected CMAC: {expected.hex().upper()}")
    
    if cmac_truncated == expected:
        print("\n[OK] CMAC MATCHES AN12343 SPEC!")
        print("\nOur crypto_primitives.calculate_cmac() is CORRECT.")
        return True
    else:
        print("\n[FAILED] CMAC MISMATCH!")
        print("\nOur crypto implementation has a bug.")
        return False


if __name__ == '__main__':
    success = test_an12343_getkeyversion_cmac()
    exit(0 if success else 1)

