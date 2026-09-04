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

# [SPRINT21-F-2] Valid pipeline_state values. Centralizes the state set that
# was previously only implicit in scattered literal-string assignments
# across core/processing.py and core/index_orchestrator.py (5+ sites) —
# see set_pipeline_state() below.
PIPELINE_STATES = ("NEW", "IDENTIFIED", "EXTRACTED", "PROCESSED", "TSU_READY", "INDEXED", "FAILED")


def set_pipeline_state(target, state: str) -> None:
    """Set pipeline_state on a DocumentContext instance or a registry
    record dict, rejecting typos/invalid values immediately instead of
    letting an unrecognized string silently sit in the registry.

    Args:
        target: DocumentContext instance, or a dict (registry record).
        state: One of PIPELINE_STATES.
    """
    if state not in PIPELINE_STATES:
        raise ValueError(f"invalid pipeline_state: {state!r} (valid: {PIPELINE_STATES})")
    if isinstance(target, dict):
        target["pipeline_state"] = state
    else:
        target.pipeline_state = state


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

    # [Task Order 017] Registry schema parity fields (§3 of Design v1)
    doc_type: Optional[str] = None
    superseded_by: Optional[str] = None
    supersedes: Optional[str] = None
    last_content_hash: Optional[str] = None
    max_retries: int = 3
    source_provenance: Optional[dict] = None

    # TSU references (ADR-002 매핑 테이블 방식 — future integration point)
    tsu_refs: list[str] = field(default_factory=list)

    # Lifecycle
    # [SPRINT21-B Phase1] pipeline_state tracks how far this document has
    # progressed toward being searchable: NEW/IDENTIFIED/EXTRACTED/PROCESSED/
    # TSU_READY/INDEXED/FAILED — orthogonal to ingest_status below, which
    # tracks whether *processing* needs to (re)run and must not change
    # meaning. Replaces lifecycle_state, which was set in exactly one place
    # (SKIP path) and never persisted (to_metadata_dict() didn't include it).
    pipeline_state: str = "NEW"
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

            # [SPRINT21-B Phase1] additive — see pipeline_state field comment.
            "pipeline_state": self.pipeline_state,

            # [Task Order 017 §4] Already existed but was missing from serialization
            "ingest_status": self.ingest_status,
            "retry_count": self.retry_count,
            "last_failure_reason": self.last_failure_reason,
            "last_processed_at": self.last_processed_at,
            "pipeline_flags": dict(self.pipeline_flags),

            # [Task Order 017 §4] New fields from §3 schema parity
            "doc_type": self.doc_type,
            "superseded_by": self.superseded_by,
            "supersedes": self.supersedes,
            "last_content_hash": self.last_content_hash,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_metadata_dict(cls, meta: dict) -> "DocumentContext":
        """Rehydrate a DocumentContext from a metadata dict.

        Inverse of to_metadata_dict(), but not a lossless round trip — see
        the note on created_at below. Accepts both the dict shape produced
        by to_metadata_dict()/build_document_metadata() and a persisted
        core.identity_registry record (a superset of those fields; unknown
        extra keys such as "status" or "superseded_by" are ignored rather
        than rejected, since registry records evolve additively — see
        migrate_registry_schema()).

        created_at: to_metadata_dict() does not serialize the dataclass's
        own (immutable, Point-A) created_at field — it writes registered_at
        under the "created_at" key instead (see that method's docstring).
        This means the original creation timestamp cannot be recovered from
        a metadata dict; __post_init__ stamps a fresh created_at on the
        rehydrated instance, exactly as it would for a newly-constructed
        DocumentContext. Only "created_at" (or "registered_at", checked
        first for forward-compatibility with a future direct dict dump of
        this dataclass) is used to restore registered_at.

        Args:
            meta: Metadata dict with at least "document_id" and "file_hash".

        Returns:
            A new DocumentContext instance.

        Raises:
            ValueError: if document_id or file_hash is missing/empty —
                mirrors to_metadata_dict()'s validation, since both are
                required for identity_registry lookups downstream.
        """
        document_id = meta.get("document_id", "")
        file_hash = meta.get("file_hash", "")
        if not document_id:
            raise ValueError("DocumentContext.from_metadata_dict(): document_id is required")
        if not file_hash:
            raise ValueError("DocumentContext.from_metadata_dict(): file_hash is required")

        ctx = cls(
            document_id=document_id,
            file_hash=file_hash,
            source_file=meta.get("source_file", ""),
            source_type=meta.get("source_type", ""),
            is_ocr=meta.get("is_ocr", False),
            title=meta.get("title"),
            author=meta.get("author"),
            book=meta.get("book"),
            chapter=meta.get("chapter"),
            page=meta.get("page"),
            batch_id=meta.get("batch_id"),
            language=meta.get("language", "en"),
            noise_score=meta.get("noise_score", 0.0),
            noise_mode=meta.get("noise_mode", "-"),
            processing_version=meta.get("processing_version", PROCESSING_VERSION),
            chunk_count=meta.get("chunk_count", 0),
            # [Task Order 017 §3] 신규 필드 — dataclass 생성자 인자로 전달
            doc_type=meta.get("doc_type"),
            superseded_by=meta.get("superseded_by"),
            supersedes=meta.get("supersedes"),
            last_content_hash=meta.get("last_content_hash"),
            max_retries=meta.get("max_retries", 3),
            pipeline_state=meta.get("pipeline_state", "NEW"),
            ingest_status=meta.get("ingest_status", "PROCESSED"),
            retry_count=meta.get("retry_count", 0),
            last_failure_reason=meta.get("last_failure_reason"),
            registered_at=meta.get("registered_at", meta.get("created_at", "")),
            last_processed_at=meta.get("last_processed_at", ""),
            md_path=meta.get("md_path"),
            copied_source_path=meta.get("copied_source_path"),
        )
        if isinstance(meta.get("pipeline_flags"), dict):
            ctx.pipeline_flags = dict(meta["pipeline_flags"])
        if isinstance(meta.get("chunk_ids"), list):
            ctx.chunk_ids = list(meta["chunk_ids"])
        if isinstance(meta.get("tsu_refs"), list):
            ctx.tsu_refs = list(meta["tsu_refs"])

        # [Task Order 017 §5] source_provenance — registry 레코드 전용 경로
        # (scripts/ingest_logos_export.py가 직접 씀). register_document()는
        # 이 필드를 모르므로 to_metadata_dict()에 포함하지 않는다(§4 참조).
        ctx.source_provenance = cls.source_provenance_from_registry_record(meta)
        return ctx

    @classmethod
    def source_provenance_from_registry_record(cls, record: dict) -> Optional[dict]:
        """registry 레코드에서 source_provenance 6개 필드만 골라 dict로 묶어
        반환한다. 6개 필드가 전부 없으면 None(문서가 Logos 출처가 아님).

        register_document()가 이 값을 쓰지 않으므로 to_metadata_dict()의
        출력과는 독립적이다 — Logos provenance는 여전히
        scripts/ingest_logos_export.py가 쓰는 경로로만 registry에 반영된다.
        """
        # 6개 필드: source_tier, logos_location, rights, export_method,
        # content_hash, review_status (scripts/ingest_logos_export.py 참조)
        FIELDS = ("source_tier", "logos_location", "rights",
                  "export_method", "content_hash", "review_status")
        parts = {k: record.get(k) for k in FIELDS}
        # 전부 None이면 문서가 Logos 출처가 아님
        if all(v is None for v in parts.values()):
            return None
        return parts
