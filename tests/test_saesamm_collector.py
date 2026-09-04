"""Regression tests — sermon_corpus/collector/saesamm.py (새삶교회).

2026-07-23 실측 확인한 실제 사이트 구조를 고정한 회귀 테스트.
- 목록: li.gall_li > a.bo_tit[href*="wr_id="] (그누보드 갤러리형 스킨)
- 상세: table#sermon-info 안 th/td로 설교자·설교본문·설교날짜가 명시적으로
  라벨링돼 있음 — 다른 그누보드 사이트보다 필드 구분이 명확하다.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sermon_corpus.collector.saesamm import SaesammCollector

FIXTURES = Path(__file__).parent / "fixtures"


def _collector():
    return SaesammCollector({"source_id": "saesamm"})


class TestParseListPage:
    def test_extracts_wr_id_and_title(self):
        html = (FIXTURES / "saesamm_list_sample.html").read_text()
        items = _collector().parse_list_page(html)

        assert len(items) == 2
        assert items[0]["wr_id"] == "276"
        assert "축복의 통로가 되는 부모" in items[0]["title_raw"]
        assert items[0]["detail_url"] == "https://www.saesamm.com/bbs/board.php?bo_table=sermon&wr_id=276"


class TestParseSermonInfo:
    def test_extracts_labeled_fields_from_sermon_info_table(self):
        html = (FIXTURES / "saesamm_detail_sample.html").read_text()
        info = _collector()._parse_sermon_info(html)

        assert info["preacher"] == "백 금현목사"
        assert info["passage_raw"] == "롬12:3"
        assert info["published_date"] == "2026-05-03"


class TestParseItem:
    def test_strips_management_number_prefix_from_title(self):
        collector = _collector()
        detail_html = (FIXTURES / "saesamm_detail_sample.html").read_text()
        item = {
            "wr_id": "265",
            "title_raw": "R479 롬(3) 삶의 방향: 믿음의 분량대로",
            "detail_url": "https://www.saesamm.com/bbs/board.php?bo_table=sermon&wr_id=265",
        }

        record = collector.parse_item(item, detail_html)

        assert record is not None
        assert record.title == "롬(3) 삶의 방향: 믿음의 분량대로"
        assert record.bible_book == "Romans"
        assert record.chapter_start == 12
        assert record.verse_start == 3
        assert record.preacher == "백 금현목사"
        assert record.published_date == "2026-05-03"

    def test_accepts_chapter_only_reference_without_verse(self):
        """[실측 확인] 이 사이트는 "신6장"처럼 장만 있고 절이 없는
        본문 참조가 흔하다 — verse가 없어도 정상 수집돼야 한다."""
        collector = _collector()
        detail_html = """
        <table id="sermon-info"><tbody>
            <tr><th>설교자</th><td>김정기 목사</td></tr>
            <tr><th>설교본문</th><td>신 18장</td></tr>
            <tr><th>설교날짜</th><td>2026-03-29</td></tr>
        </tbody></table>
        <div id="bo_v_con"><p>본문 내용</p></div>
        """
        item = {
            "wr_id": "260",
            "title_raw": "R470 어떤 제목",
            "detail_url": "https://www.saesamm.com/bbs/board.php?bo_table=sermon&wr_id=260",
        }

        record = collector.parse_item(item, detail_html)

        assert record is not None
        assert record.bible_book == "Deuteronomy"
        assert record.chapter_start == 18
        assert record.verse_start is None

    def test_rejects_unparseable_passage_without_fabricating(self):
        collector = _collector()
        detail_html = """
        <table id="sermon-info"><tbody>
            <tr><th>설교자</th><td>어떤 목사</td></tr>
            <tr><th>설교본문</th><td>롬16</td></tr>
            <tr><th>설교날짜</th><td>2026-07-05</td></tr>
        </tbody></table>
        <div id="bo_v_con"><p>본문 내용</p></div>
        """
        item = {
            "wr_id": "274",
            "title_raw": "R485 어떤 제목",
            "detail_url": "https://www.saesamm.com/bbs/board.php?bo_table=sermon&wr_id=274",
        }

        assert collector.parse_item(item, detail_html) is None

    def test_returns_none_when_sermon_info_table_missing(self):
        collector = _collector()
        item = {
            "wr_id": "999",
            "title_raw": "R999 공지",
            "detail_url": "https://www.saesamm.com/bbs/board.php?bo_table=sermon&wr_id=999",
        }

        assert collector.parse_item(item, "<html><body>내용 없음</body></html>") is None


class TestDeduplication:
    def test_is_duplicate_tracks_seen_keys(self):
        collector = _collector()
        assert collector.is_duplicate("xyz789") is False
        assert collector.is_duplicate("xyz789") is True
