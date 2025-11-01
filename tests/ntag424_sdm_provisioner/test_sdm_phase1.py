"""
Tests for Phase 1: Core SDM Commands

Simple tests to verify GetFileCounters command structure and basic functionality.
"""

import pytest
from ntag424_sdm_provisioner.commands.get_file_counters import GetFileCounters
from ntag424_sdm_provisioner.constants import APDUInstruction


class TestGetFileCounters:
    """Test GetFileCounters command"""
    
    def test_create_command(self):
        """GetFileCounters can be instantiated"""
        cmd = GetFileCounters(file_no=0x02)
        assert cmd.file_no == 0x02
    
    def test_default_file_number(self):
        """GetFileCounters defaults to NDEF file (0x02)"""
        cmd = GetFileCounters()
        assert cmd.file_no == 0x02
    
    def test_string_representation(self):
        """GetFileCounters has useful string representation"""
        cmd = GetFileCounters(file_no=0x02)
        s = str(cmd)
        assert "GetFileCounters" in s
        assert "0x02" in s
    
    def test_instruction_constant_exists(self):
        """GET_FILE_COUNTERS instruction is defined"""
        assert hasattr(APDUInstruction, 'GET_FILE_COUNTERS')
        assert APDUInstruction.GET_FILE_COUNTERS == 0xC1


class TestChangeFileSettings:
    """Test ChangeFileSettings command exists"""
    
    def test_command_exists(self):
        """ChangeFileSettings command can be imported"""
        from ntag424_sdm_provisioner.commands.change_file_settings import ChangeFileSettings
        assert ChangeFileSettings is not None


def test_phase1_summary():
    """Summary: Phase 1 core commands are available"""
    # GetFileCounters
    from ntag424_sdm_provisioner.commands.get_file_counters import GetFileCounters
    cmd1 = GetFileCounters()
    assert str(cmd1) == "GetFileCounters(file_no=0x02)"
    
    # ChangeFileSettings  
    from ntag424_sdm_provisioner.commands.change_file_settings import ChangeFileSettings
    assert ChangeFileSettings is not None
    
    # Constants
    assert APDUInstruction.GET_FILE_COUNTERS == 0xC1
    assert APDUInstruction.CHANGE_FILE_SETTINGS == 0x5F
    
    print("✓ Phase 1: Core SDM Commands - COMPLETE")

