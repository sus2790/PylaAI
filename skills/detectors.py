"""Skill readiness detection using pixel counting."""
from typing import Optional
from PIL import Image
from utils.image_utils import count_hsv_pixels


def check_if_hypercharge_ready(
    frame: Image.Image,
    window_controller: Any,
    minimum_pixels: int = 5000
) -> bool:
    """
    Check if hypercharge ability is ready by detecting purple pixels.

    Args:
        frame: Screenshot frame
        window_controller: WindowController for screen ratios
        minimum_pixels: Minimum purple pixel threshold

    Returns:
        True if hypercharge is ready
    """
    screenshot = frame.crop((
        1350 * window_controller.width_ratio,
        940 * window_controller.height_ratio,
        1450 * window_controller.width_ratio,
        1050 * window_controller.height_ratio
    ))
    purple_pixels = count_hsv_pixels(screenshot, (137, 158, 159), (179, 255, 255))
    return purple_pixels > minimum_pixels


def check_if_gadget_ready(
    frame: Image.Image,
    window_controller: Any,
    minimum_pixels: int = 5000
) -> bool:
    """
    Check if gadget ability is ready by detecting green pixels.

    Args:
        frame: Screenshot frame
        window_controller: WindowController for screen ratios
        minimum_pixels: Minimum green pixel threshold

    Returns:
        True if gadget is ready
    """
    screenshot = frame.crop((
        1580 * window_controller.width_ratio,
        930 * window_controller.height_ratio,
        1700 * window_controller.width_ratio,
        1050 * window_controller.height_ratio
    ))
    green_pixels = count_hsv_pixels(screenshot, (57, 219, 165), (62, 255, 255))
    return green_pixels > minimum_pixels


def check_if_super_ready(
    frame: Image.Image,
    window_controller: Any,
    minimum_pixels: int = 5000
) -> bool:
    """
    Check if super ability is ready by detecting yellow pixels.

    Args:
        frame: Screenshot frame
        window_controller: WindowController for screen ratios
        minimum_pixels: Minimum yellow pixel threshold

    Returns:
        True if super is ready
    """
    screenshot = frame.crop((
        1460 * window_controller.width_ratio,
        830 * window_controller.height_ratio,
        1560 * window_controller.width_ratio,
        930 * window_controller.height_ratio
    ))
    yellow_pixels = count_hsv_pixels(screenshot, (19, 190, 249), (24, 240, 255))
    return yellow_pixels > minimum_pixels
