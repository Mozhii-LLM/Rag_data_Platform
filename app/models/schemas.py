"""
=============================================================================
Mozhii RAG Data Platform - Data Schemas
=============================================================================
This module defines the data schemas/models used throughout the platform.

These are simple Python dataclasses that define the structure of data
at each stage of the pipeline:

    Raw Data → Cleaned Data → Chunks

Each schema includes:
    - Required fields
    - Optional fields with defaults
    - Validation methods
    - Serialization helpers
=============================================================================
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List
from datetime import datetime
import uuid


@dataclass
class RawDataSchema:
    """
    Schema for raw data submissions.
    
    This represents the structure of data submitted by collectors
    in the RAW DATA tab.
    
    Attributes:
        id: Unique identifier (auto-generated)
        filename: Name of the file (without extension)
        language: Language code (e.g., 'ta' for Tamil)
        source: Source type (e.g., 'gov_textbook')
        content: The raw text content
        content_length: Character count (auto-calculated)
        submitted_at: Timestamp of submission
        submitted_by: Role of submitter
        status: Approval status ('pending', 'approved', 'rejected')
        approved_at: Timestamp of approval (optional)
        approved_by: Who approved (optional)
    """
    
    filename: str
    language: str
    source: str
    content: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content_length: int = field(default=0)
    submitted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    submitted_by: str = field(default='collector')
    status: str = field(default='pending')
    approved_at: Optional[str] = field(default=None)
    approved_by: Optional[str] = field(default=None)
    
    def __post_init__(self):
        """Calculate content length after initialization."""
        if self.content:
            self.content_length = len(self.content)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_metadata(self) -> dict:
        """
        Convert to metadata dictionary (without content).
        Used for .meta.json files.
        """
        data = self.to_dict()
        del data['content']
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RawDataSchema':
        """Create instance from dictionary."""
        return cls(**data)
    
    def validate(self) -> List[str]:
        """
        Validate the schema.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if not self.filename or len(self.filename) < 3:
            errors.append('Filename must be at least 3 characters')
        
        if not self.filename.replace('_', '').replace('-', '').isalnum():
            errors.append('Filename can only contain letters, numbers, underscores, and hyphens')
        
        if not self.content or len(self.content) < 50:
            errors.append('Content must be at least 50 characters')
        
        if self.language not in ['ta', 'en', 'hi', 'te', 'ml', 'kn']:
            errors.append('Invalid language code')
        
        return errors


@dataclass
class CleanedDataSchema:
    """
    Schema for cleaned data.
    
    This represents data that has been cleaned by the NLP team
    and submitted through the CLEANING tab.
    
    Attributes:
        id: Unique identifier
        filename: Same as source raw file (for lineage)
        language: Language code
        source: Source type
        content: Cleaned text content
        original_raw_id: ID of the source raw data
        content_length: Character count
        submitted_at: Timestamp
        submitted_by: Role
        status: Approval status
    """
    
    filename: str
    content: str
    language: str = field(default='ta')
    source: str = field(default='unknown')
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_raw_id: Optional[str] = field(default=None)
    content_length: int = field(default=0)
    submitted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    submitted_by: str = field(default='cleaner')
    status: str = field(default='pending')
    approved_at: Optional[str] = field(default=None)
    approved_by: Optional[str] = field(default=None)
    
    def __post_init__(self):
        """Calculate content length after initialization."""
        if self.content:
            self.content_length = len(self.content)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_metadata(self) -> dict:
        """Convert to metadata (without content)."""
        data = self.to_dict()
        del data['content']
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CleanedDataSchema':
        """Create instance from dictionary."""
        return cls(**data)


@dataclass
class ChunkSchema:
    """
    Schema for content chunks (RAG-ready).
    
    This is the MOST IMPORTANT schema as it defines the structure
    of data that will be embedded and used for retrieval.
    
    Attributes:
        chunk_id: Unique chunk identifier (formatted)
        text: The chunk text content
        language: Language code
        category: Content category
        source: Source type
        chunk_index: Sequential index within the file
        source_file: Name of the source cleaned file
        overlap_reference: Context from previous chunk
        text_length: Character count
        created_at: Timestamp
        created_by: Role
        status: Approval status
    """
    
    text: str
    chunk_index: int
    source_file: str
    category: str
    language: str = field(default='ta')
    source: str = field(default='unknown')
    chunk_id: str = field(default='')
    overlap_reference: str = field(default='')
    text_length: int = field(default=0)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = field(default='chunker')
    status: str = field(default='pending')
    approved_at: Optional[str] = field(default=None)
    approved_by: Optional[str] = field(default=None)
    
    def __post_init__(self):
        """Calculate text length and generate chunk_id."""
        if self.text:
            self.text_length = len(self.text)
        
        if not self.chunk_id:
            self.chunk_id = self._generate_chunk_id()
    
    def _generate_chunk_id(self) -> str:
        """
        Generate a standardized chunk ID.
        
        Format: {lang}_{category_short}_{filename_short}_{index:02d}
        Example: ta_edu_grade10sci_01
        """
        cat_short = self.category[:3] if len(self.category) > 3 else self.category
        file_short = self.source_file.replace('_', '')[:10]
        return f"{self.language}_{cat_short}_{file_short}_{self.chunk_index:02d}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ChunkSchema':
        """Create instance from dictionary."""
        return cls(**data)
    
    def validate(self) -> List[str]:
        """
        Validate the chunk.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if not self.text or len(self.text) < 20:
            errors.append('Chunk text must be at least 20 characters')
        
        if not self.source_file:
            errors.append('Source file is required')
        
        if self.chunk_index < 1:
            errors.append('Chunk index must be positive')
        
        valid_categories = [
            'education', 'literature', 'news', 'science', 
            'history', 'culture', 'technology', 'health',
            'legal', 'government', 'religion', 'other'
        ]
        if self.category not in valid_categories:
            errors.append(f'Invalid category. Must be one of: {", ".join(valid_categories)}')
        
        return errors
    
    def to_rag_format(self) -> dict:
        """
        Convert to the exact format expected by the embedding pipeline.
        
        This is the format that will be stored in mozhii-chunked-data
        and consumed by the embedding pipeline.
        """
        return {
            'chunk_id': self.chunk_id,
            'text': self.text,
            'language': self.language,
            'category': self.category,
            'source': self.source,
            'chunk_index': self.chunk_index
        }
