"""core/document_context.py — DocumentContext state object.

Assembles the outputs of core/document_identity.py and core/identity_registry.py
into a single state object. Does not own identity generation or persistence
(see docs/architecture/DBMA-DocumentContext-Design-v1.md §2).

Phase 1 skeleton only: dataclass definition, no pipeline integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from core.document_identity import PROCESSING_VERSION, generate_processing_timestamp


@dataclass
class DocumentContext:
    # Identity
    document_id: str
    file_hash: str

    # Source
    source_file: str
    source_type: str
    is_ocr: bool = False

    # Structural metadata (unknown = None 원칙 유지)
    title: Optional[str] = None
    author: Optional[str] = None
    book: Optional[str] = None
    chapter: Optional[int] = None
    page: Optional[int] = None
    batch_id: Optional[str] = None

    # Processing metadata
    language: str = "en"
    noise_score: float = 0.0
    noise_mode: str = "-"
    processing_version: str = PROCESSING_VERSION

    # Chunk references
    chunk_ids: list[str] = field(default_factory=list)
    chunk_count: int = 0

    # TSU references (ADR-002 매핑 테이블 방식 — future integration point)
    tsu_refs: list[str] = field(default_factory=list)

    # Lifecycle
    lifecycle_state: str = "CREATED"
    ingest_status: str = "PROCESSED"
    retry_count: int = 0
    last_failure_reason: Optional[str] = None

    # Pipeline completion flags (identity_registry.py와 동일 스키마)
    pipeline_flags: dict = field(default_factory=lambda: {
        "ingested": False, "copied": False, "extracted": False,
        "cleaned": False, "chunked": False, "output_generated": False,
        "verified": False,
    })

    # Timestamps
    # [SPRINT17-Phase2-B] Two distinct moments, kept as two distinct fields
    # instead of overloading one mutable field for both:
    #   created_at    — when this document's identity was first established
    #                   (Point A). Immutable after construction. This is the
    #                   document's own creation time, not a pipeline event.
    #   registered_at — when this context was persisted to the identity
    #                   registry (Point C, immediately before
    #                   register_document()). Set once per registration.
    created_at: str = ""
    registered_at: str = ""
    last_processed_at: str = ""

    # Artifact paths
    md_path: Optional[str] = None
    copied_source_path: Optional[str] = None

    def __post_init__(self) -> None:
        # [SPRINT17-Phase1-B-5] created_at authority lives here — initialized
        # exactly once, at construction, unless a caller already supplied one
        # (e.g. a future from_metadata_dict() rehydration path). Never
        # reassigned afterward (see Phase2-B — registered_at is the field
        # that changes at registration time, not this one).
        if not self.created_at:
            self.created_at = generate_processing_timestamp()

    def to_metadata_dict(self) -> dict:
        """Serialize to the dict shape produced by
        core.document_identity.build_document_metadata(), so callers such as
        core.identity_registry.register_document() can consume it unchanged.

        [SPRINT17-Phase2-B] The dict's "created_at" key is sourced from
        registered_at, not created_at — this preserves existing registry
        output (register_document() has always received the Point-C
        registration timestamp under that key). The schema/key name is
        unchanged; only the internal source field is now correctly separated
        from the document's own (immutable) creation time.

        Raises:
            ValueError: if document_id, file_hash, or registered_at is empty.
                The first two are required by register_document() for
                identity/dedup lookups; registered_at must be set (by the
                caller, immediately before this call) so the registry
                continues to receive a real timestamp instead of an empty one.
        """
        if not self.document_id:
            raise ValueError("DocumentContext.to_metadata_dict(): document_id is required")
        if not self.file_hash:
            raise ValueError("DocumentContext.to_metadata_dict(): file_hash is required")
        if not self.registered_at:
            raise ValueError("DocumentContext.to_metadata_dict(): registered_at is required")

        return {
            # Mandatory fields (always present)
            "document_id": self.document_id,
            "source_file": self.source_file,
            "file_hash": self.file_hash,
            "created_at": self.registered_at,
            "processing_version": self.processing_version,

            # Structural fields (unknown = None)
            "title": self.title,
            "author": self.author,
            "book": self.book,
            "chapter": self.chapter,
            "page": self.page,
            "batch_id": self.batch_id,

            # Processing metadata (always present)
            "language": self.language,
            "noise_score": self.noise_score,
            "noise_mode": self.noise_mode,
            "source_type": self.source_type,
            "is_ocr": self.is_ocr,
            "chunk_count": self.chunk_count,
            "chunk_id_prefix": self.document_id,
        }
