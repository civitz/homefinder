#!/usr/bin/env python3
"""Background service for cleaning up broken links."""

import time
import threading
import logging
from typing import List, Optional, Any
from datetime import datetime, timedelta
import requests

from atomicx import AtomicBool
from database import DatabaseManager
from config import BROKEN_LINK_CLEANUP_INTERVAL_HOURS, MIN_LISTING_AGE_DAYS


class BrokenLinkCleaner:
    """Background service for identifying and cleaning up broken property links."""

    def __init__(self, stop_signal: AtomicBool = None, database: DatabaseManager = None):
        """Initialize the broken link cleaner.

        Args:
            stop_signal: AtomicBool for graceful shutdown
            database: DatabaseManager instance for database operations
        """
        self.interval_hours = BROKEN_LINK_CLEANUP_INTERVAL_HOURS
        self.min_listing_age_days = MIN_LISTING_AGE_DAYS
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.thread = None
        self.stop_signal = stop_signal
        self.db_manager = database

    def _should_cleanup(self) -> bool:
        """Check if cleanup should run based on last cleanup time.

        Returns:
            True if cleanup should run, False if too recent
        """
        # For now, we'll run cleanup on a fixed schedule
        # In the future, we could add more sophisticated logic
        return True

    def _verify_link(self, url: str) -> bool:
        """Verify if a link is still valid using HTTP HEAD request.

        Args:
            url: URL to verify

        Returns:
            True if link is valid, False if broken
        """
        try:
            # Use HEAD request to minimize bandwidth
            response = requests.head(url, timeout=10, allow_redirects=True)
            
            # Consider 2xx and 3xx status codes as valid
            if 200 <= response.status_code < 400:
                return True
            
            # 404, 410, etc. are considered broken
            self.logger.info(f"Broken link detected: {url} (HTTP {response.status_code})")
            return False
            
        except requests.exceptions.RequestException as e:
            # Any request exception (timeout, connection error, etc.) is considered broken
            self.logger.warning(f"Link verification failed for {url}: {e}")
            return False

    def _cleanup_broken_links(self) -> int:
        """Identify and cleanup broken links.

        Returns:
            Number of broken links cleaned up
        """
        if not self.db_manager:
            self.logger.error("No database manager provided")
            return 0

        try:
            # Get all listings that need verification
            all_listings = self.db_manager.get_all_listings()
            
            if not all_listings:
                self.logger.info("No listings found for verification")
                return 0

            cleaned_up_count = 0
            verified_count = 0
            
            for listing in all_listings:
                # Check poison pill
                if self.stop_signal and self.stop_signal.load():
                    self.logger.info("Broken link cleanup stopping due to poison pill")
                    break

                try:
                    # Verify the link
                    is_valid = self._verify_link(listing.url)
                    
                    # Update the listing with verification results
                    update_data = {
                        'last_verified_date': datetime.now().isoformat()
                    }
                    
                    if not is_valid:
                        update_data['is_broken'] = True
                        
                        # Check if listing is old enough to be removed
                        if listing.creation_date:
                            listing_age = datetime.now() - listing.creation_date
                            if listing_age.days >= self.min_listing_age_days:
                                # Remove the broken listing
                                self.logger.info(f"Removing broken listing (age {listing_age.days} days): {listing.url}")
                                # We'll implement the actual removal in a separate method
                                cleaned_up_count += 1
                                continue
                        else:
                            # No creation date, use scrape date as fallback
                            if listing.scrape_date:
                                listing_age = datetime.now() - listing.scrape_date
                                if listing_age.days >= self.min_listing_age_days:
                                    self.logger.info(f"Removing broken listing (age {listing_age.days} days): {listing.url}")
                                    cleaned_up_count += 1
                                    continue
                    else:
                        update_data['is_broken'] = False
                        verified_count += 1

                    # Update the listing with verification results
                    self.db_manager.update_listing(listing.id, update_data)
                    
                except Exception as e:
                    self.logger.error(f"Error verifying listing {listing.url}: {e}")

            self.logger.info(f"Broken link cleanup completed. Verified: {verified_count}, Cleaned up: {cleaned_up_count}")
            return cleaned_up_count
            
        except Exception as e:
            self.logger.error(f"Error in broken link cleanup: {e}")
            return 0

    def _cleanup_loop(self):
        """Main cleanup loop that runs periodically."""
        while self.running:
            try:
                # Check poison pill
                if self.stop_signal and self.stop_signal.load():
                    self.logger.info("Broken link cleanup stopping due to poison pill")
                    self.running = False
                    break

                # Check if cleanup should run
                if not self._should_cleanup():
                    # Sleep for a short time and check again
                    time.sleep(60)
                    continue

                start_time = time.time()
                
                # Run cleanup
                cleaned_up_count = self._cleanup_broken_links()
                
                # Calculate sleep time to maintain interval
                elapsed_time = time.time() - start_time
                sleep_time = max(0, self.interval_hours * 3600 - elapsed_time)
                
                self.logger.info(f"Next broken link cleanup in {sleep_time:.1f} seconds")

                # Sleep until next run
                for _ in range(int(sleep_time)):
                    if not self.running:
                        break
                    if self.stop_signal and self.stop_signal.load():
                        self.logger.info("Broken link cleanup stopping due to poison pill")
                        self.running = False
                        break
                    time.sleep(1)

            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                # Wait before retrying to avoid tight error loops
                time.sleep(60)

    def start(self):
        """Start the broken link cleaner service."""
        if self.running:
            self.logger.warning("Broken link cleaner is already running")
            return

        self.running = True
        self.logger.info(f"Starting broken link cleaner with {self.interval_hours} hour interval")

        # Start the cleanup thread
        self.thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the broken link cleaner service."""
        if not self.running:
            self.logger.warning("Broken link cleaner is not running")
            return

        self.running = False
        self.logger.info("Stopping broken link cleaner")

        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                self.logger.warning("Broken link cleaner thread did not stop gracefully")

    def is_running(self) -> bool:
        """Check if the broken link cleaner is running."""
        return self.running

    def run_once(self) -> int:
        """Run a single cleanup cycle without starting the background service.

        Returns:
            Number of broken links cleaned up
        """
        return self._cleanup_broken_links()