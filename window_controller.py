import atexit
import ctypes
import math
import time
import cv2
import numpy as np
import win32gui
import win32con
import win32ui
import pyautogui
from PIL import Image
from typing import List

# New libraries
import scrcpy
from adbutils import adb

# --- Configuration ---
orig_screen_width, orig_screen_height = 1920, 1080
brawl_stars_width, brawl_stars_height = 1774, 998

key_coords_dict = {
    "H": (1400, 970),
    "G": (1615, 970),
    "M": (1700, 810),
    "Q": (1740, 1000),
    "E": (1540, 890)
}

directions_xy_deltas_dict = {
    "w": (0, -100),
    "a": (-100, 0),
    "s": (0, 100),
    "d": (100, 0),
}

def find_window_by_substring(substring):
    hwnd_list = []
    def callback(hwnd, extra):
        title = win32gui.GetWindowText(hwnd)
        if substring.lower() in title.lower() and win32gui.IsWindowVisible(hwnd):
            hwnd_list.append(hwnd)
    win32gui.EnumWindows(callback, None)
    return hwnd_list[0] if hwnd_list else None

class WindowController:
    def __init__(self, window_name: str, camera, bot_plays_in_background: bool = False):
        self.bot_plays_in_background = bot_plays_in_background
        self.camera = camera
        if window_name == "Others":
            self.bot_plays_in_background = False
            self.setup = False
        else:
            try:
                self.hwnd_main = find_window_by_substring(window_name)
                self.hwnd_child = win32gui.GetWindow(self.hwnd_main, win32con.GW_CHILD)
                self.current_screen = win32gui.GetWindowRect(self.hwnd_child)
                self.client_rect = win32gui.GetClientRect(self.hwnd_child)
                self.width = self.client_rect[2] - self.client_rect[0]
                self.height = self.client_rect[3] - self.client_rect[1]
                self.width_ratio = self.width / brawl_stars_width
                self.height_ratio = self.height / brawl_stars_height
                self.joystick_x, self.joystick_y = 220 * self.width_ratio, 870 * self.height_ratio
                print(f"Window found: {window_name}")
                self.setup = True
            except Exception as e:
                raise ValueError(f"Error finding window '{window_name}': {e}")
        # --- 2. ADB & Scrcpy Connection ---
        print("Connecting to ADB...")
        try:
            # Connect to device (adbutils automatically handles port detection mostly)
            # If you specifically need the BlueStacks port logic, we can re-add it,
            # but adbutils is usually smarter at finding the open device.
            device_list = adb.device_list()
            if not device_list:
                # Try connecting to common ports if empty
                for port in [5555, 5037, 16384, 5635]:
                    try:
                         adb.connect(f"127.0.0.1:{port}")
                    except:
                         pass
                device_list = adb.device_list()

            if not device_list:
                 raise ConnectionError("No ADB devices found.")

            self.device = device_list[0]
            print(f"Connected to device: {self.device.serial}")

            # Initialize Scrcpy
            # max_width=0 disables video stream (saves performance since you use Win32 for video)
            self.scrcpy_client = scrcpy.Client(device=self.device, max_width=0)

            # Start the client in a separate thread
            self.scrcpy_client.start(threaded=True)
            atexit.register(self.close)
            print("Scrcpy client started successfully.")

        except Exception as e:
            raise ConnectionError(f"Failed to initialize Scrcpy: {e}")
        self.are_we_moving = False
        self.PID_JOYSTICK = 1  # ID for WASD movement
        self.PID_ATTACK = 2  # ID for clicks/attacks



    def game_screenshot(self, array=False):
        hwnd_dc = win32gui.GetWindowDC(self.hwnd_child)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        save_bitmap = win32ui.CreateBitmap()
        save_bitmap.CreateCompatibleBitmap(mfc_dc, self.width, self.height)
        save_dc.SelectObject(save_bitmap)
        # save_dc.BitBlt((0, 0), (self.width, self.height), mfc_dc, (self.client_rect[0], self.client_rect[1]), win32con.SRCCOPY)
        result = ctypes.windll.user32.PrintWindow(self.hwnd_child, save_dc.GetSafeHdc(), 2)

        # If it fails, try with flag 0 (Default)
        if result == 0:
            ctypes.windll.user32.PrintWindow(self.hwnd_child, save_dc.GetSafeHdc(), 0)
        bmp_info = save_bitmap.GetInfo()
        bmp_str = save_bitmap.GetBitmapBits(True)
        img_array = np.frombuffer(bmp_str, np.uint8).reshape(bmp_info['bmHeight'], bmp_info['bmWidth'], 4)
        img_array = cv2.cvtColor(img_array, cv2.COLOR_BGRA2RGB)

        win32gui.DeleteObject(save_bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(self.hwnd_child, hwnd_dc)

        if array:
            return img_array

        return Image.fromarray(img_array)

    def full_screenshot(self):
        try:
            image = self.camera.grab()
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            image = None
        if image is not None:
            image = Image.fromarray(image)
        c = 0
        while image is None and c < 5:
            try:
                image = self.camera.grab()
                if image is not None:
                    image = Image.fromarray(image)
            except Exception as e:
                print(f"Error capturing screenshot: {e}")
                image = None
                c += 1
                time.sleep(0.1)
        if image is None:
            print("Using pyautogui as backup for screenshotting as the main failed")
            image = pyautogui.screenshot()
        return image

    def screenshot(self):
        if not self.setup or not self.bot_plays_in_background:
            return self.full_screenshot()
        return self.game_screenshot()

    def touch_down(self, x, y, pointer_id=0):
        # We explicitly pass the pointer_id
        self.scrcpy_client.control.touch(int(x), int(y), scrcpy.ACTION_DOWN, pointer_id)

    def touch_move(self, x, y, pointer_id=0):
        self.scrcpy_client.control.touch(int(x), int(y), scrcpy.ACTION_MOVE, pointer_id)

    def touch_up(self, x, y, pointer_id=0):
        self.scrcpy_client.control.touch(int(x), int(y), scrcpy.ACTION_UP, pointer_id)

    def keys_up(self, keys: List[str]):
        if "".join(keys) == "wasd":
            if self.are_we_moving:
                # Use PID_JOYSTICK so we don't lift the attack finger
                self.touch_up(self.joystick_x, self.joystick_y, pointer_id=self.PID_JOYSTICK)
                self.are_we_moving = False

    def keys_down(self, keys: List[str]):
        # Use PID_JOYSTICK for all movement actions
        if not self.are_we_moving:
            self.touch_down(self.joystick_x, self.joystick_y, pointer_id=self.PID_JOYSTICK)
            self.are_we_moving = True

        delta_x, delta_y = 0, 0
        for key in keys:
            if key in directions_xy_deltas_dict:
                dx, dy = directions_xy_deltas_dict[key]
                delta_x += dx
                delta_y += dy

        self.touch_move(self.joystick_x + delta_x, self.joystick_y + delta_y, pointer_id=self.PID_JOYSTICK)

    def click(self, x: int, y: int, delay=0.05, already_include_ratio=True):
        if not already_include_ratio:
            x = x * self.width_ratio
            y = y * self.height_ratio
        # Use PID_ATTACK for clicks so we don't interrupt movement
        self.touch_down(x, y, pointer_id=self.PID_ATTACK)
        time.sleep(delay)
        self.touch_up(x, y, pointer_id=self.PID_ATTACK)

    def press_key(self, key, delay=0.05):
        if key not in key_coords_dict:
            return
        x, y = key_coords_dict[key]
        target_x = x * self.width_ratio
        target_y = y * self.height_ratio
        self.click(target_x, target_y, delay)

    def swipe(self, start_x, start_y, end_x, end_y, duration=0.2):
        # FIX for TypeError: ControlSender.swipe()
        # We calculate the step length and delay to match your requested duration

        # 1. Calculate distance
        dist_x = end_x - start_x
        dist_y = end_y - start_y
        distance = math.sqrt(dist_x ** 2 + dist_y ** 2)

        if distance == 0:
            return

        # 2. Set a reasonable step size (in pixels). Larger = faster/choppier.
        step_len = 25

        # 3. Calculate how many steps we need
        steps = distance / step_len

        # 4. Calculate delay per step to achieve total duration
        # duration = steps * delay  =>  delay = duration / steps
        if steps > 0:
            step_delay = duration / steps
        else:
            step_delay = 0.005  # Default safety

        # 5. Call scrcpy swipe with the correct arguments
        self.scrcpy_client.control.swipe(
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            # move_step_length=int(step_len),
            # move_steps_delay=step_delay
        )

    def close(self):
        if hasattr(self, 'scrcpy_client'):
            self.scrcpy_client.stop()