#!/usr/bin/env python3
"""
Flask web interface for HomeFinder
Displays property listings and allows searching/filtering
"""

from flask import Flask, render_template, request, jsonify
import logging
from datetime import datetime
from config import WEB_PORT, WEB_HOST, LOG_FILE
from database import db

# Set up logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Also log to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
logger.addHandler(console_handler)

app = Flask(__name__)

# Configure Flask
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Add datetime to template context
@app.context_processor
def inject_now():
    from datetime import datetime

    return {"now": datetime.now()}


@app.route("/")
def index():
    """
    Main page showing recent properties
    """
    try:
        # Get recent properties
        properties = db.get_recent_properties(20)

        # Get counts for filters
        total_count = db.get_property_count()
        vendita_count = len(db.search_properties(contratto="VENDITA"))
        affitto_count = len(db.search_properties(contratto="AFFITTO"))

        return render_template(
            "index.html",
            properties=properties,
            total_count=total_count,
            vendita_count=vendita_count,
            affitto_count=affitto_count,
        )

    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return render_template("error.html", error=str(e)), 500


@app.route("/search")
def search():
    """
    Search page with advanced filters
    """
    try:
        # Get search parameters
        contratto = request.args.get("contratto", "")
        prezzo_min = request.args.get("prezzo_min", "")
        prezzo_max = request.args.get("prezzo_max", "")
        mq_min = request.args.get("mq_min", "")
        locali_min = request.args.get("locali_min", "")
        classe = request.args.get("classe", "")
        search_text = request.args.get("search_text", "")

        # Build search filters
        filters = {}
        if contratto:
            filters["contratto"] = contratto
        if prezzo_min:
            filters["prezzo_min"] = int(prezzo_min)
        if prezzo_max:
            filters["prezzo_max"] = int(prezzo_max)
        if mq_min:
            filters["mq_min"] = int(mq_min)
        if locali_min:
            filters["locali_min"] = int(locali_min)
        if classe:
            filters["classe"] = classe
        if search_text:
            filters["search_text"] = search_text

        # Search properties
        properties = db.search_properties(**filters)

        return render_template(
            "search.html",
            properties=properties,
            filters=filters,
            total_results=len(properties),
        )

    except Exception as e:
        logger.error(f"Error in search route: {str(e)}")
        return render_template("error.html", error=str(e)), 500


@app.route("/property/<int:property_id>")
def property_detail(property_id: int):
    """
    Detailed view of a single property
    """
    try:
        property_data = db.get_property_by_id(property_id)

        if not property_data:
            return render_template("error.html", error="Property not found"), 404

        return render_template("property_detail.html", property=property_data)

    except Exception as e:
        logger.error(f"Error in property_detail route: {str(e)}")
        return render_template("error.html", error=str(e)), 500


@app.route("/api/properties")
def api_properties():
    """
    API endpoint to get properties as JSON
    """
    try:
        properties = db.get_all_properties()

        # Clean up the data for JSON response
        clean_properties = []
        for prop in properties:
            clean_prop = {k: v for k, v in prop.items()}
            clean_properties.append(clean_prop)

        return jsonify(
            {
                "success": True,
                "count": len(clean_properties),
                "properties": clean_properties,
            }
        )

    except Exception as e:
        logger.error(f"Error in API properties route: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/search")
def api_search():
    """
    API endpoint for searching properties
    """
    try:
        # Get search parameters
        contratto = request.args.get("contratto")
        prezzo_min = request.args.get("prezzo_min")
        prezzo_max = request.args.get("prezzo_max")

        # Build filters
        filters = {}
        if contratto:
            filters["contratto"] = contratto
        if prezzo_min:
            filters["prezzo_min"] = int(prezzo_min)
        if prezzo_max:
            filters["prezzo_max"] = int(prezzo_max)

        # Search
        properties = db.search_properties(**filters)

        return jsonify(
            {"success": True, "count": len(properties), "properties": properties}
        )

    except Exception as e:
        logger.error(f"Error in API search route: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/stats")
def stats():
    """
    Statistics page showing various metrics
    """
    try:
        total_properties = db.get_property_count()
        vendita_properties = len(db.search_properties(contratto="VENDITA"))
        affitto_properties = len(db.search_properties(contratto="AFFITTO"))

        # Get price statistics
        all_properties = db.get_all_properties()
        prices = [p["prezzo"] for p in all_properties if p["prezzo"]]

        price_stats = {}
        if prices:
            price_stats = {
                "min": min(prices),
                "max": max(prices),
                "avg": sum(prices) // len(prices),
            }

        # Get size statistics
        sizes = [p["mq"] for p in all_properties if p["mq"]]
        size_stats = {}
        if sizes:
            size_stats = {
                "min": min(sizes),
                "max": max(sizes),
                "avg": sum(sizes) // len(sizes),
            }

        return render_template(
            "stats.html",
            total_properties=total_properties,
            vendita_properties=vendita_properties,
            affitto_properties=affitto_properties,
            price_stats=price_stats,
            size_stats=size_stats,
        )

    except Exception as e:
        logger.error(f"Error in stats route: {str(e)}")
        return render_template("error.html", error=str(e)), 500


@app.route("/about")
def about():
    """
    About page with system information
    """
    return render_template("about.html")


# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template("error.html", error="Page not found"), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("error.html", error="Internal server error"), 500


if __name__ == "__main__":
    logger.info(f"Starting HomeFinder web interface on {WEB_HOST}:{WEB_PORT}")
    app.run(host=WEB_HOST, port=WEB_PORT, debug=True)
