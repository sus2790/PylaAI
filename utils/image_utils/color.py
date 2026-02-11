"""Image utilities for color detection and template matching."""
from typing import Tuple, Optional
import cv2
import numpy as np
from PIL import Image


def count_hsv_pixels(
    pil_image: Image.Image,
    low_hsv: Tuple[int, int, int],
    high_hsv: Tuple[int, int, int]
) -> int:
    """
    Count pixels in an image within a HSV color range.

    Args:
        pil_image: PIL Image in RGB mode
        low_hsv: Lower bound (H, S, V)
        high_hsv: Upper bound (H, S, V)

    Returns:
        Number of pixels matching the HSV range
    """
    opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    hsv_image = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv_image, np.array(low_hsv), np.array(high_hsv))
    pixel_count = np.count_nonzero(mask)
    return pixel_count


def find_template_center(
    main_img: Image.Image,
    template,
    threshold: float = 0.8
) -> Optional[Tuple[int, int] | bool]:
    """
    Find the center of a template in the main image.

    Args:
        main_img: Main PIL image to search in
        template: Template image to find
        threshold: Matching threshold (0-1)

    Returns:
        (center_x, center_y) if found, False otherwise
    """
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
