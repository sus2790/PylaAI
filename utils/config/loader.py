"""Configuration file loading utilities."""
import os
from typing import Dict, Any
import toml


def load_toml_as_dict(file_path: str) -> Dict[str, Any]:
    """
    Load a TOML file as a dictionary.

    Args:
        file_path: Path to the TOML file

    Returns:
        Dictionary with TOML contents, empty dict if file doesn't exist
    """
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return toml.load(f)
    return {}


def save_dict_as_toml(data: Dict[str, Any], file_path: str) -> None:
    """
    Save a dictionary to a TOML file.

    Args:
        data: Dictionary to save
        file_path: Path to save the TOML file
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        toml.dump(data, f)


def update_toml_file(path: str, new_data: Dict[str, Any]) -> None:
    """
    Update a TOML file with new data (overwrites entire file).

    Args:
        path: Path to the TOML file
        new_data: New dictionary data to write
    """
    with open(path, 'w', encoding='utf-8') as file:
        toml.dump(new_data, file)


class Config:
    """Singleton configuration manager for centralized config access."""

    _instance: 'Config | None' = None
    _cache: Dict[str, Dict[str, Any]] = {}

    def __new__(cls) -> 'Config':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get(self, file_path: str, key: str = None, default: Any = None) -> Any:
        """
        Get configuration value from a TOML file.

        Args:
            file_path: Path to the config file
            key: Optional key to retrieve
            default: Default value if key not found

        Returns:
            Config value or default
        """
        if file_path not in self._cache:
            self._cache[file_path] = load_toml_as_dict(file_path)

        if key is None:
            return self._cache[file_path]
        return self._cache[file_path].get(key, default)

    def reload(self, file_path: str) -> Dict[str, Any]:
        """
        Reload a config file from disk.

        Args:
            file_path: Path to the config file

        Returns:
            Loaded configuration dictionary
        """
        self._cache[file_path] = load_toml_as_dict(file_path)
        return self._cache[file_path]
