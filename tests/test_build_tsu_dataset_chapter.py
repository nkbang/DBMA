"""Regression test — TSU verse_mapping.chapter enrichment (SPRINT18-C).

_resolve_chapter() reuses the existing, already-stabilized scripture
reference parsers (SPRINT18-A/B-1) against chunk content — no new
parsing logic. Guards the "never guess" contract: chapter is set only
when a real ScriptureReference is found in the content, and the key is
omitted entirely (not set to None) otherwise.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.build_tsu_dataset import _resolve_chapter, build_tsu_records


class TestResolveChapter:
    def test_colon_form_2corinthians(self):
        assert _resolve_chapter("고후1:8-14") == 1

    def test_colon_form_1corinthians(self):
        assert _resolve_chapter("고전1:1-9") == 1

    def test_no_reference_returns_none(self):
        assert _resolve_chapter("이것은 아무 성구 참조도 없는 일반 텍스트입니다.") is None

    def test_empty_content_returns_none(self):
        assert _resolve_chapter("") is None


class TestVerseMappingChapterKeyOmission:
    """build_tsu_records() must omit the "chapter" key entirely when no
    reference is detected — never set it to None — and must never touch
    the top-level "chapter" field (a separate, document-level concept)."""

    def test_records_without_reference_have_no_chapter_key(self):
        registry = {
            "documents": {
                "doc1": {
                    "source_file": "9. 로마서1.pdf",
                    "chunk_count": 1,
                    "book": "ROM",
                }
            }
        }

        import scripts.build_tsu_dataset as mod
        from pathlib import Path

        original_read_chunk_texts = mod._read_chunk_texts
        original_read_md_fallback = mod._read_md_fallback
        mod._read_chunk_texts = lambda output_dir, source_file: ["아무 성구 참조도 없는 본문입니다."]
        mod._read_md_fallback = lambda output_dir, source_file: None
        try:
            records = build_tsu_records(registry, Path("."))
        finally:
            mod._read_chunk_texts = original_read_chunk_texts
            mod._read_md_fallback = original_read_md_fallback

        assert len(records) == 1
        assert "chapter" not in records[0]["verse_mapping"]
        assert records[0]["verse_mapping"] == {"book_id": "ROM"}
        # Top-level "chapter" (document-level metadata) is untouched and
        # separate from verse_mapping.chapter.
        assert records[0]["chapter"] is None

    def test_record_with_reference_gets_chapter_in_verse_mapping(self):
        registry = {
            "documents": {
                "doc1": {
                    "source_file": "12. 고린도후서.pdf",
                    "chunk_count": 1,
                    "book": "2CO",
                }
            }
        }

        import scripts.build_tsu_dataset as mod
        from pathlib import Path

        original_read_chunk_texts = mod._read_chunk_texts
        original_read_md_fallback = mod._read_md_fallback
        mod._read_chunk_texts = lambda output_dir, source_file: ["고후1:8-14 본문 내용입니다."]
        mod._read_md_fallback = lambda output_dir, source_file: None
        try:
            records = build_tsu_records(registry, Path("."))
        finally:
            mod._read_chunk_texts = original_read_chunk_texts
            mod._read_md_fallback = original_read_md_fallback

        assert records[0]["verse_mapping"] == {"book_id": "2CO", "chapter": 1}


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
