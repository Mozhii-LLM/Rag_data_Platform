"""
=============================================================================
Mozhii RAG Data Platform - Cleaning Routes
=============================================================================
This module handles all API endpoints for the CLEANING tab.

Workflow:
    1. Cleaner views raw files from HuggingFace (or local approved)
    2. Copies raw content and cleans it externally
    3. Pastes cleaned content with same filename
    4. Submits for admin approval
    5. Approved cleaned data is pushed to mozhii-cleaned-data repo

Endpoints:
    GET  /api/cleaning/raw-files      - List available raw files
    POST /api/cleaning/submit         - Submit cleaned data
    GET  /api/cleaning/pending        - List pending cleaned files
    GET  /api/cleaning/approved       - List approved cleaned files
    GET  /api/cleaning/file/<name>    - Get cleaned file content
=============================================================================
"""

from flask import Blueprint, request, jsonify, current_app
import os
import json
from datetime import datetime
import uuid

# -----------------------------------------------------------------------------
# Create Blueprint
# -----------------------------------------------------------------------------
cleaning_bp = Blueprint('cleaning', __name__)


# -----------------------------------------------------------------------------
# GET /api/cleaning/raw-files - List Available Raw Files
# -----------------------------------------------------------------------------
@cleaning_bp.route('/raw-files', methods=['GET'])
def list_raw_files():
    """
    List all approved raw files available for cleaning.
    
    The cleaning team can only clean files that have been:
    1. Submitted by collectors
    2. Approved by admin
    3. Pushed to mozhii-raw-data repo
    
    Returns:
        JSON: Array of raw files available for cleaning
    """
    try:
        from ..config import Config
        approved_raw_dir = Config.APPROVED_RAW_DIR
        
        raw_files = []
        
        # Get all approved raw files
        if os.path.exists(approved_raw_dir):
            for filename in os.listdir(approved_raw_dir):
                if filename.endswith('.txt'):
                    base_name = filename.replace('.txt', '')
                    meta_path = os.path.join(approved_raw_dir, f'{base_name}.meta.json')
                    
                    # Read content preview and metadata
                    content_path = os.path.join(approved_raw_dir, filename)
                    with open(content_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    metadata = {}
                    if os.path.exists(meta_path):
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    
                    # Check if already cleaned
                    cleaned_pending = os.path.exists(
                        os.path.join(Config.PENDING_CLEANED_DIR, f'{base_name}.txt')
                    )
                    cleaned_approved = os.path.exists(
                        os.path.join(Config.APPROVED_CLEANED_DIR, f'{base_name}.txt')
                    )
                    
                    raw_files.append({
                        'filename': base_name,
                        'language': metadata.get('language', 'ta'),
                        'source': metadata.get('source', 'unknown'),
                        'content_length': len(content),
                        'content_preview': content[:200] + '...' if len(content) > 200 else content,
                        'content': content,  # Full content for cleaning
                        'cleaning_status': 'approved' if cleaned_approved else ('pending' if cleaned_pending else 'not_started')
                    })
        
        return jsonify({
            'success': True,
            'files': raw_files,
            'count': len(raw_files)
        })
        
    except Exception as e:
        current_app.logger.error(f'Error listing raw files: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to list raw files'
        }), 500


