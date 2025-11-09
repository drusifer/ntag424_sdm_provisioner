"""
Trace-Based HAL Simulator

Uses captured APDU traces from SUCCESSFUL_PROVISION_FLOW.md to provide
exact replay simulation for testing provisioning workflows.

This simulator returns the EXACT responses captured from a real tag,
ensuring tests match production behavior precisely.
"""

from typing import List, Tuple, Optional, Dict
import logging

log = logging.getLogger(__name__)


class TraceBasedSimulator:
    """
    Simulates NTAG424 DNA tag using captured APDU traces.
    
    Returns exact responses from successful provisioning run, allowing
    deterministic testing without hardware.
    """
    
    def __init__(self, uid: bytes = bytes.fromhex("04536B4A2F7080")):
        """
        Initialize simulator with captured UID.
        
        Args:
            uid: 7-byte UID (default from successful run)
        """
        self.uid = uid
        self.call_count: Dict[str, int] = {}
        self.auth_phase = 0  # Track authentication phases
        
        # Build APDU trace database from successful run
        self.traces = self._build_trace_database()
    
    def send_apdu(self, apdu: List[int], use_escape: bool = False) -> Tuple[List[int], int, int]:
        """
        Send APDU and return trace-based response.
        
        Args:
            apdu: APDU command bytes
            use_escape: Whether using escape mode
            
        Returns:
            (response_data, sw1, sw2)
        """
        # Convert to signature
        sig = self._apdu_signature(apdu)
        
        # Track call count for commands that repeat
        self.call_count[sig] = self.call_count.get(sig, 0) + 1
        call_num = self.call_count[sig]
        
        # Look up in traces
        trace_key = f"{sig}_{call_num}"
        if trace_key in self.traces:
            return self.traces[trace_key]
        
        # Fallback to first occurrence
        if f"{sig}_1" in self.traces:
            log.warning(f"Using first occurrence for {sig} (call #{call_num})")
            return self.traces[f"{sig}_1"]
        
        # Unknown command
        log.error(f"No trace for: {sig} (call #{call_num})")
        return [], 0x6D, 0x00  # INS not supported
    
    def _apdu_signature(self, apdu: List[int]) -> str:
        """Create signature for APDU matching."""
        if len(apdu) < 2:
            return "INVALID"
        
        cla, ins = apdu[0], apdu[1]
        
        # Special signatures for commands with data
        if ins == 0xA4 and len(apdu) >= 5:  # SELECT
            p1, p2 = apdu[2], apdu[3]
            return f"{cla:02X}_{ins:02X}_{p1:02X}_{p2:02X}"
        elif ins == 0x71:  # AuthenticateEV2First
            return "AUTH_PHASE1"
        elif ins == 0xAF:  # AuthenticateEV2Second or GetAdditionalFrame
            if len(apdu) > 10:  # Has data = Phase 2
                return "AUTH_PHASE2"
            else:  # No data = GetAdditionalFrame
                return "GET_ADDITIONAL_FRAME"
        elif ins == 0xC4:  # ChangeKey
            if len(apdu) >= 6:
                key_no = apdu[5]
                return f"CHANGEKEY_{key_no:02X}"
        elif ins == 0xD6:  # UpdateBinary (chunked)
            if len(apdu) >= 4:
                offset = (apdu[2] << 8) | apdu[3]
                return f"UPDATE_BINARY_{offset:04X}"
        
        return f"{cla:02X}_{ins:02X}"
    
    def _build_trace_database(self) -> Dict[str, Tuple[List[int], int, int]]:
        """
        Build database of APDU traces from SUCCESSFUL_PROVISION_FLOW.md.
        
        Returns dict mapping: signature_callnum -> (data, sw1, sw2)
        """
        traces = {}
        
        # ===== PART 1: Initial Tag Info =====
        
        # Select PICC Application (00 A4 04 00)
        traces["00_A4_04_00_1"] = ([], 0x90, 0x00)
        
        # GetVersion - 3 frames
        traces["90_60_1"] = (
            [0x04, 0x04, 0x02, 0x30, 0x00, 0x11, 0x05],
            0x91, 0xAF
        )
        traces["GET_ADDITIONAL_FRAME_1"] = (
            [0x04, 0x04, 0x02, 0x01, 0x02, 0x11, 0x05],
            0x91, 0xAF
        )
        traces["GET_ADDITIONAL_FRAME_2"] = (
            [0x04, 0x53, 0x6B, 0x4A, 0x2F, 0x70, 0x80, 0xCF, 0x39, 0xD4, 0x49, 0x80, 0x34, 0x20],
            0x91, 0x00
        )
        
        # ===== PART 2: Factory Reset Session 1 - Reset Key 0 =====
        
        # Auth Phase 1 (factory key)
        traces["AUTH_PHASE1_1"] = (
            bytes.fromhex("A13F92B403E54165F1C2CD57131EF6B1"),
            0x91, 0xAF
        )
        
        # Auth Phase 2 (factory key)
        traces["AUTH_PHASE2_1"] = (
            bytes.fromhex("F7A981115A538697253C7C3CF212CF11C1C5DA2CBD291AF51219B033828BC656"),
            0x91, 0x00
        )
        
        # ChangeKey 0 (reset to factory)
        traces["CHANGEKEY_00_1"] = ([], 0x91, 0x00)
        
        # ===== PART 3: Factory Reset Session 2 - Reset Keys 1 & 3 =====
        
        # Auth Phase 1 (factory key, after Key 0 reset)
        traces["AUTH_PHASE1_2"] = (
            bytes.fromhex("2FB3483770610DF64BF0D89DB2137A50"),
            0x91, 0xAF
        )
        
        # Auth Phase 2 (factory key)
        traces["AUTH_PHASE2_2"] = (
            bytes.fromhex("6BAA33EAA9E7D71B88B6374C90EEBF1BBC5C887A6790A56A68660040E25718B2"),
            0x91, 0x00
        )
        
        # ChangeKey 1 (reset to factory with old key XOR)
        traces["CHANGEKEY_01_1"] = (
            bytes.fromhex("C90DCB190C595BD8"),  # 8-byte CMAC
            0x91, 0x00
        )
        
        # ChangeKey 3 (reset to factory with old key XOR)
        traces["CHANGEKEY_03_1"] = (
            bytes.fromhex("570A3331B9572677"),  # 8-byte CMAC
            0x91, 0x00
        )
        
        # ===== PART 4: Provision Session 1 - Change Key 0 =====
        
        # Auth Phase 1 (factory key, for provision)
        traces["AUTH_PHASE1_3"] = (
            bytes.fromhex("B2C227E95D3CD491103F78D86A4BE89E"),
            0x91, 0xAF
        )
        
        # Auth Phase 2 (factory key)
        traces["AUTH_PHASE2_3"] = (
            bytes.fromhex("501CDF247CA99BD9C8AE3CE011DD05345595D2B70BB0518634A69B9E783F12AF"),
            0x91, 0x00
        )
        
        # ChangeKey 0 (to new random key)
        traces["CHANGEKEY_00_2"] = ([], 0x91, 0x00)
        
        # ===== PART 5: Provision Session 2 - Change Keys 1 & 3 =====
        
        # Auth Phase 1 (NEW Key 0)
        traces["AUTH_PHASE1_4"] = (
            bytes.fromhex("F1DEDA32880103A8DA50A4F9C09D385D"),
            0x91, 0xAF
        )
        
        # Auth Phase 2 (NEW Key 0)
        traces["AUTH_PHASE2_4"] = (
            bytes.fromhex("6383D03B9A8205687CE9B1DACD2AEE83BED927F22259053B4EC0180FFAE5E3BE"),
            0x91, 0x00
        )
        
        # ChangeKey 1 (to new random key)
        traces["CHANGEKEY_01_2"] = (
            bytes.fromhex("9631A5318718D167"),  # 8-byte CMAC
            0x91, 0x00
        )
        
        # ChangeKey 3 (to new random key)
        traces["CHANGEKEY_03_2"] = (
            bytes.fromhex("8FA6B49208128A0C"),  # 8-byte CMAC
            0x91, 0x00
        )
        
        # ===== PART 6: NDEF Operations =====
        
        # Select NDEF file (00 A4 02 00 - ISO)
        traces["00_A4_02_00_1"] = ([], 0x90, 0x00)
        traces["00_A4_02_00_2"] = ([], 0x90, 0x00)
        traces["00_A4_02_00_3"] = ([], 0x90, 0x00)
        
        # UpdateBinary - 4 chunks
        traces["UPDATE_BINARY_0000_1"] = ([], 0x90, 0x00)  # Chunk 1: offset 0
        traces["UPDATE_BINARY_0034_1"] = ([], 0x90, 0x00)  # Chunk 2: offset 52
        traces["UPDATE_BINARY_0068_1"] = ([], 0x90, 0x00)  # Chunk 3: offset 104
        traces["UPDATE_BINARY_009C_1"] = ([], 0x90, 0x00)  # Chunk 4: offset 156
        
        # Re-select PICC after NDEF write
        traces["00_A4_04_00_2"] = ([], 0x90, 0x00)
        traces["00_A4_04_00_3"] = ([], 0x90, 0x00)
        
        # Read NDEF for verification (00 B0 00 00 C8)
        ndef_data_hex = "00B403B1D101AD55047363726970742E676F6F676C652E636F6D2F612F6D6163726F732F67757473746569"
        ndef_data_hex += "6E732E636F6D2F732F414B6679636262323267435159"
        ndef_data_hex += "6C5F4F6A454A4232366A69554C38323533493062583463"
        ndef_data_hex += "7A78796B6B636D742D4D6E4634316C4979583138534C6B52675563"
        ndef_data_hex += "4A5F564A524A626977682F657865633F7569643D30303030303030303030303030303026637472"
        ndef_data_hex += "3D303030303030266D61633D30303030303030303030303030303030FE"
        # Pad to 200 bytes
        ndef_data_hex += "00" * (200 - 182)
        traces["00_B0_1"] = (
            list(bytes.fromhex(ndef_data_hex.replace(" ", ""))),
            0x90, 0x00
        )
        
        return traces


