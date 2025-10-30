"""
Seritag NTAG424 DNA HAL Simulator

This module simulates a Seritag NTAG424 DNA tag connected to an ACR122U reader.
It implements proper EV2 authentication according to NXP NTAG424 DNA specification.
"""
import logging
import secrets
from typing import List, Tuple, Optional
from dataclasses import dataclass
from Crypto.Cipher import AES
from Crypto.Hash import CMAC

log = logging.getLogger(__name__)

@dataclass
class SeritagTagState:
    """State of the simulated Seritag NTAG424 DNA tag."""
    uid: bytes = b'\x04\x3F\x68\x4A\x2F\x70\x80'
    hw_major: int = 48
    hw_minor: int = 0
    sw_major: int = 1
    sw_minor: int = 2
    batch_no: bytes = b'\xCF\x39\xD4\x49\x80'
    fab_week: int = 52
    fab_year: int = 32
    hw_protocol: int = 5
    sw_protocol: int = 5
    hw_type: int = 4
    sw_type: int = 4
    hw_storage_size: int = 416
    sw_storage_size: int = 17
    
    # EV2 Authentication state
    authenticated: bool = False
    session_keys: Optional[dict] = None
    current_key_no: Optional[int] = None
    transaction_id: Optional[bytes] = None
    rnda: Optional[bytes] = None
    rndb: Optional[bytes] = None
    
    # Factory keys (all zeros for brand new tags)
    factory_keys: List[bytes] = None
    
    def __post_init__(self):
        if self.factory_keys is None:
            self.factory_keys = [b'\x00' * 16] * 5  # 5 keys, all zeros

