"""Custom exception classes for PylaAI."""
from .base import (
    PylaError,
    ConfigError,
    GameError,
    DetectionError,
    APIError,
    MovementError,
    SkillError,
    StateError
)

__all__ = [
    'PylaError',
    'ConfigError',
    'GameError',
    'DetectionError',
    'APIError',
    'MovementError',
    'SkillError',
    'StateError'
]
