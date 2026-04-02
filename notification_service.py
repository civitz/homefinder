import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import json
import requests

from database import (
    DatabaseManager,
    TelegramConfiguration,
    NotificationSubscription,
    NotificationHistory,
)
from models import Listing, Configuration, ConfigType


class TelegramService:
    """Service for sending Telegram notifications."""

    def __init__(self, db_manager: DatabaseManager, dry_run: bool = False):
        self.db_manager = db_manager
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)

    def send_notification(
        self,
        config_id: int,
        message: str,
        listing_url: str,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> tuple[bool, Optional[str]]:
        """Send notification to Telegram chat.

        Returns:
            Tuple of (success, telegram_message_id)
        """
        if self.dry_run:
            self.logger.info(
                f"[DRY RUN] Would send Telegram notification: {message[:50]}..."
            )
            return True, "mock_id"
        else:
            # If bot_token and chat_id are provided directly, use them for testing
            if bot_token and chat_id:
                return self._send_direct_notification(
                    bot_token, chat_id, message, listing_url
                )
            else:
                return self._send_real_notification(config_id, message, listing_url)

    def _send_direct_notification(
        self, bot_token: str, chat_id: str, message: str, listing_url: str
    ) -> tuple[bool, Optional[str]]:
        """Send direct Telegram notification without database lookup (for testing).

        Returns:
            Tuple of (success, telegram_message_id)
        """
        try:
            # Prepare Telegram API URL
            telegram_api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

            # Prepare message payload
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }

            # Send request to Telegram API
            response = requests.post(telegram_api_url, json=payload, timeout=30)

            # Check response
            if response.status_code == 200:
                result = response.json()
                if result.get("ok", False):
                    message_id = result.get("result", {}).get("message_id")
                    self.logger.info(
                        f"Successfully sent direct Telegram notification to chat {chat_id} (message_id: {message_id})"
                    )
                    return True, message_id
                else:
                    error_code = result.get("error_code")
                    error_message = result.get("description", "Unknown error")
                    self.logger.error(
                        f"Telegram API error {error_code}: {error_message}"
                    )
                    return False, None
            else:
                self.logger.error(
                    f"Telegram API HTTP error {response.status_code}: {response.text}"
                )
                return False, None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Telegram API request failed: {e}")
            return False, None
        except Exception as e:
            self.logger.error(f"Failed to send direct Telegram notification: {e}")
            return False, None

    def _send_real_notification(
        self, config_id: int, message: str, listing_url: str
    ) -> tuple[bool, Optional[str]]:
        """Send real Telegram notification using Telegram Bot API.

        Returns:
            Tuple of (success, telegram_message_id)
        """
        try:
            # Get active Telegram configuration
            config = self._get_telegram_config_by_id(config_id)
            if not config:
                self.logger.warning("No active Telegram configuration available")
                return False, None

            if not config.chat_id:
                self.logger.warning(
                    f"Telegram configuration {config_id} has no chat_id"
                )
                return False, None

            # Prepare Telegram API URL
            bot_token = config.bot_token
            chat_id = config.chat_id
            telegram_api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

            # Prepare message payload
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }

            # Send request to Telegram API
            response = requests.post(telegram_api_url, json=payload, timeout=30)

            # Check response
            if response.status_code == 200:
                result = response.json()
                if result.get("ok", False):
                    message_id = result.get("result", {}).get("message_id")
                    self.logger.info(
                        f"Successfully sent Telegram notification to chat {chat_id} (message_id: {message_id})"
                    )
                    return True, message_id
                else:
                    error_code = result.get("error_code")
                    error_message = result.get("description", "Unknown error")
                    self.logger.error(
                        f"Telegram API error {error_code}: {error_message}"
                    )
                    return False, None
            else:
                self.logger.error(
                    f"Telegram API HTTP error {response.status_code}: {response.text}"
                )
                return False, None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Telegram API request failed: {e}")
            return False, None
        except Exception as e:
            self.logger.error(f"Failed to send Telegram notification: {e}")
            return False, None

    def _get_telegram_config_by_id(
        self, config_id: int
    ) -> Optional[TelegramConfiguration]:
        """Get Telegram configuration by ID from database."""
        try:
            config = self.db_manager.get_telegram_config_by_id(config_id)
            return config
        except Exception as e:
            self.logger.error(f"Failed to get Telegram config {config_id}: {e}")
            return None


class NotificationEngine:
    """Engine for processing notifications and matching listings to subscriptions."""

    def __init__(self, db_manager: DatabaseManager, telegram_service: TelegramService):
        self.db_manager = db_manager
        self.telegram_service = telegram_service
        self.logger = logging.getLogger(__name__)

    def check_new_listings(
        self, since_timestamp: Optional[str] = None
    ) -> List[Listing]:
        """Find new listings that haven't been notified about."""
        try:
            from models import Listing

            # Get listings added since the given timestamp (or all listings if None)
            if since_timestamp:
                listings = self.db_manager.get_listings_since(since_timestamp)
            else:
                # First run - get all listings
                listings = self.db_manager.get_all_listings()

            # Filter out listings that have already been notified about
            return [
                l
                for l in listings
                if l.id is not None and not self._was_notified_about(l.id)
            ]
        except Exception as e:
            self.logger.error(f"Error checking new listings: {e}")
            return []

    def _get_last_notification_run_time(self) -> Optional[str]:
        """Get the timestamp of the last notification run."""
        try:
            # Get the most recent notification from history
            history = self.db_manager.get_recent_notification_history(limit=1)
            if history:
                return history[0].notification_sent_at
            return None
        except Exception as e:
            self.logger.error(f"Error getting last notification run time: {e}")
            return None

    def _was_notified_about(self, listing_id: int) -> bool:
        """Check if listing was already notified about."""
        try:
            count = self.db_manager.get_notification_count_for_listing(listing_id)
            return count > 0
        except Exception as e:
            self.logger.error(f"Error checking notification history: {e}")
            return False

    def process_new_listings(self) -> int:
        """Process new listings and send notifications."""
        try:
            # Get the timestamp of the last notification run
            last_run_time = self._get_last_notification_run_time()
            self.logger.debug(f"Checking notifications since {last_run_time}")
            # Check for new listings since last run
            new_listings = self.check_new_listings(last_run_time)
            if not new_listings:
                self.logger.debug("No new listings to notify about")
                return 0

            self.logger.info(f"Found {len(new_listings)} new listings to process")

            # Match listings to subscriptions
            matches = self.match_listings_to_subscriptions(new_listings)

            if not matches:
                self.logger.debug("No matching subscriptions found for new listings")
                return 0

            self.logger.info(f"Found {len(matches)} matches to notify")

            # Send notifications
            return self.send_notifications(matches)
        except Exception as e:
            self.logger.error(f"Error processing new listings: {e}")
            return 0

    def match_listings_to_subscriptions(self, listings: List[Listing]) -> List[Dict]:
        """Match listings to active subscriptions."""
        matches = []

        try:
            # Get all active subscriptions
            subscriptions = self.db_manager.get_active_notification_subscriptions()

            if not subscriptions:
                self.logger.debug("No active subscriptions found")
                return []

            # Match each listing to subscriptions
            for listing in listings:
                for subscription in subscriptions:
                    if self._listing_matches_subscription(listing, subscription):
                        matches.append(
                            {"listing": listing, "subscription": subscription}
                        )
                        self.logger.info(
                            f"Listing {listing.url} matches subscription {subscription.subscription_name}"
                        )

            return matches

        except Exception as e:
            self.logger.error(f"Error matching listings to subscriptions: {e}")
            return []

    def _listing_matches_subscription(
        self, listing: Listing, subscription: NotificationSubscription
    ) -> bool:
        """Check if a listing matches a subscription's search filters."""
        try:
            # Convert listing to dict for easier comparison
            listing_dict = listing.to_dict()

            # Check if search_filters is None or empty
            if not subscription.search_filters:
                return True

            # Check each filter in the subscription
            for filter_key, filter_value in subscription.search_filters.items():
                if filter_key == "city" and listing_dict.get("city") != filter_value:
                    return False
                elif filter_key == "contract_type":
                    # Handle contract_type matching - convert string to enum if needed
                    listing_contract = listing_dict.get("contract_type")
                    if isinstance(listing_contract, str):
                        # listing_contract is already a string, compare with case-insensitive matching
                        if listing_contract.lower() != str(filter_value).lower():
                            return False
                    else:
                        # listing_contract is an enum, convert to string for comparison
                        if listing_contract is not None and hasattr(
                            listing_contract, "value"
                        ):
                            if (
                                str(listing_contract.value).lower()
                                != str(filter_value).lower()
                            ):
                                return False
                        else:
                            # If listing_contract is None or doesn't have value attribute, it doesn't match
                            return False
                elif (
                    filter_key == "min_price"
                    and listing_dict.get("price", 0) < filter_value
                ):
                    return False
                elif (
                    filter_key == "max_price"
                    and listing_dict.get("price", float("inf")) > filter_value
                ):
                    return False
                elif (
                    filter_key == "min_size"
                    and listing_dict.get("square_meters", 0) < filter_value
                ):
                    return False
                # Add more filter comparisons as needed

            return True

        except Exception as e:
            self.logger.error(f"Error matching listing to subscription: {e}")
            return False

    def send_notifications(self, matches: List[Dict]) -> int:
        """Queue notifications for matched listings to be sent later."""
        queued_count = 0

        for match in matches:
            listing = match["listing"]
            subscription = match["subscription"]

            try:
                # Format notification message
                message = self._format_notification_message(
                    listing, subscription.subscription_name
                )

                # Log the expected message for debugging
                self.logger.debug(
                    f"Prepared Telegram notification message: {message[:100]}..."
                )

                # Log notification as pending (will be sent in next periodic check)
                self.db_manager.log_notification(
                    listing.id or 0,
                    subscription.id or 0,
                    telegram_message_id=None,
                    is_successful=False,
                    error_message="Pending notification for new property",
                )

                queued_count += 1
                self.logger.info(f"Queued notification for listing {listing.url}")

            except Exception as e:
                self.logger.error(
                    f"Error queuing notification for listing {listing.url}: {e}"
                )

        return queued_count

    def process_pending_notifications(self) -> int:
        """Process all pending notifications that haven't been sent yet."""
        try:
            pending = self.db_manager.get_pending_notifications()

            if not pending:
                return 0

            sent_count = 0
            for entry in pending:
                listing = self.db_manager.get_listing_by_id(entry.listing_id)
                subscription = self.db_manager.get_notification_subscription_by_id(
                    entry.subscription_id
                )

                if listing and subscription:
                    message = self._format_notification_message(
                        listing, subscription.subscription_name
                    )
                    success, message_id = self.telegram_service.send_notification(
                        subscription.telegram_config_id, message, listing.url
                    )

                    self.db_manager.log_notification(
                        listing.id,
                        subscription.id,
                        telegram_message_id=message_id,
                        is_successful=success,
                        error_message="Test notification" if not success else None,
                    )

                    if success:
                        sent_count += 1

            if sent_count > 0:
                self.logger.info(f"Sent {sent_count} pending notifications")

            return sent_count

        except Exception as e:
            self.logger.error(f"Error processing pending notifications: {e}")
            return 0

    def run_periodic_check(self, poison_pill: Any = None) -> None:
        """Run periodic notification check until poison pill is received."""
        import time

        self.logger.info("Starting periodic notification check service")

        while True:
            # Check for poison pill
            if poison_pill and hasattr(poison_pill, "is_set") and poison_pill.is_set():
                self.logger.info(
                    "Received poison pill, shutting down notification service"
                )
                break

            try:
                # Process pending notifications first
                pending_count = self.process_pending_notifications()

                # Then process new listings (which are queued)
                queued_count = self.process_new_listings()

                total_count = pending_count + queued_count
                if total_count > 0:
                    self.logger.info(
                        f"Successfully processed {total_count} notifications"
                    )
                if pending_count > 0:
                    self.logger.info(f"Sent {pending_count} pending notifications")
                if queued_count > 0:
                    self.logger.info(f"Queued {queued_count} new listings")

                # Sleep for 60 seconds before next check
                time.sleep(60)

            except KeyboardInterrupt:
                self.logger.info(
                    "Received keyboard interrupt, shutting down notification service"
                )
                break
            except Exception as e:
                self.logger.error(f"Error in periodic notification check: {e}")
                # Continue to next iteration even if there's an error
                time.sleep(60)

        self.logger.info("Periodic notification check service stopped")

    def _format_notification_message(
        self, listing: Listing, subscription_name: str = ""
    ) -> str:
        """Format a notification message for a listing using configurable template."""
        try:
            template = self._get_notification_template()
            if not template:
                template = self._get_default_template()

            agency_name = listing.get_agency_name(self.db_manager)

            internal_url = f"http://localhost:5000/properties/{listing.id}"

            location = listing.city
            if listing.neighborhood:
                location += f", {listing.neighborhood}"

            description = ""
            if listing.description:
                description = listing.description[:100]
                if len(listing.description) > 100:
                    description += "..."

            placeholders = {
                "title": listing.title,
                "agency": agency_name,
                "price": f"{listing.price:,.0f}",
                "size": str(listing.square_meters) if listing.square_meters else "N/A",
                "location": location,
                "url": listing.url,
                "subscription_name": subscription_name,
                "description": description,
                "internal_url": internal_url,
            }

            message = template
            for key, value in placeholders.items():
                placeholder = "{" + key + "}"
                message = message.replace(placeholder, str(value))

            return message

        except Exception as e:
            self.logger.error(f"Error formatting notification message: {e}")
            return self._get_default_message(listing, subscription_name)

    def _get_notification_template(self) -> str:
        """Get notification template from configuration as string."""
        try:
            config = self.db_manager.get_config("notification_template")
            if config:
                return config.config_value
        except Exception as e:
            self.logger.warning(f"Could not get notification template: {e}")
        return ""

    def _get_default_template(self) -> str:
        """Get hardcoded default template as fallback."""
        return (
            "🏠 *New Property Alert* 🏠\n\n"
            "🔔 *Subscription*: {subscription_name}\n\n"
            "📍 *{title}*\n"
            "🏢 *Agency*: {agency}\n"
            "💰 *Price*: €{price}\n"
            "📏 *Size*: {size} m²\n"
            "📍 *Location*: {location}\n"
            "🔗 *Details*: {url}\n"
            "📝 *Description*: {description}"
        )

    def _get_default_message(
        self, listing: Listing, subscription_name: str = ""
    ) -> str:
        """Get default message format as fallback."""
        try:
            agency_name = listing.get_agency_name(self.db_manager)

            message = f"🏠 *New Property Alert* 🏠\n\n"

            if subscription_name:
                message += f"🔔 *Subscription*: {subscription_name}\n"

            message += f"📍 *{listing.title}*\n"
            message += f"🏢 *Agency*: {agency_name}\n"
            message += f"💰 *Price*: €{listing.price:,.0f}\n"
            message += f"📏 *Size*: {listing.square_meters or 'N/A'} m²\n"
            message += f"📍 *Location*: {listing.city}"

            if listing.neighborhood:
                message += f", {listing.neighborhood}"
            message += "\n"

            message += f"🔗 *Details*: {listing.url}\n"
            message += (
                f"📝 *Description*: {listing.description[:100]}..."
                if listing.description
                else ""
            )

            return message

        except Exception as e:
            self.logger.error(f"Error formatting notification message: {e}")
            return f"New property available: {listing.title} - {listing.url}"
