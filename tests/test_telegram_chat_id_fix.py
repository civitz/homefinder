"""
Test to verify the fix for the telegram_chat_id constraint error.

This test reproduces the exact scenario that was causing the error:
"NOT NULL constraint failed: notification_subscriptions.telegram_chat_id"
"""

import tempfile
import os
import sqlite3
from pathlib import Path
from datetime import datetime

from database import DatabaseManager, TelegramConfiguration, NotificationSubscription


def test_save_subscription_with_old_schema():
    """Test saving subscriptions when database has old telegram_chat_id schema."""
    print("Testing save subscription with old schema...")
    
    # Create a temporary database file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_file.close()
    
    try:
        # First, create a database with the OLD schema (telegram_chat_id)
        conn = sqlite3.connect(temp_file.name)
        cursor = conn.cursor()
        
        # Create old schema with telegram_chat_id
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS telegram_configurations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_token TEXT NOT NULL UNIQUE,
                bot_name TEXT,
                chat_id TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
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
        ''')
        
        # Add some test data with the old schema
        cursor.execute('''
            INSERT INTO telegram_configurations 
                (bot_token, bot_name, chat_id, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('123456789:TEST_TOKEN', 'Test Bot', '123456789', True, datetime.now().isoformat(), datetime.now().isoformat()))
        config_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        # Now try to save a new subscription using DatabaseManager
        # This should trigger the migration and then work correctly
        db_manager = DatabaseManager(db_path=Path(temp_file.name))
        
        # This is the operation that was failing before the fix
        subscription = NotificationSubscription(
            user_id='test_user',
            subscription_name='Test Subscription',
            search_filters={'city': 'Padova'},
            telegram_config_id=config_id,
            is_active=True
        )
        
        # This should NOT raise "NOT NULL constraint failed: notification_subscriptions.telegram_chat_id"
        subscription_id = db_manager.save_notification_subscription(subscription)
        
        assert subscription_id > 0, f"Expected subscription_id > 0, got {subscription_id}"
        
        # Verify the subscription was saved correctly
        saved_subscription = db_manager.get_notification_subscription_by_id(subscription_id)
        assert saved_subscription is not None
        assert saved_subscription.subscription_name == 'Test Subscription'
        assert saved_subscription.telegram_config_id == config_id
        
        print("✓ Successfully saved subscription with old schema after migration!")
        
    finally:
        # Clean up
        try:
            os.unlink(temp_file.name)
        except:
            pass


def test_save_subscription_with_new_schema():
    """Test saving subscriptions with new schema (should work without migration)."""
    print("Testing save subscription with new schema...")
    
    # Create a temporary database file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_file.close()
    
    try:
        # Create DatabaseManager with fresh database (new schema)
        db_manager = DatabaseManager(db_path=Path(temp_file.name))
        
        # Create a Telegram config
        telegram_config = TelegramConfiguration(
            bot_token='123456789:TEST_TOKEN',
            bot_name='Test Bot',
            chat_id='123456789',
            is_active=True
        )
        config_id = db_manager.save_telegram_config(telegram_config)
        
        # Create a subscription - this should work without any migration
        subscription = NotificationSubscription(
            user_id='test_user',
            subscription_name='Test Subscription',
            search_filters={'city': 'Padova'},
            telegram_config_id=config_id,
            is_active=True
        )
        
        subscription_id = db_manager.save_notification_subscription(subscription)
        
        assert subscription_id > 0, f"Expected subscription_id > 0, got {subscription_id}"
        
        # Verify the subscription was saved correctly
        saved_subscription = db_manager.get_notification_subscription_by_id(subscription_id)
        assert saved_subscription is not None
        assert saved_subscription.subscription_name == 'Test Subscription'
        assert saved_subscription.telegram_config_id == config_id
        
        print("✓ Successfully saved subscription with new schema!")
        
    finally:
        # Clean up
        try:
            os.unlink(temp_file.name)
        except:
            pass


def test_multiple_subscriptions_after_migration():
    """Test saving multiple subscriptions after migration."""
    print("Testing multiple subscriptions after migration...")
    
    # Create a temporary database file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_file.close()
    
    try:
        # Create old schema with telegram_chat_id
        conn = sqlite3.connect(temp_file.name)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS telegram_configurations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_token TEXT NOT NULL UNIQUE,
                bot_name TEXT,
                chat_id TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                subscription_name TEXT NOT NULL,
                search_filters TEXT NOT NULL,
                telegram_chat_id INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (telegram_chat_id) REFERENCES telegram_configurations(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            INSERT INTO telegram_configurations 
                (bot_token, bot_name, chat_id, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('123456789:TEST_TOKEN', 'Test Bot', '123456789', True, datetime.now().isoformat(), datetime.now().isoformat()))
        config_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        # Create DatabaseManager which should trigger migration
        db_manager = DatabaseManager(db_path=Path(temp_file.name))
        
        # Save multiple subscriptions after migration
        for i in range(3):
            subscription = NotificationSubscription(
                user_id=f'test_user_{i}',
                subscription_name=f'Test Subscription {i}',
                search_filters={'city': 'Padova', 'min_price': i * 100000},
                telegram_config_id=config_id,
                is_active=True
            )
            
            subscription_id = db_manager.save_notification_subscription(subscription)
            assert subscription_id > 0, f"Failed to save subscription {i}"
            print(f"✓ Subscription {i} saved successfully")
        
        # Verify all subscriptions were saved
        all_subscriptions = db_manager.get_active_notification_subscriptions()
        assert len(all_subscriptions) == 3, f"Expected 3 subscriptions, got {len(all_subscriptions)}"
        
        print("✓ All subscriptions saved successfully after migration!")
        
    finally:
        # Clean up
        try:
            os.unlink(temp_file.name)
        except:
            pass


if __name__ == "__main__":
    print("Running telegram_chat_id fix tests...")
    print("=" * 50)
    
    test_save_subscription_with_new_schema()
    test_save_subscription_with_old_schema()
    test_multiple_subscriptions_after_migration()
    
    print("\n" + "=" * 50)
    print("✅ ALL TESTS PASSED! The telegram_chat_id issue is fixed!")
    print("✅ Subscriptions can now be saved without constraint errors!")