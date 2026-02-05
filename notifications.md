# Telegram Notification System Implementation Plan

## Overview
This document outlines the detailed plan for implementing Telegram notifications for new properties in the HomeFinder application.

## 1. Database Schema Changes

### New Tables Required

#### `telegram_configurations`
```sql
CREATE TABLE telegram_configurations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_token TEXT NOT NULL UNIQUE,
    bot_name TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

#### `notification_subscriptions`
```sql
CREATE TABLE notification_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    subscription_name TEXT NOT NULL,
    search_filters TEXT NOT NULL,
    telegram_chat_id TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (telegram_chat_id) REFERENCES telegram_configurations(id)
);
```

#### `notification_history`
```sql
CREATE TABLE notification_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL,
    subscription_id INTEGER NOT NULL,
    notification_sent_at TEXT NOT NULL,
    telegram_message_id TEXT,
    is_successful BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    FOREIGN KEY (listing_id) REFERENCES listings(id),
    FOREIGN KEY (subscription_id) REFERENCES notification_subscriptions(id),
    UNIQUE(listing_id, subscription_id)
);
```

## 2. Resilient Database Hook Design

### Key Requirements
- **No Failure on Missing Configuration**: The database hook must not fail if no Telegram configuration is available
- **Graceful Degradation**: System should continue normal operation even if notification system is not configured
- **Non-blocking**: Notification processing should not block main application flow

### Implementation Strategy

```python
class DatabaseManager:
    def save_listing(self, listing: Listing) -> int:
        """Save listing with resilient notification hook."""
        try:
            # ... existing save logic ...
            
            # Resilient notification hook
            try:
                self._trigger_notification_check(listing)
            except (NoTelegramConfigurationError, NotificationServiceUnavailableError) as e:
                self.logger.warning(f"Notification service unavailable: {e}")
                # Continue normally - notifications are optional
            except Exception as e:
                self.logger.error(f"Unexpected error in notification hook: {e}")
                # Continue normally - don't let notifications break main flow
                
            return listing_id
        except sqlite3.Error as e:
            # ... existing error handling ...

    def _trigger_notification_check(self, listing: Listing) -> None:
        """Check if notifications should be sent for this listing."""
        # Check if notification system is configured
        if not self._has_active_telegram_config():
            self.logger.debug("No active Telegram configuration - skipping notifications")
            return
            
        # Check if this is a new listing (not an update)
        if not self._is_new_listing(listing):
            self.logger.debug(f"Listing {listing.url} is an update - skipping notifications")
            return
            
        # Queue notification check in background
        self._queue_notification_check(listing)

    def _has_active_telegram_config(self) -> bool:
        """Check if active Telegram configuration exists."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM telegram_configurations WHERE is_active = TRUE')
                count = cursor.fetchone()[0]
                return count > 0
        except sqlite3.Error:
            return False
```

## 3. Notification Service Architecture

### TelegramService Class
```python
class TelegramService:
    def __init__(self, db_manager: DatabaseManager, use_mock: bool = False):
        self.db_manager = db_manager
        self.use_mock = use_mock
        self.mock_api = MockTelegramAPI() if use_mock else None
        self.logger = logging.getLogger(__name__)
        
    def send_notification(self, chat_id: str, message: str, listing_url: str) -> bool:
        """Send notification to Telegram chat."""
        if self.use_mock:
            return self._send_mock_notification(chat_id, message, listing_url)
        else:
            return self._send_real_notification(chat_id, message, listing_url)
            
    def _send_real_notification(self, chat_id: str, message: str, listing_url: str) -> bool:
        """Send real Telegram notification."""
        try:
            # Get active Telegram configuration
            config = self._get_active_telegram_config()
            if not config:
                self.logger.warning("No active Telegram configuration available")
                return False
                
            # Implement actual Telegram API call
            # Use python-telegram-bot or similar library
            # Include proper error handling and retries
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to send Telegram notification: {e}")
            return False
            
    def _get_active_telegram_config(self) -> Optional[TelegramConfiguration]:
        """Get active Telegram configuration from database."""
        try:
            configs = self.db_manager.get_active_telegram_configs()
            return configs[0] if configs else None
        except Exception as e:
            self.logger.error(f"Failed to get Telegram config: {e}")
            return None
```

## 4. Notification Engine

### NotificationEngine Class
```python
class NotificationEngine:
    def __init__(self, db_manager: DatabaseManager, telegram_service: TelegramService):
        self.db_manager = db_manager
        self.telegram_service = telegram_service
        self.logger = logging.getLogger(__name__)
        
    def check_new_listings(self) -> List[Listing]:
        """Find new listings that haven't been notified about."""
        try:
            # Get listings added since last notification run
            last_run = self._get_last_notification_run_time()
            
            if last_run:
                listings = self.db_manager.get_listings_since(last_run)
            else:
                # First run - get all listings
                listings = self.db_manager.get_all_listings()
                
            return [l for l in listings if not self._was_notified_about(l.id)]
        except Exception as e:
            self.logger.error(f"Error checking new listings: {e}")
            return []
            
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
            new_listings = self.check_new_listings()
            if not new_listings:
                self.logger.debug("No new listings to notify about")
                return 0
                
            matches = self.match_listings_to_subscriptions(new_listings)
            return self.send_notifications(matches)
        except Exception as e:
            self.logger.error(f"Error processing new listings: {e}")
            return 0
