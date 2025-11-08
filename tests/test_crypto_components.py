"""
Unit tests for crypto components using NXP specification test vectors.

Test vectors from:
- AN12196 Table 26: ChangeKey example (Key 0, counter=3)
- AN12343 Table 40: ChangeKey example (Key 0, counter=0)
"""

import pytest
from ntag424_sdm_provisioner.crypto.crypto_primitives import (
    calculate_iv_for_command,
    encrypt_key_data,
    calculate_cmac_full,
    truncate_cmac,
    calculate_cmac,
    build_key_data,
    build_changekey_apdu,
)


class TestAN12196Vectors:
    """Test against AN12196 Table 26 example"""
    
    # Test values from AN12196 Table 26
    TI = bytes.fromhex("7614281A")
    CMD_CTR = 3
    SESSION_ENC_KEY = bytes.fromhex("4CF3CB41A22583A61E89B158D252FC53")
    SESSION_MAC_KEY = bytes.fromhex("5529860B2FC5FB6154B7F28361D30BF9")
    NEW_KEY = bytes.fromhex("5004BF991F408672B1EF00F08F9E8647")
    KEY_VERSION = 0x01
    
    def test_iv_calculation(self):
        """Test IV calculation against AN12196 Step 12"""
        iv = calculate_iv_for_command(self.TI, self.CMD_CTR, self.SESSION_ENC_KEY)
        
        # Expected from AN12196 Step 12
        expected_iv = bytes.fromhex("01602D579423B2797BE8B478B0B4D27B")
        
        assert iv == expected_iv, f"IV mismatch:\nGot:      {iv.hex()}\nExpected: {expected_iv.hex()}"
    
    def test_key_data_format(self):
        """Test key data construction for Key 0"""
        key_data = build_key_data(0, self.NEW_KEY, None, self.KEY_VERSION)
        
        # Expected from AN12196 Step 11
        expected = bytes.fromhex("5004BF991F408672B1EF00F08F9E864701800000000000000000000000000000")
        
        assert key_data == expected, f"Key data mismatch:\nGot:      {key_data.hex()}\nExpected: {expected.hex()}"
    
    def test_encryption(self):
        """Test key data encryption against AN12196 Step 13"""
        plaintext = bytes.fromhex("5004BF991F408672B1EF00F08F9E864701800000000000000000000000000000")
        iv = bytes.fromhex("01602D579423B2797BE8B478B0B4D27B")
        
        encrypted = encrypt_key_data(plaintext, iv, self.SESSION_ENC_KEY)
        
        # Expected from AN12196 Step 13
        expected = bytes.fromhex("C0EB4DEEFEDDF0B513A03A95A75491818580503190D4D05053FF75668A01D6FD")
        
        assert encrypted == expected, f"Encrypted mismatch:\nGot:      {encrypted.hex()}\nExpected: {expected.hex()}"
    
    def test_cmac_full(self):
        """Test full CMAC calculation against AN12196 Step 15"""
        # MAC Input from Step 14: Cmd || CmdCtr || TI || CmdHeader || EncryptedData
        mac_input = bytes.fromhex("C40300" + "7614281A" + "00" + "C0EB4DEEFEDDF0B513A03A95A75491818580503190D4D05053FF75668A01D6FD")
        
        cmac_full = calculate_cmac_full(mac_input, self.SESSION_MAC_KEY)
        
        # Expected from AN12196 Step 15
        expected = bytes.fromhex("B7A60161F202EC3489BD4BEDEF64BB32")
        
        assert cmac_full == expected, f"CMAC full mismatch:\nGot:      {cmac_full.hex()}\nExpected: {expected.hex()}"
    
    def test_cmac_truncation(self):
        """Test CMAC truncation (even-numbered bytes) against AN12196 Step 16"""
        cmac_full = bytes.fromhex("B7A60161F202EC3489BD4BEDEF64BB32")
        
        cmac_truncated = truncate_cmac(cmac_full)
        
        # Expected from AN12196 Step 16: "even-numbered bytes"
        # Indices 1,3,5,7,9,11,13,15: A6 61 02 34 BD ED 64 32
        expected = bytes.fromhex("A6610234BDED6432")
        
        assert cmac_truncated == expected, f"CMAC truncated mismatch:\nGot:      {cmac_truncated.hex()}\nExpected: {expected.hex()}"
    
    def test_complete_changekey_apdu(self):
        """Test complete ChangeKey APDU against AN12196 Step 17"""
        apdu = build_changekey_apdu(
            key_no=0,
            new_key=self.NEW_KEY,
            old_key=None,
            version=self.KEY_VERSION,
            ti=self.TI,
            cmd_ctr=self.CMD_CTR,
            session_enc_key=self.SESSION_ENC_KEY,
            session_mac_key=self.SESSION_MAC_KEY
        )
        
        # Expected from AN12196 Step 17
        # Data portion: KeyNo || Encrypted || CMAC
        expected_data = bytes.fromhex("00" + "C0EB4DEEFEDDF0B513A03A95A75491818580503190D4D05053FF75668A01D6FD" + "A6610234BDED6432")
        
        # Extract data portion from APDU (skip CLA CMD P1 P2 Lc, take until Le)
        apdu_data = bytes(apdu[5:-1])
        
        assert apdu_data == expected_data, f"APDU data mismatch:\nGot:      {apdu_data.hex()}\nExpected: {expected_data.hex()}"
        
        # Verify structure
        assert apdu[0] == 0x90, "CLA should be 0x90"
        assert apdu[1] == 0xC4, "CMD should be 0xC4 (ChangeKey)"
        assert apdu[4] == 0x29, "Lc should be 0x29 (41 bytes)"
        assert len(apdu) == 47, f"APDU should be 47 bytes, got {len(apdu)}"


