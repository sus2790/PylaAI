import time
from queue import Empty

import numpy as np
import pyautogui
from utils import click
from utils import extract_text_and_positions, ScreenshotTaker, count_hsv_pixels, load_toml_as_dict

debug = load_toml_as_dict("cfg/general_config.toml")['super_debug'] == "yes"

orig_screen_width, orig_screen_height = 1920, 1080
width, height = pyautogui.size()
width_ratio = width / orig_screen_width
height_ratio = height / orig_screen_height
scale_factor = min(width_ratio, height_ratio)

class LobbyAutomation:

    def __init__(self, camera, frame_queue):
        self.Screenshot = ScreenshotTaker(camera)
        self.coords_cfg = load_toml_as_dict("./cfg/lobby_config.toml")
        self.frame_queue = frame_queue

    @staticmethod
    def check_for_idle(frame):
        screenshot = frame
        screenshot = screenshot.crop(
            (int(400 * width_ratio), int(380 * height_ratio), int(1500 * width_ratio), int(700 * height_ratio)))
        gray_pixels = count_hsv_pixels(screenshot, (0, 0, 66), (0, 0, 66))
        if debug: print("gray pixels (if > 1000 then bot will try to unidle) :", gray_pixels)
        if gray_pixels > 1000:
            click(535, 615)

    def select_brawler(self, brawler):
        x, y = self.coords_cfg['lobby']['brawlers_btn'][0] * width_ratio, self.coords_cfg['lobby']['brawlers_btn'][
            1] * height_ratio
        click(x, y)
        c = 0
        for i in range(50):
            try:
                screenshot = self.frame_queue.get(timeout=1)
            except Empty:
                continue

            screenshot = screenshot.resize((int(screenshot.width * 0.65), int(screenshot.height * 0.65)))
            screenshot = np.array(screenshot)
            if debug: print("extracting text on current screen...")
            results = extract_text_and_positions(screenshot)
            reworked_results = {}
            for key in results.keys():
                orig_key = key
                for symbol in [' ', '-', '.', "&"]:
                    key = key.replace(symbol, "")
                if key == "shey":
                    key = "shelly"
                if key == "larryslawrie":
                    key = "larrylawrie"
                reworked_results[key] = results[orig_key]
            if debug:
                print("All detected text while looking for brawler name:", reworked_results.keys())
                print()
            if brawler in reworked_results.keys():
                if debug: print("Found brawler ", brawler)
                x, y = reworked_results[brawler]['center']
                click(int(x * 1.5385), int(y * 1.5385))
                time.sleep(1)
                select_x, select_y = self.coords_cfg['lobby']['select_btn'][0] * width_ratio, \
                                     self.coords_cfg['lobby']['select_btn'][1] * height_ratio
                click(select_x, select_y)
                if debug: print("Selected brawler ", brawler)
                break
            if c == 0:
                pyautogui.moveTo(1700, 900)
                pyautogui.mouseDown()
                pyautogui.moveTo(1700, 850, duration=1)
                pyautogui.mouseUp()
                c += 1
                continue  # Some weird bug causing the first frame to not get any results so this redoes it
            pyautogui.moveTo(1700, 900)
            pyautogui.mouseDown()
            pyautogui.moveTo(1700, 650, duration=0.8)
            pyautogui.mouseUp()
            time.sleep(1)
