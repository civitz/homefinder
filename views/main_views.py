from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash


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