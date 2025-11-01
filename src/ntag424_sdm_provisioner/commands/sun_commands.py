"""
SUN (Secure Unique NFC) commands for Seritag NTAG424 DNA tags.

SUN is NXP's built-in security feature that provides dynamic authentication
without requiring complex EV2 authentication protocols.
"""
from typing import List, Tuple, Optional
from ntag424_sdm_provisioner.commands.base import ApduCommand, ApduError
from ntag424_sdm_provisioner.constants import SuccessResponse
from ntag424_sdm_provisioner.hal import NTag424CardConnection, hexb
from logging import getLogger

log = getLogger(__name__)


class WriteNdefMessage(ApduCommand):
    """
    Write NDEF message to NTAG424 DNA tag.
    
    SUN system automatically appends dynamic authentication codes to URLs
    when the tag is scanned, providing secure authentication without
    requiring EV2 authentication.
    """
    
    def __init__(self, ndef_data: bytes):
        """
        Args:
            ndef_data: Complete NDEF message data to write
        """
        super().__init__(use_escape=True)
        self.ndef_data = ndef_data
    
    def __str__(self) -> str:
        return f"WriteNdefMessage(length={len(self.ndef_data)} bytes)"
    
    def execute(self, connection: 'NTag424CardConnection') -> SuccessResponse:
        """Write NDEF message to the tag."""
        
        # NDEF file is file number 2
        file_no = 0x02
        
        # Build APDU: 00 D6 <offset_high> <offset_low> <length> <data>
        # ISOUpdateBinary uses CLA=00 (ISO 7816-4 standard), not CLA=90
        offset = 0
        data_length = len(self.ndef_data)
        
        # P1[7]=0: P1-P2 encodes 15-bit offset
        # For offset 0: P1=0x00, P2=0x00
        p1 = (offset >> 8) & 0x7F  # Bit 7 must be 0 for offset mode
        p2 = offset & 0xFF
        
        apdu = [
            0x00, 0xD6,  # ISOUpdateBinary (CLA=00 for ISO standard)
            p1,          # P1 = Offset high bits (bit 7=0)
            p2,          # P2 = Offset low bits
            data_length, # Lc = Data length
        ] + list(self.ndef_data)  # Data (no Le for write commands)
        
        log.debug(f"WriteNdefMessage APDU: {hexb(apdu)}")
        
        # Send command
        _, sw1, sw2 = self.send_command(connection, apdu, allow_alternative_ok=False)
        
        return SuccessResponse(f"NDEF message written ({data_length} bytes)")


class ReadNdefMessage(ApduCommand):
    """
    Read NDEF message from NTAG424 DNA tag.
    
    This reads the current NDEF data, which may include SUN-generated
    dynamic authentication codes if the tag has been scanned.
    """
    
    def __init__(self, max_length: int = 256):
        """
        Args:
            max_length: Maximum number of bytes to read
        """
        super().__init__(use_escape=True)
        self.max_length = max_length
    
    def __str__(self) -> str:
        return f"ReadNdefMessage(max_length={self.max_length})"
    
    def execute(self, connection: 'NTag424CardConnection') -> bytes:
        """Read NDEF message from the tag."""
        
        # NDEF file is file number 2
        file_no = 0x02
        
        # Build APDU: 00 B0 <offset_high> <offset_low> <length>
        # ISOReadBinary uses CLA=00 (ISO 7816-4 standard), not CLA=90
        offset = 0
        
        # P1[7]=0: P1-P2 encodes 15-bit offset
        # For offset 0: P1=0x00, P2=0x00
        p1 = (offset >> 8) & 0x7F  # Bit 7 must be 0 for offset mode
        p2 = offset & 0xFF
        
        apdu = [
            0x00, 0xB0,  # ISOReadBinary (CLA=00 for ISO standard)
            p1,          # P1 = Offset high bits (bit 7=0)
            p2,          # P2 = Offset low bits
            self.max_length  # Le = Length to read
        ]
        
        log.debug(f"ReadNdefMessage APDU: {hexb(apdu)}")
        
        # Send command
        data, sw1, sw2 = self.send_command(connection, apdu, allow_alternative_ok=False)
        
        return bytes(data)


