"""
=============================================================================
Mozhii RAG Data Platform - HuggingFace Service
=============================================================================
This service handles all interactions with HuggingFace Hub.

Responsibilities:
    - Upload approved files to HuggingFace repositories
    - Download files from HuggingFace for reference
    - Sync local approved data with HuggingFace
    - Handle authentication and error recovery

HuggingFace Repositories:
    - mozhii-raw-data: Raw collected Tamil content
    - mozhii-cleaned-data: Cleaned/processed content
    - mozhii-chunked-data: RAG-ready chunks (JSON format)
=============================================================================
"""

import os
import json
from typing import Optional, List, Dict, Any
from huggingface_hub import HfApi, upload_file, hf_hub_download
from huggingface_hub.utils import RepositoryNotFoundError, HfHubHTTPError


class HuggingFaceService:
    """
    Service class for HuggingFace Hub operations.
    
    This class provides a clean interface for uploading and downloading
    files from HuggingFace repositories. It handles authentication,
    error handling, and provides consistent responses.
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the HuggingFace service.
        
        Args:
            token: HuggingFace API token. If not provided, will try to
                   read from environment variable HF_TOKEN.
        """
        # Get token from parameter or environment
        self.token = token or os.getenv('HF_TOKEN', '')
        
        # Initialize HuggingFace API client
        self.api = HfApi(token=self.token) if self.token else None
        
        # Repository names from config
        from ..config import Config
        self.raw_repo = Config.HF_RAW_REPO
        self.cleaned_repo = Config.HF_CLEANED_REPO
        self.chunked_repo = Config.HF_CHUNKED_REPO
    
    def is_configured(self) -> bool:
        """
        Check if HuggingFace is properly configured.
        
        Returns:
            bool: True if token and repos are configured
        """
        return bool(self.token and self.api)
    
    # -------------------------------------------------------------------------
    # Upload Operations
    # -------------------------------------------------------------------------
    
    def upload_raw_file(self, filename: str, content: str, metadata: Dict[str, Any], repo: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a raw data file to mozhii-raw-data repository.
        
        Args:
            filename: Name of the file (without extension)
            content: The raw text content
            metadata: File metadata dictionary
            repo: Optional custom repository name (overrides default)
        
        Returns:
            dict: Result with success status and message
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'HuggingFace not configured. Please set HF_TOKEN.'
            }
        
        target_repo = repo or self.raw_repo
        
        try:
            # Upload content file
            content_path = f'{filename}.txt'
            self.api.upload_file(
                path_or_fileobj=content.encode('utf-8'),
                path_in_repo=content_path,
                repo_id=target_repo,
                repo_type='dataset',
                commit_message=f'Add raw file: {filename}'
            )
            
            # Upload metadata file
            meta_path = f'{filename}.meta.json'
            meta_content = json.dumps(metadata, indent=2, ensure_ascii=False)
            self.api.upload_file(
                path_or_fileobj=meta_content.encode('utf-8'),
                path_in_repo=meta_path,
                repo_id=target_repo,
                repo_type='dataset',
                commit_message=f'Add metadata for: {filename}'
            )
            
            return {
                'success': True,
                'message': f'Uploaded {filename} to {target_repo}',
                'repo': target_repo
            }
            
        except RepositoryNotFoundError:
            return {
                'success': False,
                'error': f'Repository {self.raw_repo} not found. Please create it first.'
            }
        except HfHubHTTPError as e:
            return {
                'success': False,
                'error': f'HuggingFace API error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}'
            }
    
    def upload_cleaned_file(self, filename: str, content: str, metadata: Dict[str, Any], repo: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a cleaned data file to mozhii-cleaned-data repository.
        
        Args:
            filename: Name of the file
            content: The cleaned text content
            metadata: File metadata dictionary
            repo: Optional custom repository name (overrides default)
        
        Returns:
            dict: Result with success status and message
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'HuggingFace not configured'
            }
        
        target_repo = repo or self.cleaned_repo
        
        try:
            # Upload content file
            self.api.upload_file(
                path_or_fileobj=content.encode('utf-8'),
                path_in_repo=f'{filename}.txt',
                repo_id=target_repo,
                repo_type='dataset',
                commit_message=f'Add cleaned file: {filename}'
            )
            
            # Upload metadata
            meta_content = json.dumps(metadata, indent=2, ensure_ascii=False)
            self.api.upload_file(
                path_or_fileobj=meta_content.encode('utf-8'),
                path_in_repo=f'{filename}.meta.json',
                repo_id=target_repo,
                repo_type='dataset',
                commit_message=f'Add metadata for: {filename}'
            )
            
            return {
                'success': True,
                'message': f'Uploaded {filename} to {target_repo}',
                'repo': target_repo
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}'
            }
    
    def upload_chunk(self, folder_name: str, chunk_file: str, chunk_data: Dict[str, Any], repo: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a single chunk to mozhii-chunked-data repository.
        
        Args:
            folder_name: Name of the folder (source file name)
            chunk_file: Chunk filename (e.g., chunk_01.json)
            chunk_data: Chunk data dictionary
            repo: Optional custom repository name (overrides default)
        
        Returns:
            dict: Result with success status and message
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'HuggingFace not configured'
            }
        
        target_repo = repo or self.chunked_repo
        
        try:
            chunk_filename = f'{folder_name}/{chunk_file}'
            chunk_content = json.dumps(chunk_data, indent=2, ensure_ascii=False)
            
            self.api.upload_file(
                path_or_fileobj=chunk_content.encode('utf-8'),
                path_in_repo=chunk_filename,
                repo_id=target_repo,
                repo_type='dataset',
                commit_message=f'Add {chunk_file} for {folder_name}'
            )
            
            return {
                'success': True,
                'message': f'Uploaded {chunk_file} to {target_repo}',
                'repo': target_repo
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}'
            }
    
    def upload_chunks(self, folder_name: str, chunks: List[Dict[str, Any]], repo: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload chunks to mozhii-chunked-data repository.
        
        Chunks are organized in folders named after the source file.
        Each chunk is saved as a separate JSON file.
        
        Args:
            folder_name: Name of the folder (source file name)
            chunks: List of chunk dictionaries
            repo: Optional custom repository name (overrides default)
        
        Returns:
            dict: Result with success status and message
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'HuggingFace not configured'
            }
        
        target_repo = repo or self.chunked_repo
        
        try:
            uploaded_count = 0
            
            for chunk in chunks:
                chunk_index = chunk.get('chunk_index', 1)
                chunk_filename = f'{folder_name}/chunk_{chunk_index:02d}.json'
                chunk_content = json.dumps(chunk, indent=2, ensure_ascii=False)
                
                self.api.upload_file(
                    path_or_fileobj=chunk_content.encode('utf-8'),
                    path_in_repo=chunk_filename,
                    repo_id=target_repo,
                    repo_type='dataset',
                    commit_message=f'Add chunk {chunk_index} for {folder_name}'
                )
                uploaded_count += 1
            
            return {
                'success': True,
                'message': f'Uploaded {uploaded_count} chunks to {target_repo}',
                'repo': target_repo,
                'count': uploaded_count
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}'
            }
    
    # -------------------------------------------------------------------------
    # Download Operations
    # -------------------------------------------------------------------------
    
    def list_raw_files(self) -> Dict[str, Any]:
        """
        List all files in the raw data repository.
        
        Returns:
            dict: List of files with metadata
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'HuggingFace not configured'
            }
        
        try:
            files = self.api.list_repo_files(
                repo_id=self.raw_repo,
                repo_type='dataset'
            )
            
            # Filter to only .txt files
            txt_files = [f.replace('.txt', '') for f in files if f.endswith('.txt')]
            
            return {
                'success': True,
                'files': txt_files,
                'count': len(txt_files)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to list files: {str(e)}'
            }
    
    def download_file(self, repo_type: str, filename: str) -> Dict[str, Any]:
        """
        Download a file from HuggingFace.
        
        Args:
            repo_type: 'raw', 'cleaned', or 'chunked'
            filename: Name of the file to download
        
        Returns:
            dict: File content and metadata
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'HuggingFace not configured'
            }
        
        # Select repository
        repos = {
            'raw': self.raw_repo,
            'cleaned': self.cleaned_repo,
            'chunked': self.chunked_repo
        }
        
        repo_id = repos.get(repo_type)
        if not repo_id:
            return {
                'success': False,
                'error': 'Invalid repo_type'
            }
        
        try:
            # Download content file
            file_path = hf_hub_download(
                repo_id=repo_id,
                filename=f'{filename}.txt',
                repo_type='dataset',
                token=self.token
            )
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                'success': True,
                'content': content,
                'filename': filename
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Download failed: {str(e)}'
            }
    
    # -------------------------------------------------------------------------
    # Sync Operations
    # -------------------------------------------------------------------------
    
    def sync_all_approved(self) -> Dict[str, Any]:
        """
        Sync all approved local files to HuggingFace.
        
        This is a batch operation that uploads all approved files
        that haven't been synced yet.
        
        Returns:
            dict: Sync results with counts
        """
        from ..config import Config
        
        results = {
            'raw': {'success': 0, 'failed': 0},
            'cleaned': {'success': 0, 'failed': 0},
            'chunked': {'success': 0, 'failed': 0}
        }
        
        # Sync raw files
        if os.path.exists(Config.APPROVED_RAW_DIR):
            for filename in os.listdir(Config.APPROVED_RAW_DIR):
                if filename.endswith('.txt'):
                    base_name = filename.replace('.txt', '')
                    content_path = os.path.join(Config.APPROVED_RAW_DIR, filename)
                    meta_path = os.path.join(Config.APPROVED_RAW_DIR, f'{base_name}.meta.json')
                    
                    with open(content_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    metadata = {}
                    if os.path.exists(meta_path):
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    
                    result = self.upload_raw_file(base_name, content, metadata)
                    if result['success']:
                        results['raw']['success'] += 1
                    else:
                        results['raw']['failed'] += 1
        
        # Sync cleaned files
        if os.path.exists(Config.APPROVED_CLEANED_DIR):
            for filename in os.listdir(Config.APPROVED_CLEANED_DIR):
                if filename.endswith('.txt'):
                    base_name = filename.replace('.txt', '')
                    content_path = os.path.join(Config.APPROVED_CLEANED_DIR, filename)
                    meta_path = os.path.join(Config.APPROVED_CLEANED_DIR, f'{base_name}.meta.json')
                    
                    with open(content_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    metadata = {}
                    if os.path.exists(meta_path):
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    
                    result = self.upload_cleaned_file(base_name, content, metadata)
                    if result['success']:
                        results['cleaned']['success'] += 1
                    else:
                        results['cleaned']['failed'] += 1
        
        # Sync chunks
        if os.path.exists(Config.APPROVED_CHUNKED_DIR):
            for folder_name in os.listdir(Config.APPROVED_CHUNKED_DIR):
                folder_path = os.path.join(Config.APPROVED_CHUNKED_DIR, folder_name)
                if os.path.isdir(folder_path):
                    chunks = []
                    for chunk_file in os.listdir(folder_path):
                        if chunk_file.endswith('.json'):
                            chunk_path = os.path.join(folder_path, chunk_file)
                            with open(chunk_path, 'r', encoding='utf-8') as f:
                                chunks.append(json.load(f))
                    
                    if chunks:
                        result = self.upload_chunks(folder_name, chunks)
                        if result['success']:
                            results['chunked']['success'] += 1
                        else:
                            results['chunked']['failed'] += 1
        
        return {
            'success': True,
            'results': results
        }
