"""
Base classes and constants for APDU commands.
"""
from abc import ABC, abstractmethod
from typing import Any, List, Tuple

from ntag424_sdm_provisioner.hal import NTag424CardConnection

class ApduCommand(ABC):
    """Abstract base class for all APDU commands."""

    def __init__(self, connection, use_escape: bool = False):
        """
        Args:
            use_escape: Whether to wrap APDUs in the ACR122 escape format.
        """
        self.use_escape = use_escape    
        self.connection = connection

    @abstractmethod
    def execute(self, ncc: NTag424CardConnection) -> Any:
        """
        Executes the command against a card connection.
        This method must be implemented by all subclasses.
        """
        raise NotImplementedError
