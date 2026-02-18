"""
=============================================================================
Mozhii RAG Data Platform - Flask Application Factory
=============================================================================
This module contains the Flask application factory function.
The factory pattern allows us to create multiple instances of the app,
which is useful for testing and running different configurations.

Architecture:
    - Flask as the web framework
    - Blueprint-based routing for modular code organization
    - Service layer for business logic separation
    - Local storage with HuggingFace sync capability
=============================================================================
"""

from flask import Flask
from flask_cors import CORS
import os

def create_app(config_name=None):
    """
    Application factory function.
    
    This function creates and configures the Flask application.
    Using a factory pattern allows for:
    - Multiple app instances with different configs
    - Better testing capabilities
    - Delayed initialization of extensions
    
    Args:
        config_name: Optional configuration name ('development', 'production', 'testing')
    
    Returns:
        Flask: Configured Flask application instance
    """
    
    # -------------------------------------------------------------------------
    # Create Flask App Instance
    # -------------------------------------------------------------------------
    # template_folder: Where HTML templates are stored
    # static_folder: Where CSS, JS, and assets are stored
    app = Flask(
        __name__,
        template_folder='../templates',
        static_folder='../static'
    )
    
    # -------------------------------------------------------------------------
    # Load Configuration
    # -------------------------------------------------------------------------
    # Import and apply configuration settings
    from .config import Config
    app.config.from_object(Config)
    
    # -------------------------------------------------------------------------
    # Initialize Extensions
    # -------------------------------------------------------------------------
    # Enable CORS for API access from different origins
    # This is important if the frontend is served from a different domain
    CORS(app)
    
    # -------------------------------------------------------------------------
    # Ensure Data Directories Exist
    # -------------------------------------------------------------------------
    # Create the directory structure for storing files locally
    # before they are pushed to HuggingFace
    data_dirs = [
        'data/pending/raw',
        'data/pending/cleaned', 
        'data/pending/chunked',
        'data/approved/raw',
        'data/approved/cleaned',
        'data/approved/chunked'
    ]
    
    for dir_path in data_dirs:
        full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), dir_path)
        os.makedirs(full_path, exist_ok=True)
    
    # -------------------------------------------------------------------------
    # Register Blueprints (Route Modules)
    # -------------------------------------------------------------------------
    # Blueprints allow us to organize routes into separate modules
    # Each tab in the UI has its own blueprint
    
    from .routes import main_bp, raw_data_bp, cleaning_bp, chunking_bp, admin_bp
    
    # Main routes (index page, etc.)
    app.register_blueprint(main_bp)
    
    # Raw Data Tab API endpoints
    app.register_blueprint(raw_data_bp, url_prefix='/api/raw')
    
    # Cleaning Tab API endpoints
    app.register_blueprint(cleaning_bp, url_prefix='/api/cleaning')
    
    # Chunking Tab API endpoints
    app.register_blueprint(chunking_bp, url_prefix='/api/chunking')
    
    # Admin approval endpoints
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
    # -------------------------------------------------------------------------
    # Return Configured App
    # -------------------------------------------------------------------------
    return app
