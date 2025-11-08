"""
Utility functions for working with NTAG424 UIDs.
"""


def uid_to_asset_tag(uid: bytes) -> str:
    """
    Convert UID to a short asset tag code for labeling.
    
    Format: XX-YYYY (7 chars with dash)
    Uses bytes 3-6 of UID (skips manufacturer ID and batch suffix).
    
    Args:
        uid: 7-byte UID
        
    Returns:
        7-character asset tag code (e.g., "6E-6B4A")
        
    Example:
        >>> uid_to_asset_tag(bytes.fromhex('046E6B4A2F7080'))
        '6E-6B4A'
    """
    if len(uid) < 7:
        raise ValueError(f"UID must be at least 7 bytes, got {len(uid)}")
    
    # Use bytes 1-4 (skip manufacturer byte 0x04, skip batch suffix 2F7080)
    # Format: uid[1] - uid[2]uid[3]uid[4]
    return f"{uid[1]:02X}-{uid[2]:02X}{uid[3]:02X}"


def uid_to_short_hex(uid: bytes) -> str:
    """
    Convert UID to compact hex string (last 3 bytes, 6 chars).
    
    Args:
        uid: 7-byte UID
        
    Returns:
        6-character hex code (e.g., "2F7080")
        
    Example:
        >>> uid_to_short_hex(bytes.fromhex('046E6B4A2F7080'))
        '2F7080'
    """
    if len(uid) < 7:
        raise ValueError(f"UID must be at least 7 bytes, got {len(uid)}")
    
    # Last 3 bytes
    return uid[-3:].hex().upper()


def asset_tag_matches_uid(asset_tag: str, uid: bytes) -> bool:
    """
    Check if an asset tag code matches a UID.
    
    Args:
        asset_tag: Asset tag code (format: "XX-YYYY" or "XXYYY")
        uid: 7-byte UID to check
        
    Returns:
        True if asset tag matches the UID's bytes 1-3
        
    Example:
        >>> asset_tag_matches_uid("6E-6B4A", bytes.fromhex('046E6B4A2F7080'))
        True
    """
    # Remove dash if present
    code = asset_tag.replace('-', '').upper()
    
    if len(code) != 6:
        return False
    
    # Get bytes 1-3 of UID
    expected = uid[1:4].hex().upper()
    
    return code == expected


def format_uid_with_asset_tag(uid: bytes) -> str:
    """
    Format UID with asset tag for display.
    
    Args:
        uid: 7-byte UID
        
    Returns:
        Formatted string (e.g., "046E6B4A2F7080 [4A2F-7080]")
        
    Example:
        >>> format_uid_with_asset_tag(bytes.fromhex('046E6B4A2F7080'))
        '046E6B4A2F7080 [4A2F-7080]'
    """
    full_uid = uid.hex().upper()
    asset_tag = uid_to_asset_tag(uid)
    return f"{full_uid} [Tag: {asset_tag}]"

