from flask import Blueprint, render_template, current_app


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
    return render_template('stats.html')


@main_bp.route('/health')
def health():
    """Health check endpoint."""
    return {"status": "healthy", "message": "HomeFinder is running"}, 200