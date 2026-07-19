"""Regression test — core/pdf_structure_detector.py (SPRINT30-C).

Unit tests for the adaptive detector's pure logic (no PDF required):
signal selection, OCR validity filter, candidate gating, and confidence.
Corpus-wide accuracy is covered separately in
tests/test_pdf_structure_benchmark.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.pdf_structure_detector as det
from core.pdf_structure_detector import (
    _Line,
    _letter_ratio,
    profile_document,
    _is_candidate,
    _confidence,
    detect_headings,
    MIN_LETTER_RATIO,
)


def _line(text, size, bold=False, page=0, top=True):
    return _Line(text=text, size=size, bold=bold, page=page, is_block_top=top)


class TestLetterRatio:
    def test_clean_title_high_ratio(self):
        assert _letter_ratio("Introduction") == 1.0
        assert _letter_ratio("나사로의죽음") == 1.0

    def test_ocr_glyph_noise_low_ratio(self):
        # real SPRINT30-A false-positive samples (Greek iota / symbols count
        # as non-letters, so these fall below the 0.6 gate)
        assert _letter_ratio("∼ι빠") < MIN_LETTER_RATIO
        assert _letter_ratio("J§") < MIN_LETTER_RATIO
        assert _letter_ratio("------") < MIN_LETTER_RATIO
        assert _letter_ratio("1,‘/’") < MIN_LETTER_RATIO

    def test_empty_safe(self):
        assert _letter_ratio("") == 0.0
        assert _letter_ratio("   ") == 0.0


class TestSignalSelection:
    def test_size_dominant_document(self):
        # Korean-series shape: body 9.6pt, headings larger, no bold
        lines = [_line("body text line here", 9.6) for _ in range(40)]
        lines += [_line("나사로의죽음", 12.0), _line("부활과생명", 12.0),
                  _line("예수께서무덤에가시다", 12.0)]
        p = profile_document(lines)
        assert p.selected_signal == "size"
        assert p.body_size == 9.6

    def test_bold_dominant_document(self):
        # WBC shape: body 15pt, headings bold at body size, size varies little
        lines = [_line("body prose sentence here", 15.0) for _ in range(40)]
        lines += [_line("Introduction", 15.0, bold=True),
                  _line("Main Bibliography", 15.0, bold=True),
                  _line("The Chronicler", 15.0, bold=True)]
        p = profile_document(lines)
        assert p.selected_signal == "bold"

    def test_no_signal_document_is_none(self):
        # uniform body, no size/bold distinction -> honest no-op
        lines = [_line("uniform body prose text", 12.0) for _ in range(40)]
        p = profile_document(lines)
        assert p.selected_signal is None

    def test_sparse_headings_below_floor_is_none(self):
        # only 2 real headings (< MIN_SIGNAL_HITS) -> no-op, avoids flukes
        lines = [_line("body text line here", 9.6) for _ in range(40)]
        lines += [_line("나사로의죽음", 12.0), _line("부활과생명", 12.0)]
        p = profile_document(lines)
        assert p.selected_signal is None

    def test_ocr_noise_does_not_inflate_size_signal(self):
        # large-font glyph noise must NOT count as size hits
        lines = [_line("body text line here", 9.6) for _ in range(40)]
        lines += [_line("∼ι빠", 13.0), _line("J§", 13.0), _line("------", 13.0),
                  _line("1,‘/’", 13.0)]
        p = profile_document(lines)
        assert p.size_hits == 0  # all large-font candidates were noise
        assert p.selected_signal is None


class TestCandidateGating:
    def test_size_candidate_requires_larger_font_and_letters(self):
        lines = [_line("body", 10.0) for _ in range(30)]
        lines += [_line("Real Heading", 13.0), _line("Second Head", 13.0),
                  _line("Third Head", 13.0)]
        p = profile_document(lines)
        assert _is_candidate(_line("Real Heading", 13.0), p) is True
        assert _is_candidate(_line("body", 10.0), p) is False          # not larger
        assert _is_candidate(_line("∼ι빠", 13.0), p) is False           # OCR noise
        long_big = "x" * 90
        assert _is_candidate(_line(long_big, 13.0), p) is False         # too long

    def test_bold_candidate_requires_bold_at_body(self):
        lines = [_line("body prose here", 15.0) for _ in range(30)]
        lines += [_line("Heading", 15.0, bold=True), _line("Second", 15.0, bold=True),
                  _line("Third", 15.0, bold=True)]
        p = profile_document(lines)
        assert _is_candidate(_line("Heading", 15.0, bold=True), p) is True
        assert _is_candidate(_line("body prose here", 15.0), p) is False  # not bold


class TestConfidence:
    def test_confidence_in_unit_range_and_monotone(self):
        lines = [_line("body", 10.0) for _ in range(30)] + [_line("H", 13.0)]
        p = profile_document(lines)
        small = _confidence(_line("Small Head", 11.6, top=False), p, validity=1.0)
        big = _confidence(_line("Big Head", 15.0, top=True), p, validity=1.0)
        assert 0.0 <= small <= 1.0 and 0.0 <= big <= 1.0
        assert big > small  # larger font + position bonus -> higher confidence

    def test_low_validity_lowers_confidence(self):
        lines = [_line("body", 10.0) for _ in range(30)] + [_line("H", 13.0)]
        p = profile_document(lines)
        hi = _confidence(_line("Clean Title", 13.0), p, validity=1.0)
        lo = _confidence(_line("Clean Title", 13.0), p, validity=0.6)
        assert hi > lo


class TestDetectHeadingsSafety:
    def test_missing_file_returns_empty_not_raise(self):
        assert detect_headings("/nonexistent/path/does_not_exist.pdf") == []

    def test_no_fitz_returns_empty(self, monkeypatch):
        monkeypatch.setattr(det, "_HAS_FITZ", False)
        assert detect_headings("/any/path.pdf") == []
