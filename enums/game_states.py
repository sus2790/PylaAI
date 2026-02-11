"""Enums for game states."""
from enum import Enum


class GameState(str, Enum):
    """Enum representing all possible game states."""

    END = "end"
    SHOP = "shop"
    POPUP = "popup"
    LOBBY = "lobby"
    MATCH = "match"
    PLAY_STORE = "play_store"
    STAR_DROP = "star_drop"
    MENU = "menu"
    BRAWLER_PICK_SCREEN = "brawler_pick_screen"

    @classmethod
    def from_string(cls, value: str) -> 'GameState':
        """
        Convert a string to a GameState enum.

        Args:
            value: String representation of game state

        Returns:
            GameState enum value or None if not found
        """
        for state in cls:
            if state.value == value.lower():
                return state
        raise ValueError(f"Unknown game state: {value}")

    def is_match_active(self) -> bool:
        """Check if this state represents an active match."""
        return self == self.MATCH
