"""
DNA_Calc Reference Implementation

This is the Arduino-based reference implementation for ChangeKey operations.
Kept in test package for validation and comparison with production implementation.

Original source: Arduino MFRC522_NTAG424DNA library
Purpose: Verify our production ChangeKey implementation is correct
Coverage: 99% (from original testing)
"""

from Crypto.Cipher import AES
from Crypto.Hash import CMAC
import zlib


def memcpy(dest: bytearray, src: bytearray, num_bytes: int, src_start=0, dest_start=0):
    """Helper function for array copying (Arduino-style)."""
    dest[dest_start : dest_start + num_bytes] = src[src_start : src_start + num_bytes]


class CRC32Z:
    """CRC32 checksum calculator using Python's built-in zlib."""
    
    @staticmethod
    def calculate(data: bytearray, length: int) -> int:
        """
        Calculate the CRC32 checksum of a byte array.
        
        Args:
            data: bytearray to calculate checksum for
            length: number of bytes to process
            
        Returns:
            int: The 32-bit CRC checksum
        """
        return zlib.crc32(data[:length]) & 0xFFFFFFFF


class CRC32:
    """CRC32 checksum calculator using 16-entry lookup table and nibble processing."""
    
    # CRC32 lookup table (16 entries, optimized for memory)
    # via http://forum.arduino.cc/index.php?topic=91179.0
    _CRC32_TABLE = [
        0x00000000, 0x1db71064, 0x3b6e20c8, 0x26d930ac,
        0x76dc4190, 0x6b6b51f4, 0x4db26158, 0x5005713c,
        0xedb88320, 0xf00f9344, 0xd6d6a3e8, 0xcb61b38c,
        0x9b64c2b0, 0x86d3d2d4, 0xa00ae278, 0xbdbdf21c
    ]
    
    @staticmethod
    def calculate(data: bytearray, length: int) -> int:
        """
        Calculate the CRC32 checksum of a byte array.
        
        Args:
            data: bytearray to calculate checksum for
            length: number of bytes to process
            
        Returns:
            int: The 32-bit CRC checksum
        """
        state = 0xFFFFFFFF
        
        for i in range(length):
            byte = data[i]
            # Process byte as two 4-bit nibbles
            tbl_idx = (state ^ (byte >> 0)) & 0xFFFFFFFF
            state = (CRC32._CRC32_TABLE[tbl_idx & 0x0f] ^ (state >> 4)) & 0xFFFFFFFF
            tbl_idx = (state ^ (byte >> 4)) & 0xFFFFFFFF
            state = (CRC32._CRC32_TABLE[tbl_idx & 0x0f] ^ (state >> 4)) & 0xFFFFFFFF
        
        return (~state) & 0xFFFFFFFF


