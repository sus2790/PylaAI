"""Main gameplay controller orchestrating movement, combat, and skills."""
import time
import random
from typing import Optional, List, Tuple, Dict, Any

from PIL import Image
import cv2
import numpy as np

from movement import Movement
from skills import SkillsManager
from combat import find_closest_enemy, no_enemy_movement, is_enemy_hittable
from detect import Detect
from state_finder.main import get_state
from utils.config.loader import load_toml_as_dict
from utils.api import load_brawlers_info
from utils.constants import TILE_SIZE


class Play(SkillsManager):
    """Main gameplay controller that orchestrates all game mechanics."""

    def __init__(
        self,
        main_info_model: Any,
        starting_screen_model: Any,
        tile_detector_model: Any,
        window_controller: Any
    ) -> None:
        """
        Initialize the play controller.

        Args:
            main_info_model: ONNX model for detecting enemies/teammates/player
            starting_screen_model: ONNX model for starting screen detection
            tile_detector_model: ONNX model for wall/tile detection
            window_controller: WindowController instance
        """
        bot_config = load_toml_as_dict("cfg/bot_config.toml")
        time_config = load_toml_as_dict("cfg/time_tresholds.toml")

        super().__init__(window_controller, bot_config, time_config)

        # Initialize detection models
        self.Detect_main_info = Detect(main_info_model, classes=['enemy', 'teammate', 'player'])
        self.Detect_starting_screen = Detect(starting_screen_model)

        self.tile_detector_model_classes = bot_config.get("wall_model_classes", [])
        self.Detect_tile_detector = Detect(
            tile_detector_model,
            classes=self.tile_detector_model_classes
        )

        # Detection thresholds
        self.wall_detection_confidence = bot_config.get("wall_detection_confidence", 0.5)
        self.entity_detection_confidence = bot_config.get("entity_detection_confidence", 0.5)

        # Timing
        self.time_since_movement = time.time()
        self.time_since_walls_checked = 0
        self.time_since_movement_change = time.time()
        self.time_since_player_last_found = time.time()
        self.time_since_last_proceeding = time.time()

        # Brawler info
        self.current_brawler: Optional[str] = None
        self.brawlers_info = load_brawlers_info()
        self.brawler_ranges: Optional[Dict[str, Tuple[int, int, int]]] = None

        # Detection tracking
        self.time_since_detections = {
            "player": time.time(),
            "enemy": time.time(),
        }

        # Movement
        self.last_movement = ''
        self.last_movement_time = time.time()

        # Wall detection state
        self.wall_history: List[List[Tuple[float, float, float, float]]] = []
        self.wall_history_length = 3
        self.should_detect_walls = bot_config.get("gamemode", "") in ["brawlball", "brawl_ball", "brawll ball"]
        self.minimum_movement_delay = bot_config.get("minimum_movement_delay", 0.1)
        self.no_detection_proceed_delay = time_config.get("no_detection_proceed", 5.0)

        # Visualization (for debugging)
        self.scene_data = []

    def load_brawler_ranges(self, brawlers_info: Optional[Dict[str, Any]] = None) -> Dict[str, Tuple[int, int, int]]:
        """
        Load brawler attack ranges scaled to screen size.

        Args:
            brawlers_info: Optional brawler info dictionary

        Returns:
            Dictionary mapping brawler names to (safe_range, attack_range, super_range)
        """
        if not brawlers_info:
            brawlers_info = load_brawlers_info()

        screen_size_ratio = self.window_controller.scale_factor
        ranges = {}

        for brawler, info in brawlers_info.items():
            attack_range = info.get('attack_range', 100)
            safe_range = info.get('safe_range', 50)
            super_range = info.get('super_range', 150)

            v = [safe_range, attack_range, super_range]
            ranges[brawler] = (
                int(v[0] * screen_size_ratio),
                int(v[1] * screen_size_ratio),
                int(v[2] * screen_size_ratio)
            )

        return ranges

    def get_brawler_range(self, brawler: str) -> Tuple[int, int, int]:
        """
        Get attack ranges for a specific brawler.

        Args:
            brawler: Brawler name

        Returns:
            Tuple of (safe_range, attack_range, super_range)
        """
        if self.brawler_ranges is None:
            self.brawler_ranges = self.load_brawler_ranges(self.brawlers_info)

        return self.brawler_ranges[brawler]

    def get_main_data(self, frame: Image.Image) -> Dict[str, Any]:
        """
        Detect entities in the game frame.

        Args:
            frame: Game screen frame

        Returns:
            Dictionary with detection results
        """
        return self.Detect_main_info.detect_objects(frame, conf_tresh=self.entity_detection_confidence)

    def validate_game_data(self, data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Validate that required game data is present.

        Args:
            data: Detection data dictionary

        Returns:
            Validated data or None if incomplete
        """
        if not data:
            return None

        incomplete = False
        if "player" not in data:
            incomplete = True

        if "enemy" not in data:
            data['enemy'] = None

        if 'wall' not in data or not data['wall']:
            data['wall'] = []

        if incomplete:
            return None

        return data

    def track_no_detections(self, data: Optional[Dict[str, Any]]) -> None:
        """
        Update timestamps for when entities were last detected.

        Args:
            data: Detection data dictionary
        """
        if not data:
            data = {
                "enemy": None,
                "player": None
            }

        for key in self.time_since_detections:
            if key in data and data[key]:
                self.time_since_detections[key] = time.time()

    def get_tile_data(self, frame: Image.Image) -> Dict[str, List[Tuple[float, float, float, float]]]:
        """
        Detect walls and tiles in the game frame.

        Args:
            frame: Game screen frame

        Returns:
            Dictionary mapping class names to bounding boxes
        """
        return self.Detect_tile_detector.detect_objects(frame, conf_tresh=self.wall_detection_confidence)

    def process_tile_data(
        self,
        tile_data: Dict[str, List[Tuple[float, float, float, float]]]
    ) -> List[Tuple[float, float, float, float]]:
        """
        Process tile detection data and combine with history.

        Args:
            tile_data: Raw tile detection results

        Returns:
            Combined list of wall bounding boxes
        """
        walls = []

        # Filter out bushes (not actual walls)
        for class_name, boxes in tile_data.items():
            if class_name != 'bush':
                walls.extend(boxes)

        # Add to history
        self.wall_history.append(walls)
        if len(self.wall_history) > self.wall_history_length:
            self.wall_history.pop(0)

        return self.combine_walls_from_history()

    def combine_walls_from_history(self) -> List[Tuple[float, float, float, float]]:
        """
        Combine wall detections from multiple frames.

        Returns:
            List of wall bounding boxes
        """
        wall_counts = {}

        for walls in self.wall_history:
            for wall in walls:
                wall_key = tuple(wall)
                wall_counts[wall_key] = wall_counts.get(wall_key, 0) + 1

        threshold = 1
        combined_walls = [list(wall) for wall, count in wall_counts.items() if count >= threshold]

        return combined_walls

    def get_movement(
        self,
        player_data: Tuple[float, float, float, float],
        enemy_data: Optional[List[Tuple[float, float, float, float]]],
        walls: List[Tuple[float, float, float, float]],
        brawler: str
    ) -> str:
        """
        Calculate optimal movement based on game state.

        Args:
            player_data: Player bounding box
            enemy_data: List of enemy bounding boxes
            walls: List of wall bounding boxes
            brawler: Current brawler name

        Returns:
            Movement string (WASD combination)
        """
        brawler_info = self.brawlers_info.get(brawler)
        if not brawler_info:
            raise ValueError(f"Brawler '{brawler}' not found in brawlers info.")

        safe_range, attack_range, super_range = self.get_brawler_range(brawler)
        player_pos = self.get_player_pos(player_data)

        # No enemy detected
        if not self.is_there_enemy(enemy_data):
            return no_enemy_movement(player_data, walls, self.game_mode, self.window_controller)

        # Find closest enemy
        enemy_coords, enemy_distance = find_closest_enemy(
            enemy_data,
            player_pos,
            walls,
            "attack",
            brawler,
            self.brawlers_info
        )

        if enemy_coords is None:
            return no_enemy_movement(player_data, walls, self.game_mode, self.window_controller)

        # Calculate direction to enemy
        direction_x = enemy_coords[0] - player_pos[0]
        direction_y = enemy_coords[1] - player_pos[1]

        # Determine movement direction based on distance
        if enemy_distance > safe_range:
            move_horizontal = self.get_horizontal_move_key(direction_x)
            move_vertical = self.get_vertical_move_key(direction_y)
        else:
            move_horizontal = self.get_horizontal_move_key(direction_x, opposite=True)
            move_vertical = self.get_vertical_move_key(direction_y, opposite=True)

        # Build movement options based on game mode
        movement_options = [move_horizontal + move_vertical]
        if self.game_mode == 3:
            movement_options += [move_vertical, move_horizontal]
        elif self.game_mode == 5:
            movement_options += [move_horizontal, move_vertical]
        else:
            raise ValueError("Gamemode type is invalid")

        # Check for walls and select best movement
        for move in movement_options:
            if not self.is_path_blocked(player_pos, move, walls):
                movement = move
                break
        else:
            print("Default paths are blocked")
            alternative_moves = ['W', 'A', 'S', 'D']
            random.shuffle(alternative_moves)

            for move in alternative_moves:
                if not self.is_path_blocked(player_pos, move, walls):
                    movement = move
                    break
            else:
                movement = move_horizontal + move_vertical

        # Apply movement smoothing (minimize direction changes)
        current_time = time.time()
        if movement != self.last_movement:
            if current_time - self.last_movement_time >= self.minimum_movement_delay:
                self.last_movement = movement
                self.last_movement_time = current_time
            else:
                movement = self.last_movement
        else:
            self.last_movement_time = current_time

        # Attack if in range and hittable
        if enemy_distance <= attack_range:
            if self.should_use_gadget and self.is_gadget_ready:
                self.use_gadget()
                self.time_since_gadget_checked = time.time()
                self.is_gadget_ready = False

            if self.is_hypercharge_ready:
                self.use_hypercharge()
                self.time_since_hypercharge_checked = time.time()
                self.is_hypercharge_ready = False

            enemy_hittable = is_enemy_hittable(
                player_pos,
                enemy_coords,
                walls,
                brawler,
                "attack",
                self.brawlers_info
            )

            if enemy_hittable:
                self.attack()

        # Use super if ready and conditions met
        if self.is_super_ready:
            super_type = brawler_info.get('super_type', 'projectile')
            enemy_hittable = is_enemy_hittable(
                player_pos,
                enemy_coords,
                walls,
                brawler,
                "super",
                self.brawlers_info
            )

            should_use_super = (
                enemy_hittable and
                (enemy_distance <= super_range
                 or super_type in ["spawnable", "other"]
                 or (brawler in ["stu", "surge"] and super_type == "charge"
                     and enemy_distance <= super_range + attack_range))
            )

            if should_use_super:
                self.use_super()
                self.time_since_super_checked = time.time()
                self.is_super_ready = False

        return movement

    def loop(self, brawler: str, data: Dict[str, Any], current_time: float) -> str:
        """
        Execute one game loop iteration.

        Args:
            brawler: Current brawler name
            data: Game state data
            current_time: Current timestamp

        Returns:
            Movement string that was executed
        """
        movement = self.get_movement(
            player_data=data['player'][0],
            enemy_data=data['enemy'],
            walls=data['wall'],
            brawler=brawler
        )

        if current_time - self.time_since_movement > self.minimum_movement_delay:
            movement = self.unstuck_movement_if_needed(movement, current_time)
            self.do_movement(movement)
            self.time_since_movement = current.time()

        return movement

    def main(self, frame: Image.Image, brawler: str) -> None:
        """
        Main game loop entry point.

        Args:
            frame: Current game screen frame
            brawler: Current brawler name
        """
        current_time = time.time()

        # Detect entities
        data = self.get_main_data(frame)

        # Detect walls if needed
        if self.should_detect_walls and current_time - self.time_since_walls_checked > self.walls_treshold:
            tile_data = self.get_tile_data(frame)
            walls = self.process_tile_data(tile_data)
            self.time_since_walls_checked = current_time
            self.last_walls_data = walls
            data['wall'] = walls
        elif self.keep_walls_in_memory:
            data['wall'] = self.last_walls_data

        # Validate data
        data = self.validate_game_data(data)
        self.track_no_detections(data)

        if data:
            self.time_since_player_last_found = time.time()
        else:
            # Handle no detection scenario
            if current_time - self.time_since_player_last_found > 1.0:
                self.window_controller.keys_up(list("wasd"))
            self.time_since_different_movement = time.time()

            if current_time - self.time_since_last_proceeding > self.no_detection_proceed_delay:
                current_state = get_state(frame)
                if current_state != "match":
                    self.time_since_last_proceeding = current_time
                else:
                    print("Haven't detected the player in a while, proceeding")
                    self.window_controller.press_key("Q")
                    self.time_since_last_proceeding = current_time
            return

        self.time_since_last_proceeding = current_time

        # Check skill readiness
        self.check_all_skills(frame, current_time)

        # Execute gameplay
        movement = self.loop(brawler, data, current_time)

    def generate_visualization(self, output_filename: str = 'visualization.mp4') -> None:
        """
        Generate visualization video from recorded scene data.

        Args:
            output_filename: Output video filename
        """
        frame_size = (1920, 1080)
        fps = 10

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_filename, fourcc, fps, frame_size)

        for frame_data in self.scene_data:
            img = np.zeros((frame_size[1], frame_size[0], 3), np.uint8)

            scale_x = frame_size[0] / 1920
            scale_y = frame_size[1] / 1080

            if frame_data.get('wall'):
                for wall in frame_data['wall']:
                    x1, y1, x2, y2 = map(int, wall)
                    x1, y1 = int(x1 * scale_x), int(y1 * scale_y)
                    x2, y2 = int(x2 * scale_x), int(y2 * scale_y)
                    cv2.rectangle(img, (x1, y1), (x2, y2), (128, 128, 128), -1)

            if frame_data.get('enemy'):
                for enemy in frame_data['enemy']:
                    x1, y1, x2, y2 = map(int, enemy)
                    x1, y1 = int(x1 * scale_x), int(y1 * scale_y)
                    x2, y2 = int(x2 * scale_x), int(y2 * scale_y)
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), -1)

            if frame_data.get('player'):
                for player in frame_data['player']:
                    x1, y1, x2, y2 = map(int, player)
                    x1, y1 = int(x1 * scale_x), int(y1 * scale_y)
                    x2, y2 = int(x2 * scale_x), int(y2 * scale_y)
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), -1)

            movement = frame_data.get('movement', '')
            direction = self.movement_to_direction(movement)
            cv2.putText(
                img,
                f'Movement: {direction}',
                (10, frame_size[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1
            )

            out.write(img)

        out.release()

    @staticmethod
    def movement_to_direction(movement: str) -> str:
        """
        Convert movement string to readable direction.

        Args:
            movement: WASD movement string

        Returns:
            Direction name (e.g., 'up', 'left', 'up-left')
        """
        mapping = {
            'w': 'up',
            'a': 'left',
            's': 'down',
            'd': 'right',
            'wa': 'up-left',
            'aw': 'up-left',
            'wd': 'up-right',
            'dw': 'up-right',
            'sa': 'down-left',
            'as': 'down-left',
            'sd': 'down-right',
            'ds': 'down-right',
        }

        movement = movement.lower()
        movement = ''.join(sorted(movement))
        return mapping.get(movement, 'idle' if movement == '' else movement)
