"""Game state detection using template matching and OCR."""
import os
from typing import Tuple, Optional, List
import numpy as np
import cv2
from PIL import Image

from utils.image_utils import count_hsv_pixels
from utils.config import load_toml_as_dict
from utils.ocr import EasyOCRReader
from utils.game_result import rework_game_result
from difflib import SequenceMatcher


# Constants
ORIGINAL_SCREEN_WIDTH = 1920
ORIGINAL_SCREEN_HEIGHT = 1080
TEMPLATE_MATCH_THRESHOLD = 0.7
RED_PIXEL_THRESHOLD = 200000
OCR_CONFIDENCE_THRESHOLD = 0.55


class StateDetector:
    """Detector for game states using template matching."""

    def __init__(
        self,
        config_path: str = "./cfg/lobby_config.toml",
        image_dir: str = "./state_finder/images_to_detect/"
    ) -> None:
        """
        Initialize state detector.

        Args:
            config_path: Path to lobby configuration file
            image_dir: Directory containing template images
        """
        self.config = load_toml_as_dict(config_path)
        self.image_dir = image_dir
        self.region_data = self.config.get('template_matching', {})
        self.crop_region = self.config.get('lobby', {}).get('trophy_observer', [])

        # Load star drop images
        self.star_drop_images = [
            f for f in os.listdir(image_dir) if "star_drop" in f
        ]
        self._template_cache = {}

    def _get_scaled_region(
        self,
        region: Tuple[int, int, int, int],
        image_width: int,
        image_height: int
    ) -> Tuple[int, int, int, int]:
        """
        Scale a region to match current image dimensions.

        Args:
            region: (x, y, width, height) region in original coordinates
            image_width: Current image width
            image_height: Current image height

        Returns:
            Scaled (x, y, width, height) coordinates
        """
        width_ratio = image_width / ORIGINAL_SCREEN_WIDTH
        height_ratio = image_height / ORIGINAL_SCREEN_HEIGHT

        orig_x, orig_y, orig_width, orig_height = region
        new_x = int(orig_x * width_ratio)
        new_y = int(orig_y * height_ratio)
        new_width = int(orig_width * width_ratio)
        new_height = int(orig_height * height_ratio)

        return new_x, new_y, new_width, new_height

    def _load_template(
        self,
        template_path: str,
        image_width: int,
        image_height: int
    ) -> np.ndarray:
        """
        Load and resize a template image.

        Args:
            template_path: Path to template image
            image_width: Current image width
            image_height: Current image height

        Returns:
            Resized template image
        """
        cache_key = (template_path, image_width, image_height)

        if cache_key in self._template_cache:
            return self._template_cache[cache_key]

        image = cv2.imread(template_path)
        orig_height, orig_width = image.shape[:2]

        width_ratio = image_width / ORIGINAL_SCREEN_WIDTH
        height_ratio = image_height / ORIGINAL_SCREEN_HEIGHT

        resized = cv2.resize(
            image,
            (int(orig_width * width_ratio), int(orig_height * height_ratio))
        )

        self._template_cache[cache_key] = resized
        return resized

    def is_template_in_region(
        self,
        image: np.ndarray,
        template_path: str,
        region_name: str
    ) -> bool:
        """
        Check if a template exists in a specific region.

        Args:
            image: Source image
            template_path: Path to template image
            region_name: Name of region config

        Returns:
            True if template is found
        """
        if region_name not in self.region_data:
            return False

        region = self.region_data[region_name]
        image_height, image_width = image.shape[:2]

        new_x, new_y, new_width, new_height = self._get_scaled_region(
            region, image_width, image_height
        )

        cropped = image[new_y:new_y + new_height, new_x:new_x + new_width]
        template = self._load_template(template_path, image_width, image_height)

        result = cv2.matchTemplate(cropped, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)

        return max_val > TEMPLATE_MATCH_THRESHOLD

    def _find_game_result(self, screenshot: np.ndarray, reader: EasyOCRReader) -> bool:
        """
        Determine if game ended by reading result text.

        Args:
            screenshot: Screenshot as numpy array
            reader: OCR reader instance

        Returns:
            True if game result was found
        """
        if not isinstance(screenshot, np.ndarray):
            raise TypeError(f"Expected numpy.ndarray, got {type(screenshot)}")

        x1, y1, x2, y2 = self.crop_region
        if len(self.crop_region) != 4 or 0 in self.crop_region:
            return False

        cropped = screenshot[y1:y2, x1:x2]
        result = reader.readtext(cropped)

        if len(result) == 0:
            return False

        _, text, conf = result[0]
        game_result, ratio = self._rework_game_result(text)

        if ratio < OCR_CONFIDENCE_THRESHOLD:
            if ratio > 0:
                print(f"Couldn't find game result: {game_result}, confidence: {ratio:.2f}")
            return False

        return True

    @staticmethod
    def _rework_game_result(res_string: str) -> Tuple[str, float]:
        """Refine OCR result using fuzzy matching."""
        res_string = res_string.lower()
        if res_string in ["victory", "defeat", "draw"]:
            return res_string, 1.0

        ratios = {
            "victory": SequenceMatcher(None, res_string, 'victory').ratio(),
            "defeat": SequenceMatcher(None, res_string, 'defeat').ratio(),
            "draw": SequenceMatcher(None, res_string, "draw").ratio()
        }
        highest = max(ratios, key=ratios.get)
        return highest, ratios[highest]

    def is_in_end_of_match(self, image: np.ndarray, reader: EasyOCRReader) -> bool:
        """Check if end of match screen is shown."""
        return self._find_game_result(image, reader)

    def is_in_shop(self, image: np.ndarray) -> bool:
        """Check if shop screen is shown."""
        return self.is_template_in_region(
            image,
            self.image_dir + 'powerpoint.png',
            "powerpoint"
        )

    def is_in_brawler_selection(self, image: np.ndarray) -> bool:
        """Check if brawler selection menu is shown."""
        return self.is_template_in_region(
            image,
            self.image_dir + 'brawler_menu_task.png',
            "brawler_menu_task"
        )

    def is_in_offer_popup(self, image: np.ndarray) -> bool:
        """Check if offer popup is shown."""
        return self.is_template_in_region(
            image,
            self.image_dir + 'close_popup.png',
            "close_popup"
        )

    def is_in_lobby(self, image: np.ndarray) -> bool:
        """Check if lobby menu is shown."""
        return self.is_template_in_region(
            image,
            self.image_dir + 'lobby_menu.png',
            "lobby_menu"
        )

    def is_in_brawl_pass(self, image: np.ndarray) -> bool:
        """Check if brawl pass screen is shown."""
        return self.is_template_in_region(
            image,
            self.image_dir + 'brawl_pass_house.PNG',
            'brawl_pass_house'
        )

    def is_in_star_road(self, image: np.ndarray) -> bool:
        """Check if star road screen is shown."""
        return self.is_template_in_region(
            image,
            self.image_dir + "go_back_arrow.png",
            'go_back_arrow'
        )

    def is_in_star_drop(self, image: np.ndarray) -> bool:
        """Check if star drop screen is shown."""
        for image_filename in self.star_drop_images:
            if self.is_template_in_region(
                image,
                self.image_dir + image_filename,
                'star_drop'
            ):
                return True
        return False

    def is_in_play_store(self, image: np.ndarray) -> bool:
        """Check if play store screen is shown (red screen)."""
        rgb_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        red_count = count_hsv_pixels(rgb_image, (0, 0, 255), (0, 0, 255))
        return red_count > RED_PIXEL_THRESHOLD

    def get_state(self, image_bgr: np.ndarray, reader: EasyOCRReader) -> str:
        """
        Determine current game state.

        Args:
            image_bgr: Image in BGR format
            reader: OCR reader instance

        Returns:
            Game state string
        """
        if self.is_in_end_of_match(image_bgr, reader):
            return "end"

        if self.is_in_shop(image_bgr):
            return "shop"

        if self.is_in_offer_popup(image_bgr):
            return "popup"

        if self.is_in_lobby(image_bgr):
            return "lobby"

        if self.is_in_brawler_selection(image_bgr):
            return "brawler_selection"

        if self.is_in_play_store(image_bgr):
            return "play_store"

        if self.is_in_brawl_pass(image_bgr) or self.is_in_star_road(image_bgr):
            return "shop"

        if self.is_in_star_drop(image_bgr):
            return "star_drop"

        return "match"


