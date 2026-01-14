#!/usr/bin/env python3
"""Main application entry point for HomeFinder."""

import sys
import logging
import argparse
from pathlib import Path
from typing import Optional
from atomicx import AtomicBool
from datetime import datetime

# Add project root to Python path
#project_root = Path(__file__).parent
#sys.path.insert(0, str(project_root))

from app import create_app
from config import DOWNLOAD_DIR, LOG_FILE, EXAMPLES_DIR, DEBUG
from scraper import TettorossoScraper, GalileoScraper, FakeScraper
from database import DatabaseManager
from background_scraper import BackgroundScraper
from background_scraper import set_background_scraper
from config import MIN_SCRAPE_INTERVAL_SECONDS

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
            #TettorossoScraper(request_delay_ms=request_delay_ms, stop_signal=stop_at_next),
            #GalileoScraper(request_delay_ms=request_delay_ms, stop_signal=stop_at_next)
            FakeScraper(request_delay_ms=request_delay_ms, stop_signal=stop_at_next),
            FakeScraper(request_delay_ms=request_delay_ms, stop_signal=stop_at_next)
        ]
        
         # Initialize background scraper
        # Always create a background scraper instance for API access, even if background scraping is disabled
        background_scraper = BackgroundScraper(
            request_delay_ms=request_delay_ms,
            scrapers=scrapers,
            database=db_manager
        )
        
        # Set global instance for manual triggering (API access)
        set_background_scraper(background_scraper)
        
        if args.no_background:
            logger.info("Background scraping disabled (but instance available for API)")
        else:
            # Use a separate thread to start the background scraper
            background_scraper.start()
            logger.info("Background scraping enabled")
        
        # Create necessary directories
        DOWNLOAD_DIR.mkdir(exist_ok=True)
        
        if args.no_background:
            logger.info("Running single live scraping pass...")
            # Check if we should run scraping based on last scrape time
            last_scrape_time = db_manager.get_last_scrape_time()
            
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
        create_app().run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
        
    except KeyboardInterrupt:
        stop_at_next.store(True)  # Set poison pill for graceful shutdown
        logger.info("Ctrl-C detected, setting poison pill for graceful shutdown")
        logger.info("Shutting down HomeFinder application...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        stop_at_next.store(True)
        sys.exit(1)
    finally:
        # Cleanup on exit
        # Only stop background scraper if it was actually running
        if background_scraper and not args.no_background:
            stop_at_next.store(True)
            background_scraper.stop()


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
