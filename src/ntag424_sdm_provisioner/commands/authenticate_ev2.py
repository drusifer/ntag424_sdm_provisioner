"""
EV2 Authentication commands for NTAG424 DNA.
"""

import logging
from typing import TYPE_CHECKING

from ntag424_sdm_provisioner.commands.base import ApduCommand, ApduError, AuthenticatedConnection
from ntag424_sdm_provisioner.constants import (
    AuthenticationChallengeResponse,
    StatusWordPair
)
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession

if TYPE_CHECKING:
    from ntag424_sdm_provisioner.hal import NTag424CardConnection

log = logging.getLogger(__name__)


class AuthenticateEV2First(ApduCommand):
    """
    Begins the first phase of an EV2 authentication with an AES key.
    
    This command requests an encrypted challenge (RndB) from the tag.
    Response SW=91AF is expected (means "additional frame" but is actually success).
    """
    
    def __init__(self, key_no: int):
        super().__init__(use_escape=True)
        self.key_no = key_no

    def __str__(self) -> str:
        return f"AuthenticateEV2First(key_no=0x{self.key_no:02X})"

    def execute(self, connection: 'NTag424CardConnection') -> AuthenticationChallengeResponse:
        """
        Execute Phase 1 of EV2 authentication.
        
        Args:
            connection: Card connection
            
        Returns:
            AuthenticationChallengeResponse with encrypted RndB
            
        Raises:
            ApduError: If Phase 1 fails
        """
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
        encrypted_rndb = bytes(data)
        
        # Verify we got exactly 16 bytes
        if len(encrypted_rndb) != 16:
            log.warning(f"Phase 1 returned {len(encrypted_rndb)} bytes, expected 16")
            if len(encrypted_rndb) < 16:
                raise ApduError(f"Phase 1 response too short: {len(encrypted_rndb)} bytes", sw1, sw2)
        
        log.debug(f"Successfully received challenge: {encrypted_rndb.hex().upper()}")
        return AuthenticationChallengeResponse(key_no_used=self.key_no, challenge=encrypted_rndb)


class AuthenticateEV2Second(ApduCommand):
    """
    Completes the second phase of an EV2 authentication.
    
    Sends the encrypted response (RndA || RndB') to the tag and receives
    the encrypted card response containing Ti and RndA'.
    """
    
    def __init__(self, data_to_card: bytes):
        super().__init__(use_escape=True)
        if len(data_to_card) != 32:
            raise ValueError("Authentication data for phase two must be 32 bytes.")
        self.data_to_card = data_to_card

    def __str__(self) -> str:
        return f"AuthenticateEV2Second(data=<{len(self.data_to_card)} bytes>)"

    def execute(self, connection: 'NTag424CardConnection') -> bytes:
        """
        Execute Phase 2 of EV2 authentication.
        
        Args:
            connection: Card connection
            
        Returns:
            Encrypted card response (32 bytes: Ti || RndA' || PDcap2 || PCDcap2)
            
        Raises:
            ApduError: If Phase 2 fails
        """
        apdu = [0x90, 0xAF, 0x00, 0x00, len(self.data_to_card), *self.data_to_card, 0x00]
        # send_command() handles multi-frame and status checking automatically
        full_response, sw1, sw2 = self.send_command(connection, apdu)
        return bytes(full_response)  # Return the card's encrypted response data


class AuthenticateEV2:
    """
    EV2 Authentication orchestrator (NOT a command - it's a protocol handler).
    
    This performs the two-phase EV2 authentication protocol and returns
    an AuthenticatedConnection context manager.
    
    Usage:
        key = get_key()
        with CardManager() as connection:
            with AuthenticateEV2(key, key_no=0)(connection) as auth_conn:
                # Perform authenticated operations
                auth_conn.send(ChangeKey(...))
    
    Or:
        auth_conn = AuthenticateEV2(key, key_no=0)(connection)
        auth_conn.send(ChangeKey(...))
    """
    
    def __init__(self, key: bytes, key_no: int = 0):
        """
        Args:
            key: 16-byte AES key for authentication
            key_no: Key number to authenticate with (0-4)
        """
        if len(key) != 16:
            raise ValueError(f"Key must be 16 bytes, got {len(key)}")
        if not (0 <= key_no <= 4):
            raise ValueError(f"Key number must be 0-4, got {key_no}")
        
        self.key = key
        self.key_no = key_no
    
    def __str__(self) -> str:
        return f"AuthenticateEV2(key_no=0x{self.key_no:02X})"
    
    def __call__(self, connection: 'NTag424CardConnection') -> 'AuthenticatedConnection':
        """
        Perform complete EV2 authentication and return authenticated connection.
        
        Args:
            connection: Card connection to authenticate
        
        Returns:
            AuthenticatedConnection context manager with session keys
        
        Raises:
            ApduError: If authentication fails
        """
        log.info(f"Performing EV2 authentication with key {self.key_no}")
        
        # Create session and authenticate
        session = Ntag424AuthSession(self.key)
        session.authenticate(connection, key_no=self.key_no)
        
        log.info(f"Authentication successful, session established")
        
        # Return authenticated connection wrapper
        return AuthenticatedConnection(connection, session)

