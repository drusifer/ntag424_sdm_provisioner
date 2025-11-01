"""
ReadData Command

Reads data from a standard file on the NTAG424 DNA tag.
"""

from logging import getLogger

from ntag424_sdm_provisioner.commands.base import ApduCommand, ApduError
from ntag424_sdm_provisioner.constants import ReadDataResponse, SW_OK
from ntag424_sdm_provisioner.hal import NTag424CardConnection

log = getLogger(__name__)


class ReadData(ApduCommand):
    """
    Reads data from a standard file on the card.
    
    Command: 90 BD 00 00 07 [FileNo] [Offset:3] [Length:3] 00
    
    Example:
        >>> cmd = ReadData(file_no=0x02, offset=0, length=256)
        >>> response = cmd.execute(connection)
        >>> print(f"Read {len(response.data)} bytes")
    """
    
    def __init__(self, file_no: int, offset: int, length: int):
        """
        Initialize ReadData command.
        
        Args:
            file_no: File number to read from
            offset: Byte offset within file
            length: Number of bytes to read
        """
        super().__init__(use_escape=True)
        self.file_no = file_no
        self.offset = offset
        self.length = length

    def __str__(self) -> str:
        return f"ReadData(file_no=0x{self.file_no:02X}, offset={self.offset}, length={self.length})"

    def execute(self, connection: 'NTag424CardConnection') -> ReadDataResponse:
        """
        Execute ReadData command.
        
        Returns:
            ReadDataResponse with file data
            
        Raises:
            ApduError: If read fails
        """
        apdu = [
            0x90, 0xBD, 0x00, 0x00, 0x07,
            self.file_no,
            self.offset & 0xFF, (self.offset >> 8) & 0xFF, 0x00,
            self.length & 0xFF, (self.length >> 8) & 0xFF, 0x00,
            0x00
        ]
        data, sw1, sw2 = self.send_apdu(connection, apdu)
        if (sw1, sw2) != SW_OK:
            raise ApduError(f"Failed to read file {self.file_no}", sw1, sw2)
        return ReadDataResponse(file_no=self.file_no, offset=self.offset, data=bytes(data))

