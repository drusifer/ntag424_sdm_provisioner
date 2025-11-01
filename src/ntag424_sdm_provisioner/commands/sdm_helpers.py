# file: ntag424_sdm_provisioner/commands/sdm_helpers.py

from typing import Dict, Optional
from ntag424_sdm_provisioner.constants import (
    SDMUrlTemplate, SDMConfiguration, FileOption, FileSettingsResponse, KeyVersionResponse
)

def calculate_sdm_offsets(template: SDMUrlTemplate) -> Dict[str, int]:
    """
    Calculate byte offsets for SDM mirrors in NDEF message.
    
    Args:
        template: URL template with placeholders
    
    Returns:
        Dictionary with offset keys for SDMConfiguration
    """
    # Build full URL with correct parameter order: uid, ctr, cmac
    params = [f"uid={template.uid_placeholder}"]
    if template.read_ctr_placeholder:
        params.append(f"ctr={template.read_ctr_placeholder}")
    if template.enc_placeholder:
        params.append(f"enc={template.enc_placeholder}")
    if template.cmac_placeholder:
        params.append(f"cmac={template.cmac_placeholder}")
    
    url = f"{template.base_url}?{'&'.join(params)}"
    
    # NDEF Type 4 Tag overhead
    # [T=03][L][Record Header (5 bytes)][URI Prefix=04][URL...]
    # Typical overhead = 7 bytes
    ndef_overhead = 7
    
    offsets = {}
    
    # Find UID offset by searching for 'uid=' parameter
    uid_param = url.find('uid=')
    if uid_param != -1:
        uid_value_start = uid_param + 4  # Skip 'uid='
        offsets['picc_data_offset'] = ndef_overhead + uid_value_start
        offsets['mac_input_offset'] = ndef_overhead + uid_value_start
    
    # Find CMAC offset by searching for 'cmac=' parameter
    if template.cmac_placeholder:
        cmac_param = url.find('cmac=')
        if cmac_param != -1:
            cmac_value_start = cmac_param + 5  # Skip 'cmac='
            offsets['mac_offset'] = ndef_overhead + cmac_value_start
    
    # Find encrypted data offset by searching for 'enc=' parameter
    if template.enc_placeholder:
        enc_param = url.find('enc=')
        if enc_param != -1:
            enc_value_start = enc_param + 4  # Skip 'enc='
            offsets['enc_data_offset'] = ndef_overhead + enc_value_start
            offsets['enc_data_length'] = len(template.enc_placeholder) // 2
    
    # Find read counter offset by searching for 'ctr=' parameter
    if template.read_ctr_placeholder:
        ctr_param = url.find('ctr=')
        if ctr_param != -1:
            ctr_value_start = ctr_param + 4  # Skip 'ctr='
            offsets['read_ctr_offset'] = ndef_overhead + ctr_value_start
    
    return offsets


