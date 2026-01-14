from flask import Flask
from config import FLASK_SECRET_KEY, FLASK_DEBUG, DEBUG
import logging
from logging.handlers import RotatingFileHandler
import os


def create_app():
    """Create and configure Flask application."""
    app = Flask(__name__)
    
    # Configure Flask
    app.secret_key = FLASK_SECRET_KEY
    app.config['DEBUG'] = DEBUG
    
    # Configure logging
    configure_logging(app)
    
    # Register blueprints
    from views.main_views import main_bp
    from views.property_views import property_bp
    from views.api_views import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(property_bp, url_prefix='/properties')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Create uploads directory if it doesn't exist
    os.makedirs('uploads', exist_ok=True)
    
    return app


def configure_logging(app: Flask):
    """Configure logging for the application."""
    # Remove default handlers
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)
    
    # Create rotating file handler
    file_handler = RotatingFileHandler(
        'homefinder.log', 
        maxBytes=1024 * 1024 * 5,  # 5 MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if DEBUG else logging.INFO)
    
    # Create formatter and add it to handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to the logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)
    
    # Log startup information
    app.logger.info('HomeFinder application starting...')
    app.logger.info(f'Debug mode: {DEBUG}')


#if __name__ == '__main__':
#    app.run(host='0.0.0.0', port=5000, debug=DEBUG)