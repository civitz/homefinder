from flask import Blueprint, jsonify, request
from typing import Dict, Any, List
from datetime import datetime


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
                "agency": prop.agency,
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
                "agency": property_data.agency,
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


@api_bp.route('/scrape', methods=['POST'])
def trigger_scrape():
    """Trigger manual scraping."""
    data = request.get_json() or {}
    
    # TODO: Implement scraping logic
    result = {
        "status": "not_implemented",
        "message": "Manual scraping not yet implemented",
        "params": data
    }
    
    return jsonify({
        "success": True,
        "data": result
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