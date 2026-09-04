"""Regression tests — sermon_corpus/collector/church_website.py (우리들교회).

2026-07-23 실측 확인한 실제 사이트 구조를 고정한 회귀 테스트.
- 목록 페이지: table.tbl_list01 > tbody > tr, td.title > a[href=".../view/{id}"]
- 상세 페이지: 설교자 이름은 반드시 div.cont_row 안에서만 찾아야 한다 —
  사이트 전역 내비게이션에도 "김양재 목사"라는 문구가 반복돼서 (실측 확인),
  cont_row 밖에서 찾으면 담임목사 이름을 잘못 채택하게 된다.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sermon_corpus.collector.church_website import WooriChurchCollector

FIXTURES = Path(__file__).parent / "fixtures"


def _collector():
    return WooriChurchCollector({"source_id": "woori_church"})


class TestParseListPage:
    def test_extracts_wr_id_title_and_date(self):
        html = (FIXTURES / "woori_church_list_sample.html").read_text()
        items = _collector().parse_list_page(html)

        assert len(items) == 3
        assert items[0]["wr_id"] == "1314349"
        assert "충성된 자" in items[0]["title_raw"]
        assert items[0]["list_date"] == "2026.07.20"
        assert items[0]["detail_url"] == "https://woori.cc/board/G00068/view/1314349"


class TestPreacherExtractionScopedToContRow:
    """[버그 방지] 사이트 전역 내비게이션의 "김양재 목사" 문구를 잘못
    채택하지 않고, 본문(.cont_row) 안의 실제 설교자만 채택해야 한다."""

    def test_extracts_preacher_from_cont_row_only(self):
        html = (FIXTURES / "woori_church_detail_sample.html").read_text()
        preacher = _collector()._extract_preacher(html)

        assert preacher == "이성훈"

    def test_does_not_pick_up_navigation_boilerplate_name(self):
        html = (FIXTURES / "woori_church_detail_sample.html").read_text()
        preacher = _collector()._extract_preacher(html)

        assert preacher != "김양재"


class TestParseItem:
    def test_parses_same_chapter_range_title_into_record(self):
        collector = _collector()
        detail_html = (FIXTURES / "woori_church_detail_sample.html").read_text()
        item = {
            "wr_id": "1314349",
            "title_raw": "[국문]7월12일 사무엘하 20:18~22 [충성된 자]",
            "list_date": "2026.07.20",
            "detail_url": "https://woori.cc/board/G00068/view/1314349",
        }

        record = collector.parse_item(item, detail_html)

        assert record is not None
        assert record.title == "충성된 자"
        assert record.bible_book == "2 Samuel"
        assert record.chapter_start == 20
        assert record.verse_start == 18
        assert record.verse_end == 22
        assert record.preacher == "이성훈"
        assert record.published_date == "2026-07-12"
        assert record.passage_raw == "사무엘하 20:18-22"

    def test_cross_chapter_range_is_safely_rejected_not_fabricated(self):
        """[알려진 제약] BibleReferenceParser가 장을 넘나드는 범위
        ("22:20-23:3")는 거부한다(confidence=0.0) — 잘못된 값을 지어내는
        대신 해당 레코드를 수집하지 않는 쪽을 선택한다."""
        collector = _collector()
        item = {
            "wr_id": "1310399",
            "title_raw": "[국문]6월21일 열왕기하 22:20~23:3 [연악을 세우되]",
            "list_date": "2026.06.29",
            "detail_url": "https://woori.cc/board/G00068/view/1310399",
        }

        record = collector.parse_item(item, None)

        assert record is None

    def test_returns_none_when_title_does_not_match_expected_format(self):
        collector = _collector()
        item = {
            "wr_id": "9999",
            "title_raw": "공지사항: 여름 수련회 안내",
            "list_date": "2026.07.01",
            "detail_url": "https://woori.cc/board/G00068/view/9999",
        }

        assert collector.parse_item(item, None) is None


class TestDeduplication:
    def test_is_duplicate_tracks_seen_keys(self):
        collector = _collector()
        assert collector.is_duplicate("abc123") is False
        assert collector.is_duplicate("abc123") is True
