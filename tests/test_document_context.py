"""tests/test_document_context.py — DocumentContext.from_metadata_dict()/to_metadata_dict()."""

from __future__ import annotations

import pytest

from core.document_context import DocumentContext


def _minimal_context(**overrides) -> DocumentContext:
    defaults = dict(
        document_id="abc123",
        file_hash="a" * 64,
        source_file="sermon_001.pdf",
        source_type="pdf",
    )
    defaults.update(overrides)
    ctx = DocumentContext(**defaults)
    if not ctx.registered_at:
        ctx.registered_at = "2026-07-27T10:00:00"
    return ctx


def test_to_metadata_dict_requires_document_id():
    ctx = _minimal_context(document_id="")
    with pytest.raises(ValueError, match="document_id"):
        ctx.to_metadata_dict()


def test_to_metadata_dict_requires_file_hash():
    ctx = _minimal_context(file_hash="")
    with pytest.raises(ValueError, match="file_hash"):
        ctx.to_metadata_dict()


def test_to_metadata_dict_requires_registered_at():
    ctx = _minimal_context()
    ctx.registered_at = ""
    with pytest.raises(ValueError, match="registered_at"):
        ctx.to_metadata_dict()


def test_from_metadata_dict_requires_document_id():
    with pytest.raises(ValueError, match="document_id"):
        DocumentContext.from_metadata_dict({"file_hash": "x"})


def test_from_metadata_dict_requires_file_hash():
    with pytest.raises(ValueError, match="file_hash"):
        DocumentContext.from_metadata_dict({"document_id": "x"})


def test_round_trip_preserves_serialized_fields():
    """to_metadata_dict() -> from_metadata_dict() round trip: every field
    that to_metadata_dict() actually serializes must come back unchanged.
    created_at is deliberately excluded — see from_metadata_dict()'s
    docstring note (it is not part of the serialized contract)."""
    original = _minimal_context(
        title="설교집",
        author="홍길동",
        book="John",
        chapter=3,
        page=16,
        batch_id="batch-01",
        language="ko",
        noise_score=12.5,
        noise_mode="OCR",
        is_ocr=True,
        chunk_count=7,
        pipeline_state="PROCESSED",
    )

    meta = original.to_metadata_dict()
    rehydrated = DocumentContext.from_metadata_dict(meta)

    # Fields to_metadata_dict() actually serializes must round-trip exactly.
    assert rehydrated.document_id == original.document_id
    assert rehydrated.file_hash == original.file_hash
    assert rehydrated.source_file == original.source_file
    assert rehydrated.source_type == original.source_type
    assert rehydrated.is_ocr == original.is_ocr
    assert rehydrated.title == original.title
    assert rehydrated.author == original.author
    assert rehydrated.book == original.book
    assert rehydrated.chapter == original.chapter
    assert rehydrated.page == original.page
    assert rehydrated.batch_id == original.batch_id
    assert rehydrated.language == original.language
    assert rehydrated.noise_score == original.noise_score
    assert rehydrated.noise_mode == original.noise_mode
    assert rehydrated.chunk_count == original.chunk_count
    assert rehydrated.processing_version == original.processing_version
    assert rehydrated.pipeline_state == original.pipeline_state
    # to_metadata_dict() writes registered_at under the "created_at" key.
    assert rehydrated.registered_at == original.registered_at


def test_from_metadata_dict_accepts_full_registry_record_shape():
    """A persisted identity_registry record is a superset of
    to_metadata_dict()'s output (extra keys like status/superseded_by/
    retry_count/pipeline_flags) — from_metadata_dict() must not choke on
    the extra keys and must pick up the ones it understands."""
    registry_record = {
        "document_id": "doc-1",
        "file_hash": "b" * 64,
        "source_file": "commentary.pdf",
        "created_at": "2026-07-20T09:00:00",
        "processing_version": "1.1.x",
        "status": "processed",  # unknown to DocumentContext — must be ignored
        "chunk_count": 3,
        "language": "en",
        "noise_score": 5.0,
        "noise_mode": "-",
        "source_type": "pdf",
        "is_ocr": False,
        "book": "Romans",
        "chapter": None,
        "page": None,
        "title": None,
        "author": None,
        "doc_type": "commentary",  # unknown to DocumentContext — must be ignored
        "pipeline_state": "INDEXED",
        "ingest_status": "PROCESSED",
        "retry_count": 2,
        "last_failure_reason": None,
        "pipeline_flags": {"ingested": True, "copied": True, "extracted": True,
                            "cleaned": True, "chunked": True,
                            "output_generated": True, "verified": True},
        "superseded_by": None,  # unknown to DocumentContext — must be ignored
    }

    ctx = DocumentContext.from_metadata_dict(registry_record)

    assert ctx.document_id == "doc-1"
    assert ctx.book == "Romans"
    assert ctx.pipeline_state == "INDEXED"
    assert ctx.retry_count == 2
    assert ctx.pipeline_flags["verified"] is True
    assert ctx.registered_at == "2026-07-20T09:00:00"


def test_from_metadata_dict_defaults_for_partial_metadata():
    """Sparse metadata (e.g. an early-pipeline snapshot) must round-trip
    without error, falling back to the same defaults as the dataclass."""
    ctx = DocumentContext.from_metadata_dict({
        "document_id": "sparse-doc",
        "file_hash": "c" * 64,
    })

    assert ctx.source_file == ""
    assert ctx.chunk_count == 0
    assert ctx.pipeline_state == "NEW"
    assert ctx.pipeline_flags["verified"] is False
    assert ctx.tsu_refs == []
    assert ctx.chunk_ids == []


