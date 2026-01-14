#!/usr/bin/env python3
"""Background scraper service that runs periodically to scrape live websites."""

import time
import threading
import logging
from typing import List, Optional, Any
from datetime import datetime

import threading

# Import for scraping coordination
from atomicx import AtomicBool

from scraper import BaseScraper, TettorossoScraper, GalileoScraper
from database import DatabaseManager
from config import MIN_SCRAPE_INTERVAL_SECONDS

# Global instance for manual triggering
background_scraper_instance=None

class BackgroundScraper:
    """Background service for periodic scraping of real estate websites."""
    
    def __init__(self, request_delay_ms: Optional[int] = None, stop_signal: AtomicBool = None, scrapers: Optional[List[BaseScraper]] = None, database: DatabaseManager = None):
        """Initialize the background scraper.
        
        Args:
            request_delay_ms: Delay between HTTP requests in milliseconds
            stop_signal: AtomicBool for graceful shutdown
            scrapers: List of BaseScraper instances to use (Dependency Injection)
        """
        self.interval_seconds = MIN_SCRAPE_INTERVAL_SECONDS
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.thread = None
        self.stop_signal = stop_signal
        
        # Scraping coordination flag to prevent concurrent operations
        self.scraping_in_progress = AtomicBool(False)
        
        # Urgent request flag for manual scraping that bypasses time limits
        self.urgent_request_pending = AtomicBool(False)
        
        # Use provided scrapers or create defaults for backward compatibility
        if scrapers is not None:
            self.scrapers = scrapers
        else:
            # Fallback to old behavior if no scrapers provided
            self.scrapers = [
                TettorossoScraper(request_delay_ms=request_delay_ms, stop_signal=stop_signal),
                GalileoScraper(request_delay_ms=request_delay_ms, stop_signal=stop_signal)
            ]
        self.db_manager = database
    
    def should_run_scrape(self, force: bool = False) -> bool:
        """Check if scraping should run based on last scrape time.
        
        Args:
            force: If True, always return True (bypass timestamp check)
        
        Returns:
            True if scraping should run, False if too recent
        """
        if force:
            return True
            
        last_scrape_time = self.db_manager.get_last_scrape_time()
        
        if last_scrape_time is None:
            # No previous scrape, should run
            self.logger.info("No previous scrape found, will run scraping")
            return True
            
        time_since_last_scrape = datetime.now() - last_scrape_time
        
        if time_since_last_scrape.total_seconds() >= self.interval_seconds:
            self.logger.info(f"Last scrape was {time_since_last_scrape.total_seconds():.1f} seconds ago, will run scraping")
            return True
        else:
            remaining_seconds = self.interval_seconds - time_since_last_scrape.total_seconds()
            self.logger.info(f"Last scrape was {time_since_last_scrape.total_seconds():.1f} seconds ago, skipping (next in {remaining_seconds:.1f}s)")
            return False

    def _scrape_all_websites(self, force: bool = False) -> int:
        """Scrape all websites and save listings to database.

        Args:
            force: If True, bypass timestamp check
        
        Returns:
            Number of listings successfully scraped and saved
        """
        # Check if there's an urgent request pending (bypasses all limits)
        if self.urgent_request_pending.load():
            force = True
            self.urgent_request_pending.store(False)  # Consume the urgent request
            self.logger.info("Processing urgent scrape request")
        
        # Check if scraping is already in progress
        if self.scraping_in_progress.load():
            self.logger.warning("Scraping already in progress, skipping this run")
            return 0
        
        # Check poison pill before starting
        if self.stop_signal and self.stop_signal.load():
            self.logger.info("Skipping scraping run due to poison pill")
            return 0
        
        # Set flag to indicate scraping is starting
        self.scraping_in_progress.store(True)
        
        try:
            total_listings = 0
            
            scrape_start_time = datetime.now()
            self.logger.info(f"Starting scraping run at {scrape_start_time}")
            
            # Use threading to scrape websites in parallel
            results = {}
            threads = []
            
            def scrape_website(scraper):
                try:
                    self.logger.info(f"Scraping {scraper.name} website...")
                    
                    # Scrape live listings
                    listings = scraper.scrape_live_listings()
                    
                    if listings:
                        # Save listings to database
                        saved_count = self.db_manager.save_listings(listings)
                        results[scraper.name] = saved_count
                        self.logger.info(f"Successfully scraped and saved {saved_count} listings from {scraper.name}")
                    else:
                        self.logger.warning(f"No listings found from {scraper.name}")
                        results[scraper.name] = 0
                     
                except Exception as e:
                    self.logger.error(f"Error scraping {scraper.name}: {e}")
                    results[scraper.name] = 0
            
            # Start threads for each scraper
            for scraper in self.scrapers:
                thread = threading.Thread(target=scrape_website, args=(scraper,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Sum up results
            total_listings = sum(results.values())
            
            scrape_end_time = datetime.now()
            duration_seconds = (scrape_end_time - scrape_start_time).total_seconds()
            
            # Log this scrape run to history
            self.db_manager.log_scrape_run("background", total_listings, duration_seconds)
            
            self.logger.info(f"Scraping run completed. Total listings: {total_listings} in {duration_seconds:.1f} seconds")
            return total_listings
            
        finally:
            # Always reset the scraping flag when done (success or failure)
            self.scraping_in_progress.store(False)
    
    def _scrape_loop(self):
        """Main scraping loop that runs periodically."""
        while self.running:
            try:
                # Check if scraping is already in progress
                if self.scraping_in_progress.load():
                    self.logger.debug("Scraping already in progress, waiting...")
                    time.sleep(60)
                    continue
                
                # Check if we should run scraping based on timestamp
                if not self.should_run_scrape():
                    # Sleep for a short time and check again
                    time.sleep(60)
                    continue
                    
                start_time = time.time()
                   
                # Run scraping (force=False since we already checked the timestamp)
                self._scrape_all_websites(force=False)
                
                # Calculate sleep time to maintain interval
                elapsed_time = time.time() - start_time
                sleep_time = max(0, self.interval_seconds - elapsed_time)
                
                self.logger.info(f"Next scraping run in {sleep_time:.1f} seconds")

                 # Sleep until next run
                for _ in range(int(sleep_time)):
                    if not self.running:
                        break
                    if self.stop_signal and self.stop_signal.load():
                        self.logger.info("Background scraper stopping due to poison pill")
                        self.running = False
                        break
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"Error in scraping loop: {e}")
                # Wait before retrying to avoid tight error loops
                time.sleep(60)
    
    def start(self):
        """Start the background scraper service."""
        if self.running:
            self.logger.warning("Background scraper is already running")
            return
            
        self.running = True
        self.logger.info(f"Starting background scraper with {self.interval_seconds} second interval")
        
        # Start the scraping thread
        self.thread = threading.Thread(target=self._scrape_loop, daemon=True)
        self.thread.start()
        
    
    def stop(self):
        """Stop the background scraper service."""
        if not self.running:
            self.logger.warning("Background scraper is not running")
            return
            
        self.running = False
        self.logger.info("Stopping background scraper")
        
        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                self.logger.warning("Background scraper thread did not stop gracefully")
    
    def is_running(self) -> bool:
        """Check if the background scraper is running."""
        return self.running
    
    def run_once(self, force: bool = False) -> int:
        """Run a single scraping cycle without starting the background service.
        
        Args:
            force: If True, bypass timestamp check
            
        Returns:
            Number of listings successfully scraped and saved
        """
        # Check if scraping is already in progress
        if self.scraping_in_progress.load():
            self.logger.warning("Scraping already in progress, skipping manual run")
            return 0
        
        # For run_once, we need to check the timestamp if force=False
        if not force and not self.should_run_scrape(force):
            self.logger.info("Skipping scraping run - too recent")
            return 0
        
        return self._scrape_all_websites(force=force)


def get_background_scraper() -> Optional['BackgroundScraper']:
    """Get the global background scraper instance."""
    return background_scraper_instance


def set_background_scraper(scraper: 'BackgroundScraper'):
    """Set the global background scraper instance."""
    global background_scraper_instance
    background_scraper_instance = scraper
