"""Regression test — TSU sermon-theology additive fields (ADR-009).

build_tsu_records() tags each record with additive
theological_claim/doctrine_category/baptist_theme fields (default null/
empty), without touching any pre-existing TSU field. These fields are
structure-only per ADR-009 — no tagging logic populates them yet
(doctrine vocabulary is a separate, not-yet-approved decision).
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import core.tsu_builder as mod
from core.tsu_builder import build_tsu_records


def _build_with_chunks(chunks: list, book: str = "2CO") -> list:
    registry = {
        "documents": {
            "doc1": {
                "source_file": "12. 고린도후서.pdf",
                "chunk_count": len(chunks),
                "book": book,
            }
        }
    }
    original_read_chunk_texts = mod._read_chunk_texts
    original_read_md_fallback = mod._read_md_fallback
    mod._read_chunk_texts = lambda output_dir, source_file: list(chunks)
    mod._read_md_fallback = lambda output_dir, source_file: None
    try:
        return build_tsu_records(registry, Path("."))
    finally:
        mod._read_chunk_texts = original_read_chunk_texts
        mod._read_md_fallback = original_read_md_fallback


def test_sermon_fields_present_with_default_values():
    recs = _build_with_chunks(["아무 본문입니다."])
    r = recs[0]
    assert r["theological_claim"] is None
    assert r["doctrine_category"] == []
    assert r["baptist_theme"] == []


def test_sermon_fields_do_not_alter_existing_fields():
    recs = _build_with_chunks(["고후1:8-14 본문 내용입니다."])
    r = recs[0]
    assert r["verse_mapping"] == {
        "book_id": "2CO", "chapter": 1, "verse_start": 8, "verse_end": 14,
    }
    assert "content_quality" in r          # SPRINT28-B field intact
    assert "structure" in r                # SPRINT29-C field intact
    assert r["themes"] == []               # pre-existing dead field untouched
    assert r["content"] == "고후1:8-14 본문 내용입니다."


def test_sermon_fields_present_across_multiple_records():
    recs = _build_with_chunks(["첫 번째 문단.", "두 번째 문단."])
    for r in recs:
        assert r["theological_claim"] is None
        assert r["doctrine_category"] == []
        assert r["baptist_theme"] == []
