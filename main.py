#!/usr/bin/env python3
"""Main application entry point for HomeFinder."""

import sys
import logging
import argparse
from pathlib import Path
from typing import Optional

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import atomicx for poison pill
from atomicx import AtomicBool

from app import app
from config import DOWNLOAD_DIR, LOG_FILE, EXAMPLES_DIR, DEBUG
from scraper import TettorossoScraper, GalileoScraper
from database import DatabaseManager
from background_scraper import BackgroundScraper

# Global poison pill for graceful shutdown
stop_at_next = AtomicBool(False)


def main(args=None):
    """Main application entry point."""
    if args is None:
        args = parse_arguments()
    logging.basicConfig(
        level=logging.DEBUG if DEBUG else logging.INFO,
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
        
        # Determine request delay
        request_delay_ms = args.request_delay if args.request_delay is not None else None
        
        scrapers = [
            TettorossoScraper(request_delay_ms=request_delay_ms, stop_signal=stop_at_next),
            GalileoScraper(request_delay_ms=request_delay_ms, stop_signal=stop_at_next)
        ]
        
         # Initialize background scraper
        if args.no_background:
            logger.info("Background scraping disabled")
            background_scraper = None
        else:
            background_scraper = BackgroundScraper(
                request_delay_ms=request_delay_ms,
                scrapers=scrapers
            )
            # Set global instance for manual triggering
            from background_scraper import set_background_scraper
            set_background_scraper(background_scraper)
        
        # Create necessary directories
        DOWNLOAD_DIR.mkdir(exist_ok=True)
        
        # Process data based on arguments
        if args.use_examples:
            # Check if we have example data to work with
            example_files = list(EXAMPLES_DIR.rglob("*.html"))
            if example_files:
                logger.info(f"Found {len(example_files)} example files")
                 
                # Process example files with appropriate scrapers
                for example_file in example_files:
                    try:
                        logger.info(f"Processing example file: {example_file}")
                         
                        # Determine which scraper to use based on the file path
                        if 'tettorossoimmobiliare.it' in str(example_file):
                            scraper = next(s for s in scrapers if isinstance(s, TettorossoScraper))
                        elif 'galileoimmobiliare.it' in str(example_file):
                            scraper = next(s for s in scrapers if isinstance(s, GalileoScraper))
                        else:
                            logger.warning(f"Unknown website for file: {example_file}")
                            continue
                         
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
        else:
            # Run initial live scraping if not using examples
            if not background_scraper:
                logger.info("Running single live scraping pass...")
                # Check if we should run scraping based on last scrape time
                last_scrape_time = db_manager.get_last_scrape_time()
                from config import MIN_SCRAPE_INTERVAL_SECONDS
                from datetime import datetime
                
                should_scrape = True
                if last_scrape_time:
                    time_since_last = (datetime.now() - last_scrape_time).total_seconds()
                    if time_since_last < MIN_SCRAPE_INTERVAL_SECONDS:
                        should_scrape = False
                        logger.info(f"Skipping initial scrape - last scrape was {time_since_last:.1f}s ago (interval: {MIN_SCRAPE_INTERVAL_SECONDS}s)")
                
                if should_scrape:
                    # Run a single scraping pass
                    for scraper in scrapers:
                        try:
                            listings = scraper.scrape_live_listings()
                            if listings:
                                saved_count = db_manager.save_listings(listings)
                                logger.info(f"Successfully scraped and saved {saved_count} listings from {scraper.name}")
                        except Exception as e:
                            logger.error(f"Error in initial scraping for {scraper.name}: {e}")
                else:
                    logger.info("Skipping initial scraping - recent scrape already exists")
        
        # Start Flask application first (non-blocking in debug mode)
        logger.info("Starting Flask web server...")
        
        # Start background scraper after Flask is ready
        if background_scraper:
            # Use a separate thread to start the background scraper
            background_scraper.start()
        
        try:
            app.run(host='0.0.0.0', port=5000, debug=True)
        finally:
            # Cleanup on exit
            if background_scraper:
                stop_at_next.store(True)
                background_scraper.stop()
        
    except KeyboardInterrupt:
        stop_at_next.store(True)  # Set poison pill for graceful shutdown
        logger.info("Ctrl-C detected, setting poison pill for graceful shutdown")
        logger.info("Shutting down HomeFinder application...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        stop_at_next.store(True)
        sys.exit(1)


def parse_arguments(argv=None):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='HomeFinder - Real Estate Scraper and Search Tool')
    parser.add_argument(
        '--use-examples',
        action='store_true',
        help='Use example files instead of live scraping'
    )
    parser.add_argument(
        '--no-background',
        action='store_true',
        help='Disable background scraping (live scraping only runs once at startup)'
    )
    parser.add_argument(
        '--scrape-interval',
        type=int,
        default=1,
        help='Background scraping interval in hours (default: 1)'
    )
    parser.add_argument(
        '--request-delay',
        type=int,
        default=None,
        help='Delay between HTTP requests in milliseconds (default: from config)'
    )
    
    if argv is None:
        return parser.parse_args()
    else:
        return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_arguments()
    main(args)