```

## 5. Integration Points

### Scraper Integration
```python
# In background_scraper.py or main scraping logic

def after_scrape_hook(listings: List[Listing], db_manager: DatabaseManager):
    """Hook called after successful scraping."""
    try:
        # Check if notification system is available
        if hasattr(db_manager, 'trigger_notification_check'):
            for listing in listings:
                db_manager.trigger_notification_check(listing)
    except Exception as e:
        logger.warning(f"Notification hook failed (non-critical): {e}")
```

### Search Integration
```python
# In property_views.py

@property_bp.route('/enable-notifications', methods=['POST'])
def enable_notifications():
    """Enable Telegram notifications for current search."""
    try:
        # Get current search parameters
        search_params = request.form.to_dict()
        
        # Validate Telegram configuration exists
        telegram_config = db_manager.get_active_telegram_config()
        if not telegram_config:
            return jsonify({
                "success": False,
                "error": "No Telegram configuration available"
            }), 400
            
        # Create subscription
        subscription = NotificationSubscription(
            user_id=str(request.remote_addr),  # Or use authenticated user ID
            subscription_name=request.form.get('subscription_name', 'My Search'),
            search_filters=search_params,
            telegram_chat_id=telegram_config.id,
            is_active=True
        )
        
        subscription_id = db_manager.save_notification_subscription(subscription)
        
        return jsonify({
            "success": True,
            "subscription_id": subscription_id,
            "message": "Notifications enabled for this search"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error enabling notifications: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
```

## 6. Admin Interface Enhancements

### Telegram Configuration Management
```python
@main_bp.route('/admin/telegram', methods=['GET', 'POST'])
def admin_telegram():
    """Telegram configuration management."""
    if request.method == 'POST':
        # Handle form submission
        bot_token = request.form.get('bot_token')
        bot_name = request.form.get('bot_name', 'HomeFinder Bot')
        
        # Validate bot token
        if not self._validate_telegram_token(bot_token):
            flash("Invalid Telegram bot token", "error")
            return redirect(url_for('main.admin_telegram'))
            
        # Save configuration
        config = TelegramConfiguration(
            bot_token=bot_token,
            bot_name=bot_name,
            is_active=True
        )
        
        db_manager.save_telegram_config(config)
        flash("Telegram configuration saved successfully", "success")
        return redirect(url_for('main.admin_telegram'))
        
    # GET request - show configuration form
    configs = db_manager.get_all_telegram_configs()
    return render_template('admin_telegram.html', configs=configs)
```

## 7. Testing Strategy

### Mocked Telegram API
```python
class MockTelegramAPI:
    def __init__(self):
        self.sent_messages = []
        self.should_fail = False
        
    def send_message(self, chat_id: str, message: str) -> bool:
        """Mock Telegram message sending."""
        if self.should_fail:
            return False
            
        self.sent_messages.append({
            'chat_id': chat_id,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'success': True
        })
        
        return True
        
    def get_sent_messages(self) -> List[Dict]:
        """Get all sent messages for testing."""
        return self.sent_messages.copy()
        
    def reset(self):
        """Reset mock state."""
        self.sent_messages = []
        self.should_fail = False
```

### Test Cases

1. **Successful Notification Delivery**
   - Verify message is sent correctly
   - Check notification history is updated
   - Confirm no duplicate notifications

2. **Failed Notification Handling**
   - Test with invalid bot token
   - Simulate network errors
   - Verify retry logic works

3. **Duplicate Prevention**
   - Test same listing notified only once
   - Verify unique constraint works
   - Check cooldown period enforcement

4. **Multiple Subscriptions**
   - Test listing matching multiple subscriptions
   - Verify each subscription gets notification
   - Check notification history for each

5. **Resilience Testing**
   - Test with no Telegram configuration
   - Verify system continues normal operation
   - Check error logging

## 8. Implementation Timeline

### Phase 1: Core Infrastructure (2-3 days)
- [ ] Database schema changes
- [ ] Telegram service with mocked API
- [ ] Basic notification engine
- [ ] Resilient database hook integration
- [ ] Unit tests for core functionality

### Phase 2: Admin Interface (1-2 days)
- [ ] Telegram configuration management
- [ ] Subscription management UI
- [ ] Notification history viewer
- [ ] Test notification functionality

### Phase 3: User Interface (1-2 days)
- [ ] Search page integration
- [ ] Subscription management modal
- [ ] Notification preferences
- [ ] User feedback indicators

### Phase 4: Testing & Refinement (1-2 days)
- [ ] Comprehensive test suite
- [ ] Error handling improvements
- [ ] Performance optimization
- [ ] User feedback integration

## 9. Security Considerations

- **Token Encryption**: Store Telegram tokens encrypted in database
- **Input Validation**: Validate all user inputs thoroughly
- **Rate Limiting**: Implement rate limiting for notification API
- **Authentication**: Secure admin endpoints with proper auth
- **Error Handling**: Don't expose sensitive info in error messages

## 10. Monitoring and Maintenance

- **Logging**: Comprehensive logging of all notification activities
- **Metrics**: Track notification success/failure rates
- **Alerts**: Monitor for notification system failures
- **Retries**: Automatic retry for failed notifications
- **Cleanup**: Regular cleanup of old notification history

## Conclusion

This plan provides a robust foundation for implementing Telegram notifications in HomeFinder while ensuring:
- **Resilience**: System continues working even if notifications fail
- **No Duplicates**: Comprehensive duplicate prevention strategy
- **Testability**: Full support for mocked Telegram API testing
- **User Control**: Flexible subscription management
- **Security**: Proper handling of sensitive Telegram credentials

----------------

Addendum:
- NotificationSubscription should reference the corresponding TelegramConfiguration
- NotificationSubscription should be deleted alongside TelegramConfiguration if those are deleted
- the database.py file should not call the notificaiton service
- the database.py code should only save listings (you should move _trigger_notification_check, _has_active_telegram_config, _is_new_listing, _queue_notification_check elsewhere or remove them altogether)
- a periodic job (once every minute) should check, for each NotificationSubscription, if there are new listings available that match the query; to check whether or not the listing have been sent, it should check the NotificationHistory table; you can use database.py "get_listings_since" in the periodic job. the periodic job should basically be NotificationEngine, you can modify that class if needed. Create the thread on main.py.
- the periodic job should stop with the same poison pill as the others
- the mock telegram API should only be used in tests, please don't reference it in the production code; you can remove the MockTelegramAPI and instead rely on a "dryrun" mode for TelegramService
- be sure to move the "import" statements at the top of the files
- check whether this plan is at least partially implemented
- the telegram admin page should ask for chat id in the form when creating a telegram configuration

----------------
Addendum 2:
- telegram bot configuration form in admin/telegram should be in a card
- Current Configurations card and Next Steps card in admin/telegram should be on the right at the same level of the telegram bot configuration card
- remove the "how it works" section in /properties ui, make the "Notifications Dashboard" link a button on the right of the "enable notification for this search"

----------------
Addendum 3:
- the "Enable Notifications for This Search" button should perform the POST action on the same page via an AJAX call
- when clicking on the AJAX call, we should see a spinner on the button while the button is disabled
- when the POST call is done, a toast message should be displayed on the top of the screen with either a green checkmark o a red cross depending on the result of the call.

---------------
Addendum 4:
The current implementation of the notification service has multiple problems:
- there is a periodic log of "Ensured notification tables exist" multiple times in a row, there is probably a loop or a function that should be called once on startup and instead is being called on a regular basis
- no matter the query of the subscription, the service always says "No matching subscriptions found for new listings"
- the subscription page has a useless "user" column, which can be ignored in the UI
- the subscription should keep track of which matching property it has already notified
- when creating a subscription, it should check also for already known properties which match the filter and has not be notified to the subscription
- it should send a telegram message for each matching property of a subscription
- the subscription name should be part of the message
- the debug log should contain the expected telegram message text
