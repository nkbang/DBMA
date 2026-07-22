"""core/document_identity.py — Document Identity & Content Hash Foundation.

Establishes deterministic, content-based document identity for DBMA Processing Engine.

Requirements:
- Same content → same document_id (deterministic)
- Modified content → new document_id
- Unknown metadata fields → None (never invent values)
- Non-breaking: additive only, no pipeline flow changes

Usage:
    from core.document_identity import generate_document_id, compute_content_hash, generate_chunk_id
    
    doc_id = generate_document_id(content=full_text)
    file_hash = compute_content_hash(full_text)
    chunk_id = generate_chunk_id(doc_id, index=42)
"""

from __future__ import annotations

import hashlib
import datetime
from typing import Optional

# Pipeline version identifier — increment when this module changes
PROCESSING_VERSION = "1.1.x"


def generate_document_id(content: str, source_file: str = "") -> str:
    """Generate a deterministic document identity from content.
    
    Uses SHA-256 of normalized text content for content-based identity.
    Same content → same ID regardless of filename/path changes.
    Modified content → new ID.
    
    Args:
        content: Normalized text content (or raw text to be normalized)
        source_file: Original filename used as fallback for empty content
    
    Returns:
        32-character hex SHA-256 prefix document ID
    """
    if not content or not content.strip():
        # Fallback to source file path for empty documents
        if source_file:
            fallback = f"empty_{source_file}"
        else:
            fallback = "empty_unknown"
        return hashlib.sha256(fallback.encode("utf-8")).hexdigest()[:32]
    
    # Normalize content before hashing (whitespace/formatting noise should not change ID)
    content_for_hash = _normalize_for_identity(content)
    
    if not content_for_hash.strip():
        # If normalization strips everything, use source_file as last resort
        if source_file:
            return hashlib.sha256(f"empty_{source_file}".encode("utf-8")).hexdigest()[:32]
        else:
            return hashlib.sha256("unknown_empty".encode("utf-8")).hexdigest()[:32]
    
    doc_id = hashlib.sha256(content_for_hash.encode("utf-8")).hexdigest()[:32]
    return doc_id


def compute_content_hash(content: str) -> str:
    """Compute full SHA-256 content hash for document fingerprinting.
    
    Args:
        content: Text content to hash
    
    Returns:
        64-character hex SHA-256 full hash
    """
    if not content or not content.strip():
        return hashlib.sha256("empty".encode("utf-8")).hexdigest()
    
    content_for_hash = _normalize_for_identity(content)
    return hashlib.sha256(content_for_hash.encode("utf-8")).hexdigest()


def generate_chunk_id(document_id: str, chunk_index: int) -> str:
    """Generate deterministic chunk identity.
    
    Args:
        document_id: 32-char document ID (from generate_document_id)
        chunk_index: Zero-based chunk index
    
    Returns:
        Chunk ID in format {doc_id[:16]}_chunk_{idx:05d}
    
    Example:
        >>> generate_chunk_id("a1b2c3d4e5f6...", 42)
        'a1b2c3d4e5f6..._chunk_00042'
    """
    return f"{document_id}_chunk_{chunk_index:05d}"


def generate_processing_timestamp() -> str:
    """Generate ISO 8601 timestamp for document processing.
    
    Returns:
        ISO 8601 formatted timestamp string
    """
    return datetime.datetime.now().isoformat(timespec="seconds")


def build_document_metadata(
    content: str,
    source_file: str,
    language: str = "en",
    noise_score: float = 0.0,
    noise_mode: str = "-",
    source_type: str = "",
    is_ocr: bool = False,
    chunk_count: int = 0,
    batch_id: Optional[str] = None,
    book: Optional[str] = None,
    chapter: Optional[int] = None,
    page: Optional[int] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    doc_type: Optional[str] = None,
) -> dict:
    """Build complete document metadata object per METADATA_CONTRACT_v1.
    
    Unknown values are set to None (never invents missing data).
    
    Args:
        content: Document text content
        source_file: Original filename
        language: Detected language code
        noise_score: Noise metric 0-100
        noise_mode: Noise classification string
        source_type: File extension without dot
        is_ocr: Whether OCR was used
        chunk_count: Number of chunks produced
        batch_id: Batch processing identifier (optional)
        book: Book/section identifier (None if unknown)
        chapter: Chapter number (None if unknown)
        page: Page reference (None if unknown)
        title: Document title (None if unknown)
        author: Author name (None if unknown)
        doc_type: Document type (주석/설교/시전/논문/기타, None if unknown)
    
    Returns:
        Metadata dictionary with all required fields present
    """
    doc_id = generate_document_id(content, source_file)
    file_hash = compute_content_hash(content)
    timestamp = generate_processing_timestamp()
    
    metadata = {
        # Mandatory fields (always present)
        "document_id": doc_id,
        "source_file": source_file,
        "file_hash": file_hash,
        "created_at": timestamp,
        "processing_version": PROCESSING_VERSION,
        
        # Structural fields (unknown = None)
        "title": title,
        "author": author,
        "book": book,
        "chapter": chapter,
        "page": page,
        "batch_id": batch_id,
        
        # Processing metadata (always present)
        "language": language,
        "noise_score": noise_score,
        "noise_mode": noise_mode,
        "source_type": source_type or (source_file.rsplit(".", 1)[-1] if "." in source_file else ""),
        "is_ocr": is_ocr,
        "chunk_count": chunk_count,
        "chunk_id_prefix": doc_id,
        
        # Document type (unknown = None — never invent)
        "doc_type": doc_type,
    }
    
    return metadata


def _normalize_for_identity(content: str) -> str:
    """Normalize text for identity hashing.
    
    Strips whitespace variations but preserves meaningful content.
    This ensures that minor formatting changes don't alter the document ID.
    
    Args:
        content: Raw text content
    
    Returns:
        Normalized text suitable for hashing
    """
    # Normalize line endings
    text = content.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple blank lines to one
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    # Strip leading/trailing whitespace
    text = text.strip()
    return text