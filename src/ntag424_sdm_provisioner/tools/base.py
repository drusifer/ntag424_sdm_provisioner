"""
Base classes for tool-based architecture.

Provides:
- TagPrecondition: Declarative flags for tool requirements
- TagState: Current state of a tag
- Tool: Protocol for all tool implementations
"""

from enum import Flag, auto
from typing import Protocol, Optional
from dataclasses import dataclass

from ntag424_sdm_provisioner.csv_key_manager import TagKeys, CsvKeyManager
from ntag424_sdm_provisioner.hal import NTag424CardConnection


class TagPrecondition(Flag):
    """
    Declarative preconditions for tools.
    
    Tools specify which conditions must be met using these flags.
    ToolRunner automatically filters tools based on current tag state.
    """
    NONE = 0
    
    # Database state
    IN_DATABASE = auto()           # Tag has entry in database
    NOT_IN_DATABASE = auto()       # Tag not in database
    
    # Key state  
    HAS_FACTORY_KEYS = auto()      # Tag has factory keys (all 0x00)
    HAS_CUSTOM_KEYS = auto()       # Tag has custom keys
    KEYS_KNOWN = auto()            # Keys are in database (factory or custom)
    
    # Provision state
    STATUS_PROVISIONED = auto()    # Database status = 'provisioned'
    STATUS_FAILED = auto()         # Database status = 'failed'
    STATUS_PENDING = auto()        # Database status = 'pending'
    STATUS_FACTORY = auto()        # Database status = 'factory'
    
    # NDEF state
    HAS_NDEF_CONTENT = auto()      # Tag has provisioned NDEF (uid=/ctr= params)
    BLANK_NDEF = auto()            # NDEF is blank or default
    
    # Backup availability
    HAS_BACKUPS = auto()           # At least one backup exists
    HAS_SUCCESSFUL_BACKUP = auto() # At least one 'provisioned' backup exists


@dataclass
class TagState:
    """
    Current state of a tag.
    
    Assessed once per tool invocation, used to filter available tools
    and provide context to tool execution.
    """
    # Identity
    uid: bytes
    asset_tag: str  # Human-readable (e.g., "B3-664A")
    
    # Database
    in_database: bool
    keys: Optional[TagKeys]  # None if not in database
    
    # NDEF content
    has_ndef_content: bool
    
    # Backups
    backups_count: int
    has_successful_backup: bool
    
    def matches(self, preconditions: TagPrecondition) -> bool:
        """
        Check if this tag state satisfies the given preconditions.
        
        Args:
            preconditions: Required conditions (can be combined with |)
            
        Returns:
            True if all required conditions are met
            
        Example:
            tool.preconditions = TagPrecondition.IN_DATABASE | TagPrecondition.HAS_FACTORY_KEYS
            tag_state.matches(tool.preconditions)  # True if both conditions met
        """
        if preconditions == TagPrecondition.NONE:
            return True  # No requirements
        
        # Check each flag
        checks = []
        
        # Database state
        if TagPrecondition.IN_DATABASE in preconditions:
            checks.append(self.in_database)
        if TagPrecondition.NOT_IN_DATABASE in preconditions:
            checks.append(not self.in_database)
        
        # Key state
        if TagPrecondition.HAS_FACTORY_KEYS in preconditions:
            checks.append(self.keys is not None and self.keys.status == 'factory')
        if TagPrecondition.HAS_CUSTOM_KEYS in preconditions:
            checks.append(self.keys is not None and self.keys.status != 'factory')
        if TagPrecondition.KEYS_KNOWN in preconditions:
            checks.append(self.keys is not None)
        
        # Provision status
        if TagPrecondition.STATUS_PROVISIONED in preconditions:
            checks.append(self.keys is not None and self.keys.status == 'provisioned')
        if TagPrecondition.STATUS_FAILED in preconditions:
            checks.append(self.keys is not None and self.keys.status == 'failed')
        if TagPrecondition.STATUS_PENDING in preconditions:
            checks.append(self.keys is not None and self.keys.status == 'pending')
        if TagPrecondition.STATUS_FACTORY in preconditions:
            checks.append(self.keys is not None and self.keys.status == 'factory')
        
        # NDEF state
        if TagPrecondition.HAS_NDEF_CONTENT in preconditions:
            checks.append(self.has_ndef_content)
        if TagPrecondition.BLANK_NDEF in preconditions:
            checks.append(not self.has_ndef_content)
        
        # Backup availability
        if TagPrecondition.HAS_BACKUPS in preconditions:
            checks.append(self.backups_count > 0)
        if TagPrecondition.HAS_SUCCESSFUL_BACKUP in preconditions:
            checks.append(self.has_successful_backup)
        
        # All checks must pass (AND logic for combined flags)
        return all(checks) if checks else True


class Tool(Protocol):
    """
    Protocol for all tag operation tools.
    
    Each tool is self-contained and declares its requirements via preconditions.
    Tools have full control over the card connection for their duration.
    """
    
    @property
    def name(self) -> str:
        """Tool name for menu display."""
        ...
    
    @property
    def description(self) -> str:
        """One-line description for menu."""
        ...
    
    @property
    def preconditions(self) -> TagPrecondition:
        """
        Required tag state for this tool to be applicable.
        
        Tools are only shown in menu if preconditions are met.
        Use TagPrecondition flags combined with | operator.
        
        Examples:
            TagPrecondition.NONE  # Always available
            TagPrecondition.IN_DATABASE | TagPrecondition.STATUS_PROVISIONED
            TagPrecondition.HAS_FACTORY_KEYS | TagPrecondition.BLANK_NDEF
        """
        ...
    
    def execute(self, tag_state: TagState, card: NTag424CardConnection, 
                key_mgr: CsvKeyManager) -> bool:
        """
        Execute the tool operation.
        
        Tool owns the card connection for its duration and can:
        - Perform unauthenticated commands
        - Create authenticated sessions (single or multiple)
        - Maintain session state across operations
        
        Connection stays open until tool completes.
        
        Args:
            tag_state: Current state of the tag
            card: Open connection to tag (stays open for tool duration)
            key_mgr: Key manager for database operations
            
        Returns:
            True if operation succeeded, False if completed with warnings
            
        Raises:
            Exception: If operation fails critically
        """
        ...

