"""
Tool Runner - Main loop for tag operations.

Handles connection management, tag state assessment, menu display,
and tool execution with error handling.
"""

import csv
import logging
from typing import List, Optional, Union
from contextlib import contextmanager
from pathlib import Path

from ntag424_sdm_provisioner.tools.base import Tool, TagState, TagPrecondition
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, TagKeys
from ntag424_sdm_provisioner.hal import NTag424CardConnection, CardManager
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
from ntag424_sdm_provisioner.commands.iso_commands import ISOSelectFile, ISOReadBinary, ISOFileID
from ntag424_sdm_provisioner.uid_utils import uid_to_asset_tag

log = logging.getLogger(__name__)


class ToolRunner:
    """
    Main orchestrator for tool-based tag operations.
    
    Manages:
    - Tag connection/disconnection per operation
    - Tag state assessment
    - Tool filtering based on preconditions
    - Menu display and user interaction
    - Tool execution with error handling
    """
    
    def __init__(self, key_mgr: CsvKeyManager, tools: List[Tool], 
                 reader_index: int = 0):
        """
        Initialize tool runner.
        
        Args:
            key_mgr: Key manager for database operations
            tools: List of available tools
            reader_index: Reader index (default 0 for first reader)
        """
        self.key_mgr = key_mgr
        self.tools = tools
        self.reader_index = reader_index
    
    @contextmanager
    def _connect_to_tag(self):
        """
        Connect to tag on reader, yield connection, disconnect.
        
        Fresh connection for each operation - allows tag swapping,
        rate limit recovery, and clean state.
        
        CardManager handles connection/disconnection automatically.
        """
        log.info("Connecting to tag...")
        with CardManager(reader_index=self.reader_index) as card:
            # card is already NTag424CardConnection from CardManager.__enter__
            # Select application
            card.send(SelectPiccApplication())
            log.info(f"Connected to tag")
            yield card
        # CardManager.__exit__ handles disconnect automatically
        log.info("Disconnected from tag")
    
    def _assess_tag_state(self, card: NTag424CardConnection) -> TagState:
        """
        Assess current state of the tag.
        
        Reads tag info, checks database, examines NDEF, scans backups.
        
        Args:
            card: Open connection to tag
            
        Returns:
            TagState with all relevant information
        """
        # Get UID and version
        version_info = card.send(GetChipVersion())
        uid = version_info.uid
        asset_tag = uid_to_asset_tag(uid)
        
        log.info(f"Assessing tag state for UID: {uid.hex().upper()} [{asset_tag}]")
        
        # Check database
        in_database = False
        keys = None
        try:
            keys = self.key_mgr.get_tag_keys(uid)
            in_database = True
            log.debug(f"Tag in database: status={keys.status}")
        except KeyError:
            log.debug("Tag not in database")
        
        # Check NDEF content
        has_ndef_content = False
        try:
            card.send(ISOSelectFile(ISOFileID.NDEF_FILE))
            ndef_data = card.send(ISOReadBinary(0, 100))
            # Check for SDM parameters (uid=, ctr=, cmac=)
            if b'uid=' in ndef_data or b'ctr=' in ndef_data:
                has_ndef_content = True
                log.debug("Tag has provisioned NDEF content")
            else:
                log.debug("NDEF is blank or default")
            # Re-select PICC app for subsequent commands
            card.send(SelectPiccApplication())
        except Exception as e:
            log.debug(f"Could not read NDEF: {e}")
            card.send(SelectPiccApplication())
        
        # Check backups
        backups = self._get_backups_for_uid(uid)
        has_successful_backup = any(b.get('status') == 'provisioned' for b in backups)
        
        log.debug(f"Backups: {len(backups)} total, successful={has_successful_backup}")
        
        return TagState(
            uid=uid,
            asset_tag=asset_tag,
            in_database=in_database,
            keys=keys,
            has_ndef_content=has_ndef_content,
            backups_count=len(backups),
            has_successful_backup=has_successful_backup
        )
    
    def _get_backups_for_uid(self, uid: bytes) -> list:
        """Load all backups for a specific UID."""
        backups = []
        backup_path = self.key_mgr.backup_path
        
        if not backup_path.exists():
            return backups
        
        uid_hex = uid.hex().upper()
        
        try:
            with open(backup_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['uid'].upper() == uid_hex:
                        backups.append(row)
        except Exception as e:
            log.warning(f"Error reading backups: {e}")
        
        return backups
    
    def _filter_tools(self, tag_state: TagState) -> List[Tool]:
        """
        Filter tools by preconditions.
        
        Args:
            tag_state: Current tag state
            
        Returns:
            List of tools whose preconditions are met
        """
        available = []
        for tool in self.tools:
            if tag_state.matches(tool.preconditions):
                available.append(tool)
                log.debug(f"Tool available: {tool.name}")
            else:
                log.debug(f"Tool filtered out: {tool.name}")
        
        return available
    
    def _show_menu(self, tag_state: TagState, available_tools: List[Tool]) -> Union[int, str]:
        """
        Display menu and get user choice.
        
        Args:
            tag_state: Current tag state
            available_tools: Tools that can be used
            
        Returns:
            Tool index (0-based) or 'quit'
        """
        print("\n" + "="*70)
        print("NTAG424 Tag Tool Menu")
        print("="*70)
        print(f"Tag: {tag_state.asset_tag} (UID: {tag_state.uid.hex().upper()})")
        
        if tag_state.in_database:
            status = tag_state.keys.status if tag_state.keys else "unknown"
            print(f"Database: {status}")
        else:
            print("Database: Not found")
        
        print("="*70)
        
        if not available_tools:
            print("⚠️  No tools available for current tag state")
            print("    Try diagnostics tool or check tag/database")
            print()
            print("  q. Quit")
        else:
            print("Available tools:")
            print()
            for i, tool in enumerate(available_tools, 1):
                print(f"  {i}. {tool.name}")
                print(f"     {tool.description}")
            print()
            print("  q. Quit")
        
        print("="*70)
        
        while True:
            choice = input("Select tool: ").strip().lower()
            
            if choice == 'q':
                return 'quit'
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(available_tools):
                    return idx
                else:
                    print(f"Invalid choice. Enter 1-{len(available_tools)} or 'q'")
            except ValueError:
                print("Invalid input. Enter a number or 'q'")
    
    def run(self):
        """
        Main loop: connect → assess → menu → execute → repeat.
        
        Fresh connection for each operation. Allows tag swapping,
        rate limit recovery, and clean state between tools.
        """
        print("\n" + "="*70)
        print("NTAG424 Tag Tool")
        print("="*70)
        print("Place tag on reader to begin")
        print()
        input("Press Enter when ready...")
        
        while True:
            try:
                # Fresh connection per operation
                with self._connect_to_tag() as card:
                    # Assess current tag state
                    tag_state = self._assess_tag_state(card)
                    
                    # Filter tools by preconditions
                    available_tools = self._filter_tools(tag_state)
                    
                    # Show menu and get choice
                    choice = self._show_menu(tag_state, available_tools)
                    
                    if choice == 'quit':
                        print("\nExiting...")
                        break
                    
                    # Execute chosen tool
                    tool = available_tools[choice]
                    print(f"\n{'='*70}")
                    print(f"Executing: {tool.name}")
                    print('='*70)
                    
                    try:
                        success = tool.execute(tag_state, card, self.key_mgr)
                        
                        if success:
                            log.info(f"✅ {tool.name} completed successfully")
                        else:
                            log.warning(f"⚠️  {tool.name} completed with warnings")
                    
                    except Exception as e:
                        log.error(f"❌ {tool.name} failed: {e}")
                        print(f"\n❌ Tool failed: {e}")
                        print("You can remove/replace tag and try again")
            
            except KeyboardInterrupt:
                print("\n\nInterrupted by user")
                break
            
            except Exception as e:
                log.error(f"Error in main loop: {e}")
                print(f"\n❌ Error: {e}")
                print("Remove/replace tag and try again")
            
            # Wait for user before next operation
            print("\n" + "="*70)
            response = input("Press Enter for next operation (or 'q' to quit): ").strip().lower()
            if response == 'q':
                print("\nExiting...")
                break
        
        print("\nGoodbye!")

