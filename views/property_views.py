from flask import Blueprint, render_template, request, jsonify, current_app, session
from typing import List, Dict, Any
from datetime import datetime
import json


def get_agency_name_safe(db_manager, agency_id: int) -> str:
    """Safely get agency name, returning 'Unknown Agency' if not found."""
    if not agency_id:
        return "Unknown Agency"
    agency = db_manager.get_agency_by_id(agency_id)
    return agency.name if agency else "Unknown Agency"


# Create property blueprint
property_bp = Blueprint("properties", __name__)


@property_bp.route("/")
def search_properties():
    """Search properties page."""
    # Get search parameters from request
    city = request.args.get("city")
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    min_size = request.args.get("min_size", type=int)
    contract_type = request.args.get("contract_type")
    agency_id = request.args.get("agency_id", type=int)

    # New filter parameters
    min_bedrooms = request.args.get("min_bedrooms", type=int)
    min_bathrooms = request.args.get("min_bathrooms", type=int)
    neighborhood = request.args.get("neighborhood")
    min_year_built = request.args.get("min_year_built", type=int)
    has_air_conditioning = request.args.get("has_air_conditioning") == "on"
    has_garage = request.args.get("has_garage") == "on"
    min_energy_class = request.args.get("min_energy_class")
    heating = request.args.get("heating")
    min_rooms = request.args.get("min_rooms", type=int)

    # Sorting parameters
    sort_by = request.args.get("sort_by", "scrape_date")
    sort_order = request.args.get("sort_order", "desc")

    # Implement actual search logic with database
    try:
        from database import DatabaseManager

        db_manager = DatabaseManager()

        # Build search criteria
        search_criteria = {}
        if city:
            search_criteria["city"] = city
        if min_price:
            search_criteria["min_price"] = min_price
        if max_price:
            search_criteria["max_price"] = max_price
        if min_size:
            search_criteria["min_size"] = min_size
        if contract_type:
            search_criteria["contract_type"] = contract_type
        if agency_id:
            search_criteria["agency_id"] = agency_id
        if min_bedrooms:
            search_criteria["min_bedrooms"] = min_bedrooms
        if min_bathrooms:
            search_criteria["min_bathrooms"] = min_bathrooms
        if neighborhood:
            search_criteria["neighborhood"] = neighborhood
        if min_year_built:
            search_criteria["min_year_built"] = min_year_built
        if has_air_conditioning:
            search_criteria["has_air_conditioning"] = has_air_conditioning
        if has_garage:
            search_criteria["has_garage"] = has_garage
        if min_energy_class:
            search_criteria["min_energy_class"] = min_energy_class
        if heating:
            search_criteria["heating"] = heating
        if min_rooms:
            search_criteria["min_rooms"] = min_rooms

        # Add sorting parameters
        search_criteria["sort_by"] = sort_by
        search_criteria["sort_order"] = sort_order

        # Search database
        properties = db_manager.search_listings(**search_criteria)

        # Convert to simpler format for template
        properties_data = []
        for prop in properties:
            properties_data.append(
                {
                    "id": prop.id,
                    "title": prop.title,
                    "price": prop.price,
                    "city": prop.city,
                    "neighborhood": prop.neighborhood,
                    "bedrooms": prop.bedrooms,
                    "bathrooms": prop.bathrooms,
                    "square_meters": prop.square_meters,
                    "contract_type": prop.contract_type.value,
                    "url": prop.url,
                    "agency_listing_id": prop.agency_listing_id,
                    "agency_id": prop.agency_id,
                    "energy_class": prop.energy_class,
                    "year_built": prop.year_built,
                    "floor": prop.floor,
                }
            )

        # Get all agencies for dropdown
        agencies = db_manager.get_all_agencies()

        # Check if Telegram notifications are available
        telegram_available = len(db_manager.get_active_telegram_configs()) > 0

        return render_template(
            "search.html",
            properties=properties_data,
            search_params={
                "city": city,
                "min_price": min_price,
                "max_price": max_price,
                "min_size": min_size,
                "contract_type": contract_type,
                "agency_id": agency_id,
                "min_bedrooms": min_bedrooms,
                "min_bathrooms": min_bathrooms,
                "neighborhood": neighborhood,
                "min_year_built": min_year_built,
                "has_air_conditioning": has_air_conditioning,
                "has_garage": has_garage,
                "min_energy_class": min_energy_class,
                "heating": heating,
                "min_rooms": min_rooms,
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
            agencies=agencies,
            telegram_available=telegram_available,
        )

    except Exception as e:
        current_app.logger.error(f"Error in property search: {e}")
        return render_template(
            "search.html",
            properties=[],
            search_params={
                "city": city,
                "min_price": min_price,
                "max_price": max_price,
                "min_size": min_size,
                "contract_type": contract_type,
                "agency_id": agency_id,
                "min_bedrooms": min_bedrooms,
                "min_bathrooms": min_bathrooms,
                "neighborhood": neighborhood,
                "min_year_built": min_year_built,
                "has_air_conditioning": has_air_conditioning,
                "has_garage": has_garage,
                "min_energy_class": min_energy_class,
                "heating": heating,
                "min_rooms": min_rooms,
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
            agencies=[],
            telegram_available=False,
        )


@property_bp.route("/<int:property_id>")
def property_detail(property_id: int):
    """Property detail page."""
    try:
        from database import DatabaseManager

        db_manager = DatabaseManager()

        # Fetch property from database by ID
        property_data = db_manager.get_listing_by_id(property_id)

        if property_data:
            # Convert to simpler format for template
            property_dict = {
                "id": property_id,
                "title": property_data.title,
                "price": property_data.price,
                "location": f"{property_data.city} | {property_data.neighborhood}"
                if property_data.neighborhood
                else property_data.city,
                "bedrooms": property_data.bedrooms,
                "bathrooms": property_data.bathrooms,
                "square_meters": property_data.square_meters,
                "description": property_data.description,
                "city": property_data.city,
                "neighborhood": property_data.neighborhood,
                "address": property_data.address,
                "rooms": property_data.rooms,
                "year_built": property_data.year_built,
                "floor": property_data.floor,
                "has_elevator": property_data.has_elevator,
                "heating": property_data.heating.value
                if property_data.heating
                else None,
                "has_air_conditioning": property_data.has_air_conditioning,
                "has_garage": property_data.has_garage,
                "is_furnished": property_data.is_furnished,
                "energy_class": property_data.energy_class,
                "energy_consumption": property_data.energy_consumption,
                "features": property_data.features,
                "scrape_date": property_data.scrape_date,
                "publication_date": property_data.publication_date,
                "modify_date": property_data.modify_date,
                "agency_id": property_data.agency_id,
                "agency": get_agency_name_safe(db_manager, property_data.agency_id),
                "contract_type": property_data.contract_type.value,
                "url": property_data.url,
                "agency_listing_id": property_data.agency_listing_id,
            }

            return render_template("property_detail.html", property=property_dict)
        else:
            return "Property not found", 404

    except Exception as e:
        current_app.logger.error(f"Error in property detail: {e}")
        return "Error loading property details", 500


@property_bp.route("/<int:property_id>", methods=["PUT"])
def update_property(property_id: int):
    """Update a property listing."""
    try:
        from database import DatabaseManager
        from datetime import datetime

        db_manager = DatabaseManager()

        # Get JSON data from request
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        # Validate that we have at least some data to update
        if not data or len(data) == 0:
            return jsonify({"success": False, "error": "No update data provided"}), 400

        # Convert data types appropriately
        update_data = {}

        # Handle string fields
        string_fields = [
            "title",
            "description",
            "city",
            "neighborhood",
            "address",
            "floor",
            "energy_class",
            "contract_type",
            "heating",
            "features",
            "raw_html_file",
            "agency_listing_id",
        ]
        for field in string_fields:
            if field in data:
                update_data[field] = (
                    str(data[field]) if data[field] is not None else None
                )

        # Handle numeric fields
        numeric_fields = [
            "price",
            "rooms",
            "bedrooms",
            "bathrooms",
            "square_meters",
            "year_built",
            "energy_consumption",
        ]
        for field in numeric_fields:
            if field in data:
                try:
                    if data[field] is not None:
                        if field in ["price", "energy_consumption"]:
                            update_data[field] = float(data[field])
                        else:
                            update_data[field] = int(data[field])
                except (ValueError, TypeError):
                    # Skip invalid numeric values
                    continue

        # Handle boolean fields
        boolean_fields = [
            "has_elevator",
            "has_air_conditioning",
            "has_garage",
            "is_furnished",
        ]
        for field in boolean_fields:
            if field in data:
                update_data[field] = (
                    bool(data[field]) if data[field] is not None else None
                )

        # Handle date fields
        if "publication_date" in data and data["publication_date"]:
            try:
                update_data["publication_date"] = datetime.fromisoformat(
                    data["publication_date"]
                ).isoformat()
            except (ValueError, TypeError):
                # Skip invalid date values
                pass

        # Update the listing in database
        success = db_manager.update_listing(property_id, update_data)

        if not success:
            return jsonify(
                {"success": False, "error": "Failed to update property"}
            ), 500

        # After successful update, automatically save as example
        # Fetch the updated property data
        updated_property = db_manager.get_listing_by_id(property_id)
        if updated_property:
            # Convert to dict and call save_as_example endpoint
            property_dict = updated_property.to_dict()

            # Fetch original HTML content using BaseScraper
            from scraper import BaseScraper

            scraper = BaseScraper(base_url=property_dict["url"], name="example_saver")
            html_content = scraper.fetch_url(property_dict["url"])

            if html_content:
                from example_utils import ExampleUtils

                example_utils = ExampleUtils()
                example_utils.save_as_example(html_content, property_dict)

        return jsonify({"success": True, "message": "Property updated successfully"})

    except Exception as e:
        current_app.logger.error(f"Error updating property {property_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@property_bp.route("/api/search")
def api_search():
    """API endpoint for property search."""
    try:
        # Get search parameters
        params = request.args.to_dict()

        # Implement actual database search
        from database import DatabaseManager

        db_manager = DatabaseManager()

        # Convert params to search criteria
        search_criteria = {}
        if "city" in params and params["city"]:
            search_criteria["city"] = params["city"]
        if "min_price" in params:
            search_criteria["min_price"] = float(params["min_price"])
        if "max_price" in params:
            search_criteria["max_price"] = float(params["max_price"])
        if "min_size" in params:
            search_criteria["min_size"] = int(params["min_size"])
        if "contract_type" in params:
            search_criteria["contract_type"] = params["contract_type"]

        if "agency_id" in params:
            search_criteria["agency_id"] = int(params["agency_id"])

        # New filter parameters
        if "min_bedrooms" in params:
            search_criteria["min_bedrooms"] = int(params["min_bedrooms"])
        if "min_bathrooms" in params:
            search_criteria["min_bathrooms"] = int(params["min_bathrooms"])
        if "neighborhood" in params and params["neighborhood"]:
            search_criteria["neighborhood"] = params["neighborhood"]
        if "min_year_built" in params:
            search_criteria["min_year_built"] = int(params["min_year_built"])
        if "has_air_conditioning" in params:
            search_criteria["has_air_conditioning"] = (
                params["has_air_conditioning"] == "true"
            )
        if "has_garage" in params:
            search_criteria["has_garage"] = params["has_garage"] == "true"
        if "min_energy_class" in params and params["min_energy_class"]:
            search_criteria["min_energy_class"] = params["min_energy_class"]
        if "heating" in params and params["heating"]:
            search_criteria["heating"] = params["heating"]
        if "min_rooms" in params:
            search_criteria["min_rooms"] = int(params["min_rooms"])

        # Add sorting parameters
        search_criteria["sort_by"] = params.get("sort_by", "scrape_date")
        search_criteria["sort_order"] = params.get("sort_order", "desc")

        # Search database
        results = db_manager.search_listings(**search_criteria)

        # Convert to JSON-friendly format
        results_data = []
        for prop in results:
            results_data.append(
                {
                    "id": prop.url,  # Use URL as ID
                    "title": prop.title,
                    "price": prop.price,
                    "city": prop.city,
                    "neighborhood": prop.neighborhood,
                    "bedrooms": prop.bedrooms,
                    "bathrooms": prop.bathrooms,
                    "square_meters": prop.square_meters,
                    "contract_type": prop.contract_type.value,
                    "agency_id": prop.agency_id,
                    "url": prop.url,
                }
            )

        return jsonify(
            {
                "success": True,
                "results": results_data,
                "total": len(results_data),
                "params": params,
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error in API search: {e}")
        # Get params from request in case of error
        error_params = request.args.to_dict()
        return jsonify(
            {
                "success": False,
                "error": str(e),
                "results": [],
                "total": 0,
                "params": error_params,
            }
        )


@property_bp.route("/<int:property_id>/save_as_example", methods=["POST"])
def save_as_example(property_id: int):
    """Save a property listing as an example."""
    try:
        from database import DatabaseManager
        from scraper import BaseScraper
        from example_utils import ExampleUtils

        db_manager = DatabaseManager()
        example_utils = ExampleUtils()

        # Fetch property from database by ID
        property_data = db_manager.get_listing_by_id(property_id)

        if not property_data:
            return jsonify({"success": False, "error": "Property not found"}), 404

        # Convert property data to dictionary format
        property_dict = property_data.to_dict()

        # Create a base scraper to fetch the original HTML
        scraper = BaseScraper(base_url=property_dict["url"], name="example_saver")

        # Fetch the original HTML content
        html_content = scraper.fetch_url(property_dict["url"])

        if not html_content:
            return jsonify(
                {"success": False, "error": "Failed to fetch original HTML content"}
            ), 500

        # Save as example
        success = example_utils.save_as_example(html_content, property_dict)

        if success:
            return jsonify(
                {"success": True, "message": "Property saved as example successfully"}
            )
        else:
            return jsonify(
                {"success": False, "error": "Failed to save property as example"}
            ), 500

    except Exception as e:
        current_app.logger.error(f"Error saving property as example: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@property_bp.route("/enable-notifications", methods=["POST"])
def enable_notifications():
    """Enable Telegram notifications for current search."""
    try:
        from database import DatabaseManager, NotificationSubscription
        from notification_service import TelegramService

        db_manager = DatabaseManager()

        # Get current search parameters
        search_params = request.form.to_dict()
        subscription_name = request.form.get("subscription_name", "My Search")

        # Validate Telegram configuration exists
        telegram_configs = db_manager.get_active_telegram_configs()
        if not telegram_configs:
            return jsonify(
                {
                    "success": False,
                    "error": "No Telegram configuration available. Please configure Telegram bot first.",
                }
            ), 400

        # Get the first active Telegram configuration
        telegram_config = telegram_configs[0]

        # Ensure we have a valid config ID
        if telegram_config.id is None:
            return jsonify(
                {"success": False, "error": "Telegram configuration ID is invalid"}
            ), 500

        # Create subscription
        subscription = NotificationSubscription(
            user_id=str(request.remote_addr),  # Or use authenticated user ID
            subscription_name=subscription_name,
            search_filters=search_params,
            telegram_config_id=int(
                telegram_config.id
            ),  # Cast to int since we checked it's not None
            is_active=True,
        )

        subscription_id = db_manager.save_notification_subscription(subscription)

        if subscription_id > 0:
            # Test the notification service
            telegram_service = TelegramService(db_manager, dry_run=True)
            test_message = (
                f"🎉 New notification subscription created: {subscription_name}"
            )
            test_success = telegram_service.send_notification(
                int(telegram_config.id),  # Cast to int since we checked it's not None
                test_message,
                "https://example.com",
            )

            if test_success:
                return jsonify(
                    {
                        "success": True,
                        "subscription_id": subscription_id,
                        "message": "Notifications enabled for this search",
                        "test_sent": True,
                    }
                )
            else:
                return jsonify(
                    {
                        "success": True,
                        "subscription_id": subscription_id,
                        "message": "Notifications enabled for this search (test notification failed)",
                        "test_sent": False,
                    }
                )
        else:
            return jsonify(
                {
                    "success": False,
                    "error": "Failed to create notification subscription",
                }
            ), 500

    except Exception as e:
        current_app.logger.error(f"Error enabling notifications: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@property_bp.route("/my-subscriptions")
def my_subscriptions():
    """Get current user's notification subscriptions."""
    try:
        from database import DatabaseManager

        db_manager = DatabaseManager()
        user_id = str(request.remote_addr)  # Or use authenticated user ID

        subscriptions = db_manager.get_notification_subscriptions_by_user(user_id)

        # Convert to JSON-friendly format
        subscriptions_data = []
        for sub in subscriptions:
            subscriptions_data.append(
                {
                    "id": sub.id,
                    "subscription_name": sub.subscription_name,
                    "search_filters": sub.search_filters,
                    "is_active": sub.is_active,
                    "created_at": sub.created_at,
                    "updated_at": sub.updated_at,
                }
            )

        return jsonify(
            {
                "success": True,
                "subscriptions": subscriptions_data,
                "count": len(subscriptions_data),
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error getting user subscriptions: {e}")
        return jsonify({"success": False, "error": str(e), "subscriptions": []}), 500


@property_bp.route("/subscription/<int:subscription_id>", methods=["DELETE"])
def delete_subscription(subscription_id: int):
    """Delete a notification subscription."""
    try:
        from database import DatabaseManager

        db_manager = DatabaseManager()
        user_id = str(request.remote_addr)  # Or use authenticated user ID

        # Verify this subscription belongs to the current user
        subscription = db_manager.get_notification_subscription_by_id(subscription_id)
        if not subscription:
            return jsonify({"success": False, "error": "Subscription not found"}), 404

        if subscription.user_id != user_id:
            return jsonify(
                {
                    "success": False,
                    "error": "You can only delete your own subscriptions",
                }
            ), 403

        # Delete the subscription
        success = db_manager.delete_notification_subscription(subscription_id)

        if success:
            return jsonify(
                {"success": True, "message": "Subscription deleted successfully"}
            )
        else:
            return jsonify(
                {"success": False, "error": "Failed to delete subscription"}
            ), 500

    except Exception as e:
        current_app.logger.error(f"Error deleting subscription: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
