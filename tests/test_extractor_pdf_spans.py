"""Regression test — extractor PDF span metadata (SPRINT31-D-1, Option B).

collect_pdf_spans() adds span geometry to the extractor's output so the
heading detector no longer re-opens the PDF (Transitional Adapter removal).
It must be purely additive: the flat-text extraction path is untouched and
the extract_text_from_file contract only gains a pdf_spans key.
"""

import sys
import os
import glob
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from core.extractors import collect_pdf_spans, extract_text_from_file

_CORPUS = Path(__file__).parent.parent / "data" / "beta_corpus"


def _pdfs():
    return sorted(glob.glob(str(_CORPUS / "**" / "*.pdf"), recursive=True)) if _CORPUS.exists() else []


def test_collect_spans_missing_file_returns_empty():
    assert collect_pdf_spans("/nonexistent/file.pdf") == []


@pytest.mark.skipif(not _pdfs(), reason="Beta corpus PDFs not present")
def test_span_record_shape():
    spans = collect_pdf_spans(_pdfs()[0])
    assert spans, "expected spans from a real PDF"
    rec = spans[0]
    assert set(rec.keys()) == {"text", "size", "bold", "page", "is_block_top"}
    assert isinstance(rec["text"], str) and rec["text"]
    assert isinstance(rec["size"], float)
    assert isinstance(rec["bold"], bool)
    assert isinstance(rec["page"], int)
    assert isinstance(rec["is_block_top"], bool)


@pytest.mark.skipif(not _pdfs(), reason="Beta corpus PDFs not present")
def test_extract_result_is_additive_only():
    from core.processing import build_converter
    conv = build_converter()
    r = extract_text_from_file(_pdfs()[0], conv)
    # existing keys intact + one additive key
    assert {"text", "is_ocr", "source_type", "title", "author"} <= set(r.keys())
    assert "pdf_spans" in r
    assert isinstance(r["pdf_spans"], list) and r["pdf_spans"]


@pytest.mark.skipif(not _pdfs(), reason="Beta corpus PDFs not present")
def test_text_unaffected_by_span_collection():
    # Extracting text alone vs alongside spans yields identical text — proves
    # span collection does not perturb the flat-text path.
    from core.extractors import extract_text_from_pdf
    from core.processing import build_converter
    conv = build_converter()
    path = _pdfs()[0]
    text_only = extract_text_from_pdf(path, converter=conv)
    full = extract_text_from_file(path, conv)["text"]
    assert hashlib.sha256(text_only.encode()).hexdigest() == hashlib.sha256(full.encode()).hexdigest()


def test_non_pdf_has_empty_spans(tmp_path):
    from core.processing import build_converter
    p = tmp_path / "note.txt"
    p.write_text("# Heading\n\nbody text here.", encoding="utf-8")
    r = extract_text_from_file(str(p), build_converter())
    assert r["pdf_spans"] == []
