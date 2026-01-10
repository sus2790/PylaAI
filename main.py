import threading
from queue import Queue, Full, Empty
import asyncio
import ctypes
import threading
import time
from queue import Queue, Full, Empty

import bettercam
import pyautogui
import pygetwindow

from gui.hub import Hub
from gui.login import login
from gui.main import App
from gui.select_brawler import SelectBrawler
from lobby_automation import LobbyAutomation
from play import Play
from stage_manager import StageManager, load_image
from state_finder.main import get_state
import state_finder.main as state_finder_main
from time_management import TimeManagement
from utils import ScreenshotTaker, load_toml_as_dict, current_wall_model_is_latest, api_base_url, find_template_center
from utils import get_brawler_list, update_missing_brawlers_info, update_icons, check_version, async_notify_user, \
    update_wall_model_classes, get_latest_wall_model_file, get_latest_version, cprint
from window_controller import WindowController

pyla_version = load_toml_as_dict("./cfg/general_config.toml")['pyla_version']

frame_lock = threading.Lock()
frame_available = threading.Event()

frame_queue = Queue(maxsize=1)
debug = load_toml_as_dict("cfg/general_config.toml")['super_debug'] == "yes"


def capture_loop(Screenshot):
    while True:
        try:
            image = Screenshot.take()
            frame_queue.put(image, block=False)
        except Full:
            try:
                frame_queue.get_nowait()
            except Empty:
                pass
            frame_queue.put(image, block=False)
        except Exception as e:
            print("Error in capture loop:", e)




def pyla_main(data):
    current_emulator = load_toml_as_dict("cfg/general_config.toml")["current_emulator"]

    class Main:

        def __init__(self):
            self.does_bot_player_in_background = load_toml_as_dict("cfg/general_config.toml")["bot_plays_in_background"] == "yes"
            chosen_monitor = int(load_toml_as_dict("./cfg/general_config.toml")['monitor'])
            camera = bettercam.create(device_idx=chosen_monitor)
            window_controller = WindowController(current_emulator, self.does_bot_player_in_background)
            if not window_controller.setup:
                self.does_bot_player_in_background = False
                window_controller.bot_plays_in_background = False
            Screenshot = ScreenshotTaker(camera, window_controller, self.does_bot_player_in_background)
            capture_thread = threading.Thread(target=capture_loop, args=(Screenshot,),daemon=True)
            capture_thread.start()
            self.specific_brawlers_data = []
            self.Play = Play(*self.load_models(), window_controller)
            self.Time_management = TimeManagement()
            self.lobby_automator = LobbyAutomation(frame_queue, window_controller)
            self.Stage_manager = StageManager(data, frame_queue, self.lobby_automator, window_controller)
            self.states_requiring_data = ["play_store", "brawl_stars_crashed", "lobby"]
            brawler_menu_btn_coords = find_template_center(frame_queue.get(), load_image(r'state_finder/images_to_detect/brawler_menu_btn.png'))
            self.lobby_automator.coords_cfg['lobby']['brawlers_btn'] = brawler_menu_btn_coords
            if data[0]['automatically_pick']:
                if debug: print("Picking brawler automatically")
                self.lobby_automator.select_brawler(data[0]['brawler'])
            self.Play.current_brawler = data[0]['brawler']
            self.no_detections_action_threshold = 60 * 8
            self.initialize_stage_manager()
            self.state = None
            try:
                self.max_ips = int(load_toml_as_dict("cfg/general_config.toml")['max_ips'])
            except ValueError:
                self.max_ips = None
            self.run_for_minutes = int(load_toml_as_dict("cfg/general_config.toml")['run_for_minutes'])
            self.start_time = time.time()
            self.time_to_stop = False
            self.in_cooldown = False
            self.cooldown_start_time = 0
            self.cooldown_duration = 3 * 60
            state_finder_main.check_brawl_stars_crashed = load_toml_as_dict("cfg/general_config.toml")['check_if_brawl_stars_crashed'] == "yes" and not self.does_bot_player_in_background
            state_finder_main.bot_plays_in_background = self.does_bot_player_in_background
        def initialize_stage_manager(self):
            self.Stage_manager.Trophy_observer.win_streak = data[0]['win_streak']
            self.Stage_manager.Trophy_observer.current_trophies = data[0]['trophies']
            self.Stage_manager.Trophy_observer.current_wins = data[0]['wins'] if data[0]['wins'] != "" else 0

        @staticmethod
        def load_models():
            folder_path = "./models/"
            model_names = ['mainInGameModel.onnx', 'brawlersInGame.onnx', 'startingScreenModel.onnx',
                           'tileDetector.onnx']
            loaded_models = []

            for name in model_names:
                loaded_models.append(folder_path + name)
            return loaded_models

        @staticmethod
        def restart_brawl_stars():
            loop = asyncio.new_event_loop()
            screenshot = frame_queue.get()
            loop.run_until_complete(async_notify_user("bot_is_stuck", screenshot))
            loop.close()
            print("Bot got stuck. User notified. Pause until closed.")
            time.sleep(99 * 999)

        def manage_time_tasks(self, frame):
            if self.Time_management.state_check():
                state = get_state(frame)
                self.state = state
                frame_data = frame if state in self.states_requiring_data else None
                self.Stage_manager.do_state(state, frame_data)

            if self.Time_management.no_detections_check():
                frame_data = self.Play.time_since_detections
                print(self.Play.time_since_detections)
                for key, value in frame_data.items():
                    if time.time() - value > self.no_detections_action_threshold:
                        self.restart_brawl_stars()

            if self.Time_management.idle_check():
                print("check for idle!")
                self.lobby_automator.check_for_idle(frame)

        def main(self): #this is for timer to stop after time
            s_time = time.time()
            c = 0
            while True:

                if self.run_for_minutes > 0 and not self.in_cooldown:
                    elapsed_time = (time.time() - self.start_time) / 60
                    if elapsed_time >= self.run_for_minutes:
                        cprint(f"timer is done, {self.run_for_minutes} is over. continuing for 3 minutes if in game", "#AAE5A4")
                        self.in_cooldown = True # tries to finish game if in game
                        self.cooldown_start_time = time.time()
                        self.Stage_manager.states['lobby'] = lambda data: 0

                if self.in_cooldown:
                    if time.time() - self.cooldown_start_time >= self.cooldown_duration:
                        cprint("stopping bot fully", "#AAE5A4")
                        break

                if abs(s_time - time.time()) > 1:
                    print(c, "IPS")
                    s_time = time.time()
                    c = 0

                try:
                    frame = frame_queue.get(timeout=1)
                except Empty:
                    continue

                self.manage_time_tasks(frame)  # Replace with your actual method

                if self.Time_management.specific_brawlers_check():
                    self.Play.get_specific_data(frame)
                    self.Time_management.states['game_start'] = time.time()

                brawler = self.Stage_manager.brawlers_pick_data[0]['brawler']
                self.Play.main(frame, brawler)
                c += 1

                # Enforce max IPS if set
                if self.max_ips:
                    time_per_frame = 1 / self.max_ips
                    elapsed_time = time.time() - s_time
                    if elapsed_time < time_per_frame:
                        time.sleep(time_per_frame - elapsed_time)


    if current_emulator != "Others":
        try:
            window = pygetwindow.getWindowsWithTitle(current_emulator)[0]

            if window.isMinimized:
                window.restore()

            try:
                window.activate()
            except:
                pass

            window.maximize()
        except:
            print(
                "Couldn't find chosen emulator window. Please report this to AngelFire.")

    main = Main()
    main.main()
    return width, height