# -----------------------------------------------------------------------------
# POST /api/cleaning/submit - Submit Cleaned Data
# -----------------------------------------------------------------------------
@cleaning_bp.route('/submit', methods=['POST'])
def submit_cleaned_data():
    """
    Handle cleaned data submission.
    
    Expected JSON body:
    {
        "filename": "grade_10_science",  # Must match a raw file
        "content": "Cleaned Tamil text content here..."
    }
    
    The filename MUST match an existing approved raw file
    to maintain data lineage.
    
    Returns:
        JSON: Success/error response
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'filename' not in data or 'content' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing filename or content'
            }), 400
        
        filename = data['filename'].strip()
        content = data['content']
        
        from ..config import Config
        
        # Verify that the raw file exists
        raw_path = os.path.join(Config.APPROVED_RAW_DIR, f'{filename}.txt')
        if not os.path.exists(raw_path):
            return jsonify({
                'success': False,
                'error': f'Raw file "{filename}" not found. Can only clean approved raw files.'
            }), 404
        
        # Load original metadata
        raw_meta_path = os.path.join(Config.APPROVED_RAW_DIR, f'{filename}.meta.json')
        original_metadata = {}
        if os.path.exists(raw_meta_path):
            with open(raw_meta_path, 'r', encoding='utf-8') as f:
                original_metadata = json.load(f)
        
        # Create cleaned file metadata
        cleaned_metadata = {
            'id': str(uuid.uuid4()),
            'filename': filename,
            'language': original_metadata.get('language', 'ta'),
            'source': original_metadata.get('source', 'unknown'),
            'original_raw_id': original_metadata.get('id', ''),
            'content_length': len(content),
            'submitted_at': datetime.now().isoformat(),
            'status': 'pending',
            'submitted_by': 'cleaner'
        }
        
        # Save to pending cleaned directory
        pending_dir = Config.PENDING_CLEANED_DIR
        content_path = os.path.join(pending_dir, f'{filename}.txt')
        metadata_path = os.path.join(pending_dir, f'{filename}.meta.json')
        
        # Check if already pending
        if os.path.exists(content_path):
            return jsonify({
                'success': False,
                'error': f'File "{filename}" already in cleaning queue'
            }), 409
        
        # Save files
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_metadata, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'message': 'Cleaned data submitted. Awaiting admin approval.',
            'submission_id': cleaned_metadata['id'],
            'filename': filename
        })
        
    except Exception as e:
        current_app.logger.error(f'Error submitting cleaned data: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to submit cleaned data'
        }), 500


# -----------------------------------------------------------------------------
# GET /api/cleaning/pending - List Pending Cleaned Files
# -----------------------------------------------------------------------------
@cleaning_bp.route('/pending', methods=['GET'])
def list_pending():
    """
    List all cleaned files pending admin approval.
    
    Returns:
        JSON: Array of pending cleaned file metadata
    """
    try:
        from ..config import Config
        pending_dir = Config.PENDING_CLEANED_DIR
        
        pending_files = []
        
        if os.path.exists(pending_dir):
            for filename in os.listdir(pending_dir):
                if filename.endswith('.meta.json'):
                    meta_path = os.path.join(pending_dir, filename)
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        pending_files.append(metadata)
        
        pending_files.sort(key=lambda x: x.get('submitted_at', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'files': pending_files,
            'count': len(pending_files)
        })
        
    except Exception as e:
        current_app.logger.error(f'Error listing pending cleaned files: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to list pending files'
        }), 500


# -----------------------------------------------------------------------------
# GET /api/cleaning/approved - List Approved Cleaned Files
# -----------------------------------------------------------------------------
@cleaning_bp.route('/approved', methods=['GET'])
def list_approved():
    """
    List all approved cleaned files.
    
    Returns:
        JSON: Array of approved cleaned file metadata
    """
    try:
        from ..config import Config
        approved_dir = Config.APPROVED_CLEANED_DIR
        
        approved_files = []
        
        if os.path.exists(approved_dir):
            for filename in os.listdir(approved_dir):
                if filename.endswith('.meta.json'):
                    meta_path = os.path.join(approved_dir, filename)
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        approved_files.append(metadata)
        
        approved_files.sort(key=lambda x: x.get('approved_at', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'files': approved_files,
            'count': len(approved_files)
        })
        
    except Exception as e:
        current_app.logger.error(f'Error listing approved cleaned files: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to list approved files'
        }), 500


# -----------------------------------------------------------------------------
# GET /api/cleaning/file/<filename> - Get Cleaned File Content
# -----------------------------------------------------------------------------
@cleaning_bp.route('/file/<filename>', methods=['GET'])
def get_file_content(filename):
    """
    Get content of a cleaned file.
    
    Args:
        filename: Name of the file (without extension)
    
    Returns:
        JSON: File content and metadata
    """
    try:
        from ..config import Config
        
        # Check pending first
        pending_path = os.path.join(Config.PENDING_CLEANED_DIR, f'{filename}.txt')
        pending_meta = os.path.join(Config.PENDING_CLEANED_DIR, f'{filename}.meta.json')
        
        # Check approved
        approved_path = os.path.join(Config.APPROVED_CLEANED_DIR, f'{filename}.txt')
        approved_meta = os.path.join(Config.APPROVED_CLEANED_DIR, f'{filename}.meta.json')
        
        if os.path.exists(pending_path):
            with open(pending_path, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(pending_meta, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            location = 'pending'
        elif os.path.exists(approved_path):
            with open(approved_path, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(approved_meta, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            location = 'approved'
        else:
            return jsonify({
                'success': False,
                'error': f'Cleaned file "{filename}" not found'
            }), 404
        
        return jsonify({
            'success': True,
            'filename': filename,
            'content': content,
            'metadata': metadata,
            'location': location
        })
        
    except Exception as e:
        current_app.logger.error(f'Error reading cleaned file: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to read file'
        }), 500