class TestAN12343Vectors:
    """Test against AN12343 Table 40 example"""
    
    # Test values from AN12343 Table 40
    TI = bytes.fromhex("94297F4D")
    CMD_CTR = 0  # After auth
    SESSION_ENC_KEY = bytes.fromhex("E156C8522F7C8DC82B0C99BA847DE723")
    SESSION_MAC_KEY = bytes.fromhex("45D50C1570000D2F173DF949288E3CAD")
    NEW_KEY = bytes.fromhex("01234567890123456789012345678901")
    KEY_VERSION = 0x00
    
    def test_iv_calculation(self):
        """Test IV calculation against AN12343 Table 40"""
        iv = calculate_iv_for_command(self.TI, self.CMD_CTR, self.SESSION_ENC_KEY)
        
        # Expected from AN12343 Row 18
        expected_iv = bytes.fromhex("BF4A2FB89311ED58E9DCBE56FC17794C")
        
        assert iv == expected_iv, f"IV mismatch:\nGot:      {iv.hex()}\nExpected: {expected_iv.hex()}"
    
    def test_key_data_format(self):
        """Test key data construction for Key 0"""
        key_data = build_key_data(0, self.NEW_KEY, None, self.KEY_VERSION)
        
        # Expected from AN12343 Row 16
        expected = bytes.fromhex("0123456789012345678901234567890100800000000000000000000000000000")
        
        assert key_data == expected, f"Key data mismatch:\nGot:      {key_data.hex()}\nExpected: {expected.hex()}"
    
    def test_encryption(self):
        """Test key data encryption against AN12343 Table 40"""
        plaintext = bytes.fromhex("0123456789012345678901234567890100800000000000000000000000000000")
        iv = bytes.fromhex("BF4A2FB89311ED58E9DCBE56FC17794C")
        
        encrypted = encrypt_key_data(plaintext, iv, self.SESSION_ENC_KEY)
        
        # Expected from AN12343 Row 20
        expected = bytes.fromhex("BF5400DC97A1FBD65BE870716D6F11F8161BB4CA472856DB94AB94B2EC1A13E6")
        
        assert encrypted == expected, f"Encrypted mismatch:\nGot:      {encrypted.hex()}\nExpected: {expected.hex()}"
    
    def test_cmac_truncation_value(self):
        """Test CMAC truncation result against AN12343 Table 40"""
        # MAC Input from Row 22
        mac_input = bytes.fromhex("C40000" + "94297F4D" + "00" + "BF5400DC97A1FBD65BE870716D6F11F8161BB4CA472856DB94AB94B2EC1A13E6")
        
        cmac_full = calculate_cmac_full(mac_input, self.SESSION_MAC_KEY)
        cmac_truncated = truncate_cmac(cmac_full)
        
        # Expected from AN12343 Row 23
        expected = bytes.fromhex("27CE07CF56C11091")
        
        assert cmac_truncated == expected, f"CMAC truncated mismatch:\nGot:      {cmac_truncated.hex()}\nExpected: {expected.hex()}"


