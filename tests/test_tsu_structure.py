"""Regression test — TSU.structure additive heading field (SPRINT29-C).

build_tsu_records() tags each record with an additive `structure`
(heading_path/heading_depth) computed by core/heading_extractor.py from
chunk content, without touching any pre-existing TSU field and without
changing chunk boundaries. PDF-like heading-less content yields an empty
path (no PDF heuristic).
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


def test_structure_field_present_and_empty_for_headingless():
    recs = _build_with_chunks(["아무 heading 없는 일반 본문입니다."])
    st = recs[0]["structure"]
    assert st["heading_path"] == []
    assert st["heading_depth"] == 0


def test_structure_carries_heading_path_across_chunks():
    recs = _build_with_chunks([
        "# 1장\n\n서론 본문입니다.",
        "heading 없는 이어지는 본문.",
        "## 1.1 절\n\n세부 본문입니다.",
    ])
    paths = [r["structure"]["heading_path"] for r in recs]
    assert paths == [["1장"], ["1장"], ["1장", "1.1 절"]]
    assert [r["structure"]["heading_depth"] for r in recs] == [1, 1, 2]


def test_structure_does_not_alter_existing_fields():
    recs = _build_with_chunks(["고후1:8-14 본문 내용입니다."])
    r = recs[0]
    assert r["verse_mapping"] == {
        "book_id": "2CO", "chapter": 1, "verse_start": 8, "verse_end": 14,
    }
    assert "content_quality" in r          # SPRINT28-B field intact
    assert "structure" in r                # SPRINT29-C field added
    assert r["content"] == "고후1:8-14 본문 내용입니다."
