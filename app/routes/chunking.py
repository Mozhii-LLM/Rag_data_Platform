"""
=============================================================================
Mozhii RAG Data Platform - Chunking Routes
=============================================================================
This module handles all API endpoints for the CHUNKING tab.

This is the MOST IMPORTANT stage as it produces RAG-ready data!

Workflow:
    1. Chunker views cleaned files from HuggingFace
    2. Creates manual chunks with overlap awareness
    3. Each chunk includes: text, language, category, source, index
    4. Chunks are saved as JSON files in a folder named after source file
    5. Admin reviews and approves
    6. Approved chunks pushed to mozhii-chunked-data repo

Chunk Structure:
    grade_10_science/
        ├── chunk_01.json
        ├── chunk_02.json
        └── chunk_03.json

Each JSON:
    {
        "chunk_id": "ta_edu_grade10_sci_01",
        "text": "...",
        "language": "ta",
        "category": "education",
        "source": "gov_textbook",
        "chunk_index": 1
    }
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
chunking_bp = Blueprint('chunking', __name__)


# -----------------------------------------------------------------------------
# Helper: Generate Chunk ID
# -----------------------------------------------------------------------------
def generate_chunk_id(language, category, filename, index):
    """
    Generate a standardized chunk ID.
    
    Format: {lang}_{category_short}_{filename_short}_{index:02d}
    Example: ta_edu_grade10_sci_01
    
    Args:
        language: Language code (e.g., 'ta')
        category: Category name (e.g., 'education')
        filename: Source filename
        index: Chunk index number
    
    Returns:
        str: Formatted chunk ID
    """
    # Shorten category to 3-4 chars
    cat_short = category[:3] if len(category) > 3 else category
    
    # Shorten filename
    file_short = filename.replace('_', '')[:10]
    
    return f"{language}_{cat_short}_{file_short}_{index:02d}"


# -----------------------------------------------------------------------------
# GET /api/chunking/cleaned-files - List Cleaned Files Available for Chunking
# -----------------------------------------------------------------------------
@chunking_bp.route('/cleaned-files', methods=['GET'])
def list_cleaned_files():
    """
    List all approved cleaned files available for chunking.
    
    Returns:
        JSON: Array of cleaned files with content and chunking status
    """
    try:
        from ..config import Config
        approved_cleaned_dir = Config.APPROVED_CLEANED_DIR
        
        cleaned_files = []
        
        if os.path.exists(approved_cleaned_dir):
            for filename in os.listdir(approved_cleaned_dir):
                if filename.endswith('.txt'):
                    base_name = filename.replace('.txt', '')
                    
                    # Read content
                    content_path = os.path.join(approved_cleaned_dir, filename)
                    with open(content_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Read metadata
                    meta_path = os.path.join(approved_cleaned_dir, f'{base_name}.meta.json')
                    metadata = {}
                    if os.path.exists(meta_path):
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    
                    # Count existing chunks (pending + approved)
                    pending_chunks = 0
                    approved_chunks = 0
                    
                    pending_chunk_dir = os.path.join(Config.PENDING_CHUNKED_DIR, base_name)
                    approved_chunk_dir = os.path.join(Config.APPROVED_CHUNKED_DIR, base_name)
                    
                    if os.path.exists(pending_chunk_dir):
                        pending_chunks = len([f for f in os.listdir(pending_chunk_dir) if f.endswith('.json')])
                    
                    if os.path.exists(approved_chunk_dir):
                        approved_chunks = len([f for f in os.listdir(approved_chunk_dir) if f.endswith('.json')])
                    
                    cleaned_files.append({
                        'filename': base_name,
                        'language': metadata.get('language', 'ta'),
                        'source': metadata.get('source', 'unknown'),
                        'content': content,
                        'content_length': len(content),
                        'pending_chunks': pending_chunks,
                        'approved_chunks': approved_chunks,
                        'total_chunks': pending_chunks + approved_chunks
                    })
        
        return jsonify({
            'success': True,
            'files': cleaned_files,
            'count': len(cleaned_files)
        })
        
    except Exception as e:
        current_app.logger.error(f'Error listing cleaned files: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to list cleaned files'
        }), 500


# -----------------------------------------------------------------------------
# GET /api/chunking/chunks/<filename> - Get Chunks for a File
# -----------------------------------------------------------------------------
@chunking_bp.route('/chunks/<filename>', methods=['GET'])
def get_chunks(filename):
    """
    Get all chunks (pending and approved) for a specific file.
    
    Args:
        filename: Source file name
    
    Returns:
        JSON: Array of chunk objects
    """
    try:
        from ..config import Config
        
        chunks = []
        
        # Get pending chunks
        pending_dir = os.path.join(Config.PENDING_CHUNKED_DIR, filename)
        if os.path.exists(pending_dir):
            for chunk_file in os.listdir(pending_dir):
                if chunk_file.endswith('.json'):
                    chunk_path = os.path.join(pending_dir, chunk_file)
                    with open(chunk_path, 'r', encoding='utf-8') as f:
                        chunk = json.load(f)
                        chunk['status'] = 'pending'
                        chunks.append(chunk)
        
        # Get approved chunks
        approved_dir = os.path.join(Config.APPROVED_CHUNKED_DIR, filename)
        if os.path.exists(approved_dir):
            for chunk_file in os.listdir(approved_dir):
                if chunk_file.endswith('.json'):
                    chunk_path = os.path.join(approved_dir, chunk_file)
                    with open(chunk_path, 'r', encoding='utf-8') as f:
                        chunk = json.load(f)
                        chunk['status'] = 'approved'
                        chunks.append(chunk)
        
        # Sort by chunk index
        chunks.sort(key=lambda x: x.get('chunk_index', 0))
        
        return jsonify({
            'success': True,
            'filename': filename,
            'chunks': chunks,
            'count': len(chunks)
        })
        
    except Exception as e:
        current_app.logger.error(f'Error getting chunks: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to get chunks'
        }), 500


# -----------------------------------------------------------------------------
# POST /api/chunking/submit - Submit New Chunk
# -----------------------------------------------------------------------------
@chunking_bp.route('/submit', methods=['POST'])
def submit_chunk():
    """
    Submit a new chunk for a cleaned file.
    
    Expected JSON body:
    {
        "filename": "grade_10_science",
        "text": "Chunk text content...",
        "category": "education",
        "source": "gov_textbook",
        "overlap_reference": "previous chunk context..." (optional)
    }
    
    Chunk index is auto-calculated based on existing chunks.
    
    Returns:
        JSON: Success response with chunk ID
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['filename', 'text', 'category']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        filename = data['filename'].strip()
        text = data['text']
        heading = data.get('heading', '')
        category = data['category']
        source = data.get('source', 'unknown')
        overlap_reference = data.get('overlap_reference', '')
        
        from ..config import Config
        
        # Verify cleaned file exists
        cleaned_path = os.path.join(Config.APPROVED_CLEANED_DIR, f'{filename}.txt')
        if not os.path.exists(cleaned_path):
            return jsonify({
                'success': False,
                'error': f'Cleaned file "{filename}" not found'
            }), 404
        
        # Get metadata for language
        cleaned_meta = os.path.join(Config.APPROVED_CLEANED_DIR, f'{filename}.meta.json')
        language = 'ta'
        if os.path.exists(cleaned_meta):
            with open(cleaned_meta, 'r', encoding='utf-8') as f:
                meta = json.load(f)
                language = meta.get('language', 'ta')
        
        # Calculate chunk index
        pending_dir = os.path.join(Config.PENDING_CHUNKED_DIR, filename)
        approved_dir = os.path.join(Config.APPROVED_CHUNKED_DIR, filename)
        
        existing_count = 0
        if os.path.exists(pending_dir):
            existing_count += len([f for f in os.listdir(pending_dir) if f.endswith('.json')])
        if os.path.exists(approved_dir):
            existing_count += len([f for f in os.listdir(approved_dir) if f.endswith('.json')])
        
        chunk_index = existing_count + 1
        
        # Generate chunk ID
        chunk_id = generate_chunk_id(language, category, filename, chunk_index)
        
        # Create chunk object
        chunk = {
            'chunk_id': chunk_id,
            'heading': heading,
            'text': text,
            'language': language,
            'category': category,
            'source': source,
            'chunk_index': chunk_index,
            'source_file': filename,
            'overlap_reference': overlap_reference,
            'created_at': datetime.now().isoformat(),
            'created_by': 'chunker',
            'text_length': len(text)
        }
        
        # Create pending chunk directory if needed
        os.makedirs(pending_dir, exist_ok=True)
        
        # Save chunk
        chunk_filename = f'chunk_{chunk_index:02d}.json'
        chunk_path = os.path.join(pending_dir, chunk_filename)
        
        with open(chunk_path, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'message': 'Chunk created. Awaiting admin approval.',
            'chunk_id': chunk_id,
            'chunk_index': chunk_index,
            'filename': filename
        })
        
    except Exception as e:
        current_app.logger.error(f'Error submitting chunk: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to submit chunk'
        }), 500


# -----------------------------------------------------------------------------
# POST /api/chunking/submit-batch - Submit Multiple Chunks
# -----------------------------------------------------------------------------
@chunking_bp.route('/submit-batch', methods=['POST'])
def submit_batch():
    """
    Submit multiple chunks at once.
    
    Expected JSON body:
    {
        "filename": "grade_10_science",
        "chunks": [
            {"text": "...", "category": "education"},
            {"text": "...", "category": "education"}
        ]
    }
    
    Returns:
        JSON: Success response with all chunk IDs
    """
    try:
        data = request.get_json()
        
        if 'filename' not in data or 'chunks' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing filename or chunks array'
            }), 400
        
        filename = data['filename'].strip()
        chunks_data = data['chunks']
        
        if not isinstance(chunks_data, list) or len(chunks_data) == 0:
            return jsonify({
                'success': False,
                'error': 'Chunks must be a non-empty array'
            }), 400
        
        from ..config import Config
        
        # Verify cleaned file exists
        cleaned_path = os.path.join(Config.APPROVED_CLEANED_DIR, f'{filename}.txt')
        if not os.path.exists(cleaned_path):
            return jsonify({
                'success': False,
                'error': f'Cleaned file "{filename}" not found'
            }), 404
        
        # Get language from metadata
        cleaned_meta = os.path.join(Config.APPROVED_CLEANED_DIR, f'{filename}.meta.json')
        language = 'ta'
        if os.path.exists(cleaned_meta):
            with open(cleaned_meta, 'r', encoding='utf-8') as f:
                meta = json.load(f)
                language = meta.get('language', 'ta')
        
        # Get starting index
        pending_dir = os.path.join(Config.PENDING_CHUNKED_DIR, filename)
        approved_dir = os.path.join(Config.APPROVED_CHUNKED_DIR, filename)
        
        existing_count = 0
        if os.path.exists(pending_dir):
            existing_count += len([f for f in os.listdir(pending_dir) if f.endswith('.json')])
        if os.path.exists(approved_dir):
            existing_count += len([f for f in os.listdir(approved_dir) if f.endswith('.json')])
        
        # Create pending directory
        os.makedirs(pending_dir, exist_ok=True)
        
        created_chunks = []
        
        for i, chunk_data in enumerate(chunks_data):
            if 'text' not in chunk_data or 'category' not in chunk_data:
                continue
            
            chunk_index = existing_count + i + 1
            chunk_id = generate_chunk_id(language, chunk_data['category'], filename, chunk_index)
            
            chunk = {
                'chunk_id': chunk_id,
                'text': chunk_data['text'],
                'language': language,
                'category': chunk_data['category'],
                'source': chunk_data.get('source', 'unknown'),
                'chunk_index': chunk_index,
                'source_file': filename,
                'overlap_reference': chunk_data.get('overlap_reference', ''),
                'created_at': datetime.now().isoformat(),
                'created_by': 'chunker',
                'text_length': len(chunk_data['text'])
            }
            
            chunk_filename = f'chunk_{chunk_index:02d}.json'
            chunk_path = os.path.join(pending_dir, chunk_filename)
            
            with open(chunk_path, 'w', encoding='utf-8') as f:
                json.dump(chunk, f, indent=2, ensure_ascii=False)
            
            created_chunks.append({
                'chunk_id': chunk_id,
                'chunk_index': chunk_index
            })
        
        return jsonify({
            'success': True,
            'message': f'{len(created_chunks)} chunks created. Awaiting admin approval.',
            'chunks': created_chunks,
            'filename': filename
        })
        
    except Exception as e:
        current_app.logger.error(f'Error submitting batch: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to submit chunks'
        }), 500


