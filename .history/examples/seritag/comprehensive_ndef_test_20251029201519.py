#!/usr/bin/env python3
"""
Comprehensive NDEF Read/Write Test - All Configurations

This script systematically tests all possible configurations for reading/writing
NDEF files on Seritag NTAG424 DNA tags:

1. File selection (with/without)
2. CLA byte variations (00 vs 90)
3. Escape mode (with/without)
4. P1/P2 format variations
5. Command format variations

All results are recorded for comparison and analysis.
"""
import sys
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from ntag424_sdm_provisioner.hal import CardManager, NTag242ConnectionError
from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication, GetChipVersion
from ntag424_sdm_provisioner.commands.base import ApduError
from ntag424_sdm_provisioner.constants import SW_OK
import logging
import os

# Support for using mock HAL via environment variable
USE_MOCK_HAL = os.environ.get('USE_MOCK_HAL', '').lower() in ('1', 'true', 'yes')
if USE_MOCK_HAL:
    from tests.ntag424_sdm_provisioner.mock_hal import MockCardManager as _MockCardManager
    # Create a wrapper to match CardManager interface
    class MockCardManager:
        def __init__(self, reader_index: int = 0):
            self.reader_index = reader_index
            self._manager = _MockCardManager()
        
        def __enter__(self):
            return self._manager.__enter__()
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            return self._manager.__exit__(exc_type, exc_val, exc_tb)

logging.basicConfig(level=logging.WARNING)  # Reduce noise, we'll log results ourselves
log = logging.getLogger(__name__)


