from flask import Blueprint, render_template, request, jsonify, current_app
from typing import List, Dict, Any
from datetime import datetime


# Create property blueprint
property_bp = Blueprint('properties', __name__)


@property_bp.route('/')
def search_properties():
    """Search properties page."""
    # Get search parameters from request
    city = request.args.get('city')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    min_size = request.args.get('min_size', type=int)
    contract_type = request.args.get('contract_type')
    
    # Implement actual search logic with database
    try:
        from database import DatabaseManager
        db_manager = DatabaseManager()
        
        # Build search criteria
        search_criteria = {}
        if city:
            search_criteria['city'] = city
        if min_price:
            search_criteria['min_price'] = min_price
        if max_price:
            search_criteria['max_price'] = max_price
        if min_size:
            search_criteria['min_size'] = min_size
        if contract_type:
            search_criteria['contract_type'] = contract_type
        
        # Search database
        properties = db_manager.search_listings(**search_criteria)
        
        # Convert to simpler format for template
        properties_data = []
        for prop in properties:
            properties_data.append({
                'id': prop.id,
                'title': prop.title,
                'price': prop.price,
                'city': prop.city,
                'neighborhood': prop.neighborhood,
                'bedrooms': prop.bedrooms,
                'bathrooms': prop.bathrooms,
                'square_meters': prop.square_meters,
                'contract_type': prop.contract_type.value,
                'url': prop.url,
                'agency_listing_id': prop.agency_listing_id
            })
        
        return render_template('search.html', 
                             properties=properties_data, 
                             search_params={
                                 'city': city,
                                 'min_price': min_price,
                                 'max_price': max_price,
                                 'min_size': min_size,
                                 'contract_type': contract_type
                             })
    
    except Exception as e:
        current_app.logger.error(f"Error in property search: {e}")
        return render_template('search.html', 
                             properties=[], 
                             search_params={
                                 'city': city,
                                 'min_price': min_price,
                                 'max_price': max_price,
                                 'min_size': min_size,
                                 'contract_type': contract_type
                             })


@property_bp.route('/<int:property_id>')
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
                'id': property_id,
                'title': property_data.title,
                'price': property_data.price,
                'location': f"{property_data.city} | {property_data.neighborhood}" if property_data.neighborhood else property_data.city,
                'bedrooms': property_data.bedrooms,
                'bathrooms': property_data.bathrooms,
                'square_meters': property_data.square_meters,
                'description': property_data.description,
                'city': property_data.city,
                'neighborhood': property_data.neighborhood,
                'address': property_data.address,
                'rooms': property_data.rooms,
                'year_built': property_data.year_built,
                'floor': property_data.floor,
                'has_elevator': property_data.has_elevator,
                'heating': property_data.heating.value if property_data.heating else None,
                'has_air_conditioning': property_data.has_air_conditioning,
                'has_garage': property_data.has_garage,
                'is_furnished': property_data.is_furnished,
                'energy_class': property_data.energy_class,
                'energy_consumption': property_data.energy_consumption,
                'features': property_data.features,
                'scrape_date': property_data.scrape_date,
                'publication_date': property_data.publication_date,
                'agency': property_data.agency,
                'contract_type': property_data.contract_type.value,
                'url': property_data.url,
                'agency_listing_id': property_data.agency_listing_id
            }
            
            return render_template('property_detail.html', property=property_dict)
        else:
            return "Property not found", 404
            
    except Exception as e:
        current_app.logger.error(f"Error in property detail: {e}")
        return "Error loading property details", 500


@property_bp.route('/api/search')
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
        if 'city' in params and params['city']:
            search_criteria['city'] = params['city']
        if 'min_price' in params:
            search_criteria['min_price'] = float(params['min_price'])
        if 'max_price' in params:
            search_criteria['max_price'] = float(params['max_price'])
        if 'min_size' in params:
            search_criteria['min_size'] = int(params['min_size'])
        if 'contract_type' in params:
            search_criteria['contract_type'] = params['contract_type']
        
        # Search database
        results = db_manager.search_listings(**search_criteria)
        
        # Convert to JSON-friendly format
        results_data = []
        for prop in results:
            results_data.append({
                'id': prop.url,  # Use URL as ID
                'title': prop.title,
                'price': prop.price,
                'city': prop.city,
                'neighborhood': prop.neighborhood,
                'bedrooms': prop.bedrooms,
                'bathrooms': prop.bathrooms,
                'square_meters': prop.square_meters,
                'contract_type': prop.contract_type.value,
                'agency': prop.agency,
                'url': prop.url
            })
        
        return jsonify({
            "success": True,
            "results": results_data,
            "total": len(results_data),
            "params": params
        })
    
    except Exception as e:
        current_app.logger.error(f"Error in API search: {e}")
        # Get params from request in case of error
        error_params = request.args.to_dict()
        return jsonify({
            "success": False,
            "error": str(e),
            "results": [],
            "total": 0,
            "params": error_params
        })


@property_bp.route('/<int:property_id>/save_as_example', methods=['POST'])
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
            return jsonify({
                "success": False,
                "error": "Property not found"
            }), 404
            
        # Convert property data to dictionary format
        property_dict = property_data.to_dict()
        
        # Create a base scraper to fetch the original HTML
        scraper = BaseScraper(
            base_url=property_dict['url'],
            name="example_saver"
        )
        
        # Fetch the original HTML content
        html_content = scraper.fetch_url(property_dict['url'])
        
        if not html_content:
            return jsonify({
                "success": False,
                "error": "Failed to fetch original HTML content"
            }), 500
            
        # Save as example
        success = example_utils.save_as_example(html_content, property_dict)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Property saved as example successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to save property as example"
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error saving property as example: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500