# file: ntag424_sdm_provisioner/utils/sdm_helpers.py

from typing import Dict
from ntag424_sdm_provisioner.constants import SDMUrlTemplate, SDMConfiguration, FileOption

def calculate_sdm_offsets(template: SDMUrlTemplate) -> Dict[str, int]:
    """
    Calculate byte offsets for SDM mirrors in NDEF message.
    
    Args:
        template: URL template with placeholders
    
    Returns:
        Dictionary with offset keys for SDMConfiguration
    """
    # Build full URL
    params = [f"uid={template.uid_placeholder}"]
    if template.cmac_placeholder:
        params.append(f"cmac={template.cmac_placeholder}")
    if template.enc_placeholder:
        params.append(f"enc={template.enc_placeholder}")
    if template.read_ctr_placeholder:
        params.append(f"ctr={template.read_ctr_placeholder}")
    
    url = f"{template.base_url}?{'&'.join(params)}"
    
    # NDEF Type 4 Tag overhead
    # [T=03][L][Record Header (5 bytes)][URI Prefix=04][URL...]
    # Typical overhead = 7 bytes
    ndef_overhead = 7
    
    offsets = {}
    
    # Find UID offset
    uid_start = url.find(template.uid_placeholder)
    if uid_start != -1:
        offsets['picc_data_offset'] = ndef_overhead + uid_start
        offsets['mac_input_offset'] = ndef_overhead + uid_start
    
    # Find CMAC offset
    cmac_start = url.find(template.cmac_placeholder)
    if cmac_start != -1:
        offsets['mac_offset'] = ndef_overhead + cmac_start
    
    # Find encrypted data offset
    if template.enc_placeholder:
        enc_start = url.find(template.enc_placeholder)
        if enc_start != -1:
            offsets['enc_data_offset'] = ndef_overhead + enc_start
            offsets['enc_data_length'] = len(template.enc_placeholder) // 2
    
    # Find read counter offset
    if template.read_ctr_placeholder:
        ctr_start = url.find(template.read_ctr_placeholder)
        if ctr_start != -1:
            offsets['read_ctr_offset'] = ndef_overhead + ctr_start
    
    return offsets


def build_sdm_settings_payload(config: SDMConfiguration) -> bytes:
    """
    Build the file settings data payload for ChangeFileSettings command.
    
    Args:
        config: SDM configuration
    
    Returns:
        Byte array ready to send to card
    """
    # Start with comm mode and access rights
    data = bytearray([config.comm_mode])
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
    
    # Helper to add 3-byte little-endian offset
    def add_offset(value: int):
        data.extend([
            value & 0xFF,
            (value >> 8) & 0xFF,
            (value >> 16) & 0xFF
        ])
    
    # Add required offsets
    add_offset(config.picc_data_offset)
    add_offset(config.mac_input_offset)
    
    # Optional encrypted data mirror
    if config.enc_data_offset is not None:
        add_offset(config.enc_data_offset)
        add_offset(config.enc_data_length)
    
    # MAC offset
    add_offset(config.mac_offset)
    
    # Optional read counter
    if config.read_ctr_offset is not None:
        add_offset(config.read_ctr_offset)
    
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