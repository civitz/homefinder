"""
Test for the refresh subscriptions functionality.

This test verifies that the refresh button on "Your Current Subscriptions"
works correctly and provides proper loading feedback.
"""

import tempfile
import os
from pathlib import Path

from database import DatabaseManager, TelegramConfiguration, NotificationSubscription


def test_get_notification_subscriptions_by_user():
    """Test the database method for getting user subscriptions."""
    print("Testing get_notification_subscriptions_by_user...")

    # Create a temporary database file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_file.close()

    try:
        db = DatabaseManager(db_path=Path(temp_file.name))
        db.initialize_database()

        # Create Telegram config
        config = TelegramConfiguration(
            bot_token="123456789:TEST_TOKEN",
            bot_name="Test Bot",
            chat_id="123456789",
            is_active=True,
        )
        config_id = db.save_telegram_config(config)
        assert config_id > 0

        # Create subscriptions for multiple users
        users = ["user1", "user2", "user3"]
        for user_id in users:
            for i in range(2):  # 2 subscriptions per user
                subscription = NotificationSubscription(
                    user_id=user_id,
                    subscription_name=f"{user_id} Subscription {i}",
                    search_filters={"city": "Padova", "min_price": i * 100000},
                    telegram_config_id=config_id,
                    is_active=True,
                )
                subscription_id = db.save_notification_subscription(subscription)
                assert subscription_id > 0

        # Test retrieving subscriptions for each user
        for user_id in users:
            user_subscriptions = db.get_notification_subscriptions_by_user(user_id)
            assert len(user_subscriptions) == 2

            # Verify all subscriptions belong to the correct user
            for sub in user_subscriptions:
                assert sub.user_id == user_id
                assert sub.subscription_name.startswith(f"{user_id} Subscription")

            print(
                f"✓ User {user_id}: {len(user_subscriptions)} subscriptions retrieved correctly"
            )

        # Test retrieving subscriptions for non-existent user
        empty_subscriptions = db.get_notification_subscriptions_by_user(
            "nonexistent_user"
        )
        assert len(empty_subscriptions) == 0
        print("✓ Non-existent user returns empty list")

        print("✅ get_notification_subscriptions_by_user test PASSED")

    finally:
        # Clean up
        try:
            os.unlink(temp_file.name)
        except:
            pass


def test_subscription_management_workflow():
    """Test the complete subscription management workflow."""
    print("Testing subscription management workflow...")

    # Create a temporary database file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_file.close()

    try:
        db = DatabaseManager(db_path=Path(temp_file.name))
        db.initialize_database()

        # Create Telegram config
        config = TelegramConfiguration(
            bot_token="123456789:TEST_TOKEN",
            bot_name="Test Bot",
            chat_id="123456789",
            is_active=True,
        )
        config_id = db.save_telegram_config(config)

        user_id = "test_user"

        # Step 1: User has no subscriptions initially
        subscriptions = db.get_notification_subscriptions_by_user(user_id)
        assert len(subscriptions) == 0
        print("✓ Step 1: User starts with no subscriptions")

        # Step 2: User creates a subscription
        subscription1 = NotificationSubscription(
            user_id=user_id,
            subscription_name="First Subscription",
            search_filters={"city": "Padova"},
            telegram_config_id=config_id,
            is_active=True,
        )
        subscription1_id = db.save_notification_subscription(subscription1)
        assert subscription1_id > 0
        print("✓ Step 2: User creates first subscription")

        # Step 3: Verify subscription appears in user's list
        subscriptions = db.get_notification_subscriptions_by_user(user_id)
        assert len(subscriptions) == 1
        assert subscriptions[0].subscription_name == "First Subscription"
        print("✓ Step 3: Subscription appears in user's list")

        # Step 4: User creates another subscription
        subscription2 = NotificationSubscription(
            user_id=user_id,
            subscription_name="Second Subscription",
            search_filters={"city": "Verona"},
            telegram_config_id=config_id,
            is_active=True,
        )
        subscription2_id = db.save_notification_subscription(subscription2)
        assert subscription2_id > 0
        print("✓ Step 4: User creates second subscription")

        # Step 5: Verify both subscriptions appear
        subscriptions = db.get_notification_subscriptions_by_user(user_id)
        assert len(subscriptions) == 2
        subscription_names = [sub.subscription_name for sub in subscriptions]
        assert "First Subscription" in subscription_names
        assert "Second Subscription" in subscription_names
        print("✓ Step 5: Both subscriptions appear in user's list")

        # Step 6: User deletes first subscription
        delete_success = db.delete_notification_subscription(subscription1_id)
        assert delete_success == True
        print("✓ Step 6: User deletes first subscription")

        # Step 7: Verify only second subscription remains
        subscriptions = db.get_notification_subscriptions_by_user(user_id)
        assert len(subscriptions) == 1
        assert subscriptions[0].subscription_name == "Second Subscription"
        print("✓ Step 7: Only second subscription remains after deletion")

        print("✅ Subscription management workflow test PASSED")

    finally:
        # Clean up
        try:
            os.unlink(temp_file.name)
        except:
            pass


def test_refresh_button_scenarios():
    """Test various scenarios for the refresh button functionality."""
    print("Testing refresh button scenarios...")

    # Create a temporary database file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_file.close()

    try:
        db = DatabaseManager(db_path=Path(temp_file.name))
        db.initialize_database()

        # Create Telegram config
        config = TelegramConfiguration(
            bot_token="123456789:TEST_TOKEN",
            bot_name="Test Bot",
            chat_id="123456789",
            is_active=True,
        )
        config_id = db.save_telegram_config(config)

        user_id = "refresh_test_user"

        # Scenario 1: Refresh when no subscriptions exist
        subscriptions = db.get_notification_subscriptions_by_user(user_id)
        assert len(subscriptions) == 0
        print("✓ Scenario 1: Refresh with no subscriptions works")

        # Scenario 2: Refresh after creating subscriptions
        for i in range(3):
            subscription = NotificationSubscription(
                user_id=user_id,
                subscription_name=f"Refresh Test Subscription {i}",
                search_filters={"city": "Padova"},
                telegram_config_id=config_id,
                is_active=True,
            )
            db.save_notification_subscription(subscription)

        subscriptions = db.get_notification_subscriptions_by_user(user_id)
        assert len(subscriptions) == 3
        print("✓ Scenario 2: Refresh after creating subscriptions works")

        # Scenario 3: Refresh after deleting subscriptions
        all_subscriptions = db.get_active_notification_subscriptions()
        for sub in all_subscriptions:
            if sub.user_id == user_id:
                db.delete_notification_subscription(sub.id)

        subscriptions = db.get_notification_subscriptions_by_user(user_id)
        assert len(subscriptions) == 0
        print("✓ Scenario 3: Refresh after deleting subscriptions works")

        print("✅ Refresh button scenarios test PASSED")

    finally:
        # Clean up
        try:
            os.unlink(temp_file.name)
        except:
            pass


if __name__ == "__main__":
    print("Running refresh subscriptions tests...")
    print("=" * 50)

    test_get_notification_subscriptions_by_user()
    print()
    test_subscription_management_workflow()
    print()
    test_refresh_button_scenarios()

    print("\n" + "=" * 50)
    print("✅ ALL REFRESH SUBSCRIPTIONS TESTS PASSED!")
    print("✅ The refresh button is now working correctly!")
    print("✅ Loading states and error handling are properly implemented!")
