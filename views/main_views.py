from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash
import re


# Create main blueprint
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page route."""
    return render_template('index.html')


@main_bp.route('/about')
def about():
    """About page route."""
    return render_template('about.html')


@main_bp.route('/stats')
def stats():
    """Statistics page route."""
    try:
        from database import DatabaseManager
        db_manager = DatabaseManager()
        stats = db_manager.get_stats()
        price_distribution = db_manager.get_price_distribution()
         
        return render_template('stats.html', stats=stats, price_distribution=price_distribution)
    except Exception as e:
        current_app.logger.error(f"Error loading stats page: {e}")
        return render_template('stats.html', stats={
            'total_properties': 0,
            'average_price': 0,
            'average_size': 0,
            'last_updated': None
        }, price_distribution={
            'sell': {'ranges': [], 'counts': []},
            'rent': {'ranges': [], 'counts': []}
        })


@main_bp.route('/health')
def health():
    """Health check endpoint."""
    return {"status": "healthy", "message": "HomeFinder is running"}, 200


@main_bp.route('/admin')
def admin():
    """Admin dashboard page."""
    try:
        from database import DatabaseManager
        db_manager = DatabaseManager()
        stats = db_manager.get_stats()
        scrape_history = db_manager.get_scrape_history(limit=10)
        
        return render_template('admin.html', stats=stats, scrape_history=scrape_history)
    except Exception as e:
        current_app.logger.error(f"Error loading admin page: {e}")
        flash(f"Error loading admin page: {e}", "error")
        return redirect(url_for('main.index'))


@main_bp.route('/admin/clear', methods=['POST'])
def admin_clear():
    """Clear all properties from database."""
    try:
        from database import DatabaseManager
        db_manager = DatabaseManager()
        
        # Check for confirmation
        if request.form.get('confirm') != 'true':
            flash("Please confirm that you want to delete all properties.", "warning")
            return redirect(url_for('main.admin'))
        
        # Clear all listings
        count = db_manager.clear_all_listings()
        
        if count >= 0:
            flash(f"Successfully removed {count} properties from the database.", "success")
        else:
            flash("Failed to clear properties.", "error")
            
        return redirect(url_for('main.admin'))
        
    except Exception as e:
        current_app.logger.error(f"Error clearing properties: {e}")
        flash(f"Error clearing properties: {e}", "error")
        return redirect(url_for('main.admin'))


@main_bp.route('/admin/scrape', methods=['POST'])
def admin_scrape():
    """Trigger manual scraping."""
    try:
        from background_scraper import get_background_scraper
        import logging
        
        scraper = get_background_scraper()
        
        if scraper:
            # Run scraping in background
            import threading
            logger = logging.getLogger(__name__)
            def run_scraping():
                try:
                 count = scraper.run_once(force=True)
                 logger.info(f"Manual scraping completed: {count} listings found")
                except Exception as e:
                    logger.error(f"Manual scraping failed: {e}")
            
            # Start scraping in background thread
            thread = threading.Thread(target=run_scraping, daemon=True)
            thread.start()
            
            flash("Scraping launched in background. Check logs for progress.", "success")
        else:
            flash("Background scraper is not available. Cannot launch manual scraping.", "warning")
            
        return redirect(url_for('main.admin'))
        
    except Exception as e:
        current_app.logger.error(f"Error triggering manual scraping: {e}")
        flash(f"Error triggering manual scraping: {e}", "error")
        return redirect(url_for('main.admin'))


@main_bp.route('/admin/telegram', methods=['GET', 'POST'])
def admin_telegram():
    """Telegram configuration management (single config support)."""
    try:
        from database import DatabaseManager, TelegramConfiguration
        from notification_service import TelegramService
        
        db_manager = DatabaseManager()
        
        if request.method == 'POST':
            # Handle form submission
            bot_token = request.form.get('bot_token', '').strip()
            bot_name = request.form.get('bot_name', 'HomeFinder Bot').strip()
            chat_id = request.form.get('chat_id', '').strip()
            is_active = request.form.get('is_active') == 'on'
            
            # Validate bot token format
            if not bot_token:
                flash("Bot token is required", "error")
                return redirect(url_for('main.admin_telegram'))
            
            # Simple validation - Telegram tokens typically start with numbers and contain colons
            if not re.match(r'^\d+:[a-zA-Z0-9_-]+$', bot_token):
                flash("Invalid Telegram bot token format. Expected format: 123456789:ABCdefGHIjklMNOPQRsTUVwxyZ", "error")
                return redirect(url_for('main.admin_telegram'))
            
            # Save configuration (always uses id=1)
            config = TelegramConfiguration(
                bot_token=bot_token,
                bot_name=bot_name,
                chat_id=chat_id,
                is_active=is_active
            )
            
            config_id = db_manager.save_telegram_config(config)
            
            if config_id is not None and config_id > 0:
                flash("Telegram configuration saved successfully", "success")
                
                # Test the configuration
                telegram_service = TelegramService(db_manager, dry_run=True)
                test_success = telegram_service.send_notification(
                    int(config_id),
                    "Test notification from HomeFinder",
                    "https://example.com"
                )
                
                if test_success:
                    flash("Test notification sent successfully (mock mode)", "info")
                else:
                    flash("Test notification failed", "warning")
            else:
                flash("Failed to save Telegram configuration", "error")
                
            return redirect(url_for('main.admin_telegram'))
        
        # GET request - show configuration form (fetches only the single id=1 config)
        configs = db_manager.get_all_telegram_configs()
        config = configs[0] if configs else None
        return render_template('admin_telegram.html', configs=configs, current_config=config)
    except Exception as e:
        current_app.logger.error(f"Error in Telegram admin: {e}")
        flash(f"Error in Telegram admin: {e}", "error")
        return redirect(url_for('main.admin'))


@main_bp.route('/admin/telegram/test', methods=['POST'])
def admin_telegram_test():
    """Send a test Telegram notification."""
    try:
        from notification_service import TelegramService
        from database import DatabaseManager, TelegramConfiguration
        
        # Get configuration from request form
        bot_token = request.form.get('bot_token', '').strip()
        chat_id = request.form.get('chat_id', '').strip()
        
        # Validate inputs
        if not bot_token:
            flash("Bot token is required", "error")
            return redirect(url_for('main.admin_telegram'))
            
        if not chat_id:
            flash("Chat ID is required", "error")
            return redirect(url_for('main.admin_telegram'))
        
        # Validate Telegram token format
        import re
        if not re.match(r'^\d+:[a-zA-Z0-9_-]+$', bot_token):
            flash("Invalid Telegram bot token format. Expected format: 123456789:ABCdefGHIjklMNOPQRsTUVwxyZ", "error")
            return redirect(url_for('main.admin_telegram'))
        
        # Get database manager
        db_manager = DatabaseManager()
        
        # Create a temporary Telegram service for testing
        telegram_service = TelegramService(db_manager, dry_run=False)
        
        # Create a temporary configuration for testing
        config = TelegramConfiguration(
            bot_token=bot_token,
            bot_name="Test Config",
            chat_id=chat_id,
            is_active=True
        )
        
        # Save the temporary configuration to database
        config_id = db_manager.save_telegram_config(config)
        
        if config_id > 0:
            # Get the configuration ID for testing
            test_config = db_manager.get_telegram_config_by_id(config_id)
            
            if test_config and test_config.chat_id:
                # Call TelegramService directly with the configuration
                # Note: We need to pass bot_token and chat_id directly to send_notification
                # The TelegramService will use the configured config_id if dry_run=False
                success = telegram_service._send_direct_notification(
                    bot_token=bot_token,
                    chat_id=test_config.chat_id,
                    message="Test notification from HomeFinder",
                    listing_url="https://homefinder.app/test"
                )
                
                if success:
                    flash("Test notification sent successfully! Check your Telegram chat.", "success")
                else:
                    flash("Test notification failed. Check logs for details.", "error")
            else:
                flash("Failed to send test notification. Configuration not available.", "warning")
        else:
            flash("Failed to save Telegram configuration", "error")
        
        return redirect(url_for('main.admin_telegram'))
        
    except Exception as e:
        current_app.logger.error(f"Error sending test notification: {e}")
        flash(f"Error sending test notification: {e}", "error")
        return redirect(url_for('main.admin_telegram'))


@main_bp.route('/admin/telegram/delete/<int:config_id>', methods=['POST'])
def admin_telegram_delete(config_id: int):
    """Delete Telegram configuration."""
    try:
        from database import DatabaseManager
        
        db_manager = DatabaseManager()
        
        # Check for confirmation
        if request.form.get('confirm') != 'true':
            flash("Please confirm that you want to delete this Telegram configuration.", "warning")
            return redirect(url_for('main.admin_telegram'))
        
        # Delete configuration
        success = db_manager.delete_telegram_config(config_id)
        
        if success:
            flash("Telegram configuration deleted successfully", "success")
        else:
            flash("Failed to delete Telegram configuration", "error")
            
        return redirect(url_for('main.admin_telegram'))
        
    except Exception as e:
        current_app.logger.error(f"Error deleting Telegram config: {e}")
        flash(f"Error deleting Telegram config: {e}", "error")
        return redirect(url_for('main.admin_telegram'))


@main_bp.route('/admin/notifications')
def admin_notifications():
    """Notification management dashboard."""
    try:
        from database import DatabaseManager
        
        db_manager = DatabaseManager()
        
        # Get notification statistics
        recent_notifications = db_manager.get_recent_notification_history(limit=20)
        active_subscriptions = db_manager.get_active_notification_subscriptions()
        telegram_configs = db_manager.get_active_telegram_configs()
        
        return render_template('admin_notifications.html',
                             recent_notifications=recent_notifications,
                             active_subscriptions=active_subscriptions,
                             telegram_configs=telegram_configs)
        
    except Exception as e:
        current_app.logger.error(f"Error loading notifications admin: {e}")
        flash(f"Error loading notifications admin: {e}", "error")
        return redirect(url_for('main.admin'))


@main_bp.route('/admin/notifications/delete/<int:subscription_id>', methods=['POST'])
def admin_notifications_delete(subscription_id: int):
    """Delete notification subscription."""
    try:
        from database import DatabaseManager
        
        db_manager = DatabaseManager()
        
        # Check for confirmation
        if request.form.get('confirm') != 'true':
            flash("Please confirm that you want to delete this notification subscription.", "warning")
            return redirect(url_for('main.admin_notifications'))
        
        # Delete subscription
        success = db_manager.delete_notification_subscription(subscription_id)
        
        if success:
            flash("Notification subscription deleted successfully", "success")
        else:
            flash("Failed to delete notification subscription", "error")
            
        return redirect(url_for('main.admin_notifications'))
        
    except Exception as e:
        current_app.logger.error(f"Error deleting notification subscription: {e}")
        flash(f"Error deleting notification subscription: {e}", "error")
        return redirect(url_for('main.admin_notifications'))