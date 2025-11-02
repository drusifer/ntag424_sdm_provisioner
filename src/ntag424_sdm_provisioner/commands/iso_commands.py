"""
ISO 7816-4 standard commands for NTAG424 DNA.

These commands use CLA=0x00 (ISO7816 class) and follow ISO 7816-4 specification.
"""

from enum import IntEnum
from typing import List
from ntag424_sdm_provisioner.commands.base import ApduCommand
from ntag424_sdm_provisioner.constants import APDUInstruction, SuccessResponse
from ntag424_sdm_provisioner.hal import NTag424CardConnection


class ISOFileID(IntEnum):
    """ISO 7816 Elementary File IDs for NTAG424 DNA."""
    CC_FILE = 0xE103      # Capability Container
    NDEF_FILE = 0xE104    # NDEF data file
    PROP_FILE = 0xE105    # Proprietary file
    
    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:04X})"


class ISOSelectFile(ApduCommand):
    """
    ISO 7816-4 SELECT FILE command.
    
    Selects an Elementary File (EF) by file identifier for subsequent
    read/write operations.
    """
    
    # P1 values (selection mode)
    P1_SELECT_MF = 0x00      # Select Master File
    P1_SELECT_CHILD_DF = 0x01  # Select child DF
    P1_SELECT_EF = 0x02      # Select EF under current DF
    P1_SELECT_PARENT = 0x03  # Select parent DF
    P1_SELECT_BY_NAME = 0x04  # Select by DF name
    
    def __init__(self, file_id: int, use_escape: bool = True):
        """
        Args:
            file_id: File identifier (e.g., ISOFileID.NDEF_FILE = 0xE104)
            use_escape: Whether to use escape command (default True for ACR122U)
        """
        super().__init__(use_escape)
        self.file_id = file_id
    
    def __str__(self) -> str:
        # Use enum's __str__() for formatting
        try:
            file_id_enum = ISOFileID(self.file_id)
            return f"ISOSelectFile({file_id_enum})"
        except ValueError:
            return f"ISOSelectFile(0x{self.file_id:04X})"
    
    def execute(self, connection: NTag424CardConnection) -> SuccessResponse:
        """
        Execute ISO SELECT FILE command.
        
        Args:
            connection: Card connection
        
        Returns:
            SuccessResponse on success
        
        Raises:
            ApduError: If selection fails
        """
        # Build APDU: CLA INS P1 P2 Lc Data Le
        # CLA=0x00 (ISO7816), INS=0xA4 (SELECT_FILE), P1=0x02 (select EF), P2=0x00
        file_id_bytes = [
            (self.file_id >> 8) & 0xFF,  # High byte
            self.file_id & 0xFF           # Low byte
        ]
        
        apdu = [
            0x00,  # CLA: ISO7816
            APDUInstruction.SELECT_FILE.value,  # INS: 0xA4
            self.P1_SELECT_EF,  # P1: Select EF
            0x00,  # P2
            len(file_id_bytes),  # Lc
            *file_id_bytes,  # File ID (2 bytes)
            0x00   # Le
        ]
        
        _, sw1, sw2 = self.send_command(connection, apdu, allow_alternative_ok=False)
        
        # Use enum's __str__() for formatting
        try:
            file_id_enum = ISOFileID(self.file_id)
            return SuccessResponse(f"{file_id_enum} selected")
        except ValueError:
            return SuccessResponse(f"File 0x{self.file_id:04X} selected")

