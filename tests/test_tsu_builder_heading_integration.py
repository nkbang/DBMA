"""Regression test — PDF heading provider integration in tsu_builder
(SPRINT32-C). PDF documents route through PdfHeadingProvider +
HeadingAssembler (SPRINT31 Phase A/D/B); every other source_type keeps the
unchanged HeadingStack/ATX path (SPRINT32-C approved scope).
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.tsu_builder as mod
from core.tsu_builder import build_tsu_records


def _build(chunks: list, book: str = "2CO", source_type: str = "", source_file: str = "12. 고린도후서.pdf") -> list:
    registry = {
        "documents": {
            "doc1": {
                "source_file": source_file,
                "chunk_count": len(chunks),
                "book": book,
                "source_type": source_type,
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


def test_non_pdf_uses_headingstack_unchanged():
    recs = _build(
        ["# 1장\n\n서론 본문입니다.", "heading 없는 본문.", "## 1.1 절\n\n세부 본문."],
        source_type="md",
    )
    paths = [r["structure"]["heading_path"] for r in recs]
    assert paths == [["1장"], ["1장"], ["1장", "1.1 절"]]
    # shape-normalization additive fields present without changing detection
    assert recs[0]["structure"]["heading_confidence"] == 1.0
    assert recs[0]["structure"]["heading_source"] == "atx"
    assert recs[1]["structure"]["heading_confidence"] == 1.0  # inherited


def test_non_pdf_no_heading_yields_zero_confidence():
    recs = _build(["아무 heading 없는 본문."], source_type="md")
    st = recs[0]["structure"]
    assert st["heading_path"] == []
    assert st["heading_confidence"] == 0.0
    assert st["heading_source"] == ""


def test_pdf_document_uses_provider_and_assembler(monkeypatch):
    from core.pdf_structure_detector import HeadingCandidate

    fake_spans = [{"text": "x", "size": 12.0, "bold": False, "page": 0, "is_block_top": True}]
    fake_candidates = [
        HeadingCandidate(text="서론", page=0, signal="size", confidence=0.82, validity=1.0),
    ]

    monkeypatch.setattr(mod, "collect_pdf_spans", lambda path: fake_spans)
    monkeypatch.setattr(
        "core.heading_provider.detect_headings_from_spans", lambda spans: fake_candidates
    )
    monkeypatch.setattr(os.path, "exists", lambda p: True)

    recs = _build(["서론\n\nbody one"], source_type="pdf", source_file="test.pdf")
    st = recs[0]["structure"]
    assert st["heading_path"] == ["서론"]
    assert st["heading_confidence"] == 0.82
    assert st["heading_source"] == "pdf-size"


def test_pdf_document_missing_raw_file_degrades_gracefully(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    recs = _build(["some pdf-extracted body text"], source_type="pdf", source_file="missing.pdf")
    st = recs[0]["structure"]
    assert st["heading_path"] == []
    assert st["heading_confidence"] == 0.0
    assert st["heading_source"] == ""


def test_pdf_existing_fields_unaffected():
    recs = _build(["고후1:8-14 본문 내용입니다."], source_type="pdf", source_file="12. 고린도후서.pdf")
    r = recs[0]
    assert r["verse_mapping"] == {
        "book_id": "2CO", "chapter": 1, "verse_start": 8, "verse_end": 14,
    }
    assert "content_quality" in r
    assert r["content"] == "고후1:8-14 본문 내용입니다."
