import ctypes
import time
from time import sleep
from typing import List, Union
import pyautogui

import cv2
import numpy as np
import win32gui
import win32con
import win32ui
import pyautogui
from PIL import Image
from ppadb.client import Client as AdbClient

orig_screen_width, orig_screen_height = 1920, 1080
full_width, full_height = pyautogui.size()
full_width_ratio = full_width / orig_screen_width
full_height_ratio = full_height / orig_screen_height

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
    def __init__(self, window_name: str, bot_plays_in_background: bool = False):
        self.bot_plays_in_background = bot_plays_in_background
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
                self.width_ratio = self.width / 1774
                self.height_ratio = self.height / 998
                self.joystick_x, self.joystick_y = 220*self.width_ratio, 870*self.height_ratio
                self.left_offset = 52*full_width_ratio
                self.top_offset = 35*full_height_ratio
                print(f"Window found: {window_name}")
                self.setup = True
            except Exception as e:
                raise ValueError(f"Error finding window '{window_name}': {e}")

        if self.bot_plays_in_background and self.setup:
            try:
                self.client = AdbClient(host="127.0.0.1", port=5037)
                self.device = self.client.devices()[0]
                print("ADB device connected")
                self.input_dev="/dev/input/event2"
                self.reset_all()
            except Exception as e:
                raise ConnectionError(f"Error connecting to ADB device: {e}")


    def reset_all(self):
        """Forces ALL 10 slots to lift. Clears 'Stuck ID' issues."""
        print("Resetting ALL slots...")
        cmds = []
        for i in range(10):  # Clear slots 0 to 9
            cmds.append(f"sendevent {self.input_dev} 3 47 {i}")  # ABS_MT_SLOT
            cmds.append(f"sendevent {self.input_dev} 3 57 -1")  # Lift (TRACKING_ID -1)

        cmds.append(f"sendevent {self.input_dev} 1 330 0")  # BTN_TOUCH UP
        cmds.append(f"sendevent {self.input_dev} 0 0 0")  # SYN_REPORT
        self._send_batch(cmds)
        print("resetted")
        self.are_we_moving = False
        self.active_fingers = 0

    def screenshot(self, array=False):
        hwnd_dc = win32gui.GetWindowDC(self.hwnd_child)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        save_bitmap = win32ui.CreateBitmap()
        save_bitmap.CreateCompatibleBitmap(mfc_dc, self.width, self.height)
        save_dc.SelectObject(save_bitmap)
        #save_dc.BitBlt((0, 0), (self.width, self.height), mfc_dc, (self.client_rect[0], self.client_rect[1]), win32con.SRCCOPY)
        result = ctypes.windll.user32.PrintWindow(self.hwnd_child, save_dc.GetSafeHdc(), 2)

        # If it fails, try with flag 0 (Default)
        if result == 0:
            ctypes.windll.user32.PrintWindow(self.hwnd_child, save_dc.GetSafeHdc(), 0)
            print("failed to capture with flag 2, used flag 0 instead")
        bmp_info = save_bitmap.GetInfo()
        bmp_str = save_bitmap.GetBitmapBits(True)
        img_array = np.frombuffer(bmp_str, np.uint8).reshape(bmp_info['bmHeight'], bmp_info['bmWidth'], 4)
        img_array = cv2.cvtColor(img_array, cv2.COLOR_BGRA2RGB)
        if array:
            return img_array
        # Clean up
        win32gui.DeleteObject(save_bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(self.hwnd_child, hwnd_dc)
        pil_image = Image.fromarray(img_array)
        return pil_image



    def _send_batch(self, commands):
        """
        Takes a list of command strings and executes them all at once.
        This is MUCH faster than sending them one by one.
        """
        # Join all commands with ";" to run them sequentially in one shell instance
        full_cmd = ";".join(commands)
        self.device.shell(full_cmd)

    def touch_down(self, slot_id, x, y):
        cmds = []
        cmds.append(f"sendevent {self.input_dev} 3 47 {slot_id}")  # Select Slot
        cmds.append(f"sendevent {self.input_dev} 3 57 {slot_id + 100}")  # Assign ID

        # Only send BTN_TOUCH DOWN if this is the FIRST finger
        if self.active_fingers == 0:
            cmds.append(f"sendevent {self.input_dev} 1 330 1")

        cmds.append(f"sendevent {self.input_dev} 3 53 {x}")  # Set X
        cmds.append(f"sendevent {self.input_dev} 3 54 {y}")  # Set Y

        cmds.append(f"sendevent {self.input_dev} 3 58 50")  # Pressure
        cmds.append(f"sendevent {self.input_dev} 3 48 5")
        cmds.append(f"sendevent {self.input_dev} 0 0 0")  # SYN_REPORT

        self.active_fingers += 1
        self._send_batch(cmds)

    def touch_move(self, slot_id, x, y):
        cmds = []
        cmds.append(f"sendevent {self.input_dev} 3 47 {slot_id}")  # Select Slot
        cmds.append(f"sendevent {self.input_dev} 3 53 {x}")  # Update X
        cmds.append(f"sendevent {self.input_dev} 3 54 {y}")  # Update Y
        cmds.append(f"sendevent {self.input_dev} 3 58 50")
        cmds.append(f"sendevent {self.input_dev} 0 0 0")  # SYN_REPORT

        self._send_batch(cmds)

    def touch_up(self, slot_id):
        cmds = []
        cmds.append(f"sendevent {self.input_dev} 3 47 {slot_id}")  # Select Slot
        cmds.append(f"sendevent {self.input_dev} 3 57 -1")  # Reset ID (-1)

        self.active_fingers -= 1

        # Only send BTN_TOUCH UP if this was the LAST finger
        if self.active_fingers <= 0:
            self.active_fingers = 0  # Safety reset
            cmds.append(f"sendevent {self.input_dev} 1 330 0")

        cmds.append(f"sendevent {self.input_dev} 0 0 0")  # SYN_REPORT

        self._send_batch(cmds)


    def keys_up(self, keys: List[str]):
        if not self.bot_plays_in_background:
            for key in keys:
                pyautogui.keyUp(key)
        else:
            if "".join(keys) == "wasd":
                self.touch_up(0)
                self.are_we_moving = False
                #self.reset_all()

    def keys_down(self, keys: List[str]):
        if not self.bot_plays_in_background:
            for key in keys:
                pyautogui.keyDown(key)
        else:
            if not self.are_we_moving:
                self.touch_down(0, self.joystick_x, self.joystick_y)
                self.are_we_moving = True

            delta_x, delta_y = 0, 0
            for key in keys:
                if key in directions_xy_deltas_dict:
                    dx, dy = directions_xy_deltas_dict[key]
                    delta_x += dx
                    delta_y += dy
            self.touch_move(0, self.joystick_x + delta_x, self.joystick_y + delta_y)

    def press_key(self, key, delay=0.05):
        if not self.bot_plays_in_background:
            pyautogui.press(key)
        else:
            if key not in key_coords_dict:
                raise ValueError("Trying to press an unregistered key")
            x, y = key_coords_dict[key]
            self.touch_down(1, x * self.width_ratio, y * self.height_ratio)
            sleep(delay)
            self.touch_up(1)


    def click(self, x: int, y: int, delay=0.05, already_include_ratio=True):
        if not self.bot_plays_in_background:
            if not already_include_ratio:
                x = x * full_width_ratio
                y = y * full_height_ratio
            pyautogui.click(x, y)
        else:
            self.touch_down(1,  x * self.width_ratio, y * self.height_ratio)
            print(f"Clicked at: {x * self.width_ratio}, {y * self.height_ratio}")
            print(f"Original coords: {x}, {y}")
            print(f"Ratios: {self.width_ratio}, {self.height_ratio}")
            print(f"Offsets: {self.left_offset}, {self.top_offset}")
            sleep(delay)
            self.touch_up(1)

    def swipe(self, start_x, start_y, end_x, end_y, duration=0.2):
        if not self.bot_plays_in_background:

            pyautogui.moveTo(start_x, start_y)
            pyautogui.mouseDown()
            pyautogui.moveTo(end_x, end_y, duration=duration)
            pyautogui.mouseUp()
        else:
            self.touch_down(1, start_x * self.width_ratio, start_y * self.height_ratio)
            time.sleep(0.05)
            self.touch_move(1, end_x * self.width_ratio, end_y * self.height_ratio)
            self.touch_up(1)



