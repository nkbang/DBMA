"""Regression tests — sermon_corpus/collector/manna.py (만나교회).

2026-07-23 실측 확인한 실제 사이트 구조를 고정한 회귀 테스트.
- WordPress "jt-" 테마: 상세 페이지에 .jt-content-header__title/
  __author/__time/__meta 로 제목/설교자/날짜/본문 참조가 각각
  명확히 구분돼 있다. 전문(설교 원고)은 없지만 DBMA는
  제목/본문 성경구절/설교자/날짜만 요구하므로 충분하다.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sermon_corpus.collector.manna import MannaCollector

FIXTURES = Path(__file__).parent / "fixtures"


def _collector():
    return MannaCollector({"source_id": "manna"})


class TestParseListPage:
    def test_extracts_only_sermon_detail_links(self):
        html = (FIXTURES / "manna_list_sample.html").read_text()
        items = _collector().parse_list_page(html)

        urls = {item["detail_url"] for item in items}
        assert len(items) == 2
        assert all("/설교/" in u for u in urls)
        assert not any("섬기는-사람들" in u for u in urls)


class TestParseItem:
    def test_extracts_title_passage_preacher_date(self):
        html = (FIXTURES / "manna_detail_sample.html").read_text()
        record = _collector().parse_item(html, "https://manna.or.kr/설교/14-test/")

        assert record is not None
        assert record.title == "개혁! 좌로나 우로 치우치지 않는 것(요시야)"
        assert record.preacher == "김병삼 목사"
        assert record.published_date == "2026-07-12"
        assert record.bible_book == "2 Kings"
        assert record.chapter_start == 22
        assert record.verse_start == 2

    def test_returns_none_when_meta_missing(self):
        collector = _collector()
        html = "<html><body><div class='jt-content-header__title'>제목만 있음</div></body></html>"

        assert collector.parse_item(html, "https://manna.or.kr/설교/x/") is None

    def test_returns_none_when_title_missing(self):
        collector = _collector()
        html = "<html><body><div class='jt-content-header__meta'>창 1:1</div></body></html>"

        assert collector.parse_item(html, "https://manna.or.kr/설교/x/") is None


class TestDeduplication:
    def test_is_duplicate_tracks_seen_keys(self):
        collector = _collector()
        assert collector.is_duplicate("abc") is False
        assert collector.is_duplicate("abc") is True
