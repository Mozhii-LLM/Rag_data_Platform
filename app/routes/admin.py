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
    GET  /api/admin/approved-files   - List approved files with push status
    DELETE /api/admin/delete-approved - Delete approved file(s) by stage
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
# GET /api/admin/approved-files - List all approved files with push status
# -----------------------------------------------------------------------------
@admin_bp.route('/approved-files', methods=['GET'])
def list_approved_files():
    """
    List every approved file (raw, cleaned, chunks) and whether it has
    already been pushed to HuggingFace.  Used by the admin panel to render
    per-file Push buttons.
    """
    try:
        from ..config import Config

        files = {}  # keyed by base_name

        # ── approved raw ──────────────────────────────────────────────────
        if os.path.exists(Config.APPROVED_RAW_DIR):
            for fname in os.listdir(Config.APPROVED_RAW_DIR):
                if not fname.endswith('.txt'):
                    continue
                base = fname.replace('.txt', '')
                meta_path = os.path.join(Config.APPROVED_RAW_DIR, f'{base}.meta.json')
                pushed = False
                if os.path.exists(meta_path):
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        pushed = bool(json.load(f).get('pushed_to_hf'))
                entry = files.setdefault(base, {'filename': base, 'raw': False, 'cleaned': False, 'chunks': 0, 'chunks_pushed': 0})
                entry['raw'] = True
                entry['raw_pushed'] = pushed

        # ── approved cleaned ──────────────────────────────────────────────
        if os.path.exists(Config.APPROVED_CLEANED_DIR):
            for fname in os.listdir(Config.APPROVED_CLEANED_DIR):
                if not fname.endswith('.txt'):
                    continue
                base = fname.replace('.txt', '')
                meta_path = os.path.join(Config.APPROVED_CLEANED_DIR, f'{base}.meta.json')
                pushed = False
                if os.path.exists(meta_path):
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        pushed = bool(json.load(f).get('pushed_to_hf'))
                entry = files.setdefault(base, {'filename': base, 'raw': False, 'raw_pushed': False, 'cleaned': False, 'chunks': 0, 'chunks_pushed': 0})
                entry['cleaned'] = True
                entry['cleaned_pushed'] = pushed

        # ── approved chunks ───────────────────────────────────────────────
        if os.path.exists(Config.APPROVED_CHUNKED_DIR):
            for folder in os.listdir(Config.APPROVED_CHUNKED_DIR):
                folder_path = os.path.join(Config.APPROVED_CHUNKED_DIR, folder)
                if not os.path.isdir(folder_path):
                    continue
                total = 0
                pushed_count = 0
                for cf in os.listdir(folder_path):
                    if not cf.endswith('.json'):
                        continue
                    total += 1
                    chunk_path = os.path.join(folder_path, cf)
                    try:
                        with open(chunk_path, 'r', encoding='utf-8') as f:
                            if json.load(f).get('pushed_to_hf'):
                                pushed_count += 1
                    except Exception:
                        pass
                entry = files.setdefault(folder, {'filename': folder, 'raw': False, 'raw_pushed': False, 'cleaned': False, 'cleaned_pushed': False})
                entry['chunks'] = total
                entry['chunks_pushed'] = pushed_count

        return jsonify({
            'success': True,
            'files': sorted(files.values(), key=lambda x: x['filename']),
            'count': len(files),
        })

    except Exception as e:
        current_app.logger.error('Error listing approved files: %s', str(e))
        return jsonify({'success': False, 'error': 'Failed to list approved files'}), 500


