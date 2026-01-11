#!/usr/bin/env python3
"""Background scraper service that runs periodically to scrape live websites."""

import time
import threading
import logging
from typing import List, Optional
from datetime import datetime

from scraper import TettorossoScraper, GalileoScraper
from database import DatabaseManager
from models import Listing

# Global instance for manual triggering
background_scraper_instance = None


class BackgroundScraper:
    """Background service for periodic scraping of real estate websites."""
    
    def __init__(self, interval_hours: int = 1, request_delay_ms: Optional[int] = None):
        """Initialize the background scraper.
        
        Args:
            interval_hours: How often to run the scraping (in hours)
            request_delay_ms: Delay between HTTP requests in milliseconds
        """
        self.interval_hours = interval_hours
        self.interval_seconds = interval_hours * 3600
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.thread = None
        
        # Initialize scrapers and database
        self.scrapers = [
            TettorossoScraper(request_delay_ms=request_delay_ms),
            GalileoScraper(request_delay_ms=request_delay_ms)
        ]
        self.db_manager = DatabaseManager()
    
    def _scrape_all_websites(self) -> int:
        """Scrape all websites and save listings to database.
        
        Returns:
            Number of listings successfully scraped and saved
        """
        total_listings = 0
        
        self.logger.info(f"Starting scraping run at {datetime.now()}")
        
        # Use threading to scrape websites in parallel
        import threading
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
        self.logger.info(f"Scraping run completed. Total listings: {total_listings}")
        return total_listings
    
    def _scrape_loop(self):
        """Main scraping loop that runs periodically."""
        while self.running:
            try:
                start_time = time.time()
                
                # Run scraping
                self._scrape_all_websites()
                
                # Calculate sleep time to maintain interval
                elapsed_time = time.time() - start_time
                sleep_time = max(0, self.interval_seconds - elapsed_time)
                
                self.logger.info(f"Next scraping run in {sleep_time:.1f} seconds ({self.interval_hours} hours)")
                
                # Sleep until next run
                for _ in range(int(sleep_time)):
                    if not self.running:
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
        self.logger.info(f"Starting background scraper with {self.interval_hours} hour interval")
        
        # Start the scraping thread
        self.thread = threading.Thread(target=self._scrape_loop, daemon=True)
        self.thread.start()
        
        # Run initial scrape immediately
        self._scrape_all_websites()
    
    def stop(self):
        """Stop the background scraper service."""
        if not self.running:
            self.logger.warning("Background scraper is not running")
            return
            
        self.running = False
        self.logger.info("Stopping background scraper")
        
        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=60)
            if self.thread.is_alive():
                self.logger.warning("Background scraper thread did not stop gracefully")
    
    def is_running(self) -> bool:
        """Check if the background scraper is running."""
        return self.running
    
    def run_once(self) -> int:
        """Run a single scraping cycle without starting the background service.
        
        Returns:
            Number of listings successfully scraped and saved
        """
        return self._scrape_all_websites()


def get_background_scraper() -> Optional['BackgroundScraper']:
    """Get the global background scraper instance."""
    return background_scraper_instance


def set_background_scraper(scraper: 'BackgroundScraper'):
    """Set the global background scraper instance."""
    global background_scraper_instance
    background_scraper_instance = scraper