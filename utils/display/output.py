"""Display utilities for colored console output and DPI scaling."""
import ctypes


def cprint(text: str, hex_color: str) -> None:
    """
    Print colored text to the console.

    Args:
        text: Text to print
        hex_color: Hex color code (e.g., "#FF0000")
    """
    try:
        hex_color = hex_color.lstrip("#")
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        print(f"\033[38;2;{r};{g};{b}m{text}\033[0m")
    except Exception:
        print(text)


def get_dpi_scale() -> int:
    """Get the system DPI scale factor."""
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    return int(user32.GetDpiForSystem())


class DisplayScaleManager:
    """Manager for screen scaling calculations."""

    DEFAULT_WIDTH = 1920
    DEFAULT_HEIGHT = 1080

    def __init__(self, default_width: int = DEFAULT_WIDTH, default_height: int = DEFAULT_HEIGHT) -> None:
        self.default_width = default_width
        self.default_height = default_height
        self.dpi_scale = get_dpi_scale()

    def get_scale_factor(self) -> float:
        """
        Calculate the scale factor based on screen size and DPI.

        Returns:
            Scale factor to apply to coordinates
        """
        import pyautogui
        width, height = pyautogui.size()
        width_ratio = width / self.default_width
        height_ratio = height / self.default_height
        scale_factor = min(width_ratio, height_ratio)
        scale_factor *= 96 / self.dpi_scale
        return scale_factor

    def scale_coordinate(self, x: int, y: int) -> tuple[float, float]:
        """
        Scale a coordinate pair.

        Args:
            x: Original X coordinate
            y: Original Y coordinate

        Returns:
            Tuple of (scaled_x, scaled_y)
        """
        scale = self.get_scale_factor()
        return x * scale, y * scale
