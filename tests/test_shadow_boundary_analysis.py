"""Unit tests — shadow boundary analysis driver (SPRINT33-C Phase 1).

scripts/shadow_boundary_analysis.py is a diagnostic artifact, not production
code, but its cursor-advance logic (_advance_cursor) mirrors
HeadingAssembler.assign()'s cursor step exactly and must stay correct, so it
gets the same test discipline as core/ modules. Tests import the script as a
module purely for verification — core/ never imports scripts/ (SPRINT33-C
approved boundary).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from core.heading_provider import ProviderHeading, _normalize_for_matching
from shadow_boundary_analysis import _advance_cursor


def _heading(text: str) -> ProviderHeading:
    return ProviderHeading(text=text, level=1, confidence=1.0, source="pdf-size")


class TestAdvanceCursor:
    def test_advances_past_matched_heading(self):
        headings = [_heading("서론"), _heading("본론")]
        key = _normalize_for_matching("서론")
        assert _advance_cursor(0, headings, key) == 1

    def test_advances_past_lookahead_match(self):
        headings = [_heading("서론"), _heading("본론")]
        key = _normalize_for_matching("본론")
        assert _advance_cursor(0, headings, key) == 2

    def test_unchanged_when_no_match_in_window(self):
        headings = [_heading("서론")]
        key = _normalize_for_matching("전혀 관련 없는 문장")
        assert _advance_cursor(0, headings, key) == 0

    def test_unchanged_when_cursor_already_exhausted(self):
        headings = [_heading("서론")]
        key = _normalize_for_matching("서론")
        assert _advance_cursor(1, headings, key) == 1
