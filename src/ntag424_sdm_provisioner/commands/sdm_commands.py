
from logging import getLogger
from typing import List, Optional

from ntag424_sdm_provisioner.commands.base import ApduCommand, ApduError, AuthenticatedConnection
from ntag424_sdm_provisioner.constants import (
    StatusWordPair, APDUInstruction,
    AuthenticationChallengeResponse, Ntag424VersionInfo, ReadDataResponse, SuccessResponse,
    FileSettingsResponse, KeyVersionResponse
)
from ntag424_sdm_provisioner.commands.sdm_helpers import parse_file_settings, parse_key_version
from ntag424_sdm_provisioner.hal import NTag424CardConnection, hexb

log = getLogger(__name__)

class GetChipVersion(ApduCommand):
    """
    Retrieves detailed version information from the NTAG424 DNA chip.
    """
    GET_VERSION_APDU = [0x90, 0x60, 0x00, 0x00, 0x00]

    def __init__(self):
        super().__init__(use_escape=True)

    def __str__(self) -> str:
        return "GetChipVersion()"

    def execute(self, connection: 'NTag424CardConnection') -> Ntag424VersionInfo:
        # send_command() handles multi-frame responses automatically
        full_response, sw1, sw2 = self.send_command(connection, self.GET_VERSION_APDU) 

        # 5. Now parse the complete, assembled response
        # NTAG424 DNA GetVersion returns 28 or 29 bytes total:
        # Part 1: 7 bytes (HW info)
        # Part 2: 7 bytes (SW info) 
        # Part 3: 14 or 15 bytes (Production info) - real hardware often omits FabKeyID
        if len(full_response) not in [28, 29]:
            raise ValueError(f"Received incomplete version data. "
                             f"Expected 28 or 29 bytes, got {len(full_response)}")

        final_data = bytes(full_response)
        
        # Parse according to NTAG424 DNA specification
        # Part 1: Hardware info (bytes 0-6)
        hw_vendor_id = final_data[0]
        hw_type = final_data[1] 
        hw_subtype = final_data[2]
        hw_major_version = final_data[3]
        hw_minor_version = final_data[4]
        hw_storage_size = final_data[5]
        hw_protocol = final_data[6]
        
        # Part 2: Software info (bytes 7-13)
        sw_vendor_id = final_data[7]
        sw_type = final_data[8]
        sw_subtype = final_data[9]
        sw_major_version = final_data[10]
        sw_minor_version = final_data[11]
        sw_storage_size = final_data[12]
        sw_protocol = final_data[13]
        
        # Part 3: Production info (bytes 14-27 or 14-28)
        uid = final_data[14:21]  # 7 bytes
        batch_no = final_data[21:25]  # 4 bytes
        fab_key = final_data[25]  # 1 byte
        cw_prod = final_data[26]  # 1 byte (calendar week)
        year_prod = final_data[27]  # 1 byte
        # fab_key_id is handled above based on response length
        
        return Ntag424VersionInfo(
            hw_vendor_id=hw_vendor_id,
            hw_type=hw_type,
            hw_subtype=hw_subtype,
            hw_major_version=hw_major_version,
            hw_minor_version=hw_minor_version,
            hw_storage_size=256 if hw_storage_size == 0x13 else 416,
            hw_protocol=hw_protocol,
            sw_vendor_id=sw_vendor_id,
            sw_type=sw_type,
            sw_subtype=sw_subtype,
            sw_major_version=sw_major_version,
            sw_minor_version=sw_minor_version,
            sw_storage_size=sw_storage_size,
            sw_protocol=sw_protocol,
            uid=uid,
            batch_no=batch_no,
            fab_week=cw_prod,
            fab_year=year_prod
        )


class SelectPiccApplication(ApduCommand):
    """Selects the main PICC-level application on the NTAG424 DNA tag."""
    PICC_AID = [0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01]

    def __init__(self):
        super().__init__(use_escape=True)
        
    def __str__(self) -> str:
        return f"SelectPiccApplication(AID={hexb(self.PICC_AID)})"

    def execute(self, connection: 'NTag424CardConnection') -> SuccessResponse:
        apdu = [0x00, 0xA4, 0x04, 0x00, len(self.PICC_AID), *self.PICC_AID, 0x00]
        _, sw1, sw2 = self.send_command(connection, apdu, allow_alternative_ok=False)
        return SuccessResponse("PICC Application selected.")

