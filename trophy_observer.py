"""Trophy tracking and match history management."""
import os
from typing import List, Dict, Tuple, Any, Optional

import requests
from difflib import SequenceMatcher
import numpy as np
from PIL import Image

from utils.config import update_toml_file, load_toml_as_dict, save_dict_as_toml, Config
from utils.api import get_api_client
from utils.ocr import EasyOCRReader
from utils.game_result import rework_game_result


class ConfigService:
    """Service for accessing configuration values."""
    config = Config()

    @classmethod
    def get_trophy_crop_region(cls) -> List[int]:
        return cls.config.get("./cfg/lobby_config.toml", "lobby", {}).get("trophy_observer", [])

    @classmethod
    def get_trophies_multiplier(cls) -> int:
        return cls.config.get("./cfg/general_config.toml", "trophies_multiplier", 1)

    @classmethod
    def get_api_base_url(cls) -> str:
        return cls.config.get("./cfg/general_config.toml", "api_base_url", "localhost")


class TrophyRanges:
    """Container for trophy range calculations."""

    TROPHY_LOSE_RANGES: List[Tuple[float, int]] = [
        (49, 0), (199, 1), (399, 2), (599, 3), (699, 4), (799, 5),
        (899, 6), (999, 7), (1099, 8), (1199, 11), (1299, 13),
        (1399, 16), (1499, 19), (1599, 22), (1699, 25), (1799, 28),
        (1899, 31), (1999, 34), (float("inf"), 50)
    ]

    TROPHY_WIN_RANGES: List[Tuple[float, int]] = [
        (1099, 8), (1199, 7), (1299, 6), (1399, 5), (1499, 4),
        (1599, 3), (1699, 2), (float("inf"), 1)
    ]

    @classmethod
    def calc_loss(cls, trophies: int) -> int:
        """Calculate trophies to lose."""
        for max_trophies, loss in cls.TROPHY_LOSE_RANGES:
            if float(trophies) <= float(max_trophies):
                return loss
        return 50

    @classmethod
    def calc_gain(cls, trophies: int, multiplier: int, win_streak: int) -> int:
        """Calculate trophies to gain."""
        for max_trophies, gain in cls.TROPHY_WIN_RANGES:
            if float(trophies) <= float(max_trophies):
                streak_bonus = min(win_streak - 1, 5)
                return gain * multiplier + streak_bonus
        return 24