# POST /api/admin/push-to-hf - Push Approved Data to HuggingFace
# -----------------------------------------------------------------------------
@admin_bp.route('/push-to-hf', methods=['POST'])
def push_to_huggingface():
    """
    Push approved data to HuggingFace repositories.

    KEY IMPROVEMENTS over the old version:
      - Chunks are uploaded in BATCHES via create_commit() instead of one
        API call per chunk.  This eliminates HF rate-limiting failures for
        large chunk sets (e.g. 223 chunks).
      - Already-pushed chunks are SKIPPED — each chunk JSON gets a
        'pushed_to_hf' timestamp after a successful push so re-running
        push never re-uploads what's already there.
      - Per-folder retry with exponential back-off built into the service.
      - Detailed per-folder results returned so the UI can show exactly
        what succeeded / failed.

    Expected JSON body:
    {
        "type": "raw" | "cleaned" | "chunked" | "all",
        "hf_token": "hf_...",
        "raw_repo": "org/repo",
        "cleaned_repo": "org/repo",
        "chunked_repo": "org/repo",
        "filename": "grade_10_science"   // OPTIONAL — push only this one file.
                                          // If omitted, all un-pushed files are pushed.
    }
    """
    try:
        data = request.get_json()

        if not data or 'type' not in data:
            return jsonify({'success': False, 'error': 'Missing type'}), 400

        hf_token = data.get('hf_token') or os.getenv('HF_TOKEN')
        if not hf_token:
            return jsonify({
                'success': False,
                'error': 'HuggingFace token required. Set HF_TOKEN env var or provide hf_token in request.',
            }), 400

        push_type = data['type']
        # Optional per-file filter — when set, ONLY this file is pushed.
        target_filename = data.get('filename', '').strip() or None

        from ..services.huggingface import HuggingFaceService
        from ..config import Config

        hf_service = HuggingFaceService(token=hf_token)
        if not hf_service.is_configured():
            return jsonify({'success': False, 'error': 'HuggingFace service not configured properly'}), 400

        results = {
            'raw':     {'uploaded': 0, 'failed': 0, 'skipped': 0, 'files': []},
            'cleaned': {'uploaded': 0, 'failed': 0, 'skipped': 0, 'files': []},
            'chunked': {'uploaded': 0, 'failed': 0, 'skipped': 0, 'files': [], 'failed_chunks': []},
        }

        # ------------------------------------------------------------------
        # Push raw files
        # ------------------------------------------------------------------
        if push_type in ['raw', 'all']:
            repo = data.get('raw_repo') or Config.HF_RAW_REPO
            if os.path.exists(Config.APPROVED_RAW_DIR):
                for filename in os.listdir(Config.APPROVED_RAW_DIR):
                    if not filename.endswith('.txt'):
                        continue
                    base_name = filename.replace('.txt', '')
                    # ── Per-file filter ───────────────────────────────────
                    if target_filename and base_name != target_filename:
                        continue
                    content_path = os.path.join(Config.APPROVED_RAW_DIR, filename)
                    meta_path = os.path.join(Config.APPROVED_RAW_DIR, f'{base_name}.meta.json')

                    try:
                        with open(content_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        metadata = {}
                        if os.path.exists(meta_path):
                            with open(meta_path, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)

                        # Skip already-pushed
                        if metadata.get('pushed_to_hf'):
                            results['raw']['skipped'] += 1
                            continue

                        result = hf_service.upload_raw_file(base_name, content, metadata, repo)
                        if result['success']:
                            results['raw']['uploaded'] += 1
                            results['raw']['files'].append(base_name)
                            # Mark as pushed
                            metadata['pushed_to_hf'] = datetime.utcnow().isoformat() + 'Z'
                            with open(meta_path, 'w', encoding='utf-8') as f:
                                json.dump(metadata, f, indent=2, ensure_ascii=False)
                        else:
                            results['raw']['failed'] += 1
                            current_app.logger.error('Raw upload failed for %s: %s', base_name, result.get('error'))
                    except Exception as e:
                        current_app.logger.error('Exception uploading raw %s: %s', base_name, str(e))
                        results['raw']['failed'] += 1

        # ------------------------------------------------------------------
        # Push cleaned files
        # ------------------------------------------------------------------
        if push_type in ['cleaned', 'all']:
            repo = data.get('cleaned_repo') or Config.HF_CLEANED_REPO
            if os.path.exists(Config.APPROVED_CLEANED_DIR):
                for filename in os.listdir(Config.APPROVED_CLEANED_DIR):
                    if not filename.endswith('.txt'):
                        continue
                    base_name = filename.replace('.txt', '')
                    # ── Per-file filter ───────────────────────────────────
                    if target_filename and base_name != target_filename:
                        continue
                    content_path = os.path.join(Config.APPROVED_CLEANED_DIR, filename)
                    meta_path = os.path.join(Config.APPROVED_CLEANED_DIR, f'{base_name}.meta.json')

                    try:
                        with open(content_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        metadata = {}
                        if os.path.exists(meta_path):
                            with open(meta_path, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)

                        if metadata.get('pushed_to_hf'):
                            results['cleaned']['skipped'] += 1
                            continue

                        result = hf_service.upload_cleaned_file(base_name, content, metadata, repo)
                        if result['success']:
                            results['cleaned']['uploaded'] += 1
                            results['cleaned']['files'].append(base_name)
                            metadata['pushed_to_hf'] = datetime.utcnow().isoformat() + 'Z'
                            with open(meta_path, 'w', encoding='utf-8') as f:
                                json.dump(metadata, f, indent=2, ensure_ascii=False)
                        else:
                            results['cleaned']['failed'] += 1
                            current_app.logger.error('Cleaned upload failed for %s: %s', base_name, result.get('error'))
                    except Exception as e:
                        current_app.logger.error('Exception uploading cleaned %s: %s', base_name, str(e))
                        results['cleaned']['failed'] += 1

        # ------------------------------------------------------------------
        # Push chunks  — BATCHED per folder (NEW: avoids rate-limiting)
        # ------------------------------------------------------------------
        if push_type in ['chunked', 'all']:
            repo = data.get('chunked_repo') or Config.HF_CHUNKED_REPO
            if os.path.exists(Config.APPROVED_CHUNKED_DIR):
                for folder_name in sorted(os.listdir(Config.APPROVED_CHUNKED_DIR)):
                    folder_path = os.path.join(Config.APPROVED_CHUNKED_DIR, folder_name)
                    if not os.path.isdir(folder_path):
                        continue
                    # ── Per-file filter ───────────────────────────────────
                    if target_filename and folder_name != target_filename:
                        continue

                    # Collect only chunks that haven't been pushed yet
                    unpushed_chunks = []
                    chunk_file_paths = {}   # chunk_index -> file path (for marking after push)

                    for chunk_file in sorted(os.listdir(folder_path)):
                        if not chunk_file.endswith('.json'):
                            continue
                        chunk_path = os.path.join(folder_path, chunk_file)
                        try:
                            with open(chunk_path, 'r', encoding='utf-8') as f:
                                chunk_data = json.load(f)

                            if chunk_data.get('pushed_to_hf'):
                                results['chunked']['skipped'] += 1
                                continue

                            unpushed_chunks.append(chunk_data)
                            chunk_file_paths[chunk_data.get('chunk_index', chunk_file)] = chunk_path
                        except Exception as e:
                            current_app.logger.error('Error reading chunk %s: %s', chunk_path, str(e))
                            results['chunked']['failed'] += 1

                    if not unpushed_chunks:
                        continue

                    # Upload the whole folder's unpushed chunks in one batched request
                    result = hf_service.upload_chunks_batch(folder_name, unpushed_chunks, repo=repo)

                    results['chunked']['uploaded'] += result.get('uploaded_count', 0)
                    results['chunked']['failed']   += result.get('failed_count', 0)
                    if result.get('failed_chunks'):
                        results['chunked']['failed_chunks'].extend(result['failed_chunks'])

                    if result.get('uploaded_count', 0) > 0:
                        results['chunked']['files'].append(
                            f"{folder_name} ({result['uploaded_count']} chunks)"
                        )

                    # Mark successfully-pushed chunks in their JSON files
                    failed_set = set(result.get('failed_chunks', []))
                    pushed_at = datetime.utcnow().isoformat() + 'Z'
                    for chunk_data in unpushed_chunks:
                        chunk_index = chunk_data.get('chunk_index')
                        chunk_key_name = f'{folder_name}/chunk_{chunk_index:02d}.json'
                        if chunk_key_name not in failed_set:
                            chunk_path = chunk_file_paths.get(chunk_index)
                            if chunk_path and os.path.exists(chunk_path):
                                try:
                                    chunk_data['pushed_to_hf'] = pushed_at
                                    with open(chunk_path, 'w', encoding='utf-8') as f:
                                        json.dump(chunk_data, f, indent=2, ensure_ascii=False)
                                except Exception as e:
                                    current_app.logger.warning('Could not mark chunk as pushed: %s', str(e))

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------
        total_uploaded = (results['raw']['uploaded'] +
                          results['cleaned']['uploaded'] +
                          results['chunked']['uploaded'])
        total_failed = (results['raw']['failed'] +
                        results['cleaned']['failed'] +
                        results['chunked']['failed'])
        total_skipped = (results['raw']['skipped'] +
                         results['cleaned']['skipped'] +
                         results['chunked']['skipped'])

        return jsonify({
            'success': True,
            'message': (
                f'Pushed {total_uploaded} items to HuggingFace'
                + (f', {total_failed} failed' if total_failed else '')
                + (f', {total_skipped} already pushed (skipped)' if total_skipped else '')
            ),
            'results': results,
            'totals': {
                'uploaded': total_uploaded,
                'failed': total_failed,
                'skipped': total_skipped,
            },
        })

    except Exception as e:
        current_app.logger.error('Error pushing to HuggingFace: %s', str(e))
        return jsonify({
            'success': False,
            'error': f'Failed to push to HuggingFace: {str(e)}',
        }), 500


# -----------------------------------------------------------------------------
# DELETE /api/admin/delete-approved  - Delete approved file(s) by stage
# -----------------------------------------------------------------------------
@admin_bp.route('/delete-approved', methods=['DELETE'])
def delete_approved():
    """
    Delete one or more stages of an approved file.

    Expected JSON body:
    {
        "filename": "grade_10_science",
        "type": "raw" | "cleaned" | "chunks" | "all"
    }
    """
    try:
        from ..config import Config

        data = request.get_json() or {}
        filename = (data.get('filename') or '').strip()
        delete_type = (data.get('type') or 'all').strip().lower()

        if not filename:
            return jsonify({'success': False, 'error': 'filename is required'}), 400

        deleted = []

        def _remove_raw():
            raw_content = os.path.join(Config.APPROVED_RAW_DIR, f'{filename}.txt')
            raw_meta    = os.path.join(Config.APPROVED_RAW_DIR, f'{filename}.meta.json')
            removed = False
            for p in (raw_content, raw_meta):
                if os.path.exists(p):
                    os.remove(p)
                    removed = True
            if removed:
                deleted.append('raw')

        def _remove_cleaned():
            cln_content = os.path.join(Config.APPROVED_CLEANED_DIR, f'{filename}.txt')
            cln_meta    = os.path.join(Config.APPROVED_CLEANED_DIR, f'{filename}.meta.json')
            removed = False
            for p in (cln_content, cln_meta):
                if os.path.exists(p):
                    os.remove(p)
                    removed = True
            if removed:
                deleted.append('cleaned')

        def _remove_chunks():
            chunks_dir = os.path.join(Config.APPROVED_CHUNKED_DIR, filename)
            if os.path.exists(chunks_dir) and os.path.isdir(chunks_dir):
                shutil.rmtree(chunks_dir)
                deleted.append('chunks')

        if delete_type in ('raw', 'all'):
            _remove_raw()
        if delete_type in ('cleaned', 'all'):
            _remove_cleaned()
        if delete_type in ('chunks', 'all'):
            _remove_chunks()

        if not deleted:
            return jsonify({'success': False, 'error': f'Nothing found to delete for "{filename}" ({delete_type})'}), 404

        current_app.logger.info('Deleted approved %s for %s', deleted, filename)
        return jsonify({
            'success': True,
            'message': f'Deleted {", ".join(deleted)} for "{filename}"',
            'deleted': deleted,
        })

    except Exception as e:
        current_app.logger.error('Error deleting approved file: %s', str(e))
        return jsonify({'success': False, 'error': f'Delete failed: {str(e)}'}), 500