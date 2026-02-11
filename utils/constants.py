"""Shared constants for PylaAI."""


# Game constants
TILE_SIZE = 60


# Game states (enum string values for now, will be replaced with GameState enum)
GAME_STATE_END = "end"
GAME_STATE_SHOP = "shop"
GAME_STATE_POPUP = "popup"
GAME_STATE_LOBBY = "lobby"
GAME_STATE_MATCH = "match"
GAME_STATE_PLAY_STORE = "play_store"
GAME_STATE_STAR_DROP = "star_drop"

GAME_STATE_MENU = "menu"
GAME_STATE_BRAWLER_PICK_SCREEN = "brawler_pick_screen"


# Brawler info keys
BRAWLER_KEY_RANGE = "range"
BRAWLER_KEY_SUPER_TYPE = "super_type"
BRAWLER_KEY_WALL_PENETRATION = "wall_penetration"


# Super types
SUPER_TYPE_PROJECTILE = "projectile"
SUPER_TYPE_CONE = "cone"
SUPER_TYPE_MELEE = "melee"
SUPER_TYPE_CHARGE = "charge"


# File paths
MODELS_DIR = "models"
BRAWLERS_INFO_PATH = "cfg/brawlers_info.json"
GENERAL_CONFIG_PATH = "cfg/general_config.toml"
BOT_CONFIG_PATH = "cfg/bot_config.toml"
LOBBY_CONFIG_PATH = "cfg/lobby_config.toml"
TIME_THRESHOLDS_PATH = "cfg/time_tresholds.toml"


# Brawler icons path
BRAWLER_ICONS_DIR = "api/assets/brawler_icons"
