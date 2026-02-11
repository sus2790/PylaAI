"""Network utilities for version checking and model updates."""
from typing import Optional
import hashlib
from packaging import version

from .client import get_api_client
from utils.config.loader import load_toml_as_dict, update_toml_file


def get_latest_version(api_base_url: str = "localhost") -> Optional[str]:
    """Get the latest PylaAI version from the API."""
    api_client = get_api_client(api_base_url)
    return api_client.get_latest_version()


def check_version(api_base_url: str = "localhost") -> None:
    """
    Check if the current version is the latest available.

    Args:
        api_base_url: Base URL of the API server
    """
    if api_base_url != "localhost":
        latest_version = get_latest_version(api_base_url)
        if latest_version:
            current_version = load_toml_as_dict("cfg/general_config.toml").get('pyla_version', '')
            if version.parse(current_version) < version.parse(latest_version):
                print(
                    "Warning: (ignore if you're using early access) "
                    "You are not using the latest public version of Pyla.\n"
                    "Check the discord for the latest download link."
                )
        else:
            print(
                "Error, couldn't get the version, "
                "please check your internet connection or go ask for help in the discord."
            )


def calculate_sha256(file_path: str) -> str:
    """
    Calculate the SHA-256 hash of a file.

    Args:
        file_path: Path to the file

    Returns:
        Hexadecimal SHA-256 hash
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def current_wall_model_is_latest(api_base_url: str = "localhost") -> bool:
    """
    Check if the current wall model is the latest version.

    Args:
        api_base_url: Base URL of the API server

    Returns:
        True if current model matches latest, False otherwise
    """
    local_hash = calculate_sha256("models/tileDetector.onnx")
    api_client = get_api_client(api_base_url)
    online_hash = api_client.get_online_wall_model_hash()
    return local_hash == online_hash


def get_latest_wall_model_file(api_base_url: str = "localhost") -> None:
    """
    Download the latest wall model to replace the current file.

    Args:
        api_base_url: Base URL of the API server
    """
    api_client = get_api_client(api_base_url)
    if api_client.get_latest_wall_model_file():
        print("Downloaded the latest wall model.")
    else:
        print("Failed to download the latest wall model.")


def get_latest_wall_model_classes(api_base_url: str = "localhost") -> Optional[list]:
    """
    Get the latest wall model class list.

    Args:
        api_base_url: Base URL of the API server

    Returns:
        List of class names or None if failed
    """
    api_client = get_api_client(api_base_url)
    return api_client.get_latest_wall_model_classes()


def update_wall_model_classes(api_base_url: str = "localhost") -> None:
    """
    Update the wall model classes in the bot config if newer version available.

    Args:
        api_base_url: Base URL of the API server
    """
    classes = get_latest_wall_model_classes(api_base_url)
    current_classes = load_toml_as_dict("cfg/bot_config.toml").get("wall_model_classes", [])

    if classes:
        if classes != current_classes:
            print("New wall model classes found. Updating...")
            full_config = load_toml_as_dict("cfg/bot_config.toml")
            full_config["wall_model_classes"] = classes
            update_toml_file("cfg/bot_config.toml", full_config)
            print("Updated the wall model classes.")
    else:
        print("Failed to update the wall model classes, please report this error.")
