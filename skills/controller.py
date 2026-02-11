"""Manager for skill timing and usage."""
import time
from typing import Optional
from PIL import Image
from movement import Movement
from skills.detectors import (
    check_if_hypercharge_ready,
    check_if_gadget_ready,
    check_if_super_ready
)


class SkillsManager(Movement):
    """Manages skill cooldowns and usage."""

    def __init__(self, window_controller, bot_config: dict, time_config: dict) -> None:
        """
        Initialize skills manager.

        Args:
            window_controller: WindowController instance
            bot_config: Bot configuration dictionary
            time_config: Time thresholds configuration dictionary
        """
        super().__init__(window_controller, bot_config, time_config)

        # Pixel thresholds for skill detection
        self.gadget_pixels_minimum = bot_config.get("gadget_pixels_minimum", 5000)
        self.hypercharge_pixels_minimum = bot_config.get("hypercharge_pixels_minimum", 5000)
        self.super_pixels_minimum = bot_config.get("super_pixels_minimum", 5000)

        # Skill states
        self.is_hypercharge_ready = False
        self.is_gadget_ready = False
        self.is_super_ready = False

    def check_all_skills(self, frame: Image.Image, current_time: Optional[float] = None) -> None:
        """
        Check all skills for readiness based on time thresholds.

        Args:
            frame: Screen frame to check
            current_time: Current timestamp (uses time.time() if None)
        """
        if current_time is None:
            current_time = time.time()

        # Check hypercharge
        self.is_hypercharge_ready = False
        if current_time - self.time_since_hypercharge_checked > self.hypercharge_treshold:
            self.is_hypercharge_ready = check_if_hypercharge_ready(
                frame,
                self.window_controller,
                self.hypercharge_pixels_minimum
            )
            self.time_since_hypercharge_checked = current_time

        # Check gadget
        self.is_gadget_ready = False
        if current_time - self.time_since_gadget_checked > self.gadget_treshold:
            self.is_gadget_ready = check_if_gadget_ready(
                frame,
                self.window_controller,
                self.gadget_pixels_minimum
            )
            self.time_since_gadget_checked = current_time

        # Check super
        self.is_super_ready = False
        if current_time - self.time_since_super_checked > self.super_treshold:
            self.is_super_ready = check_if_super_ready(
                frame,
                self.window_controller,
                self.super_pixels_minimum
            )
            self.time_since_super_checked = current_time

    def try_use_gadget(self, current_time: Optional[float] = None) -> bool:
        """
        Use gadget if ready and enabled.

        Args:
            current_time: Current timestamp

        Returns:
            True if gadget was used
        """
        if not self.should_use_gadget:
            return False

        if self.is_gadget_ready:
            self.use_gadget()
            if current_time is None:
                current_time = time.time()
            self.time_since_gadget_checked = current_time
            self.is_gadget_ready = False
            return True
        return False

    def try_use_hypercharge(self, current_time: Optional[float] = None) -> bool:
        """
        Use hypercharge if ready.

        Args:
            current_time: Current timestamp

        Returns:
            True if hypercharge was used
        """
        if self.is_hypercharge_ready:
            self.use_hypercharge()
            if current_time is None:
                current_time = time.time()
            self.time_since_hypercharge_checked = current_time
            self.is_hypercharge_ready = False
            return True
        return False

    def try_use_super(
        self,
        brawler: str,
        brawler_info: dict,
        player_pos: tuple,
        enemy_pos: tuple,
        enemy_distance: float,
        super_range: int,
        attack_range: int,
        walls: list
    ) -> bool:
        """
        Use super if conditions are met.

        Args:
            brawler: Current brawler name
            brawler_info: Brawler information
            player_pos: Player position
            enemy_pos: Enemy position
            enemy_distance: Distance to enemy
            super_range: Super attack range
            attack_range: Attack range
            walls: List of wall bounding boxes

        Returns:
            True if super was used
        """
        from combat.line_of_sight import is_enemy_hittable

        if not self.is_super_ready:
            return False

        super_type = brawler_info.get('super_type', 'projectile')
        enemy_hittable = is_enemy_hittable(
            player_pos,
            enemy_pos,
            walls,
            brawler,
            "super",
            self.brawlers_info
        )

        should_use = (
            enemy_hittable and
            (enemy_distance <= super_range
             or super_type in ["spawnable", "other"]
             or (brawler in ["stu", "surge"] and super_type == "charge"
                 and enemy_distance <= super_range + attack_range))
        )

        if should_use:
            self.use_super()
            import time
            self.time_since_super_checked = time.time()
            self.is_super_ready = False
            return True

        return False

    def reset_timers(self) -> None:
        """Reset all skill timers."""
        current_time = time.time()
        self.time_since_hypercharge_checked = current_time
        self.time_since_gadget_checked = current_time
        self.time_since_super_checked = current_time
