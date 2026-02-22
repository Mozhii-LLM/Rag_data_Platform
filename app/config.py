"""
=============================================================================
Mozhii RAG Data Platform - Configuration Settings
=============================================================================
This module contains all configuration settings for the application.
Settings are loaded from environment variables with sensible defaults.

Configuration Categories:
    - Flask settings (secret key, debug mode)
    - HuggingFace integration (tokens, repo names)
    - File storage paths
    - Admin credentials
=============================================================================
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """
    Main configuration class.
    
    All settings are loaded from environment variables with fallback defaults.
    This allows for different configurations in development vs production
    without changing code.
    """
    
    # -------------------------------------------------------------------------
    # Flask Core Settings
    # -------------------------------------------------------------------------
    
    # Secret key for session management and CSRF protection
    # IMPORTANT: Change this in production!
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Debug mode - enables detailed error pages and auto-reload
    # Should be False in production for security
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # -------------------------------------------------------------------------
    # HuggingFace Configuration
    # -------------------------------------------------------------------------
    
    # HuggingFace API token for authentication
    # Get yours at: https://huggingface.co/settings/tokens
    HF_TOKEN = os.getenv('HF_TOKEN', '')
    
    # Repository names for each data stage
    # Format: username/repo-name or organization/repo-name
    HF_RAW_REPO = os.getenv('HF_RAW_REPO', 'Mozhii-AI/Raw_Data')
    HF_CLEANED_REPO = os.getenv('HF_CLEANED_REPO', 'Mozhii-AI/Cleaned')
    HF_CHUNKED_REPO = os.getenv('HF_CHUNKED_REPO', 'Mozhii-AI/Chunk')
    
    # -------------------------------------------------------------------------
    # File Storage Paths
    # -------------------------------------------------------------------------
    
    # Base directory for all data storage
    # Using absolute path based on project root
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    
    # Pending files (awaiting admin approval)
    PENDING_RAW_DIR = os.path.join(DATA_DIR, 'pending', 'raw')
    PENDING_CLEANED_DIR = os.path.join(DATA_DIR, 'pending', 'cleaned')
    PENDING_CHUNKED_DIR = os.path.join(DATA_DIR, 'pending', 'chunked')
    
    # Approved files (synced with HuggingFace)
    APPROVED_RAW_DIR = os.path.join(DATA_DIR, 'approved', 'raw')
    APPROVED_CLEANED_DIR = os.path.join(DATA_DIR, 'approved', 'cleaned')
    APPROVED_CHUNKED_DIR = os.path.join(DATA_DIR, 'approved', 'chunked')
    
    # -------------------------------------------------------------------------
    # Admin Configuration
    # -------------------------------------------------------------------------
    
    # Default admin password
    # IMPORTANT: Change this in production and use proper authentication!
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
    
    # -------------------------------------------------------------------------
    # Supported Languages
    # -------------------------------------------------------------------------
    
    # List of supported languages with their codes
    SUPPORTED_LANGUAGES = {
        'ta': 'Tamil',
        'en': 'English',
        'hi': 'Hindi',
        'te': 'Telugu',
        'ml': 'Malayalam',
        'kn': 'Kannada'
    }
    
    # Default language for new submissions
    DEFAULT_LANGUAGE = 'ta'
    
    # -------------------------------------------------------------------------
    # Content Categories
    # -------------------------------------------------------------------------
    
    # Categories for organizing chunks
    CATEGORIES = [
        'education',
        'literature', 
        'news',
        'science',
        'history',
        'culture',
        'technology',
        'health',
        'legal',
        'government',
        'religion',
        'other'
    ]
    
    # -------------------------------------------------------------------------
    # Source Types
    # -------------------------------------------------------------------------
    
    # Valid source types for raw data
    SOURCE_TYPES = [
        'gov_textbook',
        'wikipedia',
        'news_article',
        'blog',
        'book',
        'research_paper',
        'manual_entry',
        'other'
    ]
