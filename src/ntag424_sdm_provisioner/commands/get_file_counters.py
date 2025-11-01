"""
GetFileCounters Command

Retrieves the SDM read counter for a specific file. The counter increments
each time the file is read in unauthenticated mode with SDM enabled.
"""

from logging import getLogger

from ntag424_sdm_provisioner.commands.base import ApduCommand, ApduError
from ntag424_sdm_provisioner.constants import APDUInstruction, SW_OK, SW_OK_ALTERNATIVE
from ntag424_sdm_provisioner.hal import NTag424CardConnection, hexb

log = getLogger(__name__)


class GetFileCounters(ApduCommand):
    """
    Retrieves the SDM read counter for a specific file.
    
    The SDM read counter increments each time the file is read in unauthenticated
    mode with SDM enabled. This is used for replay protection in SUN URLs.
    
    Command: 90 C1 00 00 01 [FileNo] 00
    Response: [Counter: 3 bytes, LSB first] 9000
    
    Example:
        >>> cmd = GetFileCounters(file_no=0x02)
        >>> counter = cmd.execute(connection)
        >>> print(f"File counter: {counter}")
    """
    
    def __init__(self, file_no: int = 0x02):
        """
        Initialize GetFileCounters command.
        
        Args:
            file_no: File number (default 0x02 for NDEF file)
        """
        super().__init__(use_escape=True)
        self.file_no = file_no
    
    def __str__(self) -> str:
        return f"GetFileCounters(file_no=0x{self.file_no:02X})"
    
    def execute(self, connection: 'NTag424CardConnection') -> int:
        """
        Execute GetFileCounters command.
        
        Args:
            connection: Active card connection
            
        Returns:
            24-bit counter value (0-16777215)
            
        Raises:
            ApduError: If command fails
        """
        # Build APDU: 90 C1 00 00 01 [FileNo] 00
        apdu = [
            0x90,  # CLA: DESFire/NTAG424
            APDUInstruction.GET_FILE_COUNTERS,  # INS: 0xC1
            0x00,  # P1
            0x00,  # P2
            0x01,  # Lc: 1 byte data
            self.file_no,  # Data: file number
            0x00   # Le: expect response
        ]
        
        log.debug(f"GetFileCounters APDU: {hexb(apdu)}")
        
        data, sw1, sw2 = self.send_apdu(connection, apdu)
        
        if (sw1, sw2) not in [SW_OK, SW_OK_ALTERNATIVE]:
            raise ApduError(
                f"GetFileCounters failed for file 0x{self.file_no:02X}",
                sw1, sw2
            )
        
        # Parse counter (3 bytes, LSB first)
        if len(data) != 3:
            raise ApduError(
                f"GetFileCounters returned {len(data)} bytes, expected 3",
                sw1, sw2
            )
        
        # Convert LSB-first 3-byte value to integer
        counter = data[0] | (data[1] << 8) | (data[2] << 16)
        
        log.info(f"File 0x{self.file_no:02X} counter: {counter}")
        
        return counter

