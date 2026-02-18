"""
=============================================================================
Mozhii RAG Data Platform - Routes Package
=============================================================================
This package contains all the route blueprints for the application.
Each blueprint handles a specific part of the application:

Blueprints:
    - main_bp: Main routes (index page, static files)
    - raw_data_bp: Raw Data Tab API endpoints
    - cleaning_bp: Cleaning Tab API endpoints  
    - chunking_bp: Chunking Tab API endpoints
    - admin_bp: Admin approval and management endpoints

Usage:
    from app.routes import main_bp, raw_data_bp, ...
=============================================================================
"""

# Import all blueprints for easy access from other modules
from .main import main_bp
from .raw_data import raw_data_bp
from .cleaning import cleaning_bp
from .chunking import chunking_bp
from .admin import admin_bp

# Export all blueprints
__all__ = [
    'main_bp',
    'raw_data_bp', 
    'cleaning_bp',
    'chunking_bp',
    'admin_bp'
]
