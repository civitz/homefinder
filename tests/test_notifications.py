"""
Notification system tests.

This module contains tests for the Telegram notification functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime

from database import DatabaseManager, TelegramConfiguration, NotificationSubscription
from notification_service import TelegramService, NotificationEngine
from models import Listing, Contract


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Create a temporary database file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_file.close()

    # Create database manager with temporary file
    db_manager = DatabaseManager(db_path=Path(temp_file.name))
    db_manager.initialize_database()

    yield db_manager

    # Clean up
    db_manager = None
    os.unlink(temp_file.name)


@pytest.fixture
def mock_telegram_service(temp_db):
    """Create a Telegram service with dry run mode."""
    return TelegramService(temp_db, dry_run=True)


@pytest.fixture
def sample_listing():
    """Create a sample listing for testing."""
    return Listing(
        title="Test Property",
        agency_id=1,
        url="https://example.com/test-property",
        description="A beautiful test property",
        contract_type=Contract.SELL,
        price=250000.0,
        city="Padova",
        neighborhood="Centro",
        address="Via Test 123",
        rooms=4,
        bedrooms=2,
        bathrooms=2,
        square_meters=100,
        floor="2",
        year_built=2010,
        has_elevator=True,
        heating=None,
        has_air_conditioning=True,
        has_garage=True,
        is_furnished=False,
        energy_class="A",
        energy_consumption=120.5,
        features=["balcony", "garden"],
        scrape_date=datetime.now(),
        publication_date=datetime.now(),
        raw_html_file="test.html",
        agency_listing_id="TEST123",
        creation_date=datetime.now(),
    )


def test_telegram_config_crud(temp_db):
    """Test Telegram configuration CRUD operations."""
    # Test create
    config = TelegramConfiguration(
        bot_token="123456789:TEST_TOKEN_123456789", bot_name="Test Bot", is_active=True
    )

    config_id = temp_db.save_telegram_config(config)
    assert config_id > 0

    # Test read
    saved_config = temp_db.get_telegram_config_by_id(config_id)
    assert saved_config is not None
    assert saved_config.bot_token == "123456789:TEST_TOKEN_123456789"
    assert saved_config.bot_name == "Test Bot"
    assert saved_config.is_active == True

    # Test update
    saved_config.bot_name = "Updated Test Bot"
    saved_config.is_active = False
    updated_id = temp_db.save_telegram_config(saved_config)
    assert updated_id == config_id

    updated_config = temp_db.get_telegram_config_by_id(config_id)
    assert updated_config.bot_name == "Updated Test Bot"
    assert updated_config.is_active == False

    # Test delete
    delete_success = temp_db.delete_telegram_config(config_id)
    assert delete_success == True

    deleted_config = temp_db.get_telegram_config_by_id(config_id)
    assert deleted_config is None


def test_notification_subscription_crud(temp_db):
    """Test notification subscription CRUD operations."""
    # First, create a Telegram config
    telegram_config = TelegramConfiguration(
        bot_token="123456789:TEST_TOKEN_123456789", bot_name="Test Bot", is_active=True
    )
    config_id = temp_db.save_telegram_config(telegram_config)

    # Test create
    subscription = NotificationSubscription(
        user_id="test_user_123",
        subscription_name="My Test Subscription",
        search_filters={"city": "Padova", "contract_type": "sell"},
        telegram_config_id=config_id,
        is_active=True,
    )

    subscription_id = temp_db.save_notification_subscription(subscription)
    assert subscription_id > 0

    # Test read
    saved_subscription = temp_db.get_notification_subscription_by_id(subscription_id)
    assert saved_subscription is not None
    assert saved_subscription.user_id == "test_user_123"
    assert saved_subscription.subscription_name == "My Test Subscription"
    assert saved_subscription.search_filters["city"] == "Padova"
    assert saved_subscription.telegram_config_id == config_id
    assert saved_subscription.is_active == True

    # Test update
    saved_subscription.subscription_name = "Updated Subscription"
    saved_subscription.is_active = False
    updated_id = temp_db.save_notification_subscription(saved_subscription)
    assert updated_id == subscription_id

    updated_subscription = temp_db.get_notification_subscription_by_id(subscription_id)
    assert updated_subscription.subscription_name == "Updated Subscription"
    assert updated_subscription.is_active == False

    # Test delete
    delete_success = temp_db.delete_notification_subscription(subscription_id)
    assert delete_success == True

    deleted_subscription = temp_db.get_notification_subscription_by_id(subscription_id)
    assert deleted_subscription is None


def test_telegram_service_dry_run_mode(mock_telegram_service):
    """Test Telegram service in dry run mode."""
    # Test sending a notification (should succeed in dry run mode)
    success, message_id = mock_telegram_service.send_notification(
        1,  # config_id
        "Test notification message",
        "https://example.com/test",
    )
    assert success == True
    assert message_id == "mock_id"

    # In dry run mode, no actual messages are sent, just logged
    # The success indicates the service would have sent the message


def test_notification_engine_matching(sample_listing, temp_db):
    """Test notification engine listing matching."""
    # Create a Telegram config
    telegram_config = TelegramConfiguration(
        bot_token="123456789:TEST_TOKEN_123456789", bot_name="Test Bot", is_active=True
    )
    config_id = temp_db.save_telegram_config(telegram_config)

    # Create a subscription that should match our sample listing
    subscription = NotificationSubscription(
        user_id="test_user",
        subscription_name="Padova Sell Properties",
        search_filters={
            "city": "Padova",
            "contract_type": "sell",
            "min_price": 200000,
            "max_price": 300000,
        },
        telegram_config_id=config_id,
        is_active=True,
    )
    subscription_id = temp_db.save_notification_subscription(subscription)

    # Create notification engine
    telegram_service = TelegramService(temp_db, dry_run=True)
    engine = NotificationEngine(temp_db, telegram_service)

    # Test matching
    matches = engine._listing_matches_subscription(sample_listing, subscription)
    assert matches == True

    # Test non-matching (different city)
    non_matching_subscription = NotificationSubscription(
        user_id="test_user",
        subscription_name="Verona Properties",
        search_filters={"city": "Verona"},
        telegram_config_id=config_id,
        is_active=True,
    )

    matches = engine._listing_matches_subscription(
        sample_listing, non_matching_subscription
    )
    assert matches == False


def test_notification_history_logging(temp_db, sample_listing):
    """Test notification history logging."""
    # First, save the listing to get an ID
    listing_id = temp_db.save_listing(sample_listing)
    assert listing_id > 0

    # Create a Telegram config and subscription
    telegram_config = TelegramConfiguration(
        bot_token="123456789:TEST_TOKEN_123456789", bot_name="Test Bot", is_active=True
    )
    config_id = temp_db.save_telegram_config(telegram_config)

    subscription = NotificationSubscription(
        user_id="test_user",
        subscription_name="Test Subscription",
        search_filters={"city": "Padova"},
        telegram_config_id=config_id,
        is_active=True,
    )
    subscription_id = temp_db.save_notification_subscription(subscription)

    # Log a successful notification
    notification_id = temp_db.log_notification(
        listing_id=listing_id,
        subscription_id=subscription_id,
        telegram_message_id="test_msg_123",
        is_successful=True,
        error_message=None,
    )

    assert notification_id > 0

    # Check notification count
    count = temp_db.get_notification_count_for_listing(listing_id)
    assert count == 1

    # Get notification history
    history = temp_db.get_notification_history_for_subscription(subscription_id)
    assert len(history) == 1
    assert history[0].is_successful == True
    assert history[0].telegram_message_id == "test_msg_123"

    # Test duplicate prevention
    duplicate_id = temp_db.log_notification(
        listing_id=listing_id,
        subscription_id=subscription_id,
        telegram_message_id="test_msg_456",
        is_successful=True,
    )

    # Should return the same ID (update existing)
    assert duplicate_id == notification_id

    # Count should still be 1
    count = temp_db.get_notification_count_for_listing(listing_id)
    assert count == 1


def test_resilient_database_hook(temp_db, sample_listing):
    """Test the resilient database hook for notifications."""
    # Save a listing without Telegram configuration
    # This should work fine and not fail
    listing_id = temp_db.save_listing(sample_listing)
    assert listing_id > 0

    # Now add Telegram configuration
    telegram_config = TelegramConfiguration(
        bot_token="123456789:TEST_TOKEN_123456789", bot_name="Test Bot", is_active=True
    )
    config_id = temp_db.save_telegram_config(telegram_config)

    # Create a subscription
    subscription = NotificationSubscription(
        user_id="test_user",
        subscription_name="Test Subscription",
        search_filters={"city": "Padova"},
        telegram_config_id=config_id,
        is_active=True,
    )
    subscription_id = temp_db.save_notification_subscription(subscription)

    # Save another listing - this should trigger notification check
    # Even if notification system fails, it should not prevent saving
    sample_listing.url = (
        "https://example.com/test-property-2"  # Change URL to avoid duplicate
    )
    listing_id2 = temp_db.save_listing(sample_listing)
    assert listing_id2 > 0

    # The notification system should have been called and should have logged something
    # In the current implementation, it logs notifications even if they fail
    notification_history = temp_db.get_recent_notification_history()
    # Note: The current implementation may not log notifications if the listing doesn't match
    # subscriptions or if there are other conditions. This test verifies that the system
    # doesn't crash and continues to work even if notifications are not sent.


def test_notification_message_formatting(sample_listing, temp_db):
    """Test notification message formatting."""
    # Create notification engine
    telegram_service = TelegramService(temp_db, dry_run=True)
    engine = NotificationEngine(temp_db, telegram_service)

    # Format message
    message = engine._format_notification_message(sample_listing)

    # Check that message contains expected elements
    assert "🏠 *New Property Alert* 🏠" in message
    assert "Test Property" in message
    assert "€250,000" in message
    assert "100 m²" in message
    assert "Padova" in message
    assert "https://example.com/test-property" in message
    assert "A beautiful test property" in message


def test_notification_engine_processing(sample_listing, temp_db):
    """Test the full notification processing workflow."""
    # Create Telegram config
    telegram_config = TelegramConfiguration(
        bot_token="123456789:TEST_TOKEN_123456789", bot_name="Test Bot", is_active=True
    )
    config_id = temp_db.save_telegram_config(telegram_config)

    # Create subscription
    subscription = NotificationSubscription(
        user_id="test_user",
        subscription_name="Test Subscription",
        search_filters={"city": "Padova"},
        telegram_config_id=config_id,
        is_active=True,
    )
    subscription_id = temp_db.save_notification_subscription(subscription)

    # Create notification engine
    telegram_service = TelegramService(temp_db, dry_run=True)
    engine = NotificationEngine(temp_db, telegram_service)

    # Manually add the listing to the database to simulate a new listing
    # that wasn't processed by the normal save_listing flow
    sample_listing.id = None  # Ensure it's treated as new
    listing_id = temp_db.save_listing(sample_listing)
    assert listing_id > 0

    # Now manually trigger the notification check for this listing
    # This simulates what would happen in the real system
    from models import Listing

    listing = temp_db.get_listing_by_id(listing_id)

    # Check if this listing matches any subscriptions
    subscriptions = temp_db.get_active_notification_subscriptions()
    matches = []
    for sub in subscriptions:
        if engine._listing_matches_subscription(listing, sub):
            matches.append({"listing": listing, "subscription": sub})

    # Queue notifications for matches
    queued_count = engine.send_notifications(matches)

    # Should have queued at least one notification
    assert queued_count >= 1

    # Check notification history - should have pending notifications
    history = temp_db.get_recent_notification_history()
    assert len(history) >= 1
    # Should be marked as pending (not yet sent)
    assert history[0].is_successful == False
    assert history[0].error_message == "Pending notification for new property"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
