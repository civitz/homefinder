from flask import Blueprint, jsonify, request, current_app
from typing import Dict, Any, List
from datetime import datetime, timedelta


# Create API blueprint
api_bp = Blueprint('api', __name__)


@api_bp.route('/properties', methods=['GET'])
def get_properties():
    """Get all properties."""
    # Implement database query
    try:
        from database import DatabaseManager
        db_manager = DatabaseManager()
        
        # Get all properties from database
        properties = db_manager.get_all_listings()
        
        # Convert to JSON-friendly format
        properties_data = []
        for prop in properties:
            properties_data.append({
                "id": prop.id,
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
                "agency_listing_id": prop.agency_listing_id
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "data": [],
            "count": 0
        })
    
    return jsonify({
        "success": True,
        "data": properties,
        "count": len(properties)
    })


@api_bp.route('/properties/<int:property_id>', methods=['GET'])
def get_property(property_id: int):
    """Get single property by ID."""
    # Implement database query
    try:
        from database import DatabaseManager
        db_manager = DatabaseManager()
        
        # Fetch property from database by ID
        property_data = db_manager.get_listing_by_id(property_id)
        
        if property_data:
            # Convert to JSON-friendly format
            property_dict = {
                "id": property_id,
                "title": property_data.title,
                "price": property_data.price,
                "city": property_data.city,
                "neighborhood": property_data.neighborhood,
                "bedrooms": property_data.bedrooms,
                "bathrooms": property_data.bathrooms,
                "square_meters": property_data.square_meters,
                "contract_type": property_data.contract_type.value,
                "agency_id": property_data.agency_id,
                "url": property_data.url,
                "agency_listing_id": property_data.agency_listing_id,
                "description": property_data.description
            }
            
            return jsonify({
                "success": True,
                "data": property_dict
            })
        else:
            return jsonify({
                "success": False,
                "error": "Property not found",
                "data": None
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "data": None
        })
    
    return jsonify({
        "success": True,
        "data": property_data
    })


@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get statistics about properties."""
    # Implement statistics calculation
    try:
        from database import DatabaseManager
        db_manager = DatabaseManager()
        
        # Get statistics from database
        stats = db_manager.get_stats()
        
        return jsonify({
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "stats": {
                "total_properties": 0,
                "average_price": 0,
                "average_size": 0,
                "last_updated": None
            }
        })
    
    return jsonify({
        "success": True,
        "stats": stats
    })


@api_bp.route('/scrape', methods=['GET'])
def get_scrape_status():
    """Get scrape status and history."""
    try:
        from database import DatabaseManager
        from config import MIN_SCRAPE_INTERVAL_SECONDS
        from datetime import datetime
        
        db_manager = DatabaseManager()
        
        # Get last scrape time
        last_scrape_time = db_manager.get_last_scrape_time()
        
        # Calculate next scrape time
        next_scrape_time = None
        if last_scrape_time:
            time_since_last = (datetime.now() - last_scrape_time).total_seconds()
            if time_since_last < MIN_SCRAPE_INTERVAL_SECONDS:
                remaining_seconds = MIN_SCRAPE_INTERVAL_SECONDS - time_since_last
                next_scrape_time = datetime.now() + timedelta(seconds=remaining_seconds)
            else:
                # Should scrape now
                next_scrape_time = datetime.now()
        else:
            # No previous scrape, can scrape now
            next_scrape_time = datetime.now()
        
        # Get scrape history
        scrape_history = db_manager.get_scrape_history(limit=10)
        
        return jsonify({
            "success": True,
            "data": {
                "last_scrape": last_scrape_time.isoformat() if last_scrape_time else None,
                "next_scrape": next_scrape_time.isoformat() if next_scrape_time else None,
                "interval_seconds": MIN_SCRAPE_INTERVAL_SECONDS,
                "history": scrape_history
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "data": {
                "last_scrape": None,
                "next_scrape": None,
                "interval_seconds": 3600,  # Default value if config import fails
                "history": []
            }
        })

@api_bp.route('/scrape', methods=['POST'])
def trigger_scrape():
    """Trigger manual scraping."""
    data = request.get_json() or {}
    
    try:
        from background_scraper import get_background_scraper
        import threading
        import logging
        
        scraper = get_background_scraper()
        
        if scraper:
            # Set urgent request flag instead of calling run_once directly
            # This allows the background scraper to handle it with proper coordination
            if scraper.urgent_request_pending.load():
                logging.warning("Ignoring urgent scrape request - one already pending")
                result = {
                    "status": "ignored",
                    "message": "Urgent scrape request already pending",
                    "params": data
                }
                return jsonify({
                    "success": False,
                    "data": result
                })
            
            scraper.urgent_request_pending.store(True)
            logging.info("Urgent scrape request set, will be processed by background scraper")
            
            result = {
                "status": "queued",
                "message": "Urgent scrape request queued for processing",
                "params": data
            }
            
            return jsonify({
                "success": True,
                "data": result
            })
        else:
            result = {
                "status": "error",
                "message": "Background scraper is not available",
                "params": data
            }
            
            return jsonify({
                "success": False,
                "data": result
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "data": {
                "status": "error",
                "message": "Failed to trigger scraping",
                "params": data
            }
        })


@api_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "success": False,
        "error": "Not found",
        "message": str(error)
    }), 404


@api_bp.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    return jsonify({
        "success": False,
        "error": "Server error",
        "message": str(error)
    }), 500


@api_bp.route('/clear', methods=['POST'])
def clear_properties():
    """Clear all properties from database."""
    try:
        from database import DatabaseManager
        db_manager = DatabaseManager()
        
        # Check for confirmation in request
        data = request.get_json() or {}
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({
                "success": False,
                "error": "Confirmation required",
                "message": "Please set confirm=true to delete all properties"
            })
        
        # Clear all listings
        count = db_manager.clear_all_listings()
        
        if count >= 0:
            return jsonify({
                "success": True,
                "message": f"Successfully removed {count} properties from the database",
                "count": count
            })
        else:
            return jsonify({
                "success": False,
                "error": "Database error",
                "message": "Failed to clear properties"
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to clear properties"
        })