class TrophyObserver:
    """Tracks trophies, match history, and win streaks."""

    HISTORY_FILE = "./cfg/match_history.toml"
    MAX_WIN_STREAK_GAIN = 5
    API_SEND_INTERVAL = 4
    OCR_CONFIDENCE_THRESHOLD = 0.55

    def __init__(
        self,
        brawler_list: List[str],
        ocr_reader: Optional[EasyOCRReader] = None
    ) -> None:
        """
        Initialize trophy observer.

        Args:
            brawler_list: List of brawler names to track
            ocr_reader: Optional OCR reader instance
        """
        self.current_trophies: Optional[int] = None
        self.current_wins: Optional[int] = None
        self.win_streak: int = 0
        self.match_counter: int = 0

        self.match_history = self._load_history(brawler_list)
        self.match_history['total'] = {"defeat": 0, "victory": 0, "draw": 0}

        self.sent_match_history: Dict[str, Dict[str, int]] = {
            brawler: {
                "defeat": self.match_history[brawler]["defeat"],
                "victory": self.match_history[brawler]["victory"],
                "draw": 0
            }
            for brawler in brawler_list
        }

        self.crop_region = ConfigService.get_trophy_crop_region()
        self.trophies_multiplier = ConfigService.get_trophies_multiplier()

        # OCR reader - use dependency injection or create default
        self.reader = ocr_reader or EasyOCRReader()

    def _load_history(self, brawler_list: List[str]) -> Dict[str, Dict[str, int]]:
        """Load match history from file."""
        if os.path.exists(self.HISTORY_FILE):
            loaded_data = load_toml_as_dict(self.HISTORY_FILE)
        else:
            loaded_data = {}

        # Ensure each brawler has an entry
        for brawler in brawler_list:
            if brawler not in loaded_data:
                loaded_data[brawler] = {"defeat": 0, "victory": 0, "draw": 0}

        if "total" not in loaded_data:
            loaded_data["total"] = {"defeat": 0, "victory": 0, "draw": 0}

        return loaded_data

    def save_history(self) -> None:
        """Save match history to file."""
        save_dict_as_toml(self.match_history, self.HISTORY_FILE)

    def _rework_game_result_from_ocr(self, res_string: str) -> Tuple[str, float]:
        """
        Refine OCR result using fuzzy matching.

        Args:
            res_string: Raw OCR result

        Returns:
            Tuple of (result_string, confidence_ratio)
        """
        res_string = res_string.lower()
        if res_string in ["victory", "defeat", "draw"]:
            return res_string, 1.0

        ratios: Dict[str, float] = {
            "victory": SequenceMatcher(None, res_string, 'victory').ratio(),
            "defeat": SequenceMatcher(None, res_string, 'defeat').ratio(),
            "draw": SequenceMatcher(None, res_string, "draw").ratio()
        }
        highest_ratio_string = max(ratios, key=ratios.get)
        return highest_ratio_string, ratios[highest_ratio_string]

    def add_trophies(self, game_result: str, current_brawler: str) -> bool:
        """
        Process game result and update trophy count.

        Args:
            game_result: "victory", "defeat", or "draw"
            current_brawler: Name of brawler being played

        Returns:
            True if successful
        """
        # Ensure entry exists
        if current_brawler not in self.sent_match_history:
            self.sent_match_history[current_brawler] = {"defeat": 0, "victory": 0, "draw": 0}
        if current_brawler not in self.match_history:
            self.match_history[current_brawler] = {"defeat": 0, "victory": 0, "draw": 0}

        old = self.current_trophies

        if game_result == "victory":
            self.win_streak += 1
            if self.current_trophies is not None:
                self.current_trophies += TrophyRanges.calc_gain(
                    self.current_trophies,
                    self.trophies_multiplier,
                    self.win_streak
                )
        elif game_result == "defeat":
            self.win_streak = 0
            if self.current_trophies is not None:
                self.current_trophies -= TrophyRanges.calc_loss(self.current_trophies)
        elif game_result == "draw":
            print("Nothing changed. Draw detected")
        else:
            print("Catastrophic failure: unknown result")
            return False

        print(f"Trophies: {old} -> {self.current_trophies}")
        print("Current wins:", self.current_wins)

        # Update match history
        if game_result in self.match_history[current_brawler]:
            self.match_history[current_brawler][game_result] += 1
        if game_result in self.match_history["total"]:
            self.match_history["total"][game_result] += 1

        # Send to API periodically
        self.match_counter += 1
        if self.match_counter % self.API_SEND_INTERVAL == 0:
            self._send_results_to_api()

        self.save_history()
        return True

    def add_win(self, game_result: str) -> None:
        """Update win count if result is victory."""
        if game_result == "victory" and self.current_wins is not None:
            self.current_wins += 1

    def find_game_result(
        self,
        screenshot: Image.Image,
        current_brawler: str,
        game_result: Optional[str] = None
    ) -> bool:
        """
        Find game result from screenshot or use provided result.

        Args:
            screenshot: Screenshot to analyze
            current_brawler: Name of brawler being played
            game_result: Optional pre-determined result

        Returns:
            True if result was found and processed
        """
        if game_result:
            # Use provided result
            result = rework_game_result(game_result)
            if result:
                self.add_trophies(result, current_brawler)
                self.add_win(result)
                return True
            return False

        # Extract result from screenshot
        screenshot = screenshot.crop(self.crop_region)
        array_screenshot = np.array(screenshot)
        result = self.reader.readtext(array_screenshot)

        if len(result) == 0:
            return False

        _, text, conf = result[0]
        game_result, ratio = self._rework_game_result_from_ocr(text)

        if ratio < self.OCR_CONFIDENCE_THRESHOLD:
            if ratio > 0:
                print(f"Couldn't find game result: {game_result}, confidence: {ratio:.2f}")
            return False

        self.add_trophies(game_result, current_brawler)
        self.add_win(game_result)
        return True

    def change_trophies(self, new: int) -> None:
        """Manually set trophy count."""
        print(f"Trophies changed from {self.current_trophies} to {new}")
        self.current_trophies = new

    def _send_results_to_api(self) -> None:
        """Send match statistics to the API."""
        api_base_url = ConfigService.get_api_base_url()

        if api_base_url == "localhost":
            return

        # Calculate differences
        data = {}
        for brawler, stats in self.match_history.items():
            if brawler != "total":
                if brawler not in self.sent_match_history:
                    self.sent_match_history[brawler] = {"defeat": 0, "victory": 0, "draw": 0}

                new_stats = {
                    "wins": stats["victory"] - self.sent_match_history[brawler]["victory"],
                    "defeats": stats["defeat"] - self.sent_match_history[brawler]["defeat"],
                    "draws": 0
                }

                if any(new_stats.values()):
                    data[brawler] = new_stats

        if not data:
            return

        # Send POST request
        try:
            response = requests.post(f'https://{api_base_url}/api/brawlers', json=data)
            if response.status_code == 200:
                print("Results successfully sent to API")
                # Update sent history
                for brawler, stats in self.match_history.items():
                    if brawler != "total":
                        self.sent_match_history[brawler]["victory"] = stats["victory"]
                        self.sent_match_history[brawler]["defeat"] = stats["defeat"]
                        self.sent_match_history[brawler]["draw"] = 0
            else:
                print(f"Failed to send results to API. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error sending results to API: {e}")