width, height = pyautogui.size()
if width > 1920:
    print("⚠️Warning:⚠️ Screen resolution is higher 1920x1080. This can cause major issues. Please lower your resolution to 1920x1080 (or lower of 16:9 ratio) in computer settings (Display Settings), NOT LDPlayer settings. ⚠️⚠️⚠️")
    time.sleep(5)

orig_screen_width, orig_screen_height = 1920, 1080
width_ratio = width / orig_screen_width
height_ratio = height / orig_screen_height

all_brawlers = get_brawler_list()
if api_base_url != "localhost":
    update_missing_brawlers_info(all_brawlers)
    update_icons()
    check_version()
    update_wall_model_classes()
    if not current_wall_model_is_latest():
        print(
            "New Wall detection model found, downloading... (this might take a few minutes depending on your internet speed)")
        get_latest_wall_model_file()

# check if the zoom is 100%
user32 = ctypes.windll.user32
user32.SetProcessDPIAware()
dpi_scale = int(user32.GetDpiForSystem())
if dpi_scale != 96:
    print("⚠️⚠️⚠️ Warning ⚠️⚠️⚠️\nScreen's zoom isn't 100%. \nPlease change your Zoom to 100% in your windows settings (just above the display resolution). \nOtherwise there will be unexpected problems (don't hesitate to ask for support in the discord server.")

# Use the smaller ratio to maintain aspect ratio
scale_factor = min(width_ratio, height_ratio)
app = App(login, SelectBrawler, pyla_main, all_brawlers, Hub)
app.start(pyla_version, get_latest_version)
