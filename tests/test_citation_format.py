"""core/citation_format.py — 공용 각주 서지 포맷 (ADR-031).

ui/pages/research.py::_build_footnote_citation 의 "최초(전체) 인용" 본문
조립을 여기로 뽑아냈다. 아래 테스트는 그 리팩터가 문자열을 바꾸지 않았음을
대표 입력으로 고정한다.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.citation_format import extract_citation_year, format_footnote_line


class TestExtractCitationYear:
    def test_iso_date(self):
        assert extract_citation_year("2024-01-02T03:04:05") == "2024"

    def test_year_only(self):
        assert extract_citation_year("1998") == "1998"

    def test_none(self):
        assert extract_citation_year(None) is None

    def test_non_numeric(self):
        assert extract_citation_year("abcd-01") is None

    def test_too_short(self):
        assert extract_citation_year("20") is None


class TestFormatFootnoteLineParity:
    """research.py 의 기존 else 분기:
        meta = ", ".join(x for x in (doc_type, year) if x)
        head = f"{author}, *{title}*" if author else f"*{title}*"
        body = f"{head} ({meta})." if meta else f"{head}."
    와 동일한 출력이어야 한다(author 는 "" 로 넘어옴).
    """

    def test_author_type_year(self):
        assert (
            format_footnote_line("F. F. Bruce", "The Epistle to the Galatians", "주석", "1982")
            == "F. F. Bruce, *The Epistle to the Galatians* (주석, 1982)."
        )

    def test_no_author(self):
        assert format_footnote_line("", "제목만", None, None) == "*제목만*."

    def test_type_only(self):
        assert format_footnote_line(None, "제목", "주석", None) == "*제목* (주석)."

    def test_year_only(self):
        assert format_footnote_line("저자", "제목", None, "2024") == "저자, *제목* (2024)."

    def test_none_title_falls_back(self):
        assert format_footnote_line("저자", None, None, None) == "저자, *제목 미상*."


class TestFormatFootnoteLineLocation:
    def test_location_appended_before_period(self):
        assert (
            format_footnote_line("저자", "제목", "주석", "2024", "요한복음 8:1-4")
            == "저자, *제목* (주석, 2024), 요한복음 8:1-4."
        )

    def test_location_without_meta(self):
        assert format_footnote_line("저자", "제목", None, None, "잠언 8장") == "저자, *제목*, 잠언 8장."
