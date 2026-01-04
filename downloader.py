#!/usr/bin/env python3
"""
Website downloader module for Tettorosso Immobiliare
Uses wget to download the entire website locally
"""

import subprocess
import logging
import shutil
import os
from datetime import datetime
from pathlib import Path
from config import DOWNLOAD_DIR, WEBSITE_URL, LOG_FILE, ensure_directories

# Set up logging
# Set up logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Also log to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
logger.addHandler(console_handler)


def download_website():
    """
    Download the entire website using wget
    Returns True if successful, False otherwise
    """

    return True
    ensure_directories()

    # Create directory if it doesn't exist
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting website download from {WEBSITE_URL}")
    logger.info(f"Download directory: {DOWNLOAD_DIR}")

    try:
        # wget command to mirror the website
        # --mirror: turn on options suitable for mirroring
        # --convert-links: convert links to be suitable for local viewing
        # --adjust-extension: add .html extension to files if needed
        # --page-requisites: get all necessary files for proper page display
        # --no-parent: don't ascend to parent directory
        # --user-agent: set a reasonable user agent
        # --wait: wait between downloads to be polite
        # --random-wait: add random wait between 0.5 and 1.5 * wait time
        # --limit-rate: limit download speed to be polite
        # --no-clobber: don't overwrite existing files
        # --domains: only follow links within this domain

        cmd = [
            "wget",
            "--mirror",
            "--convert-links",
            "--adjust-extension",
            "--page-requisites",
            "--no-parent",
            f"--user-agent=Mozilla/5.0 (compatible; HomeFinderBot/1.0; +{WEBSITE_URL})",
            "--wait=0.5",
            "--random-wait",
            "--limit-rate=200k",
            "--no-clobber",
            "--timestamping",
            f"--domains=www.tettorossoimmobiliare.it",
            WEBSITE_URL,
            f"--directory-prefix={DOWNLOAD_DIR}",
        ]

        logger.info(f"Running command: {' '.join(cmd)}")

        # Run the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout
        )

        if result.returncode == 0:
            logger.info("Website download completed successfully")
            logger.info(f"wget stdout:\n{result.stdout}")
            return True
        else:
            logger.error(
                f"Website download failed with return code {result.returncode}"
            )
            logger.error(f"wget stdout:\n{result.stdout}")
            logger.error(f"wget stderr:\n{result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("Website download timed out after 1 hour")
        return False
    except Exception as e:
        logger.error(f"Website download failed with exception: {str(e)}")
        return False


def get_downloaded_files():
    """
    Get list of downloaded HTML files that might contain property listings
    """
    if not DOWNLOAD_DIR.exists():
        return []

    # Look for HTML files that might be property listings
    html_files = list(DOWNLOAD_DIR.rglob("immobili/*/index.html"))

    # Filter out non-property pages (admin, contact, etc.)
    property_files = []
    for file in html_files:
        try:
            # Skip obvious non-property pages
            if any(
                skip in str(file)
                for skip in ["contatti", "privacy", "cookie", "lavora-con-noi"]
            ):
                continue


            property_files.append(file)
        except Exception as e:
            logger.warning(f"Error processing file {file}: {str(e)}")

    logger.info(f"Found {len(property_files)} potential property listing files")
    return property_files


def get_last_download_time():
    """
    Get the timestamp of the last successful download
    """
    timestamp_file = DOWNLOAD_DIR / ".last_download"
    if timestamp_file.exists():
        with open(timestamp_file, "r") as f:
            return f.read().strip()
    return None


def set_last_download_time():
    """
    Set the timestamp of the current download
    """
    timestamp_file = DOWNLOAD_DIR / ".last_download"
    with open(timestamp_file, "w") as f:
        f.write(datetime.now().isoformat())


if __name__ == "__main__":
    # Test the downloader
    success = download_website()
    if success:
        files = get_downloaded_files()
        print(f"Downloaded {len(files)} property files")
        set_last_download_time()
    else:
        print("Download failed")