def build_sdm_settings_payload(config: SDMConfiguration) -> bytes:
    """
    Build the file settings data payload for ChangeFileSettings command.
    
    Args:
        config: SDM configuration
    
    Returns:
        Byte array ready to send to card
    """
    # Start with FileOption byte (combines CommMode and SDM enable bit)
    # FileOption: Bit 6 = SDM enabled, Bits 1-0 = CommMode
    file_option = config.comm_mode  # Start with comm mode (bits 1-0)
    if config.enable_sdm:
        file_option |= 0x40  # Set bit 6 to enable SDM
    data = bytearray([file_option])
    # Access rights can be bytes or AccessRights object - convert if needed
    if hasattr(config.access_rights, 'to_bytes'):
        access_rights_bytes = config.access_rights.to_bytes()
    elif isinstance(config.access_rights, bytes):
        access_rights_bytes = config.access_rights
    else:
        # Assume it's a list/sequence
        access_rights_bytes = bytes(config.access_rights)
    data.extend(access_rights_bytes)
    
    if not config.enable_sdm:
        return bytes(data)
    
    # SDM options byte
    sdm_opts = config.sdm_options or (FileOption.SDM_ENABLED | FileOption.UID_MIRROR)
    data.append(sdm_opts)
    
    # SDMAccessRights (2 bytes) - REQUIRED when SDM enabled!
    # Per NXP spec: 16-bit value
    # Bits 15-12 (high byte 7-4): SDMMetaRead
    # Bits 11-8  (high byte 3-0): SDMFileRead
    # Bits 7-4   (low byte 7-4): RFU (must be F)
    # Bits 3-0   (low byte 3-0): SDMCtrRet
    # For plain UID: SDMMetaRead=E, SDMFileRead=F, SDMCtrRet=E
    # High byte = (E << 4) | F = 0xEF
    # Low byte = (F << 4) | E = 0xFE (not 0x0E!)
    data.extend([0xEF, 0xFE])  # SDMAccessRights (FIXED byte order!)
    
    # Helper to add 3-byte little-endian offset
    def add_offset(value: int):
        data.extend([
            value & 0xFF,
            (value >> 8) & 0xFF,
            (value >> 16) & 0xFF
        ])
    
    # FIELD ORDER per NXP spec Section 10.7.1:
    # The presence of each field depends on SDMOptions bits and SDMAccessRights values
    
    # From spec Table 69:
    # UIDOffset [3] - Present if: (SDMOptions[Bit 7] = 1) AND (SDMMetaRead != Fh)
    # SDMReadCtrOffset [3] - Present if: (SDMOptions[Bit 6] = 1) AND (SDMMetaRead != Fh)  
    # PICCDataOffset [3] - Present if: SDMMetaRead = 0..4 (encrypted)
    # SDMMACInputOffset [3] - Present if: SDMFileRead != Fh
    # SDMENCOffset [3] - Present if: SDMOptions[Bit 4] = 1
    # SDMENCLength [3] - Present if: SDMOptions[Bit 4] = 1
    # SDMMACOffset [3] - Present if: SDMFileRead != Fh
    # SDMReadCtrLimit [3] - Present if: SDMOptions[Bit 5] = 1
    
    # Our config: SDMMetaRead=E (plain), SDMFileRead=F (disabled)
    
    # 1. UIDOffset - if UID_MIRROR and SDMMetaRead != F
    # We have SDMMetaRead=E, so this should be present
    if sdm_opts & 0x80:  # UID_MIRROR (bit 7)
        add_offset(config.picc_data_offset)  # UID offset
    
    # 2. SDMReadCtrOffset - if READ_COUNTER and SDMMetaRead != F
    # SDMOptions bit 6 = READ_COUNTER (0x40)
    if sdm_opts & 0x40:  # READ_COUNTER (bit 6, CORRECTED!)
        if config.read_ctr_offset is not None:
            add_offset(config.read_ctr_offset)
    
    # 3. PICCDataOffset - ONLY if SDMMetaRead = 0..4 (encrypted)
    # We have SDMMetaRead=E, so SKIP
    
    # 4. SDMMACInputOffset - ONLY if SDMFileRead != F
    # We have SDMFileRead=F, so SKIP
    
    # 5-6. SDMENCOffset/Length - ONLY if encryption enabled (bit 4)
    # We don't have bit 4 set, so SKIP
    
    # 7. SDMMACOffset - ONLY if SDMFileRead != F
    # We have SDMFileRead=F, so SKIP
    
    # 8. SDMReadCtrLimit - ONLY if bit 5 set (counter limit)
    # We're not setting a limit, so SKIP
    
    return bytes(data)
# file: ntag424_sdm_provisioner/utils/sdm_helpers.py


def build_ndef_uri_record(url: str) -> bytes:
    """
    Build NDEF Type 4 Tag message with URI record.
    
    Args:
        url: Complete URL (with or without placeholders)
    
    Returns:
        NDEF message bytes ready to write to file
    """
    # URI identifier codes (0x04 = "https://")
    uri_prefix = 0x04
    
    # Remove "https://" from URL since we use prefix code
    if url.startswith("https://"):
        url_content = url[8:]
    elif url.startswith("http://"):
        uri_prefix = 0x03
        url_content = url[7:]
    else:
        uri_prefix = 0x00  # No prefix
        url_content = url
    
    url_bytes = url_content.encode('ascii')
    
    # NDEF Record: [Header][Type Length][Payload Length][Type][Payload]
    ndef_record = bytes([
        0xD1,  # MB=1, ME=1, CF=0, SR=1, IL=0, TNF=0x01 (Well-known)
        0x01,  # Type Length = 1
        len(url_bytes) + 1,  # Payload length (prefix + URL)
        0x55,  # Type = 'U' (URI)
        uri_prefix  # URI prefix code
    ]) + url_bytes
    
    # Wrap in TLV: [T=03][L][NDEF Record][T=FE]
    ndef_message = bytes([
        0x03,  # NDEF Message TLV
        len(ndef_record)
    ]) + ndef_record + bytes([0xFE])  # Terminator TLV
    
    return ndef_message


