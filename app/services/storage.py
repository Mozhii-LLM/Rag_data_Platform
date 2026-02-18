"""
=============================================================================
Mozhii RAG Data Platform - Storage Service
=============================================================================
This service handles local file storage operations.

Responsibilities:
    - Manage pending and approved directories
    - File CRUD operations
    - Backup and recovery
    - File validation

Directory Structure:
    data/
    ├── pending/
    │   ├── raw/
    │   ├── cleaned/
    │   └── chunked/
    └── approved/
        ├── raw/
        ├── cleaned/
        └── chunked/
=============================================================================
"""

import os
import json
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Any


class StorageService:
    """
    Service class for local file storage management.
    
    Provides a clean interface for file operations across the different
    data stages (raw, cleaned, chunked) and states (pending, approved).
    """
    
    def __init__(self):
        """
        Initialize the storage service.
        
        Sets up paths and ensures all required directories exist.
        """
        from ..config import Config
        
        # Store config reference
        self.config = Config
        
        # Define all directories
        self.dirs = {
            'pending_raw': Config.PENDING_RAW_DIR,
            'pending_cleaned': Config.PENDING_CLEANED_DIR,
            'pending_chunked': Config.PENDING_CHUNKED_DIR,
            'approved_raw': Config.APPROVED_RAW_DIR,
            'approved_cleaned': Config.APPROVED_CLEANED_DIR,
            'approved_chunked': Config.APPROVED_CHUNKED_DIR
        }
        
        # Ensure all directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """
        Create all required directories if they don't exist.
        
        This is called on initialization to ensure the storage
        structure is always ready.
        """
        for dir_path in self.dirs.values():
            os.makedirs(dir_path, exist_ok=True)
    
    # -------------------------------------------------------------------------
    # File Read Operations
    # -------------------------------------------------------------------------
    
    def get_file(self, stage: str, status: str, filename: str) -> Optional[Dict[str, Any]]:
        """
        Read a file and its metadata.
        
        Args:
            stage: 'raw', 'cleaned', or 'chunked'
            status: 'pending' or 'approved'
            filename: Name of the file (without extension)
        
        Returns:
            dict: File content and metadata, or None if not found
        """
        dir_key = f'{status}_{stage}'
        if dir_key not in self.dirs:
            return None
        
        base_dir = self.dirs[dir_key]
        content_path = os.path.join(base_dir, f'{filename}.txt')
        meta_path = os.path.join(base_dir, f'{filename}.meta.json')
        
        if not os.path.exists(content_path):
            return None
        
        try:
            with open(content_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            metadata = {}
            if os.path.exists(meta_path):
                with open(meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            return {
                'filename': filename,
                'content': content,
                'metadata': metadata,
                'stage': stage,
                'status': status
            }
            
        except Exception as e:
            print(f'Error reading file {filename}: {e}')
            return None
    
    def list_files(self, stage: str, status: str) -> List[Dict[str, Any]]:
        """
        List all files in a specific stage and status.
        
        Args:
            stage: 'raw', 'cleaned', or 'chunked'
            status: 'pending' or 'approved'
        
        Returns:
            list: Array of file metadata objects
        """
        dir_key = f'{status}_{stage}'
        if dir_key not in self.dirs:
            return []
        
        base_dir = self.dirs[dir_key]
        files = []
        
        if not os.path.exists(base_dir):
            return files
        
        if stage == 'chunked':
            # Chunked files are organized in folders
            for folder_name in os.listdir(base_dir):
                folder_path = os.path.join(base_dir, folder_name)
                if os.path.isdir(folder_path):
                    chunk_count = len([f for f in os.listdir(folder_path) if f.endswith('.json')])
                    files.append({
                        'filename': folder_name,
                        'chunk_count': chunk_count,
                        'status': status
                    })
        else:
            # Raw and cleaned files are single files
            for filename in os.listdir(base_dir):
                if filename.endswith('.txt'):
                    base_name = filename.replace('.txt', '')
                    meta_path = os.path.join(base_dir, f'{base_name}.meta.json')
                    
                    metadata = {'filename': base_name}
                    if os.path.exists(meta_path):
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    
                    files.append(metadata)
        
        return files
    
    # -------------------------------------------------------------------------
    # File Write Operations
    # -------------------------------------------------------------------------
    
    def save_file(self, stage: str, filename: str, content: str, metadata: Dict[str, Any]) -> bool:
        """
        Save a file to the pending directory.
        
        Args:
            stage: 'raw' or 'cleaned'
            filename: Name of the file
            content: Text content
            metadata: Metadata dictionary
        
        Returns:
            bool: True if successful
        """
        dir_key = f'pending_{stage}'
        if dir_key not in self.dirs:
            return False
        
        base_dir = self.dirs[dir_key]
        content_path = os.path.join(base_dir, f'{filename}.txt')
        meta_path = os.path.join(base_dir, f'{filename}.meta.json')
        
        try:
            with open(content_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f'Error saving file {filename}: {e}')
            return False
    
    def save_chunk(self, folder_name: str, chunk: Dict[str, Any]) -> bool:
        """
        Save a chunk to the pending chunked directory.
        
        Args:
            folder_name: Name of the source file
            chunk: Chunk dictionary
        
        Returns:
            bool: True if successful
        """
        chunk_dir = os.path.join(self.dirs['pending_chunked'], folder_name)
        os.makedirs(chunk_dir, exist_ok=True)
        
        chunk_index = chunk.get('chunk_index', 1)
        chunk_path = os.path.join(chunk_dir, f'chunk_{chunk_index:02d}.json')
        
        try:
            with open(chunk_path, 'w', encoding='utf-8') as f:
                json.dump(chunk, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f'Error saving chunk: {e}')
            return False
    
    # -------------------------------------------------------------------------
    # Approval Operations
    # -------------------------------------------------------------------------
    
    def approve_file(self, stage: str, filename: str) -> bool:
        """
        Move a file from pending to approved.
        
        Args:
            stage: 'raw' or 'cleaned'
            filename: Name of the file
        
        Returns:
            bool: True if successful
        """
        pending_dir = self.dirs[f'pending_{stage}']
        approved_dir = self.dirs[f'approved_{stage}']
        
        pending_content = os.path.join(pending_dir, f'{filename}.txt')
        pending_meta = os.path.join(pending_dir, f'{filename}.meta.json')
        approved_content = os.path.join(approved_dir, f'{filename}.txt')
        approved_meta = os.path.join(approved_dir, f'{filename}.meta.json')
        
        if not os.path.exists(pending_content):
            return False
        
        try:
            # Update metadata
            metadata = {}
            if os.path.exists(pending_meta):
                with open(pending_meta, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            metadata['status'] = 'approved'
            metadata['approved_at'] = datetime.now().isoformat()
            
            # Move content file
            shutil.move(pending_content, approved_content)
            
            # Save updated metadata
            with open(approved_meta, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Remove old metadata
            if os.path.exists(pending_meta):
                os.remove(pending_meta)
            
            return True
            
        except Exception as e:
            print(f'Error approving file {filename}: {e}')
            return False
    
    def approve_chunk(self, folder_name: str, chunk_index: int) -> bool:
        """
        Move a chunk from pending to approved.
        
        Args:
            folder_name: Name of the source file
            chunk_index: Index of the chunk
        
        Returns:
            bool: True if successful
        """
        pending_dir = os.path.join(self.dirs['pending_chunked'], folder_name)
        approved_dir = os.path.join(self.dirs['approved_chunked'], folder_name)
        
        chunk_filename = f'chunk_{chunk_index:02d}.json'
        pending_path = os.path.join(pending_dir, chunk_filename)
        approved_path = os.path.join(approved_dir, chunk_filename)
        
        if not os.path.exists(pending_path):
            return False
        
        try:
            os.makedirs(approved_dir, exist_ok=True)
            
            # Read and update chunk
            with open(pending_path, 'r', encoding='utf-8') as f:
                chunk = json.load(f)
            
            chunk['status'] = 'approved'
            chunk['approved_at'] = datetime.now().isoformat()
            
            # Save to approved
            with open(approved_path, 'w', encoding='utf-8') as f:
                json.dump(chunk, f, indent=2, ensure_ascii=False)
            
            # Remove pending
            os.remove(pending_path)
            
            # Clean up empty folder
            if not os.listdir(pending_dir):
                os.rmdir(pending_dir)
            
            return True
            
        except Exception as e:
            print(f'Error approving chunk: {e}')
            return False
    
    # -------------------------------------------------------------------------
    # Delete Operations
    # -------------------------------------------------------------------------
    
    def delete_pending(self, stage: str, filename: str) -> bool:
        """
        Delete a pending file.
        
        Args:
            stage: 'raw', 'cleaned', or 'chunked'
            filename: Name of the file
        
        Returns:
            bool: True if successful
        """
        pending_dir = self.dirs[f'pending_{stage}']
        
        if stage == 'chunked':
            folder_path = os.path.join(pending_dir, filename)
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                shutil.rmtree(folder_path)
                return True
        else:
            content_path = os.path.join(pending_dir, f'{filename}.txt')
            meta_path = os.path.join(pending_dir, f'{filename}.meta.json')
            
            deleted = False
            if os.path.exists(content_path):
                os.remove(content_path)
                deleted = True
            if os.path.exists(meta_path):
                os.remove(meta_path)
                deleted = True
            
            return deleted
        
        return False
    
    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------
    
    def get_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get file count statistics.
        
        Returns:
            dict: Counts for each stage and status
        """
        stats = {}
        
        for key, dir_path in self.dirs.items():
            if not os.path.exists(dir_path):
                stats[key] = 0
                continue
            
            if 'chunked' in key:
                # Count chunk folders
                count = 0
                for folder in os.listdir(dir_path):
                    folder_path = os.path.join(dir_path, folder)
                    if os.path.isdir(folder_path):
                        count += len([f for f in os.listdir(folder_path) if f.endswith('.json')])
                stats[key] = count
            else:
                # Count .txt files
                stats[key] = len([f for f in os.listdir(dir_path) if f.endswith('.txt')])
        
        return stats
