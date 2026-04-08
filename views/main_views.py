from flask import (
    Blueprint,
    render_template,
    current_app,
    request,
    redirect,
    url_for,
    flash,
)
import re
import json
from models import Configuration, ConfigType


# Create main blueprint
main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Home page route."""
    return render_template("index.html")


@main_bp.route("/about")
def about():
    """About page route."""
    return render_template("about.html")


@main_bp.route("/stats")
def stats():
    """Statistics page route."""
    try:
        from database import DatabaseManager

        db_manager = DatabaseManager()
        stats = db_manager.get_stats()
        price_distribution = db_manager.get_price_distribution()

        return render_template(
            "stats.html", stats=stats, price_distribution=price_distribution
        )
    except Exception as e:
        current_app.logger.error(f"Error loading stats page: {e}")
        return render_template(
            "stats.html",
            stats={
                "total_properties": 0,
                "average_price": 0,
                "average_size": 0,
                "last_updated": None,
            },
            price_distribution={
                "sell": {"ranges": [], "counts": []},
                "rent": {"ranges": [], "counts": []},
            },
        )


@main_bp.route("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy", "message": "HomeFinder is running"}, 200


@main_bp.route("/admin")
def admin():
    """Admin dashboard page."""
    try:
        from database import DatabaseManager

        db_manager = DatabaseManager()
        stats = db_manager.get_stats()
        scrape_history = db_manager.get_scrape_history(limit=10)

        return render_template("admin.html", stats=stats, scrape_history=scrape_history)
    except Exception as e:
        current_app.logger.error(f"Error loading admin page: {e}")
        flash(f"Error loading admin page: {e}", "error")
        return redirect(url_for("main.index"))


@main_bp.route("/admin/clear", methods=["POST"])
def admin_clear():
    """Clear all properties from database."""
    try:
        from database import DatabaseManager

        db_manager = DatabaseManager()

        # Check for confirmation
        if request.form.get("confirm") != "true":
            flash("Please confirm that you want to delete all properties.", "warning")
            return redirect(url_for("main.admin"))

        # Clear all listings
        count = db_manager.clear_all_listings()

        if count >= 0:
            flash(
                f"Successfully removed {count} properties from the database.", "success"
            )
        else:
            flash("Failed to clear properties.", "error")

        return redirect(url_for("main.admin"))

    except Exception as e:
        current_app.logger.error(f"Error clearing properties: {e}")
        flash(f"Error clearing properties: {e}", "error")
        return redirect(url_for("main.admin"))


@main_bp.route("/admin/scrape", methods=["POST"])
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

            flash(
                "Scraping launched in background. Check logs for progress.", "success"
            )
        else:
            flash(
                "Background scraper is not available. Cannot launch manual scraping.",
                "warning",
            )

        return redirect(url_for("main.admin"))

    except Exception as e:
        current_app.logger.error(f"Error triggering manual scraping: {e}")
        flash(f"Error triggering manual scraping: {e}", "error")
        return redirect(url_for("main.admin"))


@main_bp.route("/admin/telegram", methods=["GET", "POST"])
def admin_telegram():
    """Telegram configuration management (single config support)."""
    try:
        from database import DatabaseManager, TelegramConfiguration
        from notification_service import TelegramService

        db_manager = DatabaseManager()

        if request.method == "POST":
            # Handle form submission
            bot_token = request.form.get("bot_token", "").strip()
            bot_name = request.form.get("bot_name", "HomeFinder Bot").strip()
            chat_id = request.form.get("chat_id", "").strip()
            is_active = request.form.get("is_active") == "on"

            # Validate bot token format
            if not bot_token:
                flash("Bot token is required", "error")
                return redirect(url_for("main.admin_telegram"))

            # Simple validation - Telegram tokens typically start with numbers and contain colons
            if not re.match(r"^\d+:[a-zA-Z0-9_-]+$", bot_token):
                flash(
                    "Invalid Telegram bot token format. Expected format: 123456789:ABCdefGHIjklMNOPQRsTUVwxyZ",
                    "error",
                )
                return redirect(url_for("main.admin_telegram"))

            # Save configuration (always uses id=1)
            config = TelegramConfiguration(
                bot_token=bot_token,
                bot_name=bot_name,
                chat_id=chat_id,
                is_active=is_active,
            )

            config_id = db_manager.save_telegram_config(config)

            if config_id is not None and config_id > 0:
                flash("Telegram configuration saved successfully", "success")

                # Test the configuration
                telegram_service = TelegramService(db_manager, dry_run=True)
                test_success = telegram_service.send_notification(
                    int(config_id),
                    "Test notification from HomeFinder",
                    "https://example.com",
                )

                if test_success:
                    flash("Test notification sent successfully (mock mode)", "info")
                else:
                    flash("Test notification failed", "warning")
            else:
                flash("Failed to save Telegram configuration", "error")

            return redirect(url_for("main.admin_telegram"))

        # GET request - show configuration form (fetches only the single id=1 config)
        configs = db_manager.get_all_telegram_configs()
        config = configs[0] if configs else None

        # Get notification template for display
        template_config = db_manager.get_config("notification_template")
        template_json = ""
        if template_config:
            try:
                template_json = template_config.config_value
            except:
                pass

        return render_template(
            "admin_telegram.html",
            configs=configs,
            current_config=config,
            template_json=template_json,
        )
    except Exception as e:
        current_app.logger.error(f"Error in Telegram admin: {e}")
        flash(f"Error in Telegram admin: {e}", "error")
        return redirect(url_for("main.admin"))


@main_bp.route("/admin/telegram/test", methods=["POST"])
def admin_telegram_test():
    """Send a test Telegram notification using stored configuration."""
    try:
        from notification_service import TelegramService
        from database import DatabaseManager, TelegramConfiguration

        db_manager = DatabaseManager()

        config = db_manager.get_telegram_config_by_id(1)

        if not config:
            current_app.logger.error("No Telegram configuration found in database")
            return {
                "success": False,
                "message": "No Telegram configuration found. Please save a configuration first.",
            }, 400

        if not config.bot_token or not config.chat_id:
            current_app.logger.error("Telegram configuration missing required fields")
            return {
                "success": False,
                "message": "Configuration is missing bot token or chat ID.",
            }, 400

        # Get pattern from request (either form data or JSON)
        pattern = None
        if request.form.get("pattern"):
            pattern = request.form.get("pattern")
        elif (
            request.is_json
            and request.get_json(silent=True)
            and request.get_json().get("pattern")
        ):
            pattern = request.get_json().get("pattern")

        # If pattern is provided, use it with placeholder replacement
        if pattern:
            message = _replace_placeholders_in_pattern(pattern)
        else:
            message = request.form.get(
                "message", "Here is a test notification from HomeFinder"
            )

        telegram_service = TelegramService(db_manager, dry_run=False)

        if config.id:
            success = telegram_service.send_notification(
                config.id, message, "https://homefinder.app/test"
            )
        else:
            success = False

        if success:
            current_app.logger.info("Test notification sent successfully")
            return {
                "success": True,
                "message": "Test notification sent successfully!",
            }, 200
        else:
            current_app.logger.error("Failed to send test notification")
            return {
                "success": False,
                "message": "Failed to send test notification. Check logs for details.",
            }, 500

    except Exception as e:
        current_app.logger.error(f"Error sending test notification: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}, 500


def _replace_placeholders_in_pattern(pattern: str) -> str:
    """Replace placeholders in a pattern with sample data (same as frontend preview)."""
    sample_data = {
        "title": "Beautiful Apartment in City Center",
        "agency": "Tettorosso Immobiliare",
        "price": "150,000",
        "size": "85",
        "location": "Padova, Centro",
        "url": "https://example.com/property/123",
        "subscription_name": "My Search",
        "description": "Spacious 3-room apartment with modern amenities, close to all services.",
        "internal_url": "http://localhost:5000/properties/123",
    }

    message = pattern
    for key, value in sample_data.items():
        placeholder = "{" + key + "}"
        message = message.replace(placeholder, str(value))

    return message


@main_bp.route("/admin/telegram/template", methods=["POST"])
def admin_telegram_template():
    """Save notification template from Telegram page."""
    try:
        from database import DatabaseManager
        from models import Configuration, ConfigType

        db_manager = DatabaseManager()

        config_key = request.form.get("config_key", "").strip()
        config_type = request.form.get("config_type", "string").strip()
        config_value = request.form.get("config_value", "").strip()
        description = request.form.get("description", "").strip()

        if not config_key:
            flash("Configuration key is required", "error")
            return redirect(url_for("main.admin_telegram"))

        config = Configuration(
            config_key=config_key,
            config_type=ConfigType.STRING,
            config_value=config_value,
            description=description,
            is_active=True,
        )

        db_manager.save_config(config)
        flash(f"Configuration '{config_key}' saved successfully", "success")

    except Exception as e:
        current_app.logger.error(f"Error saving configuration: {e}")
        flash(f"Error: {e}", "error")

    return redirect(url_for("main.admin_telegram"))


@main_bp.route("/admin/telegram/template/reset", methods=["POST"])
def admin_telegram_template_reset():
    """Reset notification template to default (AJAX endpoint)."""
    try:
        from database import DatabaseManager
        from models import Configuration, ConfigType

        db_manager = DatabaseManager()

        # Get default template
        default_template = (
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

        # Save default template
        config = Configuration(
            config_key="notification_template",
            config_type=ConfigType.STRING,
            config_value=default_template,
            description="Default notification message template",
        )

        db_manager.save_config(config)

        response = {"success": True, "template": default_template}
        return json.dumps(response)

    except Exception as e:
        current_app.logger.error(f"Error resetting template: {e}")
        response = {"success": False, "message": str(e)}
        return json.dumps(response)


@main_bp.route("/admin/telegram/delete/<int:config_id>", methods=["POST"])
def admin_telegram_delete(config_id: int):
    """Delete Telegram configuration."""
    try:
        from database import DatabaseManager

        db_manager = DatabaseManager()

        # Check for confirmation
        if request.form.get("confirm") != "true":
            flash(
                "Please confirm that you want to delete this Telegram configuration.",
                "warning",
            )
            return redirect(url_for("main.admin_telegram"))

        # Delete configuration
        success = db_manager.delete_telegram_config(config_id)

        if success:
            flash("Telegram configuration deleted successfully", "success")
        else:
            flash("Failed to delete Telegram configuration", "error")

        return redirect(url_for("main.admin_telegram"))

    except Exception as e:
        current_app.logger.error(f"Error deleting Telegram config: {e}")
        flash(f"Error deleting Telegram config: {e}", "error")
        return redirect(url_for("main.admin_telegram"))


@main_bp.route("/admin/notifications")
def admin_notifications():
    """Notification management dashboard."""
    try:
        from database import DatabaseManager

        db_manager = DatabaseManager()

        # Get notification statistics
        recent_notifications = db_manager.get_recent_notification_history(limit=20)
        active_subscriptions = db_manager.get_active_notification_subscriptions()
        telegram_configs = db_manager.get_active_telegram_configs()

        return render_template(
            "admin_notifications.html",
            recent_notifications=recent_notifications,
            active_subscriptions=active_subscriptions,
            telegram_configs=telegram_configs,
        )

    except Exception as e:
        current_app.logger.error(f"Error loading notifications admin: {e}")
        flash(f"Error loading notifications admin: {e}", "error")
        return redirect(url_for("main.admin"))


@main_bp.route("/admin/notifications/delete/<int:subscription_id>", methods=["POST"])
def admin_notifications_delete(subscription_id: int):
    """Delete notification subscription."""
    try:
        from database import DatabaseManager

        db_manager = DatabaseManager()

        # Check for confirmation
        if request.form.get("confirm") != "true":
            flash(
                "Please confirm that you want to delete this notification subscription.",
                "warning",
            )
            return redirect(url_for("main.admin_notifications"))

        # Delete subscription
        success = db_manager.delete_notification_subscription(subscription_id)

        if success:
            flash("Notification subscription deleted successfully", "success")
        else:
            flash("Failed to delete notification subscription", "error")

        return redirect(url_for("main.admin_notifications"))

    except Exception as e:
        current_app.logger.error(f"Error deleting notification subscription: {e}")
        flash(f"Error deleting notification subscription: {e}", "error")
        return redirect(url_for("main.admin_notifications"))


@main_bp.route("/admin/configurations")
def admin_configurations():
    """Configuration management page."""
    try:
        from database import DatabaseManager
        from models import ConfigType

        db_manager = DatabaseManager()
        configs = db_manager.get_all_configs()

        # Get notification template for the template page
        template_config = db_manager.get_config("notification_template")
        template_json = ""
        if template_config:
            try:
                template_json = template_config.config_value
            except:
                pass

        return render_template(
            "admin_configurations.html",
            configs=configs,
            template_json=template_json,
            notification_enabled=db_manager.get_config("notification_enabled"),
        )
    except Exception as e:
        current_app.logger.error(f"Error loading configurations: {e}")
        flash(f"Error: {e}", "error")
        return redirect(url_for("main.admin"))


@main_bp.route("/admin/configurations", methods=["POST"])
def admin_config_save():
    """Save configuration."""
    try:
        from database import DatabaseManager
        from models import Configuration, ConfigType
        import json

        db_manager = DatabaseManager()

        config_key = request.form.get("config_key", "").strip()
        config_type = request.form.get("config_type", "string").strip()
        config_value = request.form.get("config_value", "").strip()
        description = request.form.get("description", "").strip()

        if not config_key:
            flash("Configuration key is required", "error")
            return redirect(url_for("main.admin_configurations"))

        # Validate based on type
        if config_type == "integer":
            try:
                int(config_value)
            except ValueError:
                flash("Invalid integer value", "error")
                return redirect(url_for("main.admin_configurations"))
        elif config_type == "boolean":
            config_value = (
                "true" if config_value in ("true", "1", "yes", "on") else "false"
            )
        elif config_type == "json":
            try:
                json.loads(config_value)
            except json.JSONDecodeError:
                flash("Invalid JSON value", "error")
                return redirect(url_for("main.admin_configurations"))

        config = Configuration(
            config_key=config_key,
            config_type=ConfigType(config_type),
            config_value=config_value,
            description=description,
            is_active=True,
        )

        db_manager.save_config(config)
        flash(f"Configuration '{config_key}' saved successfully", "success")

    except Exception as e:
        current_app.logger.error(f"Error saving configuration: {e}")
        flash(f"Error: {e}", "error")

    return redirect(url_for("main.admin_configurations"))


@main_bp.route("/admin/configurations/edit/<key>")
def admin_config_edit(key: str):
    """Fetch configuration details via AJAX."""
    try:
        from database import DatabaseManager

        db_manager = DatabaseManager()
        config = db_manager.get_config(key)

        if config:
            return {
                "success": True,
                "config_value": config.config_value,
                "description": config.description or "",
            }
        else:
            return {"success": False, "message": "Configuration not found"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@main_bp.route("/admin/configurations/delete/<key>", methods=["POST"])
def admin_config_delete(key: str):
    """Delete configuration."""
    try:
        from database import DatabaseManager

        if request.form.get("confirm") != "true":
            flash("Please confirm deletion", "warning")
            return redirect(url_for("main.admin_configurations"))

        db_manager = DatabaseManager()

        # Prevent deletion of critical configs
        protected_keys = ["notification_enabled", "notification_template"]
        if key in protected_keys:
            flash(f"Cannot delete protected configuration: {key}", "error")
            return redirect(url_for("main.admin_configurations"))

        if db_manager.delete_config(key):
            flash(f"Configuration '{key}' deleted", "success")
        else:
            flash(f"Configuration '{key}' not found", "warning")

    except Exception as e:
        current_app.logger.error(f"Error deleting configuration: {e}")
        flash(f"Error: {e}", "error")

    return redirect(url_for("main.admin_configurations"))


@main_bp.route("/admin/logs")
def admin_logs():
    """Admin logs viewing page."""
    from database import DatabaseManager
    from datetime import datetime, timedelta

    db_manager = DatabaseManager()

    # Parse date filters from query params
    end_date = request.args.get("end_date", datetime.now().isoformat())
    start_date = request.args.get(
        "start_date", (datetime.now() - timedelta(days=1)).isoformat()
    )
    level = request.args.get("level")
    source = request.args.get("source")
    search = request.args.get("search")
    limit = int(request.args.get("limit", 100))

    logs = db_manager.get_log_entries(
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        level=level,
        source=source,
        search=search,
    )

    # Get unique sources for dropdown
    cursor = db_manager._get_connection().cursor()
    cursor.execute("SELECT DISTINCT source FROM application_logs ORDER BY source")
    sources = [row[0] for row in cursor.fetchall()]

    return render_template(
        "admin_logs.html",
        logs=logs,
        start_date=start_date,
        end_date=end_date,
        level=level,
        source=source,
        search=search,
        sources=sources,
        levels=["DEBUG", "INFO", "WARNING", "ERROR"],
        total_count=len(logs),
    )


@main_bp.route("/admin/configurations/reset-template", methods=["POST"])
def admin_config_reset_template():
    """Reset notification template to default."""
    try:
        from database import DatabaseManager

        db_manager = DatabaseManager()

        # Get default template
        default_template = json.dumps(
            {
                "template": "🏠 *New Property Alert* 🏠\n\n🔔 *Subscription*: {subscription_name}\n\n📍 *{title}*\n🏢 *Agency*: {agency}\n💰 *Price*: €{price}\n📏 *Size*: {size} m²\n📍 *Location*: {location}\n🔗 *Details*: {url}\n📝 *Description*: {description}",
                "placeholders": {
                    "title": "Property title",
                    "agency": "Agency name",
                    "price": "Price in euros (formatted with thousands separator)",
                    "size": "Property size in square meters",
                    "location": "City and neighborhood",
                    "url": "Original property URL",
                    "subscription_name": "Name of the notification subscription",
                    "description": "Property description (truncated to 100 chars)",
                    "internal_url": "HomeFinder internal property detail URL",
                },
            }
        )

        # Save default template
        config = Configuration(
            config_key="notification_template",
            config_type=ConfigType.JSON,
            config_value=default_template,
            description="Default notification message template",
        )

        db_manager.save_config(config)

        return json.dumps({"success": True, "template": default_template})

    except Exception as e:
        current_app.logger.error(f"Error resetting template: {e}")
        return json.dumps({"success": False, "message": str(e)})