def parse_file_settings(file_no: int, data: bytes) -> FileSettingsResponse:
    """
    Parse GetFileSettings response data into structured format.
    
    Args:
        file_no: File number that was queried
        data: Raw response data from GetFileSettings command
    
    Returns:
        FileSettingsResponse dataclass with parsed fields
    """
    if len(data) < 7:
        raise ValueError(f"File settings data too short: {len(data)} bytes (minimum 7)")
    
    # Required fields (always present)
    file_type = data[0]
    file_option = data[1]
    access_rights = data[2:4]
    file_size = int.from_bytes(data[4:7], 'little')
    
    # Optional SDM fields (present if SDM is enabled)
    sdm_options = None
    sdm_access_rights = None
    uid_offset = None
    read_ctr_offset = None
    picc_data_offset = None
    mac_input_offset = None
    enc_offset = None
    enc_length = None
    mac_offset = None
    read_ctr_limit = None
    
    if len(data) > 7 and (file_option & FileOption.SDM_ENABLED):
        offset = 7
        
        # SDM options byte
        if offset < len(data):
            sdm_options = data[offset]
            offset += 1
        
        # SDM access rights (2 bytes)
        if offset + 2 <= len(data):
            sdm_access_rights = data[offset:offset+2]
            offset += 2
        
        # UID offset (3 bytes, little-endian)
        if offset + 3 <= len(data):
            uid_offset = int.from_bytes(data[offset:offset+3], 'little')
            offset += 3
        
        # SDM Read Counter offset (3 bytes)
        if offset + 3 <= len(data):
            read_ctr_offset = int.from_bytes(data[offset:offset+3], 'little')
            offset += 3
        
        # PICC Data offset (3 bytes)
        if offset + 3 <= len(data):
            picc_data_offset = int.from_bytes(data[offset:offset+3], 'little')
            offset += 3
        
        # MAC Input offset (3 bytes)
        if offset + 3 <= len(data):
            mac_input_offset = int.from_bytes(data[offset:offset+3], 'little')
            offset += 3
        
        # Encrypted data offset (3 bytes) - optional
        if offset + 3 <= len(data):
            enc_offset = int.from_bytes(data[offset:offset+3], 'little')
            offset += 3
            
            # Encryption length (3 bytes) - present if enc_offset is present
            if offset + 3 <= len(data):
                enc_length = int.from_bytes(data[offset:offset+3], 'little')
                offset += 3
        
        # MAC offset (3 bytes)
        if offset + 3 <= len(data):
            mac_offset = int.from_bytes(data[offset:offset+3], 'little')
            offset += 3
        
        # Read Counter Limit (3 bytes) - optional
        if offset + 3 <= len(data):
            read_ctr_limit = int.from_bytes(data[offset:offset+3], 'little')
    
    return FileSettingsResponse(
        file_no=file_no,
        file_type=file_type,
        file_option=file_option,
        access_rights=access_rights,
        file_size=file_size,
        sdm_options=sdm_options,
        sdm_access_rights=sdm_access_rights,
        uid_offset=uid_offset,
        read_ctr_offset=read_ctr_offset,
        picc_data_offset=picc_data_offset,
        mac_input_offset=mac_input_offset,
        enc_offset=enc_offset,
        enc_length=enc_length,
        mac_offset=mac_offset,
        read_ctr_limit=read_ctr_limit,
    )


def parse_key_version(key_no: int, data: bytes) -> KeyVersionResponse:
    """
    Parse GetKeyVersion response data into structured format.
    
    Args:
        key_no: Key number that was queried
        data: Raw response data from GetKeyVersion command
    
    Returns:
        KeyVersionResponse dataclass with parsed fields
    """
    if not data or len(data) < 1:
        raise ValueError(f"Key version data too short: {len(data)} bytes (minimum 1)")
    
    version = data[0]
    
    return KeyVersionResponse(key_no=key_no, version=version)