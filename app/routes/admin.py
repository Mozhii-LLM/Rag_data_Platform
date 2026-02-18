"""
=============================================================================
Mozhii RAG Data Platform - Admin Routes
=============================================================================
This module handles all admin-related API endpoints.

Admin Responsibilities:
    1. Review pending submissions (raw, cleaned, chunks)
    2. Approve or reject submissions
    3. Push approved data to HuggingFace
    4. View audit logs
    5. Manage platform configuration

Endpoints:
    GET  /api/admin/pending          - Get all pending items
    GET  /api/admin/item             - Get a specific pending item for editing
    POST /api/admin/update           - Update a pending item
    POST /api/admin/approve          - Approve a submission
    POST /api/admin/reject           - Reject a submission
    POST /api/admin/push-to-hf       - Push approved data to HuggingFace
    GET  /api/admin/stats            - Get platform statistics
=============================================================================
"""

from flask import Blueprint, request, jsonify, current_app
import os
import json
import shutil
from datetime import datetime

# -----------------------------------------------------------------------------
# Create Blueprint
# -----------------------------------------------------------------------------
admin_bp = Blueprint('admin', __name__)


# -----------------------------------------------------------------------------
# GET /api/admin/pending - Get All Pending Items
# -----------------------------------------------------------------------------
@admin_bp.route('/pending', methods=['GET'])
def get_all_pending():
    """
    Get all pending submissions across all stages.
    
    This gives admin a consolidated view of everything that needs review.
    
    Returns:
        JSON: Object with pending counts and items for each stage
    """
    try:
        from ..config import Config
        
        pending = {
            'raw': [],
            'cleaned': [],
            'chunked': {}
        }
        
        # Get pending raw files
        if os.path.exists(Config.PENDING_RAW_DIR):
            for filename in os.listdir(Config.PENDING_RAW_DIR):
                if filename.endswith('.meta.json'):
                    meta_path = os.path.join(Config.PENDING_RAW_DIR, filename)
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        pending['raw'].append(json.load(f))
        
        # Get pending cleaned files
        if os.path.exists(Config.PENDING_CLEANED_DIR):
            for filename in os.listdir(Config.PENDING_CLEANED_DIR):
                if filename.endswith('.meta.json'):
                    meta_path = os.path.join(Config.PENDING_CLEANED_DIR, filename)
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        pending['cleaned'].append(json.load(f))
        
        # Get pending chunks
        if os.path.exists(Config.PENDING_CHUNKED_DIR):
            for folder_name in os.listdir(Config.PENDING_CHUNKED_DIR):
                folder_path = os.path.join(Config.PENDING_CHUNKED_DIR, folder_name)
                if os.path.isdir(folder_path):
                    chunks = []
                    for chunk_file in os.listdir(folder_path):
                        if chunk_file.endswith('.json'):
                            chunk_path = os.path.join(folder_path, chunk_file)
                            with open(chunk_path, 'r', encoding='utf-8') as f:
                                chunks.append(json.load(f))
                    if chunks:
                        chunks.sort(key=lambda x: x.get('chunk_index', 0))
                        pending['chunked'][folder_name] = chunks
        
        # Calculate totals
        totals = {
            'raw': len(pending['raw']),
            'cleaned': len(pending['cleaned']),
            'chunked': sum(len(c) for c in pending['chunked'].values()),
            'total': len(pending['raw']) + len(pending['cleaned']) + 
                     sum(len(c) for c in pending['chunked'].values())
        }
        
        return jsonify({
            'success': True,
            'pending': pending,
            'totals': totals
        })
        
    except Exception as e:
        current_app.logger.error(f'Error getting pending items: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to get pending items'
        }), 500


