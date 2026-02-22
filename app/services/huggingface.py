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
import time
import logging
from typing import Optional, List, Dict, Any
from huggingface_hub import HfApi, hf_hub_download, CommitOperationAdd
from huggingface_hub.utils import RepositoryNotFoundError, HfHubHTTPError

logger = logging.getLogger(__name__)


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
            # Upload content + metadata in ONE commit (avoids double rate-limit hit)
            operations = [
                CommitOperationAdd(
                    path_in_repo=f'{filename}.txt',
                    path_or_fileobj=content.encode('utf-8'),
                ),
                CommitOperationAdd(
                    path_in_repo=f'{filename}.meta.json',
                    path_or_fileobj=json.dumps(metadata, indent=2, ensure_ascii=False).encode('utf-8'),
                ),
            ]
            self.api.create_commit(
                repo_id=target_repo,
                repo_type='dataset',
                operations=operations,
                commit_message=f'Add raw file: {filename}',
            )

            return {
                'success': True,
                'message': f'Uploaded {filename} to {target_repo}',
                'repo': target_repo,
            }

        except RepositoryNotFoundError:
            return {
                'success': False,
                'error': f'Repository {target_repo} not found. Please create it first.',
            }
        except HfHubHTTPError as e:
            return {
                'success': False,
                'error': f'HuggingFace API error: {str(e)}',
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}',
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
            operations = [
                CommitOperationAdd(
                    path_in_repo=f'{filename}.txt',
                    path_or_fileobj=content.encode('utf-8'),
                ),
                # NOTE: meta.json intentionally NOT pushed to cleaned repo
                #       — only the plain text file is uploaded.
            ]
            self.api.create_commit(
                repo_id=target_repo,
                repo_type='dataset',
                operations=operations,
                commit_message=f'Add cleaned file: {filename}',
            )

            return {
                'success': True,
                'message': f'Uploaded {filename} to {target_repo}',
                'repo': target_repo,
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}',
            }
    
    def upload_chunk(self, folder_name: str, chunk_file: str, chunk_data: Dict[str, Any], repo: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a single chunk to mozhii-chunked-data repository.
        Uses create_commit for atomicity and to avoid rate-limit issues.
        """
        if not self.is_configured():
            return {'success': False, 'error': 'HuggingFace not configured'}

        target_repo = repo or self.chunked_repo

        try:
            chunk_filename = f'{folder_name}/{chunk_file}'
            chunk_content = json.dumps(chunk_data, indent=2, ensure_ascii=False).encode('utf-8')

            self.api.create_commit(
                repo_id=target_repo,
                repo_type='dataset',
                operations=[CommitOperationAdd(path_in_repo=chunk_filename, path_or_fileobj=chunk_content)],
                commit_message=f'Add {chunk_file} for {folder_name}',
            )

            return {
                'success': True,
                'message': f'Uploaded {chunk_file} to {target_repo}',
                'repo': target_repo,
            }

        except Exception as e:
            return {'success': False, 'error': f'Upload failed: {str(e)}'}

    def upload_chunks_batch(
        self,
        folder_name: str,
        chunks: List[Dict[str, Any]],
        repo: Optional[str] = None,
        batch_size: int = 50,
    ) -> Dict[str, Any]:
        """
        Upload many chunks in batched create_commit calls.

        Instead of one API call per chunk (which triggers HuggingFace rate
        limits for large sets like 223 chunks), we group chunks into batches
        and push each batch as a SINGLE commit.  This is drastically faster
        and avoids rate-limiting / timeout failures.

        Args:
            folder_name: Name of the folder (source file name)
            chunks: List of chunk dicts to upload
            repo: Optional custom repository name
            batch_size: How many chunks per commit (default 50)

        Returns:
            dict with success status, uploaded count, and per-chunk errors
        """
        if not self.is_configured():
            return {'success': False, 'error': 'HuggingFace not configured'}

        target_repo = repo or self.chunked_repo
        uploaded_count = 0
        failed_chunks: List[str] = []
        MAX_RETRIES = 3

        # Split into batches
        for batch_start in range(0, len(chunks), batch_size):
            batch = chunks[batch_start: batch_start + batch_size]
            operations = []

            for chunk in batch:
                chunk_index = chunk.get('chunk_index', 1)
                chunk_filename = f'{folder_name}/chunk_{chunk_index:02d}.json'
                chunk_content = json.dumps(chunk, indent=2, ensure_ascii=False).encode('utf-8')
                operations.append(
                    CommitOperationAdd(path_in_repo=chunk_filename, path_or_fileobj=chunk_content)
                )

            # Retry the whole batch up to MAX_RETRIES times
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    self.api.create_commit(
                        repo_id=target_repo,
                        repo_type='dataset',
                        operations=operations,
                        commit_message=(
                            f'Add chunks {batch_start + 1}-{batch_start + len(batch)} for {folder_name}'
                        ),
                    )
                    uploaded_count += len(batch)
                    break  # success — move to next batch
                except HfHubHTTPError as e:
                    status = getattr(e, 'response', None)
                    status_code = status.status_code if status is not None else 0
                    if status_code == 429 or attempt < MAX_RETRIES:
                        wait = 2 ** attempt  # exponential back-off: 2s, 4s, 8s
                        logger.warning(
                            'HF rate-limit / transient error on batch %d-%d (attempt %d/%d). '
                            'Retrying in %ds. Error: %s',
                            batch_start + 1, batch_start + len(batch), attempt, MAX_RETRIES, wait, e,
                        )
                        time.sleep(wait)
                    else:
                        # Final attempt failed — record failed chunk IDs
                        for chunk in batch:
                            failed_chunks.append(
                                f'{folder_name}/chunk_{chunk.get("chunk_index", "?"):02d}.json'
                            )
                        logger.error('Batch upload permanently failed: %s', e)
                        break
                except Exception as e:
                    if attempt < MAX_RETRIES:
                        time.sleep(2 ** attempt)
                    else:
                        for chunk in batch:
                            failed_chunks.append(
                                f'{folder_name}/chunk_{chunk.get("chunk_index", "?"):02d}.json'
                            )
                        logger.error('Batch upload error: %s', e)
                        break

        success = len(failed_chunks) == 0
        return {
            'success': success,
            'message': f'Uploaded {uploaded_count} chunks ({len(failed_chunks)} failed) to {target_repo}',
            'repo': target_repo,
            'uploaded_count': uploaded_count,
            'failed_count': len(failed_chunks),
            'failed_chunks': failed_chunks,
        }

    def upload_chunks(self, folder_name: str, chunks: List[Dict[str, Any]], repo: Optional[str] = None) -> Dict[str, Any]:
        """
        Legacy wrapper — delegates to upload_chunks_batch for reliability.
        """
        return self.upload_chunks_batch(folder_name, chunks, repo=repo)

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
