"""
Test for telegram_chat_id to telegram_config_id migration.

This test verifies that the database can handle the migration from the old
telegram_chat_id column to the new telegram_config_id column.
"""

import tempfile
import os
import sqlite3
from pathlib import Path
from datetime import datetime

from database import DatabaseManager, TelegramConfiguration, NotificationSubscription


def test_telegram_chat_id_migration():
    """Test migration from telegram_chat_id to telegram_config_id."""
    # Create a temporary database file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_file.close()

    try:
        # First, create a database with the OLD schema (telegram_chat_id)
        conn = sqlite3.connect(temp_file.name)
        cursor = conn.cursor()

        # Create old schema with telegram_chat_id
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telegram_configurations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_token TEXT NOT NULL UNIQUE,
                bot_name TEXT,
                chat_id TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notification_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                subscription_name TEXT NOT NULL,
                search_filters TEXT NOT NULL,
                telegram_chat_id INTEGER NOT NULL,  -- OLD COLUMN NAME
                is_active BOOLEAN DEFAULT TRUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (telegram_chat_id) REFERENCES telegram_configurations(id) ON DELETE CASCADE
            )
        """)

        # Add some test data with the old schema
        cursor.execute(
            """
            INSERT INTO telegram_configurations 
                (bot_token, bot_name, chat_id, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                "123456789:TEST_TOKEN",
                "Test Bot",
                "123456789",
                True,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
            ),
        )
        config_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO notification_subscriptions 
                (user_id, subscription_name, search_filters, telegram_chat_id, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                "test_user",
                "Test Subscription",
                '{"city": "Padova"}',
                config_id,
                True,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
            ),
        )
        subscription_id = cursor.lastrowid

        conn.commit()
        conn.close()

        # Now create DatabaseManager which should trigger migration
        db_manager = DatabaseManager(db_path=Path(temp_file.name))
        db_manager.initialize_database()

        # Verify that the subscription can be retrieved (proving migration worked)
        subscriptions = db_manager.get_active_notification_subscriptions()
        assert len(subscriptions) == 1
        assert subscriptions[0].subscription_name == "Test Subscription"
        assert subscriptions[0].telegram_config_id > 0

        # Verify that we can save new subscriptions (proving the new schema works)
        new_subscription = NotificationSubscription(
            user_id="test_user_2",
            subscription_name="New Test Subscription",
            search_filters={"city": "Verona"},
            telegram_config_id=config_id,
            is_active=True,
        )

        new_subscription_id = db_manager.save_notification_subscription(
            new_subscription
        )
        assert new_subscription_id > 0

        # Verify both subscriptions exist
        all_subscriptions = db_manager.get_active_notification_subscriptions()
        assert len(all_subscriptions) == 2

        print("✓ Telegram chat ID migration test passed!")

    finally:
        # Clean up
        try:
            os.unlink(temp_file.name)
        except:
            pass


def test_new_database_schema():
    """Test that new databases use the correct schema."""
    # Create a temporary database file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_file.close()

    try:
        # Create DatabaseManager with fresh database
        db_manager = DatabaseManager(db_path=Path(temp_file.name))
        db_manager.initialize_database()

        # Create a Telegram config
        telegram_config = TelegramConfiguration(
            bot_token="123456789:TEST_TOKEN",
            bot_name="Test Bot",
            chat_id="123456789",
            is_active=True,
        )
        config_id = db_manager.save_telegram_config(telegram_config)
        assert config_id > 0

        # Create a subscription
        subscription = NotificationSubscription(
            user_id="test_user",
            subscription_name="Test Subscription",
            search_filters={"city": "Padova"},
            telegram_config_id=config_id,
            is_active=True,
        )
        subscription_id = db_manager.save_notification_subscription(subscription)
        assert subscription_id > 0

        # Verify the subscription was saved correctly
        saved_subscription = db_manager.get_notification_subscription_by_id(
            subscription_id
        )
        assert saved_subscription is not None
        assert saved_subscription.telegram_config_id == config_id

        print("✓ New database schema test passed!")

    finally:
        # Clean up
        try:
            os.unlink(temp_file.name)
        except:
            pass


def test_save_subscription_without_telegram_chat_id():
    """Test that saving subscriptions works without telegram_chat_id column."""
    # Create a temporary database file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_file.close()

    try:
        # Create DatabaseManager with fresh database
        db_manager = DatabaseManager(db_path=Path(temp_file.name))
        db_manager.initialize_database()

        # Create a Telegram config
        telegram_config = TelegramConfiguration(
            bot_token="123456789:TEST_TOKEN",
            bot_name="Test Bot",
            chat_id="123456789",
            is_active=True,
        )
        config_id = db_manager.save_telegram_config(telegram_config)

        # Create multiple subscriptions to test the save functionality
        for i in range(3):
            subscription = NotificationSubscription(
                user_id=f"test_user_{i}",
                subscription_name=f"Test Subscription {i}",
                search_filters={"city": "Padova", "min_price": i * 100000},
                telegram_config_id=config_id,
                is_active=True,
            )
            subscription_id = db_manager.save_notification_subscription(subscription)
            assert subscription_id > 0
            print(f"✓ Subscription {i} saved successfully with ID: {subscription_id}")

        # Verify all subscriptions were saved
        all_subscriptions = db_manager.get_active_notification_subscriptions()
        assert len(all_subscriptions) == 3

        print("✓ Save subscription test passed!")

    finally:
        # Clean up
        try:
            os.unlink(temp_file.name)
        except:
            pass


if __name__ == "__main__":
    print("Running telegram_chat_id migration tests...")

    test_new_database_schema()
    test_save_subscription_without_telegram_chat_id()
    test_telegram_chat_id_migration()

    print("\n=== All migration tests passed! ===")