class AuthenticateEV2First(ApduCommand):
    """Begins the first phase of an EV2 authentication with an AES key."""
    def __init__(self, key_no: int):
        super().__init__(use_escape=True)
        self.key_no = key_no

    def __str__(self) -> str:
        return f"AuthenticateEV2First(key_no=0x{self.key_no:02X})"

    def execute(self, connection: 'NTag424CardConnection') -> AuthenticationChallengeResponse:
        # Format: CLA CMD P1 P2 Lc KeyNo LenCap Le
        # LenCap=00h means no PCDcap2 present
        apdu = [0x90, 0x71, 0x00, 0x00, 0x02, self.key_no, 0x00, 0x00]
        log.debug(f"AuthenticateEV2First APDU: {[hex(x) for x in apdu]}")
        log.debug(f"Requesting challenge for key number: {self.key_no}")
        
        # Special case: This command expects SW_ADDITIONAL_FRAME as success, not error
        # So we can't use send_command() and must call connection.send_apdu() directly
        data, sw1, sw2 = connection.send_apdu(apdu, use_escape=self.use_escape)
        log.debug(f"Response: data={len(data)} bytes, SW={sw1:02X}{sw2:02X}")
        
        if (sw1, sw2) != StatusWordPair.SW_ADDITIONAL_FRAME:
            log.error(f"AuthenticateEV2First failed with SW={sw1:02X}{sw2:02X}")
            log.error(f"Expected {StatusWordPair.SW_ADDITIONAL_FRAME}, got SW={sw1:02X}{sw2:02X}")
            raise ApduError("AuthenticateEV2First failed", sw1, sw2)
        
        # Phase 1 returns SW=91AF with encrypted RndB (16 bytes)
        # SW=91AF means "Additional Frame" but in this context, the 16 bytes ARE the complete challenge
        # We should NOT send GetAdditionalFrame - Phase 1 is complete with these 16 bytes
        # The SW=91AF is just NTAG424's way of saying "I have data for you"
        encrypted_rndb = bytes(data)
        
        # Verify we got exactly 16 bytes
        if len(encrypted_rndb) != 16:
            log.warning(f"Phase 1 returned {len(encrypted_rndb)} bytes, expected 16")
            if len(encrypted_rndb) < 16:
                raise ApduError(f"Phase 1 response too short: {len(encrypted_rndb)} bytes", sw1, sw2)
        
        log.debug(f"Successfully received challenge: {encrypted_rndb.hex().upper()}")
        return AuthenticationChallengeResponse(key_no_used=self.key_no, challenge=encrypted_rndb)


class AuthenticateEV2(ApduCommand):
    """
    Complete EV2 authentication command that returns an AuthenticatedConnection.
    
    This is a high-level command that performs both authentication phases
    and returns a context manager for authenticated operations.
    
    Usage:
        key = get_key()
        with CardManager() as connection:
            with AuthenticateEV2(key).execute(connection) as auth_conn:
                settings = GetFileSettings(file_no=2).execute(auth_conn)
                key_ver = GetKeyVersion(key_no=0).execute(auth_conn)
    """
    
    def __init__(self, key: bytes, key_no: int = 0, use_escape: bool = True):
        """
        Args:
            key: 16-byte AES key for authentication
            key_no: Key number to authenticate with (0-4)
            use_escape: Whether to use escape commands (needed for ACR122U)
        """
        super().__init__(use_escape)
        self.key = key
        self.key_no = key_no
    
    def __str__(self) -> str:
        return f"AuthenticateEV2(key_no=0x{self.key_no:02X})"
    
    def execute(self, connection: NTag424CardConnection) -> AuthenticatedConnection:
        """
        Perform complete EV2 authentication and return authenticated connection.
        
        Args:
            connection: Card connection to authenticate
        
        Returns:
            AuthenticatedConnection context manager with session keys
        
        Raises:
            ApduError: If authentication fails
        """
        from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
        
        log.info(f"Performing EV2 authentication with key {self.key_no}")
        
        # Create session and authenticate
        session = Ntag424AuthSession(self.key)
        session.authenticate(connection, key_no=self.key_no)
        
        log.info(f"Authentication successful, session established")
        
        # Return authenticated connection wrapper
        return AuthenticatedConnection(connection, session)