class SeritagSimulator:
    """Simulates a Seritag NTAG424 DNA tag."""
    
    def __init__(self):
        self.state = SeritagTagState()
        self.connected = False
        
    def connect(self) -> str:
        """Simulate card connection."""
        self.connected = True
        return "3B8180018080"  # Seritag ATR
        
    def disconnect(self):
        """Simulate card disconnection."""
        self.connected = False
        self.state.authenticated = False
        self.state.session_keys = None
        
    def send_apdu(self, apdu: List[int]) -> Tuple[List[int], int, int]:
        """
        Simulate APDU command processing.
        
        Args:
            apdu: APDU command bytes
            
        Returns:
            Tuple of (response_data, sw1, sw2)
        """
        if not self.connected:
            return [], 0x6F, 0x00  # No card present
            
        # Parse APDU
        if len(apdu) < 4:
            return [], 0x6D, 0x00  # Wrong length
            
        cla, ins, p1, p2 = apdu[0], apdu[1], apdu[2], apdu[3]
        lc = apdu[4] if len(apdu) > 4 else 0
        data = apdu[5:5+lc] if lc > 0 else []
        
        log.debug(f"SeritagSim: Processing APDU {[hex(x) for x in apdu]}")
        
        # Route commands
        if cla == 0x00 and ins == 0xA4:
            return self._handle_select_application(p1, p2, data)
        elif cla == 0x90 and ins == 0x60:
            return self._handle_get_version()
        elif cla == 0x90 and ins == 0x71:
            return self._handle_authenticate_ev2_first(p1, p2, data)
        elif cla == 0x90 and ins == 0xAF:
            return self._handle_authenticate_ev2_second(p1, p2, data)
        else:
            log.warning(f"SeritagSim: Unknown command {cla:02X} {ins:02X}")
            return [], 0x6D, 0x00  # Command not supported
            
    def _handle_select_application(self, p1: int, p2: int, data: List[int]) -> Tuple[List[int], int, int]:
        """Handle Select PICC Application command."""
        log.debug("SeritagSim: SelectPICCApplication")
        return [], 0x90, 0x00  # Success
        
    def _handle_get_version(self) -> Tuple[List[int], int, int]:
        """Handle Get Chip Version command."""
        log.debug("SeritagSim: GetChipVersion")
        
        # Build 28-byte version data according to Ntag424VersionInfo format:
        # Byte 0: hw_vendor_id
        # Byte 1: hw_type  
        # Byte 2: hw_subtype
        # Byte 3: hw_major_version
        # Byte 4: hw_minor_version
        # Byte 5: hw_storage_size (low byte)
        # Byte 6: hw_protocol
        # Byte 7: sw_vendor_id
        # Byte 8: sw_type
        # Byte 9: sw_subtype
        # Byte 10: sw_major_version
        # Byte 11: sw_minor_version
        # Byte 12: sw_storage_size (low byte)
        # Byte 13: sw_protocol
        # Bytes 14-20: uid (7 bytes)
        # Bytes 21-25: batch_no (5 bytes)
        # Byte 26: fab_week
        # Byte 27: fab_year
        
        version_data = [
            0x04,  # hw_vendor_id (NXP)
            self.state.hw_type,  # hw_type
            0x00,  # hw_subtype
            self.state.hw_major,  # hw_major_version
            self.state.hw_minor,  # hw_minor_version
            self.state.hw_storage_size & 0xFF,  # hw_storage_size (low byte)
            self.state.hw_protocol,  # hw_protocol
            0x04,  # sw_vendor_id (NXP)
            self.state.sw_type,  # sw_type
            0x00,  # sw_subtype
            self.state.sw_major,  # sw_major_version
            self.state.sw_minor,  # sw_minor_version
            self.state.sw_storage_size & 0xFF,  # sw_storage_size (low byte)
            self.state.sw_protocol,  # sw_protocol
        ]
        
        # Add UID (7 bytes)
        version_data.extend(self.state.uid)
        
        # Add batch number (5 bytes)
        version_data.extend(self.state.batch_no)
        
        # Add fabrication info (2 bytes)
        version_data.extend([self.state.fab_week, self.state.fab_year])
        
        log.debug(f"SeritagSim: Version data length: {len(version_data)} bytes")
        log.debug(f"SeritagSim: Version data: {[hex(x) for x in version_data]}")
        
        return version_data, 0x91, 0xAF  # Additional frame
        
    def _handle_authenticate_ev2_first(self, p1: int, p2: int, data: List[int]) -> Tuple[List[int], int, int]:
        """Handle AuthenticateEV2First command with proper EV2 implementation."""
        if len(data) != 2:
            return [], 0x6A, 0x80  # Wrong parameters
            
        key_no = data[0]
        len_cap = data[1]  # Should be 0x00 for no PCDcap2
        log.debug(f"SeritagSim: AuthenticateEV2First for key {key_no}, LenCap={len_cap}")
        
        if key_no >= len(self.state.factory_keys):
            return [], 0x6A, 0x80  # Invalid key number
            
        # Store the current key number for phase 2
        self.state.current_key_no = key_no
            
        # Generate random RndB (16 bytes)
        self.state.rndb = secrets.token_bytes(16)
        log.debug(f"SeritagSim: Generated RndB: {self.state.rndb.hex()}")
        
        # Encrypt RndB with the specified key
        key = self.state.factory_keys[key_no]
        cipher = AES.new(key, AES.MODE_CBC, iv=b'\x00' * 16)
        encrypted_rndb = cipher.encrypt(self.state.rndb)
        
        log.debug(f"SeritagSim: Encrypted RndB: {encrypted_rndb.hex()}")
        log.debug(f"SeritagSim: Using key {key_no}: {key.hex()}")
        
        # Return encrypted RndB with SW_ADDITIONAL_FRAME
        return list(encrypted_rndb), 0x91, 0xAF
        
    def _handle_authenticate_ev2_second(self, p1: int, p2: int, data: List[int]) -> Tuple[List[int], int, int]:
        """Handle AuthenticateEV2Second command with proper EV2 implementation."""
        log.debug(f"SeritagSim: AuthenticateEV2Second with {len(data)} bytes")
        
        if len(data) != 32:
            return [], 0x6A, 0x80  # Wrong length
            
        if self.state.rndb is None:
            return [], 0x91, 0x7E  # No previous authentication
            
        # Decrypt the incoming data (RndA + RndB')
        key = self.state.factory_keys[self.state.current_key_no]
        cipher = AES.new(key, AES.MODE_CBC, iv=b'\x00' * 16)
        decrypted_data = cipher.decrypt(bytes(data))
        
        # Extract RndA and RndB'
        rnda = decrypted_data[0:16]
        rndb_prime = decrypted_data[16:32]
        
        log.debug(f"SeritagSim: Decrypted RndA: {rnda.hex()}")
        log.debug(f"SeritagSim: Decrypted RndB': {rndb_prime.hex()}")
        
        # Verify RndB' matches expected rotation
        expected_rndb_prime = self.state.rndb[1:] + self.state.rndb[0:1]
        if rndb_prime != expected_rndb_prime:
            log.error(f"SeritagSim: RndB' verification failed")
            log.error(f"  Expected: {expected_rndb_prime.hex()}")
            log.error(f"  Received: {rndb_prime.hex()}")
            return [], 0x91, 0x7E  # Authentication failed
            
        log.debug("SeritagSim: RndB' verification successful")
        
        # Store RndA and generate transaction ID
        self.state.rnda = rnda
        self.state.transaction_id = secrets.token_bytes(4)
        
        # Generate response: Ti || RndA' || PDcap || PCDcap
        rnda_prime = rnda[1:] + rnda[0:1]  # Rotate RndA
        pdcap = b'\x00'  # Minimal PDcap
        pcdcap = b'\x00'  # Minimal PCDcap
        
        response_data = self.state.transaction_id + rnda_prime + pdcap + pcdcap
        log.debug(f"SeritagSim: Response data: {response_data.hex()}")
        
        # Encrypt response
        encrypted_response = cipher.encrypt(response_data)
        log.debug(f"SeritagSim: Encrypted response: {encrypted_response.hex()}")
        
        # Mark as authenticated
        self.state.authenticated = True
        self.state.current_key_no = self.state.current_key_no
        
        log.info("SeritagSim: EV2 authentication successful!")
        
        return list(encrypted_response), 0x90, 0x00

class SeritagCardConnection:
    """Simulated Seritag card connection."""
    
    def __init__(self, simulator: SeritagSimulator):
        self.simulator = simulator
        
    def send_apdu(self, apdu: List[int], use_escape: bool = False) -> Tuple[List[int], int, int]:
        """Send APDU to simulated Seritag tag."""
        log.debug(f"SeritagCard: Sending APDU {[hex(x) for x in apdu]}")
        return self.simulator.send_apdu(apdu)
        
    def control(self, control_code: int, data: List[int]) -> List[int]:
        """Simulate control command (for escape sequences)."""
        log.debug(f"SeritagCard: Control command {control_code:04X}")
        # For now, just pass through to send_apdu
        response, sw1, sw2 = self.simulator.send_apdu(data)
        return response + [sw1, sw2]

class SeritagCardManager:
    """Simulated card manager for Seritag tags."""
    
    def __init__(self, reader_index: int = 0):
        self.reader_index = reader_index
        self.simulator = SeritagSimulator()
        self.connection = None
        
    def __enter__(self):
        """Context manager entry."""
        log.info("SeritagSim: Simulating card connection...")
        atr = self.simulator.connect()
        log.info(f"SeritagSim: Card detected with ATR: {atr}")
        self.connection = SeritagCardConnection(self.simulator)
        return self.connection
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        log.info("SeritagSim: Disconnecting from simulated card.")
        self.simulator.disconnect()
        self.connection = None
