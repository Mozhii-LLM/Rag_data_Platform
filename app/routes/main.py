"""
=============================================================================
Mozhii RAG Data Platform - Main Routes
=============================================================================
This module contains the main routes for serving the application.
These routes handle:
    - Serving the main index.html page
    - Health check endpoint
    - Configuration endpoint for frontend

The main blueprint uses no URL prefix, so routes are at the root level.
=============================================================================
"""

from flask import Blueprint, render_template, jsonify, current_app

# -----------------------------------------------------------------------------
# Create Blueprint
# -----------------------------------------------------------------------------
# Blueprints are Flask's way of organizing related routes
# 'main' is the blueprint name, __name__ helps Flask find resources
main_bp = Blueprint('main', __name__)


# -----------------------------------------------------------------------------
# Index Route - Serve Main Application
# -----------------------------------------------------------------------------
@main_bp.route('/')
def index():
    """
    Serve the main application page.
    
    This is the entry point for the web application.
    The index.html template contains the complete SPA (Single Page Application)
    with all three tabs: RAW DATA, CLEANING, and CHUNKING.
    
    Returns:
        HTML: The rendered index.html template
    """
    return render_template('index.html')


# -----------------------------------------------------------------------------
# Health Check Endpoint
# -----------------------------------------------------------------------------
@main_bp.route('/health')
def health_check():
    """
    Health check endpoint for monitoring.
    
    This endpoint is useful for:
    - Load balancer health checks
    - Monitoring systems (Prometheus, etc.)
    - Deployment verification
    
    Returns:
        JSON: Status object with 'ok' status and version info
    """
    return jsonify({
        'status': 'ok',
        'version': '0.1.0',
        'platform': 'Mozhii RAG Data Platform'
    })


# -----------------------------------------------------------------------------
# Frontend Configuration Endpoint
# -----------------------------------------------------------------------------
@main_bp.route('/api/config')
def get_config():
    """
    Provide configuration to the frontend.
    
    This endpoint exposes safe configuration values that the frontend
    needs to operate. Sensitive values like tokens are NOT exposed.
    
    Returns:
        JSON: Configuration object with languages, categories, sources
    """
    from ..config import Config
    
    return jsonify({
        'languages': Config.SUPPORTED_LANGUAGES,
        'defaultLanguage': Config.DEFAULT_LANGUAGE,
        'categories': Config.CATEGORIES,
        'sourceTypes': Config.SOURCE_TYPES,
        'hfRepos': {
            'raw': Config.HF_RAW_REPO,
            'cleaned': Config.HF_CLEANED_REPO,
            'chunked': Config.HF_CHUNKED_REPO
        }
    })