class TestCRC32:
    """Test CRC32 calculation for non-zero keys"""
    
    def test_crc32_all_zeros(self):
        """Test CRC32 of all-zeros key"""
        import zlib
        key = bytes(16)
        
        # Arduino: crc = CRC32::calculate(message16, 16) & 0xFFFFFFFF ^ 0xFFFFFFFF
        crc = zlib.crc32(key) ^ 0xFFFFFFFF
        crc_bytes = crc.to_bytes(4, byteorder='little')
        
        # CRC32 of 16 zero bytes with inversion
        # zlib.crc32(bytes(16)) = 0xC8DF7B94
        # Inverted: 0xC8DF7B94 ^ 0xFFFFFFFF = 0x3720846B
        expected = bytes.fromhex("6B842037")  # Little-endian
        
        assert crc_bytes == expected, f"CRC32 mismatch:\nGot:      {crc_bytes.hex()}\nExpected: {expected.hex()}"
    
    def test_crc32_one_followed_by_zeros(self):
        """Test CRC32 of [1, 0, 0, ..., 0]"""
        import zlib
        key = bytes([1] + [0]*15)
        
        crc = zlib.crc32(key) ^ 0xFFFFFFFF
        crc_bytes = crc.to_bytes(4, byteorder='little')
        
        # This should match Arduino captured value when we run it
        print(f"CRC32 of [1,0,0,...]: {crc_bytes.hex()}")
        assert len(crc_bytes) == 4
    
    def test_build_key_data_with_crc(self):
        """Test key data construction for non-zero key"""
        old_key = bytes(16)
        new_key = bytes([1] + [0]*15)
        
        key_data = build_key_data(1, new_key, old_key, 0x01)
        
        # Format: XOR(16) + Version(1) + CRC32(4) + 0x80 + padding(10)
        assert len(key_data) == 32
        assert key_data[16] == 0x01  # Version
        assert key_data[21] == 0x80  # Padding marker
        assert key_data[22:] == bytes(10)  # Zeros
        
        # XOR should be same as new_key (since old is zeros)
        assert key_data[0:16] == new_key
        
        # CRC32 should be at bytes 17-20
        import zlib
        expected_crc = (zlib.crc32(new_key) ^ 0xFFFFFFFF).to_bytes(4, 'little')
        assert key_data[17:21] == expected_crc


class TestByteOrder:
    """Test byte order for various fields"""
    
    def test_counter_little_endian(self):
        """Verify counter is little-endian"""
        cmd_ctr = 3
        counter_bytes = cmd_ctr.to_bytes(2, byteorder='little')
        
        # 3 in little-endian = 0x0300
        assert counter_bytes == b'\x03\x00'
    
    def test_iv_structure(self):
        """Verify IV structure"""
        ti = bytes.fromhex("7614281A")
        cmd_ctr = 3
        
        # Build plaintext IV manually
        plaintext_iv = bytearray(16)
        plaintext_iv[0] = 0xA5
        plaintext_iv[1] = 0x5A
        plaintext_iv[2:6] = ti
        plaintext_iv[6:8] = cmd_ctr.to_bytes(2, 'little')
        
        expected = bytes.fromhex("A55A7614281A03000000000000000000")
        assert bytes(plaintext_iv) == expected
    
    def test_mac_input_structure(self):
        """Verify MAC input structure"""
        cmd = 0xC4
        cmd_ctr = 3
        ti = bytes.fromhex("7614281A")
        key_no = 0
        encrypted = bytes(32)  # Dummy
        
        # Build MAC input
        mac_input = bytearray()
        mac_input.append(cmd)
        mac_input.extend(cmd_ctr.to_bytes(2, 'little'))
        mac_input.extend(ti)
        mac_input.append(key_no)
        mac_input.extend(encrypted)
        
        # Should start with: C4 03 00 76 14 28 1A 00
        assert mac_input[0] == 0xC4
        assert mac_input[1:3] == b'\x03\x00'
        assert mac_input[3:7] == ti
        assert mac_input[7] == key_no


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

