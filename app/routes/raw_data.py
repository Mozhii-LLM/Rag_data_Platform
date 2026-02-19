"""
=============================================================================
Mozhii RAG Data Platform - Raw Data Routes
=============================================================================
This module handles all API endpoints for the RAW DATA tab.

Workflow:
    1. Collector submits raw Tamil content via UI
    2. Data is saved locally in pending/raw directory
    3. Admin reviews and approves the submission
    4. Approved data is pushed to HuggingFace mozhii-raw-data repo

Endpoints:
    POST /api/raw/submit     - Submit new raw data
    GET  /api/raw/pending    - List pending submissions
    GET  /api/raw/approved   - List approved files
    GET  /api/raw/file/<id>  - Get specific file content
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
raw_data_bp = Blueprint('raw_data', __name__)


# -----------------------------------------------------------------------------
# Helper Function: Generate Metadata
# -----------------------------------------------------------------------------
def generate_metadata(filename, language, source, content):
    """
    Generate metadata object for a raw data submission.
    
    Args:
        filename: Name of the file (without extension)
        language: Language code (e.g., 'ta' for Tamil)
        source: Source type (e.g., 'gov_textbook')
        content: The actual text content
    
    Returns:
        dict: Metadata object with all required fields
    """
    return {
        'id': str(uuid.uuid4()),                    # Unique identifier
        'filename': filename,                         # File name
        'language': language,                         # Language code
        'source': source,                             # Source type
        'content_length': len(content),               # Character count
        'submitted_at': datetime.now().isoformat(),   # Submission timestamp
        'status': 'approved',                         # Auto-approved
        'submitted_by': 'collector'                   # Role (for audit)
    }


# -----------------------------------------------------------------------------
# POST /api/raw/submit - Submit New Raw Data
# -----------------------------------------------------------------------------
@raw_data_bp.route('/submit', methods=['POST'])
def submit_raw_data():
    """
    Handle raw data submission from the UI.
    
    Expected JSON body:
    {
        "filename": "grade_10_science",
        "language": "ta",
        "source": "gov_textbook",
        "content": "Tamil text content here..."
    }
    
    The data is saved locally and queued for admin approval.
    It is NOT pushed to HuggingFace until approved.
    
    Returns:
        JSON: Success/error response with submission ID
    """
    try:
        # Get JSON data from request
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['filename', 'language', 'source', 'content']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Extract fields
        filename = data['filename'].strip()
        language = data['language']
        source = data['source']
        content = data['content']
        
        # Validate filename (no special characters)
        if not filename.replace('_', '').replace('-', '').isalnum():
            return jsonify({
                'success': False,
                'error': 'Filename can only contain letters, numbers, underscores, and hyphens'
            }), 400
        
        # Generate metadata
        metadata = generate_metadata(filename, language, source, content)
        
        # Get approved directory path from config
        from ..config import Config
        approved_dir = Config.APPROVED_RAW_DIR
        
        # Create file paths
        content_path = os.path.join(approved_dir, f'{filename}.txt')
        metadata_path = os.path.join(approved_dir, f'{filename}.meta.json')
        
        # Check if file already exists
        if os.path.exists(content_path):
            return jsonify({
                'success': False,
                'error': f'File "{filename}" already exists'
            }), 409
        
        # Save content file locally
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Save metadata file locally
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # --- Push to HuggingFace immediately ---
        hf_result = {'success': False, 'error': 'HuggingFace not attempted'}
        try:
            from ..services.huggingface import HuggingFaceService
            hf_service = HuggingFaceService()
            if hf_service.is_configured():
                hf_result = hf_service.upload_raw_file(filename, content, metadata)
                current_app.logger.info(f'HuggingFace upload result: {hf_result}')
            else:
                hf_result = {'success': False, 'error': 'HF_TOKEN not configured'}
                current_app.logger.warning('HuggingFace not configured, skipping upload')
        except Exception as hf_err:
            hf_result = {'success': False, 'error': str(hf_err)}
            current_app.logger.error(f'HuggingFace upload error: {hf_err}')
        
        # Return success response
        return jsonify({
            'success': True,
            'message': 'Raw data submitted and approved successfully.',
            'submission_id': metadata['id'],
            'filename': filename,
            'huggingface': hf_result
        })
        
    except Exception as e:
        # Log error and return error response
        current_app.logger.error(f'Error submitting raw data: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred. Please try again.'
        }), 500


# -----------------------------------------------------------------------------
# GET /api/raw/pending - List Pending Submissions
# -----------------------------------------------------------------------------
@raw_data_bp.route('/pending', methods=['GET'])
def list_pending():
    """
    List all raw data files pending admin approval.
    
    Returns:
        JSON: Array of pending file metadata
    """
    try:
        from ..config import Config
        pending_dir = Config.PENDING_RAW_DIR
        
        pending_files = []
        
        # Iterate through all .meta.json files in pending directory
        if os.path.exists(pending_dir):
            for filename in os.listdir(pending_dir):
                if filename.endswith('.meta.json'):
                    meta_path = os.path.join(pending_dir, filename)
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        pending_files.append(metadata)
        
        # Sort by submission time (newest first)
        pending_files.sort(key=lambda x: x.get('submitted_at', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'files': pending_files,
            'count': len(pending_files)
        })
        
    except Exception as e:
        current_app.logger.error(f'Error listing pending files: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to list pending files'
        }), 500


# -----------------------------------------------------------------------------
# GET /api/raw/approved - List Approved Files
# -----------------------------------------------------------------------------
@raw_data_bp.route('/approved', methods=['GET'])
def list_approved():
    """
    List all approved raw data files.
    
    These files have been approved by admin and synced to HuggingFace.
    
    Returns:
        JSON: Array of approved file metadata
    """
    try:
        from ..config import Config
        approved_dir = Config.APPROVED_RAW_DIR
        
        approved_files = []
        
        # Iterate through all .meta.json files in approved directory
        if os.path.exists(approved_dir):
            for filename in os.listdir(approved_dir):
                if filename.endswith('.meta.json'):
                    meta_path = os.path.join(approved_dir, filename)
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        approved_files.append(metadata)
        
        # Sort by approval time (newest first)
        approved_files.sort(key=lambda x: x.get('approved_at', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'files': approved_files,
            'count': len(approved_files)
        })
        
    except Exception as e:
        current_app.logger.error(f'Error listing approved files: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to list approved files'
        }), 500


# -----------------------------------------------------------------------------
# GET /api/raw/file/<filename> - Get Specific File Content
# -----------------------------------------------------------------------------
@raw_data_bp.route('/file/<filename>', methods=['GET'])
def get_file_content(filename):
    """
    Get the content of a specific raw data file.
    
    Checks both pending and approved directories.
    
    Args:
        filename: Name of the file (without .txt extension)
    
    Returns:
        JSON: File content and metadata
    """
    try:
        from ..config import Config
        
        # Check pending directory first
        pending_content_path = os.path.join(Config.PENDING_RAW_DIR, f'{filename}.txt')
        pending_meta_path = os.path.join(Config.PENDING_RAW_DIR, f'{filename}.meta.json')
        
        # Check approved directory
        approved_content_path = os.path.join(Config.APPROVED_RAW_DIR, f'{filename}.txt')
        approved_meta_path = os.path.join(Config.APPROVED_RAW_DIR, f'{filename}.meta.json')
        
        content = None
        metadata = None
        location = None
        
        # Try pending first
        if os.path.exists(pending_content_path):
            with open(pending_content_path, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(pending_meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            location = 'pending'
        # Try approved
        elif os.path.exists(approved_content_path):
            with open(approved_content_path, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(approved_meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            location = 'approved'
        else:
            return jsonify({
                'success': False,
                'error': f'File "{filename}" not found'
            }), 404
        
        return jsonify({
            'success': True,
            'filename': filename,
            'content': content,
            'metadata': metadata,
            'location': location
        })
        
    except Exception as e:
        current_app.logger.error(f'Error reading file {filename}: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to read file'
        }), 500


# -----------------------------------------------------------------------------
# DELETE /api/raw/file/<filename> - Delete an Approved Raw File
# -----------------------------------------------------------------------------
@raw_data_bp.route('/file/<filename>', methods=['DELETE'])
def delete_raw_file(filename):
    """
    Delete an approved raw data file.
    
    Args:
        filename: Name of the file (without .txt extension)
    
    Returns:
        JSON: Success/error response
    """
    try:
        from ..config import Config
        
        content_path = os.path.join(Config.APPROVED_RAW_DIR, f'{filename}.txt')
        meta_path = os.path.join(Config.APPROVED_RAW_DIR, f'{filename}.meta.json')
        
        if not os.path.exists(content_path):
            return jsonify({
                'success': False,
                'error': f'File "{filename}" not found'
            }), 404
        
        if os.path.exists(content_path):
            os.remove(content_path)
        if os.path.exists(meta_path):
            os.remove(meta_path)
        
        return jsonify({
            'success': True,
            'message': f'File "{filename}" deleted successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f'Error deleting raw file: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to delete file'
        }), 500


# -----------------------------------------------------------------------------
# PUT /api/raw/file/<filename> - Update an Approved Raw File
# -----------------------------------------------------------------------------
@raw_data_bp.route('/file/<filename>', methods=['PUT'])
def update_raw_file(filename):
    """
    Update content of an approved raw data file.
    
    Expected JSON body:
    {
        "content": "Updated Tamil text content..."
    }
    
    Args:
        filename: Name of the file (without .txt extension)
    
    Returns:
        JSON: Success/error response
    """
    try:
        from ..config import Config
        
        data = request.get_json()
        content = data.get('content', '').strip()
        
        if not content:
            return jsonify({
                'success': False,
                'error': 'Content is required'
            }), 400
        
        content_path = os.path.join(Config.APPROVED_RAW_DIR, f'{filename}.txt')
        meta_path = os.path.join(Config.APPROVED_RAW_DIR, f'{filename}.meta.json')
        
        if not os.path.exists(content_path):
            return jsonify({
                'success': False,
                'error': f'File "{filename}" not found'
            }), 404
        
        # Update content
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Update metadata
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            metadata['content_length'] = len(content)
            metadata['updated_at'] = datetime.now().isoformat()
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'message': f'File "{filename}" updated successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f'Error updating raw file: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to update file'
        }), 500