class AuthenticateEV2Second(ApduCommand):
    """Completes the second phase of an EV2 authentication."""
    def __init__(self, data_to_card: bytes):
        super().__init__(use_escape=True)
        if len(data_to_card) != 32:
            raise ValueError("Authentication data for phase two must be 32 bytes.")
        self.data_to_card = data_to_card

    def __str__(self) -> str:
        return f"AuthenticateEV2Second(data=<{len(self.data_to_card)} bytes>)"

    def execute(self, connection: 'NTag424CardConnection') -> bytes:
        apdu = [0x90, 0xAF, 0x00, 0x00, len(self.data_to_card), *self.data_to_card, 0x00]
        # send_command() handles multi-frame and status checking automatically
        full_response, sw1, sw2 = self.send_command(connection, apdu)
        return bytes(full_response)  # Return the card's encrypted response data

class ChangeKey(ApduCommand):
    """Changes a key on the card. Must be in an authenticated state."""
    def __init__(self, key_no_to_change: int, new_key: bytes, old_key: bytes):
        super().__init__(use_escape=True)
        # ... (constructor logic)
        self.key_no = key_no_to_change
        xored_key_data = bytes(a ^ b for a, b in zip(new_key, old_key))
        self.data_to_card = [key_no_to_change] + list(xored_key_data)
        
    def __str__(self) -> str:
        return f"ChangeKey(key_no=0x{self.key_no:02X})"

    def execute(self, connection: 'NTag424CardConnection') -> SuccessResponse:
        apdu = [0x90, 0xC4, 0x00, 0x00, len(self.data_to_card), *self.data_to_card]
        _, sw1, sw2 = self.send_command(connection, apdu, allow_alternative_ok=False)
        return SuccessResponse(f"Key 0x{self.key_no:02X} changed successfully.")

class GetFileIds(ApduCommand):
    """Get list of file IDs in the application."""
    
    def __init__(self):
        super().__init__(use_escape=True)
    
    def __str__(self) -> str:
        return "GetFileIds()"
    
    def execute(self, connection: 'NTag424CardConnection') -> List[int]:
        apdu = [0x90, 0x6F, 0x00, 0x00, 0x00]
        data, sw1, sw2 = self.send_command(connection, apdu)
        return list(data)


class GetFileSettings(ApduCommand):
    """
    Get settings for a specific file.
    
    Can be called with regular or authenticated connection.
    Most files allow reading settings without authentication (CommMode.PLAIN).
    """
    
    def __init__(self, file_no: int):
        super().__init__(use_escape=True)
        self.file_no = file_no
    
    def __str__(self) -> str:
        return f"GetFileSettings(file_no=0x{self.file_no:02X})"
    
    def execute(self, connection: 'NTag424CardConnection') -> FileSettingsResponse:
        """
        Execute command. Works with both regular and authenticated connections.
        
        Args:
            connection: NTag424CardConnection or AuthenticatedConnection
        
        Returns:
            FileSettingsResponse with parsed file settings
        
        Raises:
            ApduError: If command fails
        """
        # Build command - GetFileSettings typically doesn't need CMAC (CommMode.PLAIN)
        # Just send plain APDU
        apdu = [0x90, 0xF5, 0x00, 0x00, 0x01, self.file_no, 0x00]
        
        # Use send_command for automatic multi-frame handling
        data, sw1, sw2 = self.send_command(connection, apdu)
        
        # Parse and return structured response
        return parse_file_settings(self.file_no, bytes(data))


class GetKeyVersion(ApduCommand):
    """
    Get version of a specific key.
    
    Typically requires authentication (CommMode.MAC), but works with
    both regular and authenticated connections.
    """
    
    def __init__(self, key_no: int):
        super().__init__(use_escape=True)
        self.key_no = key_no
    
    def __str__(self) -> str:
        return f"GetKeyVersion(key_no=0x{self.key_no:02X})"
    
    def execute(self, connection: 'NTag424CardConnection') -> KeyVersionResponse:
        """
        Execute command. Try without auth first, use auth if needed.
        
        Args:
            connection: NTag424CardConnection or AuthenticatedConnection
        
        Returns:
            KeyVersionResponse with key version info
        
        Raises:
            ApduError: If command fails
        """
        # Build command - try plain first
        apdu = [0x90, 0x64, 0x00, 0x00, 0x01, self.key_no, 0x00]
        
        # Use send_command for automatic multi-frame handling
        data, sw1, sw2 = self.send_command(connection, apdu)
        
        # Parse and return structured response
        return parse_key_version(self.key_no, bytes(data))