# -----------------------------------------------------------------------------
# GET /api/chunking/pending - List All Pending Chunks
# -----------------------------------------------------------------------------
@chunking_bp.route('/pending', methods=['GET'])
def list_pending():
    """
    List all chunks pending admin approval.
    
    Returns:
        JSON: Array of pending chunks grouped by source file
    """
    try:
        from ..config import Config
        pending_base = Config.PENDING_CHUNKED_DIR
        
        pending_files = {}
        
        if os.path.exists(pending_base):
            for folder_name in os.listdir(pending_base):
                folder_path = os.path.join(pending_base, folder_name)
                if os.path.isdir(folder_path):
                    chunks = []
                    for chunk_file in os.listdir(folder_path):
                        if chunk_file.endswith('.json'):
                            chunk_path = os.path.join(folder_path, chunk_file)
                            with open(chunk_path, 'r', encoding='utf-8') as f:
                                chunk = json.load(f)
                                chunks.append(chunk)
                    
                    if chunks:
                        chunks.sort(key=lambda x: x.get('chunk_index', 0))
                        pending_files[folder_name] = chunks
        
        return jsonify({
            'success': True,
            'files': pending_files,
            'total_files': len(pending_files),
            'total_chunks': sum(len(c) for c in pending_files.values())
        })
        
    except Exception as e:
        current_app.logger.error(f'Error listing pending chunks: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to list pending chunks'
        }), 500


# -----------------------------------------------------------------------------
# DELETE /api/chunking/chunk/<filename>/<chunk_id> - Delete a Pending Chunk
# -----------------------------------------------------------------------------
@chunking_bp.route('/chunk/<filename>/<int:chunk_index>', methods=['DELETE'])
def delete_chunk(filename, chunk_index):
    """
    Delete a pending chunk.
    
    Only pending chunks can be deleted. Approved chunks cannot be deleted.
    
    Args:
        filename: Source file name
        chunk_index: Index of the chunk to delete
    
    Returns:
        JSON: Success/error response
    """
    try:
        from ..config import Config
        
        chunk_file = f'chunk_{chunk_index:02d}.json'
        chunk_path = os.path.join(Config.PENDING_CHUNKED_DIR, filename, chunk_file)
        
        if not os.path.exists(chunk_path):
            return jsonify({
                'success': False,
                'error': 'Chunk not found or already approved'
            }), 404
        
        os.remove(chunk_path)
        
        return jsonify({
            'success': True,
            'message': 'Chunk deleted successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f'Error deleting chunk: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to delete chunk'
        }), 500
