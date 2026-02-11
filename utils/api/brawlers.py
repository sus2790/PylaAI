"""Brawler data management and icon utilities."""
from typing import Dict, Any, Optional
import os
from io import BytesIO
import requests
from PIL import Image
import google_play_scraper
from .client import get_api_client
from utils.config.loader import load_toml_as_dict, update_toml_file


BRAWLERS_INFO_FILE_PATH = "cfg/brawlers_info.json"


def load_brawlers_info() -> Dict[str, Any]:
    """Load brawlers info from JSON file."""
    if os.path.exists(BRAWLERS_INFO_FILE_PATH):
        with open(BRAWLERS_INFO_FILE_PATH, 'r', encoding='utf-8') as f:
            import json
            return json.load(f)
    return {}


def update_brawlers_info(brawlers_info: Dict[str, Any]) -> None:
    """Save brawlers info to JSON file."""
    import json
    with open(BRAWLERS_INFO_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(brawlers_info, f, indent=4)


def save_brawler_data(data: list) -> None:
    """Save the given brawler data to a JSON file."""
    import json
    with open("latest_brawler_data.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


def update_missing_brawlers_info(brawlers: list) -> None:
    """
    Update info for brawlers not already in the local cache.

    Args:
        brawlers: List of brawler names to check/update
    """
    api_client = get_api_client()
    brawlers_info = load_brawlers_info()

    for brawler in brawlers:
        if brawler not in brawlers_info:
            brawler_info = api_client.get_brawler_info(brawler)
            if brawler_info:
                brawlers_info[brawler] = brawler_info
                update_brawlers_info(brawlers_info)
                print(f"Added info for brawler '{brawler}': {brawler_info}")
                save_brawler_icon(brawler)
            else:
                print(f"Could not find info for brawler '{brawler}'")

        if not os.path.exists(f"./api/assets/brawler_icons/{brawler}.png"):
            save_brawler_icon(brawler)


def save_brawler_icon(brawler_name: str) -> None:
    """
    Download and save a brawler's icon from BrawlAPI.

    Args:
        brawler_name: Name of the brawler
    """
    brawler_name_clean = (
        brawler_name.lower()
        .replace(' ', '')
        .replace('-', '')
        .replace('.', '')
        .replace('&', '')
    )

    brawlers_url = "https://api.brawlapi.com/v1/brawlers"
    try:
        response = requests.get(brawlers_url)
        if response.status_code != 200:
            print(f"Failed to fetch brawlers from API: {response.status_code}")
            return

        brawlers_data = response.json()['list']

        for brawler_obj in brawlers_data:
            api_brawler_name = (
                brawler_obj['name'].lower()
                .replace(' ', '')
                .replace('-', '')
                .replace('.', '')
                .replace('&', '')
            )

            if api_brawler_name == brawler_name_clean:
                icon_url = brawler_obj['imageUrl2']
                img_response = requests.get(icon_url)
                if img_response.status_code == 200:
                    os.makedirs(f"api/assets/brawler_icons", exist_ok=True)
                    image = Image.open(BytesIO(img_response.content))
                    image.save(f"api/assets/brawler_icons/{brawler_name_clean}.png")
                    print(f"Saved icon for brawler '{brawler_name}'")
                else:
                    print(f"Failed to download icon for '{brawler_name}'")
                return

        print(f"Icon not found for brawler '{brawler_name}'")
    except Exception as e:
        print(f"Error saving brawler icon: {e}")


def update_icons() -> None:
    """Update the Brawl Stars icon from Google Play Store."""
    try:
        icon_link = google_play_scraper.app("com.supercell.brawlstars")["icon"]
    except Exception:
        import time
        time.sleep(1)
        try:
            icon_link = google_play_scraper.app("com.supercell.brawlstars")["icon"]
        except Exception as e:
            print(f"Failed to get latest icon link from Google Play Store: {e}")
            return

    response = requests.get(icon_link)
    big_icon = 'brawl_stars_icon_big.png'
    small_icon = 'brawl_stars.png'

    if response.status_code == 200:
        icon_image = Image.open(BytesIO(response.content))

        # Big icon (69x69, then crop to 50x50)
        big_icon_image = icon_image.resize((69, 69))
        width, height = big_icon_image.size
        left = (width - 50) / 2
        top = (height - 50) / 2
        right = (width + 50) / 2
        bottom = (height + 50) / 2
        big_icon_image = big_icon_image.crop((left, top, right, bottom))
        big_icon_image.save(f'./state_finder/images_to_detect/{big_icon}')

        # Small icon (16x16, then crop to 12x12)
        small_icon_image = icon_image.resize((16, 16))
        width, height = small_icon_image.size
        left = (width - 12) / 2
        top = (height - 12) / 2
        right = (width + 12) / 2
        bottom = (height + 12) / 2
        small_icon_image = small_icon_image.crop((left, top, right, bottom))
        small_icon_image.save(f'./state_finder/images_to_detect/{small_icon}')
        print("Updated to the latest icon!")
    else:
        print(f"Failed to download latest icon. Status code: {response.status_code}")
