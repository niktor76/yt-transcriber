import os
from pathlib import Path

def _get_int_env(name: str, default: int, min_val: int = 1, max_val: int = 86400) -> int:
    """
    Get integer environment variable with bounds checking.

    Args:
        name: Environment variable name
        default: Default value if not set
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Validated integer value

    Raises:
        ValueError: If value is out of bounds
    """
    try:
        value = int(os.getenv(name, str(default)))
        if value < min_val or value > max_val:
            raise ValueError(f"{name} must be between {min_val} and {max_val}, got {value}")
        return value
    except ValueError as e:
        raise ValueError(f"Invalid {name}: {e}")

class Config:
    """Application configuration"""

    # Server settings
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = _get_int_env("PORT", 8000, min_val=1, max_val=65535)

    # Cache settings
    CACHE_DIR: Path = Path(os.getenv("CACHE_DIR", "./cache"))
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"

    # yt-dlp settings (timeout in seconds, max 10 minutes)
    YTDLP_TIMEOUT: int = _get_int_env("YTDLP_TIMEOUT", 30, min_val=5, max_val=600)
    MAX_CONCURRENT_PROCESSES: int = _get_int_env("MAX_CONCURRENT_PROCESSES", 2, min_val=1, max_val=10)

    # GitHub Copilot CLI settings (for summarization)
    COPILOT_CLI_PATH: str = os.getenv("COPILOT_CLI_PATH", "copilot")
    COPILOT_TIMEOUT: int = _get_int_env("COPILOT_TIMEOUT", 120, min_val=10, max_val=600)
    COPILOT_MODEL: str = os.getenv("COPILOT_MODEL", "gpt-5-mini")
    MAX_CONCURRENT_COPILOT: int = _get_int_env("MAX_CONCURRENT_COPILOT", 1, min_val=1, max_val=5)

    # Summary settings (max transcript length: 10MB characters)
    SUMMARY_CACHE_ENABLED: bool = os.getenv("SUMMARY_CACHE_ENABLED", "true").lower() == "true"
    MAX_TRANSCRIPT_LENGTH: int = _get_int_env("MAX_TRANSCRIPT_LENGTH", 100000, min_val=1000, max_val=10000000)

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Default language
    DEFAULT_LANGUAGE: str = "en"

    # CORS configuration - restrict in production
    ALLOWED_ORIGINS: list[str] = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000"
    ).split(",")

    @classmethod
    def initialize(cls):
        """Initialize configuration (create cache directory, etc.)"""
        if cls.CACHE_ENABLED:
            cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)

config = Config()
