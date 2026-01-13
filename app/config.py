import os
from pathlib import Path

class Config:
    """Application configuration"""

    # Server settings
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Cache settings
    CACHE_DIR: Path = Path(os.getenv("CACHE_DIR", "./cache"))
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"

    # yt-dlp settings
    YTDLP_TIMEOUT: int = int(os.getenv("YTDLP_TIMEOUT", "30"))
    MAX_CONCURRENT_PROCESSES: int = int(os.getenv("MAX_CONCURRENT_PROCESSES", "2"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Default language
    DEFAULT_LANGUAGE: str = "en"

    @classmethod
    def initialize(cls):
        """Initialize configuration (create cache directory, etc.)"""
        if cls.CACHE_ENABLED:
            cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)

config = Config()
