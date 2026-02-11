"""OCR utilities for text extraction from images."""
from typing import Dict, List, Tuple, Any
import easyocr


TextDetails = Dict[str, Dict[str, Tuple[float, float] | Tuple[Tuple[int, int], ...]]]


class EasyOCRReader:
    """Wrapper around EasyOCR for consistent text extraction."""

    def __init__(self, language: str = 'en') -> None:
        self._reader = easyocr.Reader([language])

    def readtext(self, image_input) -> List[Tuple[Any, str, float]]:
        """Read text from an image input."""
        return self._reader.readtext(image_input)


def extract_text_and_positions(
    reader: EasyOCRReader,
    image_input
) -> TextDetails:
    """
    Extract text and their bounding box positions from an image.

    Args:
        reader: EasyOCRReader instance
        image_input: Image path or image array

    Returns:
        Dictionary mapping text (lowercase) to their bbox details
    """
    results = reader.readtext(image_input)
    text_details = {}

    for bbox, text, prob in results:
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
