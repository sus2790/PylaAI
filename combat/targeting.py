"""Enemy targeting and movement selection utilities."""
import random
from typing import List, Tuple, Optional, Any
from movement import Movement
from combat.line_of_sight import is_enemy_hittable
from utils.constants import TILE_SIZE


def find_closest_enemy(
    enemy_data: List[Tuple[float, float, float, float]],
    player_coords: Tuple[float, float],
    walls: List[Tuple[float, float, float, float]],
    skill_type: str,
    brawler: str,
    brawlers_info: Dict[str, Any]
) -> Tuple[Optional[Tuple[float, float]], Optional[float]]:
    """
    Find the closest enemy, prioritizing hittable enemies.

    Args:
        enemy_data: List of enemy bounding boxes
        player_coords: Player position (x, y)
        walls: List of wall bounding boxes
        skill_type: Either 'attack' or 'super'
        brawler: Name of the current brawler
        brawlers_info: Dictionary of brawler information

    Returns:
        Tuple of (enemy_position, distance) or (None, None)
    """
    player_pos_x, player_pos_y = player_coords
    closest_hittable_distance = float('inf')
    closest_unhittable_distance = float('inf')
    closest_hittable = None
    closest_unhittable = None

    for enemy in enemy_data:
        enemy_pos = Movement.get_enemy_pos(enemy)
        distance = Movement.get_distance(enemy_pos, player_coords)

        hittable = is_enemy_hittable(
            (player_pos_x, player_pos_y),
            enemy_pos,
            walls,
            brawler,
            skill_type,
            brawlers_info
        )

        if hittable:
            if distance < closest_hittable_distance:
                closest_hittable_distance = distance
                closest_hittable = (enemy_pos, distance)
        else:
            if distance < closest_unhittable_distance:
                closest_unhittable_distance = distance
                closest_unhittable = (enemy_pos, distance)

    if closest_hittable:
        return closest_hittable
    elif closest_unhittable:
        return closest_unhittable

    return None, None


def no_enemy_movement(
    player_data: Tuple[float, float, float, float],
    walls: List[Tuple[float, float, float, float]],
    game_mode: int,
    window_controller: Any
) -> str:
    """
    Determine movement when no enemy is detected.

    Args:
        player_data: Player bounding box
        walls: List of wall bounding boxes
        game_mode: Game mode identifier
        window_controller: WindowController for scale factor

    Returns:
        Movement string (WASD combination)
    """
    player_position = Movement.get_player_pos(player_data)
    preferred_movement = 'W' if game_mode == 3 else 'D'

    if not is_path_blocked(player_position, preferred_movement, walls, window_controller):
        return preferred_movement

    # Try alternative movements
    alternative_moves = ['W', 'A', 'S', 'D']
    alternative_moves.remove(preferred_movement)
    random.shuffle(alternative_moves)

    for move in alternative_moves:
        if not is_path_blocked(player_position, move, walls, window_controller):
            return move

    print("No movement possible?")
    return preferred_movement


def is_path_blocked(
    player_pos: Tuple[float, float],
    move_direction: str,
    walls: List[Tuple[float, float, float, float]],
    window_controller: Any,
    distance: Optional[float] = None
) -> bool:
    """
    Check if a movement direction is blocked by walls.

    Args:
        player_pos: Player position (x, y)
        move_direction: Movement direction (wasd)
        walls: List of wall bounding boxes
        window_controller: WindowController for scale factor
        distance: Distance to check, defaults to TILE_SIZE scaled

    Returns:
        True if path is blocked, False otherwise
    """
    if distance is None:
        distance = TILE_SIZE * window_controller.scale_factor

    dx, dy = 0, 0
    move_direction = move_direction.lower()

    if 'w' in move_direction:
        dy -= distance
    if 's' in move_direction:
        dy += distance
    if 'a' in move_direction:
        dx -= distance
    if 'd' in move_direction:
        dx += distance

    new_pos = (player_pos[0] + dx, player_pos[1] + dy)
    path_line = LineString([player_pos, new_pos])

    from combat.line_of_sight import walls_are_in_line_of_sight
    return walls_are_in_line_of_sight(path_line, walls)