# -----------------------------------------------------------------------------
# GET /api/admin/item - Get a Specific Pending Item for Editing
# -----------------------------------------------------------------------------
@admin_bp.route('/item', methods=['GET'])
def get_pending_item():
    """
    Get a specific pending item with its content for editing.
    
    Query params:
        type: "raw" | "cleaned" | "chunk"
        filename: filename without extension
        chunk_index: (optional) chunk index for chunks
    
    Returns:
        JSON: Item content and metadata
    """
    try:
        from ..config import Config
        
        item_type = request.args.get('type')
        filename = request.args.get('filename')
        
        if not item_type or not filename:
            return jsonify({
                'success': False,
                'error': 'Missing type or filename'
            }), 400
        
        result = {
            'success': True,
            'type': item_type,
            'filename': filename
        }
        
        if item_type == 'raw':
            content_path = os.path.join(Config.PENDING_RAW_DIR, f'{filename}.txt')
            meta_path = os.path.join(Config.PENDING_RAW_DIR, f'{filename}.meta.json')
            
            if not os.path.exists(content_path):
                return jsonify({
                    'success': False,
                    'error': 'Item not found'
                }), 404
            
            with open(content_path, 'r', encoding='utf-8') as f:
                result['content'] = f.read()
            
            with open(meta_path, 'r', encoding='utf-8') as f:
                result['metadata'] = json.load(f)
                
        elif item_type == 'cleaned':
            content_path = os.path.join(Config.PENDING_CLEANED_DIR, f'{filename}.txt')
            meta_path = os.path.join(Config.PENDING_CLEANED_DIR, f'{filename}.meta.json')
            
            if not os.path.exists(content_path):
                return jsonify({
                    'success': False,
                    'error': 'Item not found'
                }), 404
            
            with open(content_path, 'r', encoding='utf-8') as f:
                result['content'] = f.read()
            
            with open(meta_path, 'r', encoding='utf-8') as f:
                result['metadata'] = json.load(f)
                
        elif item_type == 'chunk':
            chunk_index = request.args.get('chunk_index')
            if chunk_index is None:
                return jsonify({
                    'success': False,
                    'error': 'Missing chunk_index'
                }), 400
            
            chunk_file = f'chunk_{int(chunk_index):02d}.json'
            chunk_path = os.path.join(Config.PENDING_CHUNKED_DIR, filename, chunk_file)
            
            if not os.path.exists(chunk_path):
                return jsonify({
                    'success': False,
                    'error': 'Chunk not found'
                }), 404
            
            with open(chunk_path, 'r', encoding='utf-8') as f:
                chunk_data = json.load(f)
                result['chunk'] = chunk_data
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid type'
            }), 400
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f'Error getting pending item: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to get item'
        }), 500


# -----------------------------------------------------------------------------
# POST /api/admin/update - Update a Pending Item
# -----------------------------------------------------------------------------
@admin_bp.route('/update', methods=['POST'])
def update_pending_item():
    """
    Update a pending item's content and/or metadata.
    
    Expected JSON body:
    {
        "type": "raw" | "cleaned" | "chunk",
        "filename": "grade_10_science",
        "content": "updated content...",  // For raw and cleaned
        "metadata": {...},                // Optional metadata updates
        "chunk_index": 1,                 // For chunks
        "chunk": {...}                    // For chunk updates
    }
    
    Returns:
        JSON: Success/error response
    """
    try:
        data = request.get_json()
        
        if 'type' not in data or 'filename' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing type or filename'
            }), 400
        
        item_type = data['type']
        filename = data['filename']
        
        from ..config import Config
        
        if item_type == 'raw':
            content_path = os.path.join(Config.PENDING_RAW_DIR, f'{filename}.txt')
            meta_path = os.path.join(Config.PENDING_RAW_DIR, f'{filename}.meta.json')
            
            if not os.path.exists(content_path):
                return jsonify({
                    'success': False,
                    'error': 'Item not found'
                }), 404
            
            # Update content if provided
            if 'content' in data:
                with open(content_path, 'w', encoding='utf-8') as f:
                    f.write(data['content'])
            
            # Update metadata
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            if 'metadata' in data:
                # Merge metadata updates
                metadata.update(data['metadata'])
            
            # Track edit history
            metadata['updated_at'] = datetime.now().isoformat()
            metadata['updated_by'] = 'admin'
            
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
                
        elif item_type == 'cleaned':
            content_path = os.path.join(Config.PENDING_CLEANED_DIR, f'{filename}.txt')
            meta_path = os.path.join(Config.PENDING_CLEANED_DIR, f'{filename}.meta.json')
            
            if not os.path.exists(content_path):
                return jsonify({
                    'success': False,
                    'error': 'Item not found'
                }), 404
            
            # Update content if provided
            if 'content' in data:
                with open(content_path, 'w', encoding='utf-8') as f:
                    f.write(data['content'])
            
            # Update metadata
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            if 'metadata' in data:
                metadata.update(data['metadata'])
            
            metadata['updated_at'] = datetime.now().isoformat()
            metadata['updated_by'] = 'admin'
            
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
                
        elif item_type == 'chunk':
            chunk_index = data.get('chunk_index')
            if chunk_index is None:
                return jsonify({
                    'success': False,
                    'error': 'Missing chunk_index'
                }), 400
            
            chunk_file = f'chunk_{int(chunk_index):02d}.json'
            chunk_path = os.path.join(Config.PENDING_CHUNKED_DIR, filename, chunk_file)
            
            if not os.path.exists(chunk_path):
                return jsonify({
                    'success': False,
                    'error': 'Chunk not found'
                }), 404
            
            # Update chunk
            if 'chunk' in data:
                chunk_data = data['chunk']
                chunk_data['updated_at'] = datetime.now().isoformat()
                chunk_data['updated_by'] = 'admin'
                
                with open(chunk_path, 'w', encoding='utf-8') as f:
                    json.dump(chunk_data, f, indent=2, ensure_ascii=False)
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid type'
            }), 400
        
        return jsonify({
            'success': True,
            'message': f'{item_type} updated successfully',
            'type': item_type,
            'filename': filename
        })
        
    except Exception as e:
        current_app.logger.error(f'Error updating item: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to update item'
        }), 500