class MockCardManager:
    """
    Mock CardManager that creates trace-based simulator connections.
    
    Usage:
        with MockCardManager() as card:
            card.send(SelectPiccApplication())
            version = card.send(GetChipVersion())
    """
    
    def __init__(self, uid: bytes = bytes.fromhex("04536B4A2F7080")):
        """
        Args:
            uid: UID to simulate (default from successful run)
        """
        self.uid = uid
        self.connection = None
    
    def __enter__(self):
        """Enter context - create mock connection."""
        self.connection = MockNTag424CardConnection(self.uid)
        return self.connection
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - cleanup."""
        self.connection = None
        return False


class MockNTag424CardConnection:
    """
    Mock connection that matches NTag424CardConnection interface.
    
    Uses TraceBasedSimulator for responses.
    """
    
    def __init__(self, uid: bytes):
        """
        Args:
            uid: UID to simulate
        """
        self.simulator = TraceBasedSimulator(uid)
    
    def send_apdu(self, apdu: List[int], use_escape: bool = False) -> Tuple[List[int], int, int]:
        """
        Send APDU (matches real HAL interface).
        
        Args:
            apdu: APDU command bytes
            use_escape: Ignored for mock
            
        Returns:
            (response_data, sw1, sw2)
        """
        return self.simulator.send_apdu(apdu, use_escape)
    
    def send(self, command):
        """
        Execute command using new pattern.
        
        Args:
            command: ApduCommand to execute
            
        Returns:
            Parsed response from command
        """
        # Build APDU
        apdu = command.build_apdu()
        
        # Send via simulator
        data, sw1, sw2 = self.send_apdu(apdu, use_escape=command.use_escape)
        
        # Handle multi-frame responses (like GetVersion)
        full_data = list(data) if data else []
        while (sw1, sw2) == (0x91, 0xAF):  # MORE_DATA_AVAILABLE
            # Send GetAdditionalFrame
            af_apdu = [0x90, 0xAF, 0x00, 0x00, 0x00]
            data, sw1, sw2 = self.send_apdu(af_apdu, use_escape=command.use_escape)
            full_data.extend(data if data else [])
        
        # Parse response with full data
        return command.parse_response(bytes(full_data), sw1, sw2)
    
    def send_write_chunked(
        self,
        cla: int,
        ins: int,
        offset: int,
        data: bytes,
        chunk_size: int = 52,
        use_escape: bool = False
    ) -> Tuple[int, int]:
        """
        Chunked write (matches real HAL interface).
        
        Returns final (sw1, sw2) after all chunks.
        """
        written = 0
        while written < len(data):
            chunk_data = data[written:written + chunk_size]
            chunk_offset = offset + written
            
            # Build APDU for this chunk
            apdu = [
                cla, ins,
                (chunk_offset >> 8) & 0xFF,
                chunk_offset & 0xFF,
                len(chunk_data),
                *chunk_data
            ]
            
            # Send chunk
            _, sw1, sw2 = self.send_apdu(apdu, use_escape)
            
            # Check for error
            if (sw1, sw2) not in [(0x90, 0x00), (0x91, 0x00)]:
                return sw1, sw2
            
            written += len(chunk_data)
        
        return sw1, sw2


def get_mock_connection(uid: bytes = bytes.fromhex("04536B4A2F7080")):
    """
    Get a mock connection for testing.
    
    Args:
        uid: UID to simulate
        
    Returns:
        MockNTag424CardConnection
    """
    return MockNTag424CardConnection(uid)


# ===== USAGE EXAMPLE =====

if __name__ == "__main__":
    """
    Example of using trace-based simulator.
    """
    logging.basicConfig(level=logging.INFO)
    
    print("Trace-Based Simulator Example")
    print("=" * 70)
    
    with MockCardManager() as card:
        from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
        from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
        
        # Test basic commands
        card.send(SelectPiccApplication())
        print("[OK] Selected PICC Application")
        
        version = card.send(GetChipVersion())
        print(f"[OK] UID: {version.uid.hex().upper()}")
        
    print("\n[SUCCESS] Trace-based simulator working!")

