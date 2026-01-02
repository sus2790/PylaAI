from time import sleep
from typing import List, Union

import cv2
import numpy as np
import win32api
import win32con
import win32gui
import ctypes
import win32ui
from PIL import Image

import ctypes
import win32con
import win32gui

user32 = ctypes.windll.user32

_EXTENDED_VKS = {
    win32con.VK_RCONTROL, win32con.VK_RMENU,
    win32con.VK_INSERT, win32con.VK_DELETE,
    win32con.VK_HOME, win32con.VK_END,
    win32con.VK_PRIOR, win32con.VK_NEXT,
    win32con.VK_LEFT, win32con.VK_RIGHT,
    win32con.VK_UP, win32con.VK_DOWN,
    win32con.VK_DIVIDE, win32con.VK_NUMLOCK,
}

def vk_to_scancode(vk: int) -> int:
    return user32.MapVirtualKeyW(vk, 0)

def make_key_lparam(vk: int, *, keyup: bool, repeat: bool = False) -> int:
    sc = vk_to_scancode(vk)
    repeat_count = 1

    lp = repeat_count | (sc << 16)

    if vk in _EXTENDED_VKS:
        lp |= 1 << 24  # extended key

    if repeat:
        lp |= 1 << 30  # previous key state = 1 (auto-repeat style)

    if keyup:
        lp |= (1 << 30) | (1 << 31)  # prev=1, transition=1

    return lp


class WindowController:
    def __init__(self, window_name: str):
        if window_name == "Others":
            self.setup = False
        else:
            try:
                self.hwnd_main = win32gui.FindWindow(None, window_name)
                self.hwnd_child = win32gui.GetWindow(self.hwnd_main, win32con.GW_CHILD)
                self.current_screen = win32gui.GetWindowRect(self.hwnd_child)
                self.client_rect = win32gui.GetClientRect(self.hwnd_child)
                self.width = self.client_rect[2] - self.client_rect[0]
                self.height = self.client_rect[3] - self.client_rect[1]
                self._down = set()
                self.setup = True
                print(f"Window found: {window_name}")
            except Exception as e:
                print(f"Error finding window '{window_name}': {e}")
                self.setup = False

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

    def send_keys(self):
        while True:
            for key in self._down:
                win32gui.PostMessage(self.hwnd_child, win32con.WM_KEYDOWN, key,
                                     make_key_lparam(key, keyup=False, repeat=True))
            sleep(0.01)

    def key_down(self, vk_code: int):
        if vk_code not in self._down:
            win32gui.PostMessage(self.hwnd_child, win32con.WM_KEYDOWN, vk_code, make_key_lparam(vk_code, keyup=False, repeat=True))
            return

        self._down.add(vk_code)


    def key_up(self, vk_code: int):
        if vk_code not in self._down:
            return

        self._down.remove(vk_code)

    def keys_up(self, keys: List[str]):
        for key in keys:
            vk_code = ord(key.upper())
            self.key_up(vk_code)

    def keys_down(self, keys: List[str]):
        for key in keys:
            vk_code = ord(key.upper())
            self.key_down(vk_code)

    def send_keys_to_window(self, keys: List[str], duration: float = 0.1):
        for key in keys:
            vk_code = ord(key.upper())
            self.key_down(vk_code)
            sleep(duration)
            self.key_up(vk_code)

    def left_click_absolute(self, x_screen: int, y_screen: int):
        point = win32gui.ScreenToClient(self.hwnd_child, (x_screen, y_screen))
        l_param = win32api.MAKELONG(point[0], point[1])
        win32api.SendMessage(self.hwnd_child, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, l_param)
        sleep(0.05)
        win32api.SendMessage(self.hwnd_child, win32con.WM_LBUTTONUP, 0, l_param)

