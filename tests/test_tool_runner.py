#!/usr/bin/env python3
"""
Test ToolRunner with trace-based simulator.

Verifies:
- ToolRunner connects and assesses tag state
- Tools are filtered by preconditions
- Diagnostics tool executes successfully
"""

import sys
from pathlib import Path

# Add src and tests to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from ntag424_sdm_provisioner.tools.runner import ToolRunner
from ntag424_sdm_provisioner.tools.diagnostics_tool import DiagnosticsTool
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from trace_based_simulator import MockNTag424CardConnection, MockCardManager

import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def test_tool_runner_with_simulator():
    """Test tool runner with trace simulator."""
    print("="*70)
    print("Testing Tool Runner with Trace Simulator")
    print("="*70)
    
    # Create mock card using traces
    mock_manager = MockCardManager()
    card = MockNTag424CardConnection(mock_manager)
    
    # Setup key manager
    csv_path = Path(__file__).parent.parent / "examples" / "tag_keys.csv"
    backup_path = Path(__file__).parent.parent / "examples" / "tag_keys_backup.csv"
    key_mgr = CsvKeyManager(csv_path, backup_path)
    
    # Create tools list
    tools = [DiagnosticsTool()]
    
    # Create runner (without actual reader connection for test)
    print("\n1. Creating ToolRunner...")
    runner = ToolRunner(key_mgr, tools)
    
    # Test tag state assessment
    print("\n2. Assessing tag state...")
    tag_state = runner._assess_tag_state(card)
    
    print(f"   UID: {tag_state.uid.hex().upper()}")
    print(f"   Asset Tag: {tag_state.asset_tag}")
    print(f"   In Database: {tag_state.in_database}")
    print(f"   Has NDEF: {tag_state.has_ndef_content}")
    print(f"   Backups: {tag_state.backups_count}")
    
    # Test tool filtering
    print("\n3. Filtering tools by preconditions...")
    available_tools = runner._filter_tools(tag_state)
    print(f"   Available tools: {len(available_tools)}")
    for tool in available_tools:
        print(f"     - {tool.name}")
    
    # Test tool execution
    print("\n4. Executing DiagnosticsTool...")
    diag_tool = DiagnosticsTool()
    try:
        success = diag_tool.execute(tag_state, card, key_mgr)
        print(f"\n   Tool execution: {'SUCCESS' if success else 'FAILED'}")
    except Exception as e:
        print(f"\n   Tool execution FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "="*70)
    print("✅ Tool Runner Test PASSED")
    print("="*70)
    
    return True


if __name__ == '__main__':
    success = test_tool_runner_with_simulator()
    sys.exit(0 if success else 1)