class DNA_Calc:
    """
    DNA calculation helper for NTAG424 change key operations.
    
    Reference implementation based on Arduino MFRC522_NTAG424DNA library.
    Used for testing and validating the production implementation.
    """

    def __init__(self, sesAuthEncKey: bytes, sesAuthMacKey: bytes, ti: bytes):
        self.CmdCtr = bytearray(2)
        self.CmdCtr[0] = 0x00
        self.CmdCtr[1] = 0x00
  
        self.SesAuthEncKey = sesAuthEncKey
        self.SesAuthMacKey = sesAuthMacKey
        self.TI = ti
        self.cbc = AES.new(self.SesAuthEncKey, AES.MODE_CBC)
    
    def get_full_change_key(self) -> bytes:
        """Full change key command."""
        newKey = bytearray(16)
        newKey[0] = 1
        return self.full_change_key(0, newKey, oldKey=None, newKeyVersion=0)
    
    def full_change_key(self, keyNumber: int, newKey: bytes, oldKey: bytes, newKeyVersion: int) -> bytes:
        """Calculate the full change key command."""
        Cmd = 0xC4
        sendData = bytearray(47)
        sendData[0] = 0x90  # CLA
        sendData[1] = Cmd   # CMD
        sendData[2] = 0x00  # P1
        sendData[3] = 0x00  # P2
        sendData[4] = 0x29  # LC - length of data (0x29 = 41)
        sendData[5] = keyNumber

        keyData = bytearray(32)
        keyData[:16] = newKey
        keyData[16] = newKeyVersion
        
        if keyNumber == 0:
            keyData[17] = 0x80
            result = self.DNA_CalculateDataEncAndCMACt(Cmd, keyData, 32, sendData[5:6], 1, sendData, 6)
            return result
        else:
            keyData[21] = 0x80
            for i in range(16):
                keyData[i] = oldKey[i] ^ newKey[i]

            # Calculate CRC32 of new key and store inverted value
            crc = self.DNA_CalculateCRC32NK(newKey)
            crc_inverted = crc ^ 0xFFFFFFFF
            crc_bytes = crc_inverted.to_bytes(4, 'little')
            keyData[17:21] = crc_bytes

            result = self.DNA_CalculateDataEncAndCMACt(Cmd, keyData, 32, sendData[5:6], 1, sendData, 6)
            return result

    def DNA_CalculateIV(self, b0: int, b1: int) -> bytes:
        """Calculate the IV."""
        iv = bytearray(16)
        iv[0] = b0
        iv[1] = b1
        iv[2] = self.TI[0]
        iv[3] = self.TI[1]
        iv[4] = self.TI[2]
        iv[5] = self.TI[3]
        iv[6] = self.CmdCtr[0]
        iv[7] = self.CmdCtr[1]

        # Encrypt IV with zero IV to get the actual IV
        cipher = AES.new(bytes(self.SesAuthEncKey), AES.MODE_CBC, iv=bytes(16))
        iv_enc = cipher.encrypt(bytes(iv))
        
        return bytearray(iv_enc)

    def DNA_CalculateIVCmd(self) -> bytearray:
        """Calculate the IV for command encryption (0xA5, 0x5A)."""
        return self.DNA_CalculateIV(0xA5, 0x5A)
  
    def DNA_CalculateCRC32NK(self, newKey: bytes) -> int:
        """Calculate the CRC32NK of the new key."""
        crc = CRC32.calculate(newKey, 16)
        return crc

    def DNA_CalculateCMACt(self, CMACInput: bytearray, CMACInputSize: int) -> bytes:
        """Calculate the CMACt (truncated CMAC - first 8 bytes)."""
        cmac = CMAC.new(bytes(self.SesAuthMacKey), ciphermod=AES)
        cmac.update(bytes(CMACInput[:CMACInputSize]))
        digest = cmac.digest()
        return bytearray(digest)[:8]

    def DNA_CalculateDataEncAndCMACt(
        self,
        cmd: int,
        dataToEncode: bytes,
        dataToEncLen: int, 
        cmdHeader: bytes,
        cmdHeaderLen: int,
        dest: bytearray,
        dest_start: int
    ) -> bytes:
        """Calculate the data encryption and CMACt."""
        dataEnc = bytearray(dataToEncLen)
        IVCmd = self.DNA_CalculateIVCmd()
        
        # Encrypt data with session key and command IV
        cipher = AES.new(bytes(self.SesAuthEncKey), AES.MODE_CBC, iv=bytes(IVCmd))
        dataEnc = bytearray(cipher.encrypt(bytes(dataToEncode[:dataToEncLen])))
        
        backDataEncAndCMACt = bytearray(dataToEncLen)
        memcpy(backDataEncAndCMACt, dataEnc, num_bytes=dataToEncLen)
        
        CMACinput = bytearray(cmdHeaderLen + dataToEncLen + 7)
        CMACinput[0] = cmd
        CMACinput[1] = self.CmdCtr[0]
        CMACinput[2] = self.CmdCtr[1]
        memcpy(CMACinput, self.TI, dest_start=3, num_bytes=4)
        memcpy(CMACinput, cmdHeader, dest_start=7, num_bytes=cmdHeaderLen)
        memcpy(CMACinput, dataEnc, dest_start=7 + cmdHeaderLen, num_bytes=dataToEncLen)
        
        CMACt = self.DNA_CalculateCMACt(CMACinput, cmdHeaderLen + dataToEncLen + 7)
        memcpy(backDataEncAndCMACt, dest_start=dataToEncLen, src=CMACt, num_bytes=8)
        
        return backDataEncAndCMACt