class TestStatus:
    """Test result status constants."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ERROR = "ERROR"


@dataclass
class TestConfiguration:
    """Configuration for a single test."""
    name: str
    select_file_first: bool = False
    cla: int = 0x00
    use_escape: bool = True
    p1_mode: str = "offset"  # "offset" or "file_id"
    description: str = ""


@dataclass
class TestResult:
    """Result of a test."""
    config: TestConfiguration
    result: str  # TestStatus.SUCCESS, TestStatus.FAILED, TestStatus.ERROR
    sw1: int = 0
    sw2: int = 0
    data_len: int = 0
    error_msg: str = ""
    apdu_sent: Optional[List[int]] = None
    
    def __str__(self) -> str:
        status = f"{self.result:8s}"
        sw = f"{self.sw1:02X}{self.sw2:02X}"
        return f"{status} | SW={sw:6s} | {self.config.name:40s} | {self.error_msg}"


class ComprehensiveNdefTest:
    """Comprehensive NDEF read/write testing with all configurations."""
    
    # File IDs from spec
    NDEF_FILE_ID = [0xE1, 0x04]  # E104h - NDEF file
    CC_FILE_ID = [0xE1, 0x03]    # E103h - CC file
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.card_manager = None
        self.card = None
        
    def setup(self):
        """Connect and select PICC application."""
        # Use mock HAL if requested via environment variable
        if USE_MOCK_HAL:
            self.card_manager = MockCardManager(0)
            print("[MOCK] Using MOCK HAL for testing")
        else:
            self.card_manager = CardManager(0)
            print("[REAL] Using REAL HAL (hardware required)")
        
        self.card = self.card_manager.__enter__()
        SelectPiccApplication().execute(self.card)
        version_info = GetChipVersion().execute(self.card)
        return version_info
    
    def teardown(self):
        """Close connection."""
        if self.card_manager:
            self.card_manager.__exit__(None, None, None)
    
    def select_ndef_file(self, use_escape: bool = True, p1_mode: int = 0x02) -> Tuple[bool, int, int]:
        """Select NDEF file using ISOSelectFile (00 A4)."""
        # ISOSelectFile format: 00 A4 P1 P2 [Lc] [File ID] [Le]
        # Per spec:
        #   P1=0x00: Select MF, DF or EF by file identifier
        #   P1=0x02: Select EF under the current DF, by file identifier (CORRECT for NDEF file)
        #   P1=0x04: Select by DF name (WRONG - we want EF, not DF!)
        # Since application is already selected, use P1=0x02 to select EF under current DF
        apdu = [
            0x00, 0xA4,  # ISOSelectFile
            p1_mode, 0x00,  # P1=0x02 (select EF under current DF), P2=00 (no FCI)
            0x02,        # Lc = 2 bytes (file ID length)
        ] + self.NDEF_FILE_ID + [0x00]  # File ID E104h + Le
        
        try:
            _, sw1, sw2 = self.card.send_apdu(apdu, use_escape=use_escape)
            return (sw1 == 0x90 and sw2 == 0x00), sw1, sw2
        except Exception as e:
            return False, 0xFF, 0xFF
    
    def test_iso_read_binary(self, config: TestConfiguration) -> TestResult:
        """Test ISOReadBinary with given configuration."""
        name = f"Read-{config.name}"
        
        # Select file if requested
        if config.select_file_first:
            success, sw1, sw2 = self.select_ndef_file(use_escape=config.use_escape, p1_mode=0x02)
            if not success:
                return TestResult(
                    config=config,
                    result=TestStatus.FAILED,
                    sw1=sw1,
                    sw2=sw2,
                    error_msg=f"File select failed: {sw1:02X}{sw2:02X}"
                )
        
        # Build ISOReadBinary APDU
        offset = 0
        length = 64  # Try reading 64 bytes
        
        if config.p1_mode == "offset":
            # P1[7]=0: P1-P2 encodes 15-bit offset
            p1 = (offset >> 8) & 0x7F  # Bit 7 = 0
            p2 = offset & 0xFF
        else:  # file_id mode
            # P1[7]=1: P1[4:0] is short file ID, P2 is offset
            # For file 02: try file_id_bits = 0x02
            file_id_bits = 0x02
            p1 = 0x80 | (file_id_bits & 0x1F)  # Bit 7 = 1, bits 4:0 = file ID
            p2 = offset
        
        apdu = [
            config.cla, 0xB0,  # ISOReadBinary
            p1,
            p2,
            length  # Le
        ]
        
        try:
            data, sw1, sw2 = self.card.send_apdu(apdu, use_escape=config.use_escape)
            
            if (sw1, sw2) == SW_OK:
                return TestResult(
                    config=config,
                    result=TestStatus.SUCCESS,
                    sw1=sw1,
                    sw2=sw2,
                    data_len=len(data),
                    apdu_sent=apdu,
                    error_msg=f"Read {len(data)} bytes"
                )
            else:
                return TestResult(
                    config=config,
                    result=TestStatus.FAILED,
                    sw1=sw1,
                    sw2=sw2,
                    apdu_sent=apdu,
                    error_msg=f"SW={sw1:02X}{sw2:02X}"
                )
        except Exception as e:
                return TestResult(
                    config=config,
                    result=TestStatus.ERROR,
                error_msg=str(e),
                apdu_sent=apdu
            )
    
    def test_iso_update_binary(self, config: TestConfiguration) -> TestResult:
        """Test ISOUpdateBinary with given configuration."""
        name = f"Write-{config.name}"
        
        # Select file if requested
        if config.select_file_first:
            success, sw1, sw2 = self.select_ndef_file(use_escape=config.use_escape, p1_mode=0x02)
            if not success:
                return TestResult(
                    config=config,
                    result=TestStatus.FAILED,
                    sw1=sw1,
                    sw2=sw2,
                    error_msg=f"File select failed: {sw1:02X}{sw2:02X}"
                )
        
        # Build test data (small NDEF TLV)
        test_data = bytes([0x03, 0x05, 0xD1, 0x01, 0x03, 0x55, 0x01])  # Minimal NDEF
        offset = 0
        
        if config.p1_mode == "offset":
            p1 = (offset >> 8) & 0x7F
            p2 = offset & 0xFF
        else:  # file_id mode
            file_id_bits = 0x02
            p1 = 0x80 | (file_id_bits & 0x1F)
            p2 = offset
        
        apdu = [
            config.cla, 0xD6,  # ISOUpdateBinary
            p1,
            p2,
            len(test_data)  # Lc
        ] + list(test_data)
        
        try:
            _, sw1, sw2 = self.card.send_apdu(apdu, use_escape=config.use_escape)
            
            if (sw1, sw2) == SW_OK:
                return TestResult(
                    config=config,
                    result=TestStatus.SUCCESS,
                    sw1=sw1,
                    sw2=sw2,
                    data_len=len(test_data),
                    apdu_sent=apdu,
                    error_msg=f"Wrote {len(test_data)} bytes"
                )
            else:
                return TestResult(
                    config=config,
                    result=TestStatus.FAILED,
                    sw1=sw1,
                    sw2=sw2,
                    apdu_sent=apdu,
                    error_msg=f"SW={sw1:02X}{sw2:02X}"
                )
        except Exception as e:
                return TestResult(
                    config=config,
                    result=TestStatus.ERROR,
                error_msg=str(e),
                apdu_sent=apdu
            )
    
    def run_all_tests(self):
        """Run all test configurations."""
        print("=" * 80)
        print("COMPREHENSIVE NDEF READ/WRITE TEST")
        print("=" * 80)
        print()
        
        try:
            version_info = self.setup()
            print(f"Tag: HW {version_info.hw_major_version}.{version_info.hw_minor_version}")
            print(f"UID: {version_info.uid.hex().upper()}")
            print()
            
            # Test file selection first - try different P1 values
            print("Testing NDEF file selection...")
            for p1_mode in [0x02, 0x00]:  # Try P1=0x02 first (select EF under current DF), then 0x00
                p1_name = f"P1=0x{p1_mode:02X}"
                if p1_mode == 0x02:
                    p1_name += " (select EF under current DF)"
                elif p1_mode == 0x00:
                    p1_name += " (select by file ID)"
                    
                select_success, sw1, sw2 = self.select_ndef_file(use_escape=True, p1_mode=p1_mode)
                if select_success:
                    print(f"✅ File selection works with {p1_name}: SW={sw1:02X}{sw2:02X}")
                    break
                else:
                    print(f"❌ File selection failed with {p1_name}: SW={sw1:02X}{sw2:02X}")
            print()
            
            # Define all test configurations
            configurations = [
                # Test 1: ISOReadBinary with CLA=00 (correct format)
                TestConfiguration(
                    name="Read-ISO CLA=00, escape=True, offset",
                    cla=0x00,
                    use_escape=True,
                    p1_mode="offset",
                    description="ISOReadBinary CLA=00, escape mode, offset mode"
                ),
                TestConfiguration(
                    name="Read-ISO CLA=00, escape=False, offset",
                    cla=0x00,
                    use_escape=False,
                    p1_mode="offset",
                    description="ISOReadBinary CLA=00, no escape, offset mode"
                ),
                TestConfiguration(
                    name="Read-ISO CLA=00, escape=True, select_file",
                    cla=0x00,
                    use_escape=True,
                    select_file_first=True,
                    p1_mode="offset",
                    description="ISOReadBinary CLA=00, select file first"
                ),
                TestConfiguration(
                    name="Read-ISO CLA=00, escape=True, file_id",
                    cla=0x00,
                    use_escape=True,
                    p1_mode="file_id",
                    description="ISOReadBinary CLA=00, P1[7]=1 file ID mode"
                ),
                
                # Test 2: ReadBinary with CLA=90 (proprietary, might work differently)
                TestConfiguration(
                    name="Read-Proprietary CLA=90, escape=True",
                    cla=0x90,
                    use_escape=True,
                    p1_mode="offset",
                    description="ReadBinary CLA=90 (proprietary format)"
                ),
                TestConfiguration(
                    name="Read-Proprietary CLA=90, escape=False",
                    cla=0x90,
                    use_escape=False,
                    p1_mode="offset",
                    description="ReadBinary CLA=90, no escape"
                ),
                
                # Test 3: ISOUpdateBinary (write) configurations
                TestConfiguration(
                    name="Write-ISO CLA=00, escape=True, offset",
                    cla=0x00,
                    use_escape=True,
                    p1_mode="offset",
                    description="ISOUpdateBinary CLA=00"
                ),
                TestConfiguration(
                    name="Write-ISO CLA=00, escape=True, select_file",
                    cla=0x00,
                    use_escape=True,
                    select_file_first=True,
                    p1_mode="offset",
                    description="ISOUpdateBinary CLA=00, select file first"
                ),
                TestConfiguration(
                    name="Write-ISO CLA=00, escape=False, offset",
                    cla=0x00,
                    use_escape=False,
                    p1_mode="offset",
                    description="ISOUpdateBinary CLA=00, no escape"
                ),
                TestConfiguration(
                    name="Write-ISO CLA=00, escape=True, file_id",
                    cla=0x00,
                    use_escape=True,
                    p1_mode="file_id",
                    description="ISOUpdateBinary CLA=00, file ID mode"
                ),
                
                # Test 4: UpdateBinary with CLA=90 (proprietary)
                TestConfiguration(
                    name="Write-Proprietary CLA=90, escape=True",
                    cla=0x90,
                    use_escape=True,
                    p1_mode="offset",
                    description="UpdateBinary CLA=90 (proprietary)"
                ),
            ]
            
            # Run read tests
            print("READ TESTS")
            print("-" * 80)
            read_configs = [c for c in configurations if c.name.startswith("Read-")]
            for config in read_configs:
                result = self.test_iso_read_binary(config)
                self.results.append(result)
                print(result)
            
            print()
            print("WRITE TESTS")
            print("-" * 80)
            write_configs = [c for c in configurations if c.name.startswith("Write-")]
            for config in write_configs:
                result = self.test_iso_update_binary(config)
                self.results.append(result)
                print(result)
            
            # Also test ReadData/WriteData (proprietary commands) for comparison
            print()
            print("PROPRIETARY COMMAND TESTS (ReadData/WriteData)")
            print("-" * 80)
            
            # ReadData: 90 BD 00 00 [Lc] [FileNo OffsetHigh OffsetLow 00 LenHigh LenLow 00] [Data] 00
            # Note: ReadData uses 0xBD, not 0xAD!
            try:
                read_data_apdu = [
                    0x90, 0xBD,  # ReadData (correct instruction code)
                    0x00, 0x00,  # P1, P2
                    0x07,        # Lc = 7 bytes
                    0x02,        # FileNo = 02 (NDEF)
                    0x00, 0x00, 0x00,  # Offset = 0
                    0x00, 0x40, 0x00,  # Length = 64 (0x0040)
                    0x00        # Le
                ]
                data, sw1, sw2 = self.card.send_apdu(read_data_apdu, use_escape=True)
                if (sw1, sw2) == SW_OK:
                    result = TestResult(
                        config=TestConfiguration(name="ReadData (90 AD) proprietary"),
                        result=TestStatus.SUCCESS,
                        sw1=sw1,
                        sw2=sw2,
                        data_len=len(data),
                        apdu_sent=read_data_apdu,
                        error_msg=f"Read {len(data)} bytes with ReadData"
                    )
                    print(result)
                    self.results.append(result)
                else:
                    result = TestResult(
                        config=TestConfiguration(name="ReadData (90 AD) proprietary"),
                        result=TestStatus.FAILED,
                        sw1=sw1,
                        sw2=sw2,
                        apdu_sent=read_data_apdu,
                        error_msg=f"SW={sw1:02X}{sw2:02X}"
                    )
                    print(result)
                    self.results.append(result)
            except Exception as e:
                result = TestResult(
                    config=TestConfiguration(name="ReadData (90 AD) proprietary"),
                    result=TestStatus.ERROR,
                    error_msg=str(e)
                )
                print(result)
                self.results.append(result)
            
            # Summary
            print()
            print("=" * 80)
            print("SUMMARY")
            print("=" * 80)
            
            successes = [r for r in self.results if r.result == TestStatus.SUCCESS]
            failures = [r for r in self.results if r.result != TestStatus.SUCCESS]
            
            print(f"Total tests: {len(self.results)}")
            print(f"✅ Successful: {len(successes)}")
            print(f"❌ Failed: {len(failures)}")
            
            if successes:
                print()
                print("SUCCESSFUL CONFIGURATIONS:")
                for result in successes:
                    print(f"  ✅ {result.config.name}")
                    if result.apdu_sent:
                        apdu_hex = ' '.join([f"{b:02X}" for b in result.apdu_sent])
                        print(f"     APDU: {apdu_hex}")
            
            if failures:
                print()
                print("FAILED CONFIGURATIONS:")
                # Group by error code
                errors_by_sw = {}
                for result in failures:
                    sw = f"{result.sw1:02X}{result.sw2:02X}"
                    if sw not in errors_by_sw:
                        errors_by_sw[sw] = []
                    errors_by_sw[sw].append(result)
                
                for sw, results in sorted(errors_by_sw.items()):
                    print(f"  SW={sw} ({len(results)} tests):")
                    for result in results[:3]:  # Show first 3
                        print(f"    - {result.config.name}")
                    if len(results) > 3:
                        print(f"    ... and {len(results) - 3} more")
            
        except NTag242ConnectionError as e:
            print(f"❌ CONNECTION FAILED: {e}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.teardown()


if __name__ == "__main__":
    print("=" * 80)
    print("COMPREHENSIVE NDEF TEST")
    print("=" * 80)
    if USE_MOCK_HAL:
        print("[MOCK] Running with MOCK HAL (no hardware required)")
        print("       Set USE_MOCK_HAL=0 to use real hardware")
    else:
        print("[REAL] Running with REAL HAL (hardware required)")
        print("       Set USE_MOCK_HAL=1 to use mock instead")
    print()
    
    tester = ComprehensiveNdefTest()
    tester.run_all_tests()

