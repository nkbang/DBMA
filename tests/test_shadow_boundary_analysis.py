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
from shadow_boundary_analysis import _advance_cursor, _extract_body_text


def _heading(text: str) -> ProviderHeading:
    return ProviderHeading(text=text, level=1, confidence=1.0, source="pdf-size")


class TestExtractBodyText:
    def test_strips_yaml_header_and_front_matter_section(self):
        md = (
            "---\n"
            "source: x.pdf\n"
            "source_type: pdf\n"
            "---\n"
            "## 전면부 (제목/판권/목차 — 검색·노이즈 채점 대상 제외)\n\n"
            "표지 판권 목차 내용\n\n"
            "---\n\n"
            "## 본문\n\n"
            "실제 본문 내용입니다."
        )
        assert _extract_body_text(md) == "실제 본문 내용입니다."

    def test_strips_only_yaml_header_when_no_front_matter_detected(self):
        md = "---\nsource: x.pdf\n---\n실제 본문 내용입니다."
        assert _extract_body_text(md) == "실제 본문 내용입니다."

    def test_no_body_marker_confusion_when_absent(self):
        md = "---\nsource: x.pdf\n---\n본문만 있고 전면부 마커는 없습니다."
        assert _extract_body_text(md) == "본문만 있고 전면부 마커는 없습니다."


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
