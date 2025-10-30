"""
Base classes and constants for APDU commands.
"""
from abc import ABC, abstractmethod
from typing import Any, List, Tuple

from ntag424_sdm_provisioner.hal import NTag424CardConnection

class ApduCommand(ABC):
    """
    Abstract base class for all APDU commands.

    This class holds the APDU structure and logic but delegates the actual
    sending of the command to the connection object.
    """
    def __init__(self, use_escape: bool = False) -> None:
        """
        Args:
            use_escape: Whether to wrap the APDU in a reader-specific escape
                        command (required for some readers like the ACR122U).
        """
        self.use_escape = use_escape

    @abstractmethod
    def execute(self, connection: 'NTag424CardConnection') -> Any: 
        """
        Executes the command against a card connection. This method must be
        implemented by all subclasses.
        """
        raise NotImplementedError

    def send_apdu(self, connection: 'NTag424CardConnection', apdu: List[int]) -> Tuple[List[int], int, int]:
        """
        A proxy method that calls the send_apdu method on the connection object.

        This keeps the pyscard dependency out of the command classes.
        """
        # This now calls the method on the connection object, fulfilling your design goal.
        return connection.send_apdu(apdu, use_escape=self.use_escape)