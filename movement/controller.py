"""Movement controller for keyboard-based character movement."""
import math
import random
import time
from typing import Tuple, Optional, Any
from utils.constants import TILE_SIZE


class Movement:
    """Base class for movement control using keyboard inputs."""

    def __init__(self, window_controller: Any, bot_config: dict, time_config: dict) -> None:
        """
        Initialize movement controller.

        Args:
            window_controller: WindowController instance for input
            bot_config: Bot configuration dictionary
            time_config: Time thresholds configuration dictionary
        """
        self.window_controller = window_controller

        # Unstuck movement configuration
        self.fix_movement_keys = {
            "delay_to_trigger": bot_config.get("unstuck_movement_delay", 1.0),
            "duration": bot_config.get("unstuck_movement_hold_time", 0.5),
            "toggled": False,
            "started_at": time.time(),
            "fixed": ""
        }

        # Game mode
        self.game_mode = bot_config.get("gamemode_type", 3)

        # Ability thresholds
        gadget_value = bot_config.get("bot_uses_gadgets", "no")
        self.should_use_gadget = str(gadget_value).lower() in ("yes", "true", "1")

        self.super_treshold = time_config.get("super", 2.0)
        self.gadget_treshold = time_config.get("gadget", 2.0)
        self.hypercharge_treshold = time_config.get("hypercharge", 2.0)

        # Wall detection
        self.walls_treshold = time_config.get("wall_detection", 2.0)
        self.keep_walls_in_memory = self.walls_treshold <= 1
        self.last_walls_data = []

        # Movement tracking
        self.keys_hold = []
        self.time_since_different_movement = time.time()
        self.time_since_gadget_checked = time.time()
        self.is_gadget_ready = False
        self.time_since_hypercharge_checked = time.time()
        self.is_hypercharge_ready = False

    @staticmethod
    def get_enemy_pos(enemy: Tuple[float, float, float, float]) -> Tuple[float, float]:
        """
        Get center coordinates of enemy bounding box.

        Args:
            enemy: (x1, y1, x2, y2) bounding box

        Returns:
            Tuple of (center_x, center_y)
        """
        return (enemy[0] + enemy[2]) / 2, (enemy[1] + enemy[3]) / 2

    @staticmethod
    def get_player_pos(player_data: Tuple[float, float, float, float]) -> Tuple[float, float]:
        """
        Get center coordinates of player bounding box.

        Args:
            player_data: (x1, y1, x2, y2) bounding box

        Returns:
            Tuple of (center_x, center_y)
        """
        return (player_data[0] + player_data[2]) / 2, (player_data[1] + player_data[3]) / 2

    @staticmethod
    def get_distance(
        enemy_coords: Tuple[float, float],
        player_coords: Tuple[float, float]
    ) -> float:
        """
        Calculate Euclidean distance between two points.

        Args:
            enemy_coords: Enemy position (x, y)
            player_coords: Player position (x, y)

        Returns:
            Distance in pixels
        """
        return math.hypot(enemy_coords[0] - player_coords[0], enemy_coords[1] - player_coords[1])

    @staticmethod
    def is_there_enemy(enemy_data: Optional[Any]) -> bool:
        """
        Check if enemy data exists and is valid.

        Args:
            enemy_data: Enemy bounding box data or None

        Returns:
            True if enemy exists, False otherwise
        """
        if enemy_data is None or enemy_data[0] is None:
            return False
        return True

    @staticmethod
    def get_horizontal_move_key(direction_x: float, opposite: bool = False) -> str:
        """
        Get horizontal movement key based on X direction.

        Args:
            direction_x: X direction (positive = right, negative = left)
            opposite: If True, reverse the direction

        Returns:
            'D' or 'A'
        """
        if opposite:
            return "A" if direction_x > 0 else "D"
        return "D" if direction_x > 0 else "A"

    @staticmethod
    def get_vertical_move_key(direction_y: float, opposite: bool = False) -> str:
        """
        Get vertical movement key based on Y direction.

        Args:
            direction_y: Y direction (positive = down, negative = up)
            opposite: If True, reverse the direction

        Returns:
            'S' or 'W'
        """
        if opposite:
            return "W" if direction_y > 0 else "S"
        return "S" if direction_y > 0 else "W"

    def attack(self) -> None:
        """Press attack key."""
        self.window_controller.press_key("M")

    def use_hypercharge(self) -> None:
        """Press hypercharge key."""
        print("Using hypercharge")
        self.window_controller.press_key("H")

    def use_gadget(self) -> None:
        """Press gadget key."""
        print("Using gadget")
        self.window_controller.press_key("G")

    def use_super(self) -> None:
        """Press super key."""
        print("Using super")
        self.window_controller.press_key("E")

    @staticmethod
    def get_random_attack_key() -> str:
        """
        Get a random movement key combination.

        Returns:
            Two-character string like 'WA', 'SD', etc.
        """
        random_movement = random.choice(["A", "W", "S", "D"])
        random_movement += random.choice(["A", "W", "S", "D"])
        return random_movement

    @staticmethod
    def reverse_movement(movement: str) -> str:
        """
        Reverse a movement direction string.

        Args:
            movement: Movement string like 'wasd'

        Returns:
            Reversed movement string 'sdwa'
        """
        movement = movement.lower()
        translation_table = str.maketrans("wasd", "sdwa")
        return movement.translate(translation_table)

    def unstuck_movement_if_needed(
        self,
        movement: str,
        current_time: Optional[float] = None
    ) -> str:
        """
        Apply unstuck logic if movement hasn't changed recently.

        Args:
            movement: Current movement string
            current_time: Current timestamp (uses time.time() if None)

        Returns:
            Movement string (possibly reversed)
        """
        if current_time is None:
            current_time = time.time()
        movement = movement.lower()

        # If unstuck mode is active
        if self.fix_movement_keys['toggled']:
            if current_time - self.fix_movement_keys['started_at'] > self.fix_movement_keys['duration']:
                self.fix_movement_keys['toggled'] = False
            return self.fix_movement_keys['fixed']

        # Track movement changes
        if "".join(self.keys_hold) != movement and movement[::-1] != "".join(self.keys_hold):
            self.time_since_different_movement = current_time

        # Check if stuck (no movement change for too long)
        if current_time - self.time_since_different_movement > self.fix_movement_keys["delay_to_trigger"]:
            reversed_movement = self.reverse_movement(movement)

            # Diagonal alternatives for pure forward/backward movement
            if reversed_movement == "s":
                reversed_movement = random.choice(['aw', 'dw'])
            elif reversed_movement == "w":
                reversed_movement = random.choice(['as', 'ds'])

            self.fix_movement_keys['fixed'] = reversed_movement
            self.fix_movement_keys['toggled'] = True
            self.fix_movement_keys['started_at'] = current_time
            return reversed_movement

        return movement

    def do_movement(self, movement: str) -> None:
        """
        Execute movement by pressing and releasing appropriate keys.

        Args:
            movement: Movement string containing WASD characters
        """
        movement = movement.lower()
        keys_to_keyDown = []
        keys_to_keyUp = []

        for key in ['w', 'a', 's', 'd']:
            if key in movement:
                keys_to_keyDown.append(key)
            else:
                keys_to_keyUp.append(key)

        if keys_to_keyDown:
            self.window_controller.keys_down(keys_to_keyDown)

        self.window_controller.keys_up(keys_to_keyUp)
        self.keys_hold = keys_to_keyDown
