"""
Legacy utils module - maintains backward compatibility.

Imports are re-exported from new modular structure.

Note: This file is deprecated. Please import directly from specific modules:
- utils.ocr for OCR utilities
- utils.image_utils for image processing
- utils.config for configuration loading
- utils.api for API client and brawler utilities
- utils.network for version checking and model updates
- utils.notify for Discord notifications
- utils.display for colored output and DPI scaling
"""

# OCR
try:
    from utils.ocr import EasyOCRReader, extract_text_and_positions
except ImportError:
    # Fallback to old implementation for backward compatibility
    import easyocr

    class DefaultEasyOCR:
        def __init__(self):
            self.reader = easyocr.Reader(['en'])

        def readtext(self, image_input):
            return self.reader.readtext(image_input)

    EasyOCRReader = DefaultEasyOCR
    reader = DefaultEasyOCR()

    def extract_text_and_positions(reader, image_path):
        results = reader.readtext(image_path)
        text_details = {}
        for (bbox, text, prob) in results:
            top_left, top_right, bottom_right, bottom_left = bbox
            cx = (top_left[0] + top_right[0] + bottom_right[0] + bottom_left[0]) / 4
            cy = (top_left[1] + top_right[1] + bottom_right[1] + bottom_left[1]) / 4
            center = (cx, cy)
            text_details[text.lower()] = {
                'top_left': top_left,
                'top_right': top_right,
                'bottom_right': bottom_right,
                'bottom_left': bottom_left,
                'center': center
            }
        return text_details


# Configuration
import os
import toml


def load_toml_as_dict(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return toml.load(f)
    return {}


def save_dict_as_toml(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        toml.dump(data, f)


def update_toml_file(path, new_data):
    with open(path, 'w', encoding='utf-8') as file:
        toml.dump(new_data, file)


# Image utilities
import cv2
import numpy as np
from PIL import Image


def count_hsv_pixels(pil_image, low_hsv, high_hsv):
    opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    hsv_image = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv_image, np.array(low_hsv), np.array(high_hsv))
    pixel_count = np.count_nonzero(mask)
    return pixel_count


def find_template_center(main_img, template, threshold=0.8):
    main_image_cv = cv2.cvtColor(np.array(main_img), cv2.COLOR_RGB2GRAY)
    template_arr = np.array(template)
    if len(template_arr.shape) == 3 and template_arr.shape[2] == 3:
        template_cv = cv2.cvtColor(template_arr, cv2.COLOR_BGR2GRAY)
    else:
        template_cv = template_arr
    w, h = template_cv.shape[::-1]

    result = cv2.matchTemplate(main_image_cv, template_cv, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        center_x = max_loc[0] + w // 2
        center_y = max_loc[1] + h // 2
        return center_x, center_y
    return False


# Game result utility
from difflib import SequenceMatcher


def rework_game_result(res_string):
    res_string = res_string.lower()
    if res_string in ["victory", "defeat", "draw"]:
        return res_string

    ratios = {
        "victory": SequenceMatcher(None, res_string, 'victory').ratio(),
        "defeat": SequenceMatcher(None, res_string, 'defeat').ratio(),
        "draw": SequenceMatcher(None, res_string, "draw").ratio()
    }
    highest_ratio_string = max(ratios, key=ratios.get)

    return highest_ratio_string


# Display
import ctypes


def cprint(text, hex_color):
    try:
        hex_color = hex_color.lstrip("#")
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        print(f"\033[38;2;{r};{g};{b}m{text}\033[0m")
    except Exception:
        print(text)


def get_dpi_scale():
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    return int(user32.GetDpiForSystem())


# Legacy globals
api_base_url = "localhost"
brawlers_info_file_path = "cfg/brawlers_info.json"
TILE_SIZE = 60