# -----------------------------------------------------------------------------
# POST /api/admin/approve - Approve a Submission
# -----------------------------------------------------------------------------
@admin_bp.route('/approve', methods=['POST'])
def approve_submission():
    """
    Approve a pending submission.
    
    Expected JSON body:
    {
        "type": "raw" | "cleaned" | "chunk",
        "filename": "grade_10_science",
        "chunk_index": 1  // Only for chunks
    }
    
    Moves the file from pending to approved directory.
    
    Returns:
        JSON: Success/error response
    """
    try:
        data = request.get_json()
        
        if 'type' not in data or 'filename' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing type or filename'
            }), 400
        
        submission_type = data['type']
        filename = data['filename']
        
        from ..config import Config
        
        if submission_type == 'raw':
            # Move raw file from pending to approved
            pending_content = os.path.join(Config.PENDING_RAW_DIR, f'{filename}.txt')
            pending_meta = os.path.join(Config.PENDING_RAW_DIR, f'{filename}.meta.json')
            approved_content = os.path.join(Config.APPROVED_RAW_DIR, f'{filename}.txt')
            approved_meta = os.path.join(Config.APPROVED_RAW_DIR, f'{filename}.meta.json')
            
            if not os.path.exists(pending_content):
                return jsonify({
                    'success': False,
                    'error': 'Pending file not found'
                }), 404
            
            # Update metadata with approval info
            with open(pending_meta, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            metadata['status'] = 'approved'
            metadata['approved_at'] = datetime.now().isoformat()
            metadata['approved_by'] = 'admin'
            
            # Move files
            shutil.move(pending_content, approved_content)
            with open(approved_meta, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            os.remove(pending_meta)
            
        elif submission_type == 'cleaned':
            # Move cleaned file from pending to approved
            pending_content = os.path.join(Config.PENDING_CLEANED_DIR, f'{filename}.txt')
            pending_meta = os.path.join(Config.PENDING_CLEANED_DIR, f'{filename}.meta.json')
            approved_content = os.path.join(Config.APPROVED_CLEANED_DIR, f'{filename}.txt')
            approved_meta = os.path.join(Config.APPROVED_CLEANED_DIR, f'{filename}.meta.json')
            
            if not os.path.exists(pending_content):
                return jsonify({
                    'success': False,
                    'error': 'Pending file not found'
                }), 404
            
            # Update metadata
            with open(pending_meta, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            metadata['status'] = 'approved'
            metadata['approved_at'] = datetime.now().isoformat()
            metadata['approved_by'] = 'admin'
            
            # Move files
            shutil.move(pending_content, approved_content)
            with open(approved_meta, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            os.remove(pending_meta)
            
        elif submission_type == 'chunk':
            # Move chunk from pending to approved
            chunk_index = data.get('chunk_index')
            if chunk_index is None:
                return jsonify({
                    'success': False,
                    'error': 'Missing chunk_index'
                }), 400
            
            chunk_file = f'chunk_{chunk_index:02d}.json'
            pending_chunk = os.path.join(Config.PENDING_CHUNKED_DIR, filename, chunk_file)
            
            if not os.path.exists(pending_chunk):
                return jsonify({
                    'success': False,
                    'error': 'Pending chunk not found'
                }), 404
            
            # Create approved directory if needed
            approved_dir = os.path.join(Config.APPROVED_CHUNKED_DIR, filename)
            os.makedirs(approved_dir, exist_ok=True)
            
            # Update chunk with approval info
            with open(pending_chunk, 'r', encoding='utf-8') as f:
                chunk = json.load(f)
            
            chunk['status'] = 'approved'
            chunk['approved_at'] = datetime.now().isoformat()
            chunk['approved_by'] = 'admin'
            
            approved_chunk = os.path.join(approved_dir, chunk_file)
            with open(approved_chunk, 'w', encoding='utf-8') as f:
                json.dump(chunk, f, indent=2, ensure_ascii=False)
            
            os.remove(pending_chunk)
            
            # Clean up empty directory
            pending_dir = os.path.join(Config.PENDING_CHUNKED_DIR, filename)
            if os.path.exists(pending_dir) and not os.listdir(pending_dir):
                os.rmdir(pending_dir)
        
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid type. Must be raw, cleaned, or chunk'
            }), 400
        
        return jsonify({
            'success': True,
            'message': f'{submission_type} approved successfully',
            'type': submission_type,
            'filename': filename
        })
        
    except Exception as e:
        current_app.logger.error(f'Error approving submission: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to approve submission'
        }), 500


# -----------------------------------------------------------------------------
# POST /api/admin/reject - Reject a Submission
# -----------------------------------------------------------------------------
@admin_bp.route('/reject', methods=['POST'])
def reject_submission():
    """
    Reject a pending submission.
    
    Expected JSON body:
    {
        "type": "raw" | "cleaned" | "chunk",
        "filename": "grade_10_science",
        "chunk_index": 1,  // Only for chunks
        "reason": "Optional rejection reason"
    }
    
    Deletes the pending file and logs the rejection.
    
    Returns:
        JSON: Success/error response
    """
    try:
        data = request.get_json()
        
        if 'type' not in data or 'filename' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing type or filename'
            }), 400
        
        submission_type = data['type']
        filename = data['filename']
        reason = data.get('reason', 'No reason provided')
        
        from ..config import Config
        
        if submission_type == 'raw':
            pending_content = os.path.join(Config.PENDING_RAW_DIR, f'{filename}.txt')
            pending_meta = os.path.join(Config.PENDING_RAW_DIR, f'{filename}.meta.json')
            
            if os.path.exists(pending_content):
                os.remove(pending_content)
            if os.path.exists(pending_meta):
                os.remove(pending_meta)
                
        elif submission_type == 'cleaned':
            pending_content = os.path.join(Config.PENDING_CLEANED_DIR, f'{filename}.txt')
            pending_meta = os.path.join(Config.PENDING_CLEANED_DIR, f'{filename}.meta.json')
            
            if os.path.exists(pending_content):
                os.remove(pending_content)
            if os.path.exists(pending_meta):
                os.remove(pending_meta)
                
        elif submission_type == 'chunk':
            chunk_index = data.get('chunk_index')
            if chunk_index is None:
                return jsonify({
                    'success': False,
                    'error': 'Missing chunk_index'
                }), 400
            
            chunk_file = f'chunk_{chunk_index:02d}.json'
            pending_chunk = os.path.join(Config.PENDING_CHUNKED_DIR, filename, chunk_file)
            
            if os.path.exists(pending_chunk):
                os.remove(pending_chunk)
            
            # Clean up empty directory
            pending_dir = os.path.join(Config.PENDING_CHUNKED_DIR, filename)
            if os.path.exists(pending_dir) and not os.listdir(pending_dir):
                os.rmdir(pending_dir)
        
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid type'
            }), 400
        
        # Log rejection (could be stored in a rejection log file)
        current_app.logger.info(f'Rejected {submission_type}: {filename}, Reason: {reason}')
        
        return jsonify({
            'success': True,
            'message': f'{submission_type} rejected',
            'type': submission_type,
            'filename': filename
        })
        
    except Exception as e:
        current_app.logger.error(f'Error rejecting submission: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to reject submission'
        }), 500