# Global detector instance for backward compatibility
_detector: Optional[StateDetector] = None


def get_state(screenshot: Image.Image | np.ndarray) -> str:
    """
    Get the current game state from a screenshot.

    Args:
        screenshot: PIL Image or numpy array screenshot

    Returns:
        Game state string
    """
    global _detector

    if _detector is None:
        from utils.ocr import EasyOCRReader
        _detector = StateDetector()
        _detector._reader = EasyOCRReader()
    elif not hasattr(_detector, '_reader'):
        from utils.ocr import EasyOCRReader
        _detector._reader = EasyOCRReader()

    # Convert to numpy array if PIL Image
    if isinstance(screenshot, Image.Image):
        screenshot = np.array(screenshot)

    screenshot_bgr = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
    state = _detector.get_state(screenshot_bgr, _detector._reader)
    print(f"State: {state}")
    return state


# Legacy exports
find_game_result = lambda screenshot: len(
    StateDetector()._find_game_result(
        np.array(screenshot) if not isinstance(screenshot, np.ndarray) else screenshot,
        EasyOCRReader()
    )
) > 0


rework_game_result = rework_game_result
load_template = StateDetector()._load_template
is_template_in_region = StateDetector().is_template_in_region
region_data = load_toml_as_dict("./cfg/lobby_config.toml").get('template_matching', {})
crop_region = load_toml_as_dict("./cfg/lobby_config.toml").get('lobby', {}).get('trophy_observer', [])
path = "./state_finder/images_to_detect/"
