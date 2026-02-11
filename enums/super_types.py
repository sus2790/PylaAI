"""Enums for brawler super types."""
from enum import Enum


class SuperType(str, Enum):
    """Enum representing different types of super abilities."""

    PROJECTILE = "projectile"
    CONE = "cone"
    MELEE = "melee"
    CHARGE = "charge"
    SPAWNABLE = "spawnable"
    OTHER = "other"

    def can_pierce_walls(self) -> bool:
        """Check if this super type can pierce through walls."""
        return self in (self.SPAWNABLE, self.OTHER)

    def is_ranged(self) -> bool:
        """Check if this super type is ranged."""
        return self in (self.PROJECTILE, self.CONE, self.SPAWNABLE)

    def is_melee(self) -> bool:
        """Check if this super type is melee-range."""
        return self in (self.MELEE, self.CHARGE)


class GamemodeType(int, Enum):
    """Enum representing game mode types."""

    GEM_GRAB = 3
    BRAWL_BALL = 5

    def get_movement_priority(self) -> tuple[str, ...]:
        """
        Get movement key priorities for this game mode.

        Returns:
            Tuple of movement key combinations in priority order
        """
        if self == self.GEM_GRAB:
            return ('WD', 'W', 'D')
        elif self == self.BRAWL_BALL:
            return ('DW', 'D', 'W')
        return ('D', 'W')
