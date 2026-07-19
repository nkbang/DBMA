"""Regression test — detector span injection (SPRINT31-D-2, Option B).

detect_headings_from_spans() detects headings from pre-collected span
records WITHOUT re-opening the PDF, funnelling through the same core
(_detect_from_lines) as the path-based detect_headings(). Both must be
result-identical; the public detect_headings(path) API is preserved.
"""

import sys
import glob
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from core.pdf_structure_detector import (
    detect_headings,
    detect_headings_from_spans,
    _spans_to_lines,
    HeadingCandidate,
)

_CORPUS = Path(__file__).parent.parent / "data" / "beta_corpus"


def _pdfs():
    return sorted(glob.glob(str(_CORPUS / "**" / "*.pdf"), recursive=True)) if _CORPUS.exists() else []


def test_empty_spans_yield_no_headings():
    assert detect_headings_from_spans([]) == []


def test_spans_to_lines_maps_records():
    spans = [{"text": "H", "size": 12.0, "bold": True, "page": 1, "is_block_top": True}]
    lines = _spans_to_lines(spans)
    assert len(lines) == 1
    assert lines[0].text == "H" and lines[0].size == 12.0 and lines[0].bold is True
    assert lines[0].page == 1 and lines[0].is_block_top is True


def test_spans_to_lines_skips_empty_text():
    assert _spans_to_lines([{"text": "", "size": 12.0, "bold": False, "page": 0, "is_block_top": True}]) == []


def test_synthetic_size_signal_detected_from_spans():
    spans = [{"text": "body text line here", "size": 9.6, "bold": False, "page": 0, "is_block_top": False}
             for _ in range(40)]
    spans += [
        {"text": "나사로의죽음", "size": 12.0, "bold": False, "page": 0, "is_block_top": True},
        {"text": "부활과생명", "size": 12.0, "bold": False, "page": 0, "is_block_top": True},
        {"text": "예수께서무덤에가시다", "size": 12.0, "bold": False, "page": 0, "is_block_top": True},
    ]
    out = detect_headings_from_spans(spans)
    assert out and all(c.signal == "size" for c in out)
    assert {c.text for c in out} >= {"나사로의죽음", "부활과생명"}


@pytest.mark.skipif(not _pdfs(), reason="Beta corpus PDFs not present")
def test_span_injection_equals_path_detection():
    from core.extractors import collect_pdf_spans
    for path in _pdfs():
        # bounded page range for speed; the detection core is range-independent
        via_path = detect_headings(path, start_page=0, max_pages=40)
        spans = [s for s in collect_pdf_spans(path) if s["page"] < 40]
        via_spans = detect_headings_from_spans(spans)
        assert len(via_path) == len(via_spans), os.path.basename(path)
        for a, b in zip(via_path, via_spans):
            assert (a.text, a.page, a.signal, a.confidence, a.validity) == \
                   (b.text, b.page, b.signal, b.confidence, b.validity), os.path.basename(path)
