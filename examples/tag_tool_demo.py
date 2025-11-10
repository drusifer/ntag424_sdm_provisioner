#!/usr/bin/env python3
"""
NTAG424 Tag Tool - Interactive tag operations (Demo Version).

This demonstrates the new tool-based architecture with DiagnosticsTool.
More tools will be added incrementally.

Usage:
    python tag_tool_demo.py
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ntag424_sdm_provisioner.tools.runner import ToolRunner
from ntag424_sdm_provisioner.tools.diagnostics_tool import DiagnosticsTool
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

log = logging.getLogger(__name__)


def main():
    """Main entry point."""
    print("\n" + "="*70)
    print("NTAG424 Tag Tool (Demo Version)")
    print("="*70)
    print()
    print("Available tools:")
    print("  - Diagnostics Tool (show complete tag information)")
    print()
    print("Coming soon:")
    print("  - Provision Factory Tool")
    print("  - Restore Backup Tool")
    print("  - Update URL Tool")
    print("  - And more...")
    print()
    
    # Setup key manager
    csv_path = Path(__file__).parent / "tag_keys.csv"
    backup_path = Path(__file__).parent / "tag_keys_backup.csv"
    key_mgr = CsvKeyManager(csv_path=csv_path, backup_path=backup_path)
    
    # Setup tools (just diagnostics for now)
    tools = [
        DiagnosticsTool(),
    ]
    
    # Create and run tool runner (reader_index=0 uses first reader)
    runner = ToolRunner(key_mgr, tools, reader_index=0)
    
    try:
        runner.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

