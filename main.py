#!/usr/bin/env python3
"""
Main application for HomeFinder system
Orchestrates the entire workflow: download, scrape, store, and serve
"""

import logging
import time
import threading
import schedule
from datetime import datetime
from config import DOWNLOAD_INTERVAL_MINUTES, LOG_FILE, ensure_directories
from downloader import download_website, get_downloaded_files, set_last_download_time
from scraper import scrape_all_properties
from database import db
from webapp import app


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
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(console_handler)

def full_update_cycle():
    """
    Perform a complete update cycle: download, scrape, store
    """
    logger.info("Starting full update cycle")

    try:
        # Step 1: Download website
        logger.info("Step 1/3: Downloading website...")
        download_success = download_website()

        if not download_success:
            logger.warning("Website download failed, scraping anyway")
            #return False

        set_last_download_time()

        # Step 2: Scrape properties
        logger.info("Step 2/3: Scraping properties...")
        properties = scrape_all_properties()
        logger.info(f"Found {len(properties)} properties")

        # Step 3: Store in database
        logger.info("Step 3/3: Storing properties in database...")
        success_count = db.insert_or_update_properties(properties)
        logger.info(f"Successfully stored {success_count} properties")

        logger.info("Full update cycle completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error in full update cycle: {str(e)}")
        return False


def run_scheduled_updates():
    """
    Run scheduled updates in background
    """
    logger.info(f"Starting scheduled updates every {DOWNLOAD_INTERVAL_MINUTES} minutes")

    # Initial delay to avoid immediate execution
    #time.sleep(60)

    while True:
        try:
            logger.info(f"Running scheduled update at {datetime.now()}")
            full_update_cycle()

            # Wait for the configured interval
            wait_minutes = DOWNLOAD_INTERVAL_MINUTES
            logger.info(f"Next update scheduled in {wait_minutes} minutes...")
            time.sleep(wait_minutes * 60)

        except Exception as e:
            logger.error(f"Error in scheduled update: {str(e)}")
            # Wait a bit before retrying
            time.sleep(300)  # 5 minutes


def run_web_interface():
    """
    Run the Flask web interface
    """
    logger.info("Starting web interface")
    app.run(host="0.0.0.0", port=5000, debug=False)


def main():
    """
    Main entry point
    """
    
    ensure_directories()
    logger.info("Starting HomeFinder system")

    try:
        # Start scheduled updates in background thread
        scheduler_thread = threading.Thread(target=run_scheduled_updates, daemon=True)
        scheduler_thread.start()

        # Start web interface in main thread
        run_web_interface()

    except KeyboardInterrupt:
        logger.info("Shutting down HomeFinder system")
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")


if __name__ == "__main__":
    main()
