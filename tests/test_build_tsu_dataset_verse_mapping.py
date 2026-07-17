"""Regression test — TSU verse_mapping.verse_start/verse_end enrichment
(SPRINT19-A).

Closes a producer-consumer schema gap: core/retrieval.py's
ContextAssembler/CitationBuilder already read
verse_mapping.get("verse_start"/"verse_end") (SPRINT19-A Preflight
finding), but build_tsu_dataset.py never wrote them. _resolve_scripture_ref()
reuses the same parser call SPRINT18-C already made — no new parsing
logic, no core/retrieval.py changes. Guards the "never guess" contract:
verse_start/verse_end are set only when the parser actually returned a
ScriptureReference, chapter enrichment policy is unchanged from
SPRINT18-C (first-match).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.build_tsu_dataset import _resolve_scripture_ref, _resolve_chapter, build_tsu_records


class TestResolveScriptureRef:
    def test_colon_form_with_verse_range(self):
        ref = _resolve_scripture_ref("고전1:1-9")
        assert ref.book_id == "1CO"
        assert ref.chapter == 1
        assert ref.verse_start == 1
        assert ref.verse_end == 9

    def test_colon_form_single_verse_verse_end_none(self):
        ref = _resolve_scripture_ref("요3:16")
        assert ref.book_id == "JHN"
        assert ref.chapter == 3
        assert ref.verse_start == 16
        assert ref.verse_end is None

    def test_no_reference_returns_none(self):
        assert _resolve_scripture_ref("이것은 아무 성구 참조도 없는 일반 텍스트입니다.") is None

    def test_empty_content_returns_none(self):
        assert _resolve_scripture_ref("") is None


class TestResolveChapterUnchanged:
    """SPRINT18-C chapter enrichment policy (first-match, None on no ref)
    must be unaffected by the _resolve_scripture_ref refactor."""

    def test_colon_form_2corinthians(self):
        assert _resolve_chapter("고후1:8-14") == 1

    def test_no_reference_returns_none(self):
        assert _resolve_chapter("이것은 아무 성구 참조도 없는 일반 텍스트입니다.") is None

    def test_empty_content_returns_none(self):
        assert _resolve_chapter("") is None


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

    import core.tsu_builder as mod
    from pathlib import Path

    original_read_chunk_texts = mod._read_chunk_texts
    original_read_md_fallback = mod._read_md_fallback
    mod._read_chunk_texts = lambda output_dir, source_file: [content]
    mod._read_md_fallback = lambda output_dir, source_file: None
    try:
        return build_tsu_records(registry, Path("."))
    finally:
        mod._read_chunk_texts = original_read_chunk_texts
        mod._read_md_fallback = original_read_md_fallback


class TestVerseMappingFields:
    def test_verse_range_populates_start_and_end(self):
        records = _build_with_content("고후1:8-14 본문 내용입니다.")
        assert records[0]["verse_mapping"] == {
            "book_id": "2CO", "chapter": 1, "verse_start": 8, "verse_end": 14,
        }

    def test_single_verse_omits_verse_end_key(self):
        records = _build_with_content("고후1:8 본문 내용입니다.")
        vm = records[0]["verse_mapping"]
        assert vm == {"book_id": "2CO", "chapter": 1, "verse_start": 8}
        assert "verse_end" not in vm

    def test_no_reference_has_only_book_id(self):
        records = _build_with_content("아무 성구 참조도 없는 본문입니다.")
        assert records[0]["verse_mapping"] == {"book_id": "2CO"}
        assert "chapter" not in records[0]["verse_mapping"]
        assert "verse_start" not in records[0]["verse_mapping"]
        assert "verse_end" not in records[0]["verse_mapping"]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
