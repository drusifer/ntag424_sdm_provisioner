"""
Base classes for APDU command implementations.
"""
from abc import ABC, abstractmethod
from typing import Any
from smartcard.CardConnection import CardConnection


class ApduError(Exception):
    """Custom exception for APDU command failures."""
    def __init__(self, command_name: str, sw1: int, sw2: int):
        self.command_name = command_name
        self.sw1 = sw1
        self.sw2 = sw2
        super().__init__(
            f"{command_name} failed with status words: {sw1:02X}{sw2:02X}"
        )


class ApduCommand(ABC):
    """Abstract base class for all APDU commands."""

    @abstractmethod
    def execute(self, connection: CardConnection) -> Any:
        """
        Executes the command against a card connection.

        Args:
            connection: An active CardConnection object.

        Returns:
            The result of the command, which varies by implementation.
        """
        raise NotImplementedError
