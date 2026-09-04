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


def _wrapped_line(text, size, top=False):
    """A wrapped body-text continuation line — never a block start."""
    return _Line(text=text, size=size, bold=False, page=0, is_block_top=top)


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


class TestSecondaryBodyBand:
    """[Root cause fix, SPRINT33-D Preflight 2026-07-23] A document with two
    comparably-sized body text bands (e.g. quoted Scripture vs. commentary
    prose) must not have the whole second band misclassified as headings —
    real data: "2 Kings, Anchor Bible Commentary" measured 2170 false-
    positive size_hits (mostly wrapped continuation lines from a ~16.1pt
    secondary band) before this fix, 203 after (86 of which are the real
    "Notes"/"Comment" section headings)."""

    def test_secondary_wrapped_text_band_is_not_classified_as_headings(self):
        lines = [_line("primary body prose line here", 14.2) for _ in range(60)]
        # A large, mostly-non-block-top secondary band (wrapped Scripture
        # quote continuation lines) — must be folded into "body", not
        # treated as heading candidates. 17.0 > body(14.2) * 1.15 = 16.33,
        # so this band would trip SIZE_HEADING_FACTOR without the fix.
        lines += [_wrapped_line("quoted scripture continuation line", 17.0) for _ in range(40)]
        p = profile_document(lines)
        assert p.size_ceiling > p.body_size  # ceiling raised above raw body
        assert _is_candidate(_wrapped_line("quoted scripture continuation line", 17.0), p) is False

    def test_genuinely_numerous_block_top_headings_are_not_suppressed(self):
        # A document with MANY real headings (all block starts, like
        # "Notes"/"Comment" repeating every entry) must still detect them —
        # the block-top ratio, not the count, is what distinguishes this
        # from a false-positive secondary body band (root cause data:
        # 86/86 = 100% block-top for real headings vs. 15.6% for the
        # false-positive band).
        lines = [_line("primary body prose line here", 14.2) for _ in range(60)]
        lines += [_line("Notes", 18.0, top=True) for _ in range(20)]
        p = profile_document(lines)
        assert p.size_ceiling == p.body_size  # not folded into body
        assert _is_candidate(_line("Notes", 18.0, top=True), p) is True

    def test_small_secondary_band_below_line_floor_is_unaffected(self):
        # Too few lines to safely judge a block-top ratio (root-cause fix
        # must not regress the "sparse-but-real headings" case the original
        # design protects — MIN_SIGNAL_HITS's absolute-floor rationale).
        lines = [_line("body", 10.0) for _ in range(30)]
        lines += [_line("Real Heading", 13.0), _line("Second Head", 13.0),
                  _line("Third Head", 13.0)]
        p = profile_document(lines)
        assert p.size_ceiling == p.body_size
        assert _is_candidate(_line("Real Heading", 13.0), p) is True


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

    def test_bold_candidate_requires_block_top(self):
        # [Root cause fix, SPRINT33-D Preflight 2026-07-23] Bolded
        # mid-paragraph text (e.g. bolded original-language citations) must
        # not count as a heading — real data: "2 Kings, Volume 13" had
        # 6768 bold-at-body-size lines, only 841 were block starts; the
        # rest were bolded Hebrew words inside body prose.
        lines = [_line("body prose here", 15.0) for _ in range(30)]
        lines += [_line("Heading", 15.0, bold=True, top=True) for _ in range(3)]
        lines += [_wrapped_line("bolded mid-paragraph term", 15.0) for _ in range(20)]
        for ln in lines[-20:]:
            ln.bold = True
        p = profile_document(lines)
        assert p.selected_signal == "bold"
        assert _is_candidate(_line("Heading", 15.0, bold=True, top=True), p) is True
        assert _is_candidate(_wrapped_line("bolded mid-paragraph term", 15.0), p) is False


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
