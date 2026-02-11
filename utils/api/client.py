"""API client for PylaAI backend services."""
from typing import Dict, List, Any, Optional
import os
import requests


class ApiClient:
    """Client for making requests to the PylaAI API."""

    def __init__(self, base_url: str = "localhost") -> None:
        self.base_url = base_url

    def get_brawler_list(self) -> List[str]:
        """Get list of available brawlers."""
        if self.base_url == "localhost":
            from utils.config.loader import load_toml_as_dict
            brawlers_info = load_toml_as_dict("cfg/brawlers_info.json")
            return list(brawlers_info.keys())

        url = f'https://{self.base_url}/get_brawler_list'
        response = requests.post(url)
        if response.status_code == 201:
            data = response.json()
            return data.get('brawlers', [])
        return []

    def get_brawler_info(self, brawler_name: str) -> Optional[Dict[str, Any]]:
        """Get information for a specific brawler."""
        url = f'https://{self.base_url}/get_brawler_info'
        response = requests.post(url, json={'brawler_name': brawler_name})
        if response.status_code == 200:
            data = response.json()
            return data.get('info', [])
        return None

    def get_latest_version(self) -> Optional[str]:
        """Get the latest PylaAI version from the API."""
        url = f'https://{self.base_url}/check_version'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get('version', '')
        return None

    def get_discord_link(self) -> Optional[str]:
        """Get the Discord invite link."""
        if self.base_url == "localhost":
            return "https://discord.gg/xUusk3fw4A"

        url = f'https://{self.base_url}/get_discord_link'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get('link', '')
        return None

    def get_online_wall_model_hash(self) -> Optional[str]:
        """Get the hash of the latest wall model."""
        url = f'https://{self.base_url}/get_wall_model_hash'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get('hash', '')
        return None

    def get_latest_wall_model_file(self, save_path: str = "./models/tileDetector.onnx") -> bool:
        """
        Download the latest wall model file.

        Args:
            save_path: Path to save the model file

        Returns:
            True if successful, False otherwise
        """
        url = f'https://{self.base_url}/get_wall_model_file'
        response = requests.get(url)
        if response.status_code == 200:
            with open(save_path, "wb") as file:
                file.write(response.content)
            return True
        return False

    def get_latest_wall_model_classes(self) -> Optional[List[str]]:
        """Get the latest wall model class list."""
        url = f'https://{self.base_url}/get_wall_model_classes'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get('classes', [])
        return None


# Global instance for backward compatibility
_api_client: Optional[ApiClient] = None


def get_api_client(base_url: str = "localhost") -> ApiClient:
    """Get or create the global API client instance."""
    global _api_client
    if _api_client is None:
        _api_client = ApiClient(base_url)
    return _api_client


def set_api_base_url(base_url: str) -> None:
    """Set the base URL for the API client."""
    global _api_client
    _api_client = ApiClient(base_url)
