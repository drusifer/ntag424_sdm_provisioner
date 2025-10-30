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

logging.basicConfig(level=logging.WARNING)  # Reduce noise, we'll log results ourselves
log = logging.getLogger(__name__)


class TestResult:
    """Result of a test configuration."""
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
    result: str  # SUCCESS, FAILED, ERROR
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
        self.card = None
        
    def setup(self):
        """Connect and select PICC application."""
        self.card = CardManager(0)
        self.card.__enter__()
        SelectPiccApplication().execute(self.card.connection)
        version_info = GetChipVersion().execute(self.card.connection)
        return version_info
    
    def teardown(self):
        """Close connection."""
        if self.card:
            self.card.__exit__(None, None, None)
    
    def select_ndef_file(self, use_escape: bool = True) -> Tuple[bool, int, int]:
        """Select NDEF file using ISOSelectFile (00 A4)."""
        # ISOSelectFile format: 00 A4 04 00 [Lc] [File ID] [Le]
        # For file ID selection: P1=04, P2=00, Lc=02, File ID=E104h
        apdu = [
            0x00, 0xA4,  # ISOSelectFile
            0x04, 0x00,  # P1=04 (by file ID), P2=00 (no FCI)
            0x02,        # Lc = 2 bytes (file ID length)
        ] + self.NDEF_FILE_ID + [0x00]  # File ID + Le
        
        try:
            _, sw1, sw2 = self.card.connection.send_apdu(apdu, use_escape=use_escape)
            return (sw1 == 0x90 and sw2 == 0x00), sw1, sw2
        except Exception as e:
            return False, 0xFF, 0xFF
    
    def test_iso_read_binary(self, config: TestConfiguration) -> TestResult:
        """Test ISOReadBinary with given configuration."""
        name = f"Read-{config.name}"
        
        # Select file if requested
        if config.select_file_first:
            success, sw1, sw2 = self.select_ndef_file(use_escape=config.use_escape)
            if not success:
                return TestResult(
                    config=config,
                    result=TestResult.FAILED,
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
            data, sw1, sw2 = self.card.connection.send_apdu(apdu, use_escape=config.use_escape)
            
            if (sw1, sw2) == SW_OK:
                return TestResult(
                    config=config,
                    result=TestResult.SUCCESS,
                    sw1=sw1,
                    sw2=sw2,
                    data_len=len(data),
                    apdu_sent=apdu,
                    error_msg=f"Read {len(data)} bytes"
                )
            else:
                return TestResult(
                    config=config,
                    result=TestResult.FAILED,
                    sw1=sw1,
                    sw2=sw2,
                    apdu_sent=apdu,
                    error_msg=f"SW={sw1:02X}{sw2:02X}"
                )
        except Exception as e:
            return TestResult(
                config=config,
                result=TestResult.ERROR,
                error_msg=str(e),
                apdu_sent=apdu
            )
    
    def test_iso_update_binary(self, config: TestConfiguration) -> TestResult:
        """Test ISOUpdateBinary with given configuration."""
        name = f"Write-{config.name}"
        
        # Select file if requested
        if config.select_file_first:
            success, sw1, sw2 = self.select_ndef_file(use_escape=config.use_escape)
            if not success:
                return TestResult(
                    config=config,
                    result=TestResult.FAILED,
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
            _, sw1, sw2 = self.card.connection.send_apdu(apdu, use_escape=config.use_escape)
            
            if (sw1, sw2) == SW_OK:
                return TestResult(
                    config=config,
                    result=TestResult.SUCCESS,
                    sw1=sw1,
                    sw2=sw2,
                    data_len=len(test_data),
                    apdu_sent=apdu,
                    error_msg=f"Wrote {len(test_data)} bytes"
                )
            else:
                return TestResult(
                    config=config,
                    result=TestResult.FAILED,
                    sw1=sw1,
                    sw2=sw2,
                    apdu_sent=apdu,
                    error_msg=f"SW={sw1:02X}{sw2:02X}"
                )
        except Exception as e:
            return TestResult(
                config=config,
                result=TestResult.ERROR,
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
            
            # Define all test configurations
            configurations = [
                # Test 1: ISOReadBinary with CLA=00 (correct)
                TestConfiguration(
                    name="CLA=00, escape=True, offset_mode",
                    cla=0x00,
                    use_escape=True,
                    p1_mode="offset",
                    description="ISOReadBinary CLA=00 with escape mode, offset mode"
                ),
                TestConfiguration(
                    name="CLA=00, escape=False, offset_mode",
                    cla=0x00,
                    use_escape=False,
                    p1_mode="offset",
                    description="ISOReadBinary CLA=00 without escape mode"
                ),
                TestConfiguration(
                    name="CLA=00, escape=True, select_file_first",
                    cla=0x00,
                    use_escape=True,
                    select_file_first=True,
                    p1_mode="offset",
                    description="ISOReadBinary CLA=00, select file first"
                ),
                TestConfiguration(
                    name="CLA=00, escape=True, file_id_mode",
                    cla=0x00,
                    use_escape=True,
                    p1_mode="file_id",
                    description="ISOReadBinary CLA=00, P1[7]=1 file ID mode"
                ),
                
                # Test 2: Try CLA=90 (wrong, but test it)
                TestConfiguration(
                    name="CLA=90, escape=True, offset_mode",
                    cla=0x90,
                    use_escape=True,
                    p1_mode="offset",
                    description="ReadBinary CLA=90 (proprietary, might not work)"
                ),
                
                # Test 3: Write configurations
                TestConfiguration(
                    name="Write-CLA=00, escape=True, offset_mode",
                    cla=0x00,
                    use_escape=True,
                    p1_mode="offset",
                    description="ISOUpdateBinary CLA=00"
                ),
                TestConfiguration(
                    name="Write-CLA=00, escape=True, select_file_first",
                    cla=0x00,
                    use_escape=True,
                    select_file_first=True,
                    p1_mode="offset",
                    description="ISOUpdateBinary CLA=00, select file first"
                ),
                TestConfiguration(
                    name="Write-CLA=90, escape=True, offset_mode",
                    cla=0x90,
                    use_escape=True,
                    p1_mode="offset",
                    description="UpdateBinary CLA=90 (proprietary)"
                ),
            ]
            
            # Run read tests
            print("READ TESTS")
            print("-" * 80)
            read_configs = [c for c in configurations if c.name.startswith("CLA=") or "Read" in c.name]
            for config in read_configs:
                if "Write" not in config.name:
                    result = self.test_iso_read_binary(config)
                    self.results.append(result)
                    print(result)
            
            print()
            print("WRITE TESTS")
            print("-" * 80)
            write_configs = [c for c in configurations if "Write" in c.name]
            for config in write_configs:
                result = self.test_iso_update_binary(config)
                self.results.append(result)
                print(result)
            
            # Summary
            print()
            print("=" * 80)
            print("SUMMARY")
            print("=" * 80)
            
            successes = [r for r in self.results if r.result == TestResult.SUCCESS]
            failures = [r for r in self.results if r.result != TestResult.SUCCESS]
            
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
    tester = ComprehensiveNdefTest()
    tester.run_all_tests()

