"""
WriteData Command

Writes data to a standard file on the NTAG424 DNA tag.
"""

from logging import getLogger

from ntag424_sdm_provisioner.commands.base import ApduCommand, ApduError
from ntag424_sdm_provisioner.constants import SuccessResponse, SW_OK, SW_OK_ALTERNATIVE
from ntag424_sdm_provisioner.hal import NTag424CardConnection

log = getLogger(__name__)


class WriteData(ApduCommand):
    """
    Writes data to a standard file on the card.
    
    Command: 90 3D 00 00 [Lc] [FileNo] [Offset:3] [Length:3] [Data] 00
    
    Example:
        >>> cmd = WriteData(file_no=0x02, offset=0, data_to_write=b'Hello')
        >>> result = cmd.execute(connection)
    """
    
    def __init__(self, file_no: int, offset: int, data_to_write: bytes):
        """
        Initialize WriteData command.
        
        Args:
            file_no: File number to write to
            offset: Byte offset within file
            data_to_write: Data bytes to write
        """
        super().__init__(use_escape=True)
        self.file_no = file_no
        self.offset = offset
        self.data = data_to_write

    def __str__(self) -> str:
        return f"WriteData(file_no=0x{self.file_no:02X}, offset={self.offset}, data=<{len(self.data)} bytes>)"

    def execute(self, connection: 'NTag424CardConnection') -> SuccessResponse:
        """
        Execute WriteData command.
        
        Returns:
            SuccessResponse with bytes written confirmation
            
        Raises:
            ApduError: If write fails
        """
        header = [
            self.file_no,
            self.offset & 0xFF, (self.offset >> 8) & 0xFF, 0x00,
            len(self.data) & 0xFF, (len(self.data) >> 8) & 0xFF, 0x00,
        ]
        apdu = [0x90, 0x3D, 0x00, 0x00, len(header) + len(self.data), *header, *self.data, 0x00]
        _, sw1, sw2 = self.send_apdu(connection, apdu)
        if (sw1, sw2) not in [SW_OK, SW_OK_ALTERNATIVE]:
            raise ApduError(f"Failed to write to file {self.file_no}", sw1, sw2)
        return SuccessResponse(f"Wrote {len(self.data)} bytes to file 0x{self.file_no:02X}.")