class ConfigureSunSettings(ApduCommand):
    """
    Configure SUN (Secure Unique NFC) settings for Seritag tags.
    
    SUN settings control how dynamic authentication codes are generated
    and appended to NDEF messages.
    """
    
    def __init__(self, enable_sun: bool = True, sun_options: int = 0x00):
        """
        Args:
            enable_sun: Enable SUN dynamic authentication
            sun_options: SUN configuration options
        """
        super().__init__(use_escape=True)
        self.enable_sun = enable_sun
        self.sun_options = sun_options
    
    def __str__(self) -> str:
        return f"ConfigureSunSettings(enable={self.enable_sun}, options=0x{self.sun_options:02X})"
    
    def execute(self, connection: 'NTag424CardConnection') -> SuccessResponse:
        """Configure SUN settings."""
        
        # Build SUN configuration data
        # ChangeFileSettings format: 90 5F 00 00 [Lc] [FileNo] [FileOption] [AccessRights] [SDMOptions...] 00
        # FileNo must be first byte in data payload!
        file_no = 0x02  # NDEF file
        
        # FileOption byte (communication mode and file options)
        file_option = 0x00  # Plain communication mode
        
        # Access rights (4 bytes: Read, Write, ReadWrite, Change)
        # FREE access = 0xEEEE (all Eh = free access)
        access_rights = [0x0E, 0x0E, 0x0E, 0x0E]  # FREE access for all operations
        
        # SDM/SUN options if enabled
        if self.enable_sun:
            # SDMOptions: 1 byte
            # SMDAccessRights: 1 byte  
            # Then SUN-specific options
            sdm_options = [0x01]  # Enable SDM/SUN
            sdm_access = [0x00]  # SDM access rights
            sun_config = [self.sun_options, 0x00, 0x00, 0x00]  # SUN options + reserved
            sdm_data = sdm_options + sdm_access + sun_config
        else:
            sdm_data = []
        
        # Build data payload: [FileNo] [FileOption] [AccessRights] [SDMOptions...]
        config_data = [file_no, file_option] + access_rights + sdm_data
        
        # Build APDU: 90 5F 00 00 [Lc] [config_data] 00
        apdu = [
            0x90, 0x5F,  # ChangeFileSettings command
            0x00, 0x00,  # P1, P2
            len(config_data),  # Lc = Data length
        ] + config_data + [0x00]  # Data + Le
        
        log.debug(f"ConfigureSunSettings APDU: {hexb(apdu)}")
        
        # Send command
        _, sw1, sw2 = self.send_command(connection, apdu, allow_alternative_ok=False)
        
        return SuccessResponse("SUN settings configured")


def build_ndef_uri_record(url: str) -> bytes:
    """
    Build NDEF URI record for SUN authentication.
    
    SUN system will automatically append dynamic authentication codes
    to URLs when the tag is scanned.
    
    Args:
        url: Base URL (SUN will append authentication parameters)
    
    Returns:
        Complete NDEF URI record ready to write to tag
    """
    # NDEF URI record structure:
    # [TNF=0x01][Type Length][Payload Length][Type="U"][URI Identifier][URI]
    
    uri_type = b"U"  # URI type
    uri_data = url.encode('utf-8')
    
    # NDEF record header
    record = bytearray()
    record.append(0x01)  # TNF = Well Known Type
    record.append(len(uri_type))  # Type Length
    record.append(len(uri_data))  # Payload Length
    record.extend(uri_type)  # Type
    record.append(0x04)  # URI Identifier = "https://"
    record.extend(uri_data)  # URI payload
    
    # Wrap in NDEF TLV
    ndef_tlv = bytearray()
    ndef_tlv.append(0x03)  # NDEF TLV tag
    ndef_tlv.append(len(record))  # Length
    ndef_tlv.extend(record)  # NDEF record
    
    # Add terminator TLV
    ndef_tlv.append(0xFE)  # Terminator TLV
    
    return bytes(ndef_tlv)


def parse_sun_url(url_with_sun: str) -> dict:
    """
    Parse SUN-enhanced URL to extract authentication data.
    
    SUN appends parameters like ?uid=XXXX&c=YYYY&mac=ZZZZ to URLs.
    
    Args:
        url_with_sun: URL that has been enhanced by SUN system
    
    Returns:
        Dictionary with parsed SUN parameters
    """
    import urllib.parse
    
    parsed = urllib.parse.urlparse(url_with_sun)
    params = urllib.parse.parse_qs(parsed.query)
    
    sun_data = {}
    
    if 'uid' in params:
        sun_data['uid'] = params['uid'][0]
    if 'c' in params:  # Counter
        sun_data['counter'] = int(params['c'][0], 16)
    if 'mac' in params:  # MAC/CMAC
        sun_data['mac'] = params['mac'][0]
    
    return sun_data
