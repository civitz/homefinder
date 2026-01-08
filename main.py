#!/usr/bin/env python3
"""Main application entry point for HomeFinder."""

import sys
import logging
from pathlib import Path
from typing import Optional

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app import app
from config import DOWNLOAD_DIR, LOG_FILE, EXAMPLES_DIR
from scraper import TettorossoScraper
from database import DatabaseManager


def main():
    """Main application entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting HomeFinder application...")
    
    try:
        # Initialize components
        db_manager = DatabaseManager()
        scraper = TettorossoScraper()
        
        # Create necessary directories
        DOWNLOAD_DIR.mkdir(exist_ok=True)
        
        # Check if we have example data to work with
        example_files = list(EXAMPLES_DIR.rglob("*.html"))
        if example_files:
            logger.info(f"Found {len(example_files)} example files")
            
            # Process example files
            for example_file in example_files:
                try:
                    logger.info(f"Processing example file: {example_file}")
                    listing = scraper.scrape_html_file(example_file)
                    if listing:
                        db_manager.save_listing(listing)
                        logger.info(f"Successfully processed and saved: {listing.title}")
                    else:
                        logger.warning(f"Failed to scrape: {example_file}")
                except Exception as e:
                    logger.error(f"Error processing {example_file}: {e}")
        else:
            logger.warning("No example files found")
        
        # Start Flask application
        logger.info("Starting Flask web server...")
        app.run(host='0.0.0.0', port=5000, debug=True)
        
    except KeyboardInterrupt:
        logger.info("Shutting down HomeFinder application...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()