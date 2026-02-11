"""Line of sight and wall intersection utilities."""
from typing import List, Tuple, Dict, Any
from shapely.geometry import Polygon, LineString


def walls_are_in_line_of_sight(
    line_of_sight: LineString,
    walls: List[Tuple[float, float, float, float]]
) -> bool:
    """
    Check if any wall intersects with the line of sight.

    Args:
        line_of_sight: LineString representing the line of sight
        walls: List of wall bounding boxes (x1, y1, x2, y2)

    Returns:
        True if a wall blocks the line of sight, False otherwise
    """
    for wall in walls:
        x1, y1, x2, y2 = wall
        wall_polygon = Polygon([
            (x1, y1), (x2, y1),
            (x2, y2), (x1, y2)
        ])
        if line_of_sight.intersects(wall_polygon):
            return True
    return False


def can_attack_through_walls(
    brawler: str,
    skill_type: str,
    brawlers_info: Dict[str, Any]
) -> bool:
    """
    Check if a brawler can attack through walls for a given skill type.

    Args:
        brawler: Name of the brawler
        skill_type: Either 'attack' or 'super'
        brawlers_info: Dictionary of brawler information

    Returns:
        True if the skill can pass through walls, False otherwise

    Raises:
        ValueError: If skill_type is not 'attack' or 'super'
    """
    if not brawlers_info or brawler not in brawlers_info:
        return False

    if skill_type == "attack":
        return brawlers_info[brawler].get('ignore_walls_for_attacks', False)
    elif skill_type == "super":
        return brawlers_info[brawler].get('ignore_walls_for_supers', False)

    raise ValueError("skill_type must be either 'attack' or 'super'")


def is_enemy_hittable(
    player_pos: Tuple[float, float],
    enemy_pos: Tuple[float, float],
    walls: List[Tuple[float, float, float, float]],
    brawler: str,
    skill_type: str,
    brawlers_info: Dict[str, Any]
) -> bool:
    """
    Check if an enemy can be hit considering walls and brawler abilities.

    Args:
        player_pos: Player position (x, y)
        enemy_pos: Enemy position (x, y)
        walls: List of wall bounding boxes
        brawler: Name of the current brawler
        skill_type: Either 'attack' or 'super'
        brawlers_info: Dictionary of brawler information

    Returns:
        True if hittable, False otherwise
    """
    # Check if skill can penetrate walls
    if can_attack_through_walls(brawler, skill_type, brawlers_info):
        return True

    # Check line of sight
    line_of_sight = LineString([player_pos, enemy_pos])
    if walls_are_in_line_of_sight(line_of_sight, walls):
        return False

    return True
