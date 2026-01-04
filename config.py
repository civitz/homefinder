# Configuration file for the homefinder system
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Website download configuration
WEBSITE_URL = "https://www.tettorossoimmobiliare.it/"
DOWNLOAD_DIR = BASE_DIR / "downloaded_website"
DOWNLOAD_INTERVAL_MINUTES = 15  # Configurable interval

# Database configuration
DATABASE_PATH = BASE_DIR / "listings.db"

# LLM configuration (placeholder for future implementation)
LLM_PROMPT_TEMPLATE = """
Analyze the following real estate listing description and extract structured information:

{description}

Return the result as JSON with the following fields:
- locali: number of rooms
- mq: square meters
- piano: floor
- riscaldamento: heating type (autonomo/centralizzato)
- condizionatore: boolean
- ascensore: boolean
- garage: boolean
- arredato: boolean
- anno: construction year
- note: any additional notes

Only return valid JSON, no other text.
"""

# Web interface configuration
WEB_PORT = 5000
WEB_HOST = "0.0.0.0"

# Logging configuration
LOG_FILE = BASE_DIR / "homefinder.log"
LOG_LEVEL = "INFO"


# Ensure directories exist
def ensure_directories():
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    # Create log directory if needed
    if not LOG_FILE.parent.exists():
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    ensure_directories()
