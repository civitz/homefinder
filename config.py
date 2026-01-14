import os
from pathlib import Path
from typing import Final

# Directories
BASE_DIR: Final[Path] = Path(__file__).parent
DOWNLOAD_DIR: Final[Path] = BASE_DIR / "downloads"
LOG_FILE: Final[Path] = BASE_DIR / "homefinder.log"
DB_FILE: Final[Path] = BASE_DIR / "properties.db"
EXAMPLES_DIR: Final[Path] = BASE_DIR / "examples"

# Scraping configuration
USER_AGENT: Final[str] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
REQUEST_TIMEOUT: Final[int] = 30
MAX_RETRIES: Final[int] = 3
REQUEST_DELAY_MS: Final[int] = 2000  # Delay between requests in milliseconds

# Debug configuration
DEBUG: Final[bool] = os.getenv("DEBUG", "false").lower() == "true"

# Scraping interval configuration (in seconds)
MIN_SCRAPE_INTERVAL_SECONDS: Final[int] = int(os.getenv("MIN_SCRAPE_INTERVAL_SECONDS", "3600"))  # Default: 1 hour
MAX_SCRAPE_HISTORY_ENTRIES: Final[int] = int(os.getenv("MAX_SCRAPE_HISTORY_ENTRIES", "100"))

# Flask configuration
FLASK_SECRET_KEY: Final[str] = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
FLASK_DEBUG: Final[bool] = os.getenv("FLASK_DEBUG", str(DEBUG)).lower() == "true"
FLASK_HOST: Final[str] = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT: Final[int] = int(os.getenv("FLASK_PORT", "5000"))

# Database configuration
DB_CONNECTION_STRING: Final[str] = f"sqlite:///{DB_FILE}"
