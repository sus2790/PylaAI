"""Base exception classes for PylaAI."""


class PylaError(Exception):
    """Base exception for all PylaAI errors."""

    def __init__(self, message: str, details: str | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class ConfigError(PylaError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, config_file: str | None = None) -> None:
        self.config_file = config_file
        details = f"Config file: {config_file}" if config_file else None
        super().__init__(message, details)


class GameError(PylaError):
    """Raised when game state is invalid or unexpected."""

    pass


class DetectionError(PylaError):
    """Raised when object detection fails."""

    def __init__(self, message: str, detection_type: str | None = None) -> None:
        self.detection_type = detection_type
        details = f"Detection type: {detection_type}" if detection_type else None
        super().__init__(message, details)


class APIError(PylaError):
    """Raised when API request fails."""

    def __init__(self, message: str, status_code: int | None = None, url: str | None = None) -> None:
        self.status_code = status_code
        self.url = url
        parts = [f"Status: {status_code}" if status_code else None, f"URL: {url}" if url else None]
        details = ", ".join(p for p in parts if p) if any(parts) else None
        super().__init__(message, details)


class MovementError(PylaError):
    """Raised when movement operations fail."""

    pass


class SkillError(PylaError):
    """Raised when skill operations fail."""

    pass


class StateError(PylaError):
    """Raised when game state transitions are invalid."""

    pass