# -----------------------------------------------------------------------------
# POST /api/admin/approve-all - Approve All Items of a Type
# -----------------------------------------------------------------------------
@admin_bp.route('/approve-all', methods=['POST'])
def approve_all():
    """
    Approve all pending items of a specific type.
    
    Expected JSON body:
    {
        "type": "raw" | "cleaned" | "chunks",
        "filename": "grade_10_science"  // Only for chunks
    }
    
    Returns:
        JSON: Count of approved items
    """
    try:
        data = request.get_json()
        submission_type = data.get('type')
        
        if not submission_type:
            return jsonify({
                'success': False,
                'error': 'Missing type'
            }), 400
        
        from ..config import Config
        approved_count = 0
        
        if submission_type == 'raw':
            if os.path.exists(Config.PENDING_RAW_DIR):
                for filename in list(os.listdir(Config.PENDING_RAW_DIR)):
                    if filename.endswith('.txt'):
                        base_name = filename.replace('.txt', '')
                        # Approve each file
                        # (Reusing approve logic)
                        pending_content = os.path.join(Config.PENDING_RAW_DIR, filename)
                        pending_meta = os.path.join(Config.PENDING_RAW_DIR, f'{base_name}.meta.json')
                        approved_content = os.path.join(Config.APPROVED_RAW_DIR, filename)
                        approved_meta = os.path.join(Config.APPROVED_RAW_DIR, f'{base_name}.meta.json')
                        
                        if os.path.exists(pending_meta):
                            with open(pending_meta, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                            metadata['status'] = 'approved'
                            metadata['approved_at'] = datetime.now().isoformat()
                            
                            shutil.move(pending_content, approved_content)
                            with open(approved_meta, 'w', encoding='utf-8') as f:
                                json.dump(metadata, f, indent=2, ensure_ascii=False)
                            os.remove(pending_meta)
                            approved_count += 1
        
        elif submission_type == 'cleaned':
            if os.path.exists(Config.PENDING_CLEANED_DIR):
                for filename in list(os.listdir(Config.PENDING_CLEANED_DIR)):
                    if filename.endswith('.txt'):
                        base_name = filename.replace('.txt', '')
                        pending_content = os.path.join(Config.PENDING_CLEANED_DIR, filename)
                        pending_meta = os.path.join(Config.PENDING_CLEANED_DIR, f'{base_name}.meta.json')
                        approved_content = os.path.join(Config.APPROVED_CLEANED_DIR, filename)
                        approved_meta = os.path.join(Config.APPROVED_CLEANED_DIR, f'{base_name}.meta.json')
                        
                        if os.path.exists(pending_meta):
                            with open(pending_meta, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                            metadata['status'] = 'approved'
                            metadata['approved_at'] = datetime.now().isoformat()
                            
                            shutil.move(pending_content, approved_content)
                            with open(approved_meta, 'w', encoding='utf-8') as f:
                                json.dump(metadata, f, indent=2, ensure_ascii=False)
                            os.remove(pending_meta)
                            approved_count += 1
        
        elif submission_type == 'chunks':
            target_file = data.get('filename')
            if not target_file:
                return jsonify({
                    'success': False,
                    'error': 'Filename required for chunk approval'
                }), 400
            
            pending_dir = os.path.join(Config.PENDING_CHUNKED_DIR, target_file)
            approved_dir = os.path.join(Config.APPROVED_CHUNKED_DIR, target_file)
            
            if os.path.exists(pending_dir):
                os.makedirs(approved_dir, exist_ok=True)
                for chunk_file in list(os.listdir(pending_dir)):
                    if chunk_file.endswith('.json'):
                        pending_path = os.path.join(pending_dir, chunk_file)
                        approved_path = os.path.join(approved_dir, chunk_file)
                        
                        with open(pending_path, 'r', encoding='utf-8') as f:
                            chunk = json.load(f)
                        chunk['status'] = 'approved'
                        chunk['approved_at'] = datetime.now().isoformat()
                        
                        with open(approved_path, 'w', encoding='utf-8') as f:
                            json.dump(chunk, f, indent=2, ensure_ascii=False)
                        os.remove(pending_path)
                        approved_count += 1
                
                # Clean up empty directory
                if not os.listdir(pending_dir):
                    os.rmdir(pending_dir)
        
        return jsonify({
            'success': True,
            'message': f'Approved {approved_count} items',
            'approved_count': approved_count
        })
        
    except Exception as e:
        current_app.logger.error(f'Error in bulk approve: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to approve items'
        }), 500


# -----------------------------------------------------------------------------
# GET /api/admin/stats - Get Platform Statistics
# -----------------------------------------------------------------------------
@admin_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    Get platform statistics.
    
    Returns counts for:
    - Pending vs approved files at each stage
    - Total chunks created
    - Languages and categories distribution
    
    Returns:
        JSON: Statistics object
    """
    try:
        from ..config import Config
        
        stats = {
            'raw': {'pending': 0, 'approved': 0},
            'cleaned': {'pending': 0, 'approved': 0},
            'chunked': {'pending': 0, 'approved': 0}
        }
        
        # Count raw files
        if os.path.exists(Config.PENDING_RAW_DIR):
            stats['raw']['pending'] = len([f for f in os.listdir(Config.PENDING_RAW_DIR) if f.endswith('.txt')])
        if os.path.exists(Config.APPROVED_RAW_DIR):
            stats['raw']['approved'] = len([f for f in os.listdir(Config.APPROVED_RAW_DIR) if f.endswith('.txt')])
        
        # Count cleaned files
        if os.path.exists(Config.PENDING_CLEANED_DIR):
            stats['cleaned']['pending'] = len([f for f in os.listdir(Config.PENDING_CLEANED_DIR) if f.endswith('.txt')])
        if os.path.exists(Config.APPROVED_CLEANED_DIR):
            stats['cleaned']['approved'] = len([f for f in os.listdir(Config.APPROVED_CLEANED_DIR) if f.endswith('.txt')])
        
        # Count chunks
        if os.path.exists(Config.PENDING_CHUNKED_DIR):
            for folder in os.listdir(Config.PENDING_CHUNKED_DIR):
                folder_path = os.path.join(Config.PENDING_CHUNKED_DIR, folder)
                if os.path.isdir(folder_path):
                    stats['chunked']['pending'] += len([f for f in os.listdir(folder_path) if f.endswith('.json')])
        
        if os.path.exists(Config.APPROVED_CHUNKED_DIR):
            for folder in os.listdir(Config.APPROVED_CHUNKED_DIR):
                folder_path = os.path.join(Config.APPROVED_CHUNKED_DIR, folder)
                if os.path.isdir(folder_path):
                    stats['chunked']['approved'] += len([f for f in os.listdir(folder_path) if f.endswith('.json')])
        
        # Calculate totals
        stats['totals'] = {
            'pending': stats['raw']['pending'] + stats['cleaned']['pending'] + stats['chunked']['pending'],
            'approved': stats['raw']['approved'] + stats['cleaned']['approved'] + stats['chunked']['approved']
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        current_app.logger.error(f'Error getting stats: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to get statistics'
        }), 500

# -----------------------------------------------------------------------------
# POST /api/admin/test-hf - Test HuggingFace Connection
# -----------------------------------------------------------------------------
@admin_bp.route('/test-hf', methods=['POST'])
def test_hf_connection():
    """
    Test HuggingFace connection, token validity, and create repos if needed.
    
    Expected JSON body:
    {
        "hf_token": "hf_...",
        "raw_repo": "Org/RepoName",
        "cleaned_repo": "Org/RepoName",
        "chunked_repo": "Org/RepoName"
    }
    """
    try:
        data = request.get_json()
        hf_token = data.get('hf_token') or os.getenv('HF_TOKEN')
        
        if not hf_token:
            return jsonify({
                'success': False,
                'error': 'HuggingFace token is required'
            }), 400
        
        from ..services.huggingface import HuggingFaceService
        from ..config import Config
        
        hf_service = HuggingFaceService(token=hf_token)
        
        # Test 1: Verify token by getting user info
        try:
            user_info = hf_service.api.whoami()
            username = user_info.get('name', 'unknown')
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Invalid token or connection error: {str(e)}'
            }), 400
        
        # Test 2: Try to create/verify each repo
        repos = {
            'raw': data.get('raw_repo') or Config.HF_RAW_REPO,
            'cleaned': data.get('cleaned_repo') or Config.HF_CLEANED_REPO,
            'chunked': data.get('chunked_repo') or Config.HF_CHUNKED_REPO
        }
        
        repo_status = {}
        for repo_type, repo_id in repos.items():
            try:
                hf_service.ensure_repo_exists(repo_id)
                repo_status[repo_type] = {'repo': repo_id, 'status': 'ready'}
            except Exception as e:
                repo_status[repo_type] = {'repo': repo_id, 'status': 'error', 'error': str(e)}
        
        # Count local approved files
        file_counts = {
            'raw': len([f for f in os.listdir(Config.APPROVED_RAW_DIR) if f.endswith('.txt')]) if os.path.exists(Config.APPROVED_RAW_DIR) else 0,
            'cleaned': len([f for f in os.listdir(Config.APPROVED_CLEANED_DIR) if f.endswith('.txt')]) if os.path.exists(Config.APPROVED_CLEANED_DIR) else 0,
            'chunked': sum(
                len([f for f in os.listdir(os.path.join(Config.APPROVED_CHUNKED_DIR, d)) if f.endswith('.json')])
                for d in os.listdir(Config.APPROVED_CHUNKED_DIR)
                if os.path.isdir(os.path.join(Config.APPROVED_CHUNKED_DIR, d))
            ) if os.path.exists(Config.APPROVED_CHUNKED_DIR) else 0
        }
        
        all_repos_ok = all(r['status'] == 'ready' for r in repo_status.values())
        
        return jsonify({
            'success': all_repos_ok,
            'user': username,
            'repos': repo_status,
            'file_counts': file_counts,
            'message': 'All repos ready!' if all_repos_ok else 'Some repos had errors'
        })
        
    except Exception as e:
        current_app.logger.error(f'HF test error: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'Test failed: {str(e)}'
        }), 500


# -----------------------------------------------------------------------------
# POST /api/admin/push-to-hf - Push Approved Data to HuggingFace
# -----------------------------------------------------------------------------
@admin_bp.route('/push-to-hf', methods=['POST'])
def push_to_huggingface():
    """
    Push approved data to HuggingFace repositories.
    
    Expected JSON body:
    {
        "type": "raw" | "cleaned" | "chunked" | "all",
        "hf_token": "hf_...",  // HuggingFace token
        "repo": "username/repo-name"  // Target repo
    }
    
    Returns:
        JSON: Upload results with count of files pushed
    """
    try:
        data = request.get_json()
        
        if not data or 'type' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing type'
            }), 400
        
        # Get HuggingFace config
        hf_token = data.get('hf_token') or os.getenv('HF_TOKEN')
        if not hf_token:
            return jsonify({
                'success': False,
                'error': 'HuggingFace token required. Set HF_TOKEN in .env or provide in request.'
            }), 400
        
        push_type = data['type']
        
        from ..services.huggingface import HuggingFaceService
        from ..config import Config
        
        # Initialize HF service with token
        hf_service = HuggingFaceService(token=hf_token)
        
        if not hf_service.is_configured():
            return jsonify({
                'success': False,
                'error': 'HuggingFace service not configured properly'
            }), 400
        
        # Ensure all target repos exist before uploading
        raw_repo = data.get('raw_repo') or data.get('repo') or Config.HF_RAW_REPO
        cleaned_repo = data.get('cleaned_repo') or data.get('repo') or Config.HF_CLEANED_REPO
        chunked_repo = data.get('chunked_repo') or data.get('repo') or Config.HF_CHUNKED_REPO
        
        repo_errors = []
        for repo_name, repo_id in [('raw', raw_repo), ('cleaned', cleaned_repo), ('chunked', chunked_repo)]:
            try:
                hf_service.ensure_repo_exists(repo_id)
            except Exception as e:
                repo_errors.append(f'{repo_name} ({repo_id}): {str(e)}')
        
        if repo_errors:
            return jsonify({
                'success': False,
                'error': 'Failed to create/access repos: ' + '; '.join(repo_errors)
            }), 400
        
        results = {
            'raw': {'uploaded': 0, 'failed': 0, 'files': []},
            'cleaned': {'uploaded': 0, 'failed': 0, 'files': []},
            'chunked': {'uploaded': 0, 'failed': 0, 'files': []}
        }
        
        # Push raw files
        if push_type in ['raw', 'all']:
            repo = raw_repo
            if os.path.exists(Config.APPROVED_RAW_DIR):
                for filename in os.listdir(Config.APPROVED_RAW_DIR):
                    if filename.endswith('.txt'):
                        base_name = filename.replace('.txt', '')
                        content_path = os.path.join(Config.APPROVED_RAW_DIR, filename)
                        meta_path = os.path.join(Config.APPROVED_RAW_DIR, f'{base_name}.meta.json')
                        
                        try:
                            with open(content_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            with open(meta_path, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                            
                            result = hf_service.upload_raw_file(base_name, content, metadata, repo)
                            
                            if result['success']:
                                results['raw']['uploaded'] += 1
                                results['raw']['files'].append(base_name)
                            else:
                                results['raw']['failed'] += 1
                                
                        except Exception as e:
                            current_app.logger.error(f'Failed to upload {base_name}: {str(e)}')
                            results['raw']['failed'] += 1
        
        # Push cleaned files
        if push_type in ['cleaned', 'all']:
            repo = cleaned_repo
            if os.path.exists(Config.APPROVED_CLEANED_DIR):
                for filename in os.listdir(Config.APPROVED_CLEANED_DIR):
                    if filename.endswith('.txt'):
                        base_name = filename.replace('.txt', '')
                        content_path = os.path.join(Config.APPROVED_CLEANED_DIR, filename)
                        meta_path = os.path.join(Config.APPROVED_CLEANED_DIR, f'{base_name}.meta.json')
                        
                        try:
                            with open(content_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            with open(meta_path, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                            
                            result = hf_service.upload_cleaned_file(base_name, content, metadata, repo)
                            
                            if result['success']:
                                results['cleaned']['uploaded'] += 1
                                results['cleaned']['files'].append(base_name)
                            else:
                                results['cleaned']['failed'] += 1
                                
                        except Exception as e:
                            current_app.logger.error(f'Failed to upload {base_name}: {str(e)}')
                            results['cleaned']['failed'] += 1
        
        # Push chunks
        if push_type in ['chunked', 'all']:
            repo = chunked_repo
            if os.path.exists(Config.APPROVED_CHUNKED_DIR):
                for folder_name in os.listdir(Config.APPROVED_CHUNKED_DIR):
                    folder_path = os.path.join(Config.APPROVED_CHUNKED_DIR, folder_name)
                    if os.path.isdir(folder_path):
                        for chunk_file in os.listdir(folder_path):
                            if chunk_file.endswith('.json'):
                                chunk_path = os.path.join(folder_path, chunk_file)
                                
                                try:
                                    with open(chunk_path, 'r', encoding='utf-8') as f:
                                        chunk_data = json.load(f)
                                    
                                    result = hf_service.upload_chunk(folder_name, chunk_file, chunk_data, repo)
                                    
                                    if result['success']:
                                        results['chunked']['uploaded'] += 1
                                        results['chunked']['files'].append(f'{folder_name}/{chunk_file}')
                                    else:
                                        results['chunked']['failed'] += 1
                                        
                                except Exception as e:
                                    current_app.logger.error(f'Failed to upload chunk {chunk_file}: {str(e)}')
                                    results['chunked']['failed'] += 1
        
        # Calculate totals
        total_uploaded = results['raw']['uploaded'] + results['cleaned']['uploaded'] + results['chunked']['uploaded']
        total_failed = results['raw']['failed'] + results['cleaned']['failed'] + results['chunked']['failed']
        
        return jsonify({
            'success': True,
            'message': f'Pushed {total_uploaded} files to HuggingFace',
            'results': results,
            'totals': {
                'uploaded': total_uploaded,
                'failed': total_failed
            }
        })
        
    except Exception as e:
        current_app.logger.error(f'Error pushing to HuggingFace: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'Failed to push to HuggingFace: {str(e)}'
        }), 500