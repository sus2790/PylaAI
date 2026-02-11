"""Combat utilities for enemy detection and targeting."""
from .line_of_sight import (
    walls_are_in_line_of_sight,
    is_enemy_hittable,
    can_attack_through_walls
)
from .targeting import find_closest_enemy, no_enemy_movement

__all__ = [
    'walls_are_in_line_of_sight',
    'is_enemy_hittable',
    'can_attack_through_walls',
    'find_closest_enemy',
    'no_enemy_movement'
]
