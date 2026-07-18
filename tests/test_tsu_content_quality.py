"""Regression test — TSU.content_quality additive field (SPRINT28-B).
Verifies build_tsu_records() tags each record with content_quality
(noise_type/quality_score/section_type) without touching any pre-existing
TSU field.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import core.tsu_builder as mod
from core.tsu_builder import build_tsu_records


def _build_with_content(content: str, book: str = "2CO") -> list:
    registry = {
        "documents": {
            "doc1": {
                "source_file": "12. 고린도후서.pdf",
                "chunk_count": 1,
                "book": book,
            }
        }
    }
    original_read_chunk_texts = mod._read_chunk_texts
    original_read_md_fallback = mod._read_md_fallback
    mod._read_chunk_texts = lambda output_dir, source_file: [content]
    mod._read_md_fallback = lambda output_dir, source_file: None
    try:
        return build_tsu_records(registry, Path("."))
    finally:
        mod._read_chunk_texts = original_read_chunk_texts
        mod._read_md_fallback = original_read_md_fallback


def test_normal_content_gets_content_quality_field():
    records = _build_with_content("아무 성구 참조도 없는 일반 본문입니다.")
    cq = records[0]["content_quality"]
    assert cq["noise_type"] == "NORMAL_CONTENT"
    assert cq["quality_score"] == 1.0
    assert cq["section_type"] == "body"


def test_original_language_chunk_is_preserved_in_tsu():
    records = _build_with_content("א ני כי")
    cq = records[0]["content_quality"]
    assert cq["noise_type"] == "ORIGINAL_LANGUAGE"
    assert cq["quality_score"] == 1.0


def test_content_quality_does_not_alter_existing_fields():
    records = _build_with_content("고후1:8-14 본문 내용입니다.")
    r = records[0]
    # Pre-existing SPRINT19-A fields must be untouched by the SPRINT28-B addition.
    assert r["verse_mapping"] == {
        "book_id": "2CO", "chapter": 1, "verse_start": 8, "verse_end": 14,
    }
    assert r["content"] == "고후1:8-14 본문 내용입니다."
    assert "content_quality" in r
