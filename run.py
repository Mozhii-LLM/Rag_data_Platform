"""
=============================================================================
Mozhii RAG Data Platform - Application Entry Point
=============================================================================
This is the main entry point for the Flask application.
Run this file to start the development server.

Usage:
    python run.py

The server will start on http://localhost:5000 by default.
=============================================================================
"""

# Import the Flask application factory
from app import create_app

# Import environment variable loader
from dotenv import load_dotenv
import os

# -----------------------------------------------------------------------------
# Load Environment Variables
# -----------------------------------------------------------------------------
# Load variables from .env file if it exists
# This allows us to configure the app without modifying code
load_dotenv()

# -----------------------------------------------------------------------------
# Create Flask Application
# -----------------------------------------------------------------------------
# Using the application factory pattern for better testing and modularity
app = create_app()

# -----------------------------------------------------------------------------
# Run Development Server
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    # Get configuration from environment or use defaults
    debug_mode = os.getenv('DEBUG', 'True').lower() == 'true'
    port = int(os.getenv('PORT', 5000))
    
    # Print startup message
    print("=" * 60)
    print("🏗️  Mozhii RAG Data Platform v0.1")
    print("   Creating Universal Tamil AI Ecosystem")
    print("=" * 60)
    print(f"🌐 Server running at: http://localhost:{port}")
    print(f"🔧 Debug mode: {'ON' if debug_mode else 'OFF'}")
    print("=" * 60)
    
    # Start the Flask development server
    # Note: In production, use a proper WSGI server like Gunicorn
    app.run(
        host='0.0.0.0',      # Allow external connections
        port=port,            # Port number
        debug=debug_mode      # Enable/disable debug mode
    )
