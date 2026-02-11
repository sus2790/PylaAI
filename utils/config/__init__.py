"""Configuration utilities."""
from .loader import load_toml_as_dict, save_dict_as_toml, update_toml_file, Config

__all__ = ['load_toml_as_dict', 'save_dict_as_toml', 'update_toml_file', 'Config']