# [Task Order 017] New fields (§3 schema parity) — doc_type, superseded_by,
# supersedes, last_content_hash, max_retries, source_provenance


def test_new_fields_default_values():
    """6개 신규 필드의 기본값: doc_type/superseded_by/supersedes/last_content_hash
    는 None, max_retries 는 3, source_provenance 는 None."""
    ctx = _minimal_context()
    assert ctx.doc_type is None
    assert ctx.superseded_by is None
    assert ctx.supersedes is None
    assert ctx.last_content_hash is None
    assert ctx.max_retries == 3
    assert ctx.source_provenance is None


def test_new_fields_set_and_round_trip():
    """신규 필드에 값을 설정 → to_metadata_dict() → from_metadata_dict()
    round trip에서 값이 복원된다."""
    original = _minimal_context(
        doc_type="sermon",
        superseded_by="doc-2",
        supersedes="doc-1",
        last_content_hash="d" * 64,
        max_retries=5,
    )

    meta = original.to_metadata_dict()
    # to_metadata_dict()에 신규 필드가 포함되어야 함
    assert meta["doc_type"] == "sermon"
    assert meta["superseded_by"] == "doc-2"
    assert meta["supersedes"] == "doc-1"
    assert meta["last_content_hash"] == "d" * 64
    assert meta["max_retries"] == 5

    rehydrated = DocumentContext.from_metadata_dict(meta)
    assert rehydrated.doc_type == "sermon"
    assert rehydrated.superseded_by == "doc-2"
    assert rehydrated.supersedes == "doc-1"
    assert rehydrated.last_content_hash == "d" * 64
    assert rehydrated.max_retries == 5


def test_source_provenance_from_registry_record_all_none():
    """6개 필드가 전부 없으면 None."""
    record = {"document_id": "x", "file_hash": "y"}
    result = DocumentContext.source_provenance_from_registry_record(record)
    assert result is None


def test_source_provenance_from_registry_record_some_present():
    """6개 필드 중 일부가 있으면 dict로 반환."""
    record = {
        "source_tier": "scholarly_commentary",
        "logos_location": "Romans 12:1-2, p.748-752",
        "rights": "personal_study_export",
        "export_method": "Logos Print/Export",
        "content_hash": "abc123",
        "review_status": "reviewed",
    }
    result = DocumentContext.source_provenance_from_registry_record(record)
    assert result == record


def test_source_provenance_from_registry_record_partial():
    """6개 필드 중 일부만 있어도 dict 반환 (전부 None일 때만 None)."""
    record = {"source_tier": "primary", "review_status": "unreviewed"}
    result = DocumentContext.source_provenance_from_registry_record(record)
    assert result == {"source_tier": "primary", "logos_location": None,
                      "rights": None, "export_method": None,
                      "content_hash": None, "review_status": "unreviewed"}


def test_from_metadata_dict_picks_up_source_provenance():
    """from_metadata_dict()가 registry record에서 source_provenance를
    올바르게 복원한다."""
    record = {
        "document_id": "doc-1",
        "file_hash": "b" * 64,
        "source_file": "commentary.pdf",
        "source_tier": "scholarly_commentary",
        "logos_location": "Romans 12:1-2",
        "rights": "personal_study_export",
        "export_method": "Logos Print/Export",
        "content_hash": "abc123",
        "review_status": "reviewed",
    }
    ctx = DocumentContext.from_metadata_dict(record)
    assert ctx.source_provenance == {
        "source_tier": "scholarly_commentary",
        "logos_location": "Romans 12:1-2",
        "rights": "personal_study_export",
        "export_method": "Logos Print/Export",
        "content_hash": "abc123",
        "review_status": "reviewed",
    }


def test_from_metadata_dict_no_source_provenance():
    """source_provenance 6개 필드가 없으면 source_provenance는 None."""
    record = {
        "document_id": "doc-1",
        "file_hash": "b" * 64,
        "source_file": "sermon.pdf",
    }
    ctx = DocumentContext.from_metadata_dict(record)
    assert ctx.source_provenance is None


def test_to_metadata_dict_includes_new_fields():
    """to_metadata_dict()가 신규 필드를 포함한다."""
    ctx = _minimal_context(
        doc_type="sermon",
        superseded_by="doc-2",
        supersedes="doc-1",
        last_content_hash="e" * 64,
        max_retries=5,
    )
    meta = ctx.to_metadata_dict()
    assert "doc_type" in meta
    assert "superseded_by" in meta
    assert "supersedes" in meta
    assert "last_content_hash" in meta
    assert "max_retries" in meta
    assert meta["doc_type"] == "sermon"
    assert meta["superseded_by"] == "doc-2"
    assert meta["supersedes"] == "doc-1"
    assert meta["last_content_hash"] == "e" * 64
    assert meta["max_retries"] == 5


def test_to_metadata_dict_includes_already_missing_fields():
    """to_metadata_dict()가 기존에 누락되었던 필드들(ingest_status,
    retry_count, last_failure_reason, last_processed_at, pipeline_flags)을
    포함한다."""
    ctx = _minimal_context(
        ingest_status="REPROCESS",
        retry_count=3,
        last_failure_reason="timeout",
        last_processed_at="2026-07-28T10:00:00",
    )
    meta = ctx.to_metadata_dict()
    assert meta["ingest_status"] == "REPROCESS"
    assert meta["retry_count"] == 3
    assert meta["last_failure_reason"] == "timeout"
    assert meta["last_processed_at"] == "2026-07-28T10:00:00"
    assert isinstance(meta["pipeline_flags"], dict)
    assert meta["pipeline_flags"]["ingested"] is False
