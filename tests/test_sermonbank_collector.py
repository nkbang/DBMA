"""Regression tests — sermon_corpus/collector/sermonbank.py.

두 가지 실제 버그를 고정한다:
1. SermonRecord에 dedupe_key 필드가 없어 save_to_jsonl()이 항상
   AttributeError로 실패하던 것.
2. BibleReferenceParser.parse()가 _extract_chapter_verse()의 반환값을
   어디에도 대입하지 않아 chapter_start/verse_start 등이 항상 None으로
   남던 것.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sermon_corpus.collector.sermonbank import (
    BibleReferenceParser,
    SermonBankCollector,
    SermonRecord,
    compute_dedupe_key,
)


def _record(title="사랑은 오래 참고", passage_raw="고린도전서 13:4-7") -> SermonRecord:
    return SermonRecord(
        record_id="sb_test",
        source="sermonbank",
        title=title,
        passage_raw=passage_raw,
        bible_book="1 Corinthians",
        chapter_start=13,
        chapter_end=13,
        verse_start=4,
        verse_end=7,
        preacher=None,
        published_date=None,
        source_url="https://sermonbank.net/x",
        collected_at=datetime.utcnow().isoformat(),
    )


class TestDedupeKeyBugFix:
    def test_record_has_dedupe_key_property(self):
        rec = _record()
        assert rec.dedupe_key == compute_dedupe_key(rec.title, rec.passage_raw)

    def test_collector_generate_dedupe_key_matches_record_property(self):
        rec = _record()
        collector = SermonBankCollector({"source_id": "sermonbank"})
        assert collector.generate_dedupe_key(rec.title, rec.passage_raw) == rec.dedupe_key

    def test_save_to_jsonl_does_not_raise(self, tmp_path):
        collector = SermonBankCollector({"source_id": "sermonbank"})
        out_path = tmp_path / "out.jsonl"
        saved = collector.save_to_jsonl([_record()], path=out_path)
        assert saved == 1
        assert out_path.exists()

    def test_save_to_jsonl_skips_duplicates(self, tmp_path):
        collector = SermonBankCollector({"source_id": "sermonbank"})
        out_path = tmp_path / "out.jsonl"
        saved = collector.save_to_jsonl([_record(), _record()], path=out_path)
        assert saved == 1
        assert collector.stats["duplicates_skipped"] == 1


class TestParseSermonFromHtmlRealSiteStructure:
    """[2026-07-22] 크롤링 결과가 항상 0건이던 버그의 회귀 테스트.

    실제 원인: sources.yml의 수집 URL(/sermons, /search)이 404였고,
    parse_sermon_from_html()의 selector(div.sermon-item 등)도 실제 사이트
    (그누보드 게시판, div/li 컨테이너 없이 <table> 반복 + wr_id 링크 앵커
    구조)와 전혀 일치하지 않는 추측값이었다. sermonbank.net/bbs/board.php
    ?bo_table=sermon에서 실제로 받아온 HTML 샘플로 파싱이 정상 동작하는지
    고정한다."""

    def _sample_html(self) -> str:
        fixture = Path(__file__).parent / "fixtures" / "sermonbank_board_list_sample.html"
        return fixture.read_text(encoding="utf-8")

    def test_parses_records_from_real_board_html(self):
        collector = SermonBankCollector({"source_id": "sermonbank"})
        records = collector.parse_sermon_from_html(
            self._sample_html(), "https://sermonbank.net/bbs/board.php?bo_table=sermon"
        )
        assert len(records) > 0
        assert collector.stats["errors"] == 0

    def test_first_record_fields_match_known_sample(self):
        # 샘플 HTML의 최상단 게시글 — 실측 값과 정확히 일치해야 한다.
        collector = SermonBankCollector({"source_id": "sermonbank"})
        records = collector.parse_sermon_from_html(
            self._sample_html(), "https://sermonbank.net/bbs/board.php?bo_table=sermon"
        )
        first = records[0]
        assert first.title == "하나님의 주권에 순복하라"
        assert first.passage_raw == "로마서 9:11-16"
        assert first.preacher == "강종수"
        assert first.published_date == "2026-07-19"
        assert first.source_url == "https://sermonbank.net/bbs/board.php?bo_table=sermon&wr_id=65799"


class _StubFetcher:
    """collect_all() 페이지네이션 테스트용 — url별로 미리 정해둔 HTML을
    반환하는 가짜 fetcher (실제 네트워크 요청 없음)."""

    def __init__(self, pages: dict):
        self.pages = pages
        self.requested_urls = []

    def get_text(self, url: str):
        self.requested_urls.append(url)
        return self.pages.get(url, "")


def _board_html_with_one_item(wr_id: int, title: str) -> str:
    return f"""
    <table style="margin:0 0 15px 0">
      <tr><td><table><tr><td>
        <span class="f_s_list"><a href='../bbs/board.php?bo_table=sermon&wr_id={wr_id}'>{title}</a></span>
        <span class="f_d2_6">창세기 1:1</span>
      </td><td class="f_d1_6"><strong class="f_d1_3"><a><span class='member'>테스트목사</span></a></strong></td></tr></table></td></tr>
      <tr><td class="bd_sermon_L02">2026-01-01</td></tr>
    </table>
    """


class TestCollectAllPagination:
    """[기능 추가] 목록 페이지가 페이지당 15건만 보여주는데 collect_all()이
    self.urls의 페이지(보통 1페이지)만 가져오고 끝나서 매번 15건에서
    멈추던 것 — page=2, page=3... 로 이어서 수집하도록 고침."""

    BASE = "https://sermonbank.net/bbs/board.php?bo_table=sermon"

    def test_paginates_across_multiple_pages(self):
        pages = {
            self.BASE: _board_html_with_one_item(1, "1페이지 설교"),
            f"{self.BASE}&page=2": _board_html_with_one_item(2, "2페이지 설교"),
            f"{self.BASE}&page=3": _board_html_with_one_item(3, "3페이지 설교"),
        }
        fetcher = _StubFetcher(pages)
        collector = SermonBankCollector({"source_id": "sermonbank", "urls": [self.BASE]})

        records = collector.collect_all(fetcher, max_pages=5)

        assert [r.title for r in records] == ["1페이지 설교", "2페이지 설교", "3페이지 설교"]
        # 4페이지는 빈 결과라 요청은 갔지만(끝 확인용) 5페이지는 요청 안 함
        assert f"{self.BASE}&page=4" in fetcher.requested_urls
        assert f"{self.BASE}&page=5" not in fetcher.requested_urls

    def test_stops_at_max_records_mid_page_list(self):
        pages = {
            self.BASE: _board_html_with_one_item(1, "1페이지 설교"),
            f"{self.BASE}&page=2": _board_html_with_one_item(2, "2페이지 설교"),
        }
        fetcher = _StubFetcher(pages)
        collector = SermonBankCollector({"source_id": "sermonbank", "urls": [self.BASE]})

        records = collector.collect_all(fetcher, max_records=1, max_pages=5)

        assert len(records) == 1
        assert records[0].title == "1페이지 설교"
        # max_records에 도달했으니 2페이지는 요청하지 않아야 함
        assert f"{self.BASE}&page=2" not in fetcher.requested_urls

    def test_respects_max_pages_limit(self):
        # 모든 페이지가 항목을 반환하는 무한 사이트를 흉내 — max_pages로만 멈춰야 함
        class _InfiniteFetcher:
            def __init__(self):
                self.requested_urls = []

            def get_text(self, url: str):
                self.requested_urls.append(url)
                return _board_html_with_one_item(len(self.requested_urls), "설교")

        fetcher = _InfiniteFetcher()
        collector = SermonBankCollector({"source_id": "sermonbank", "urls": [self.BASE]})

        records = collector.collect_all(fetcher, max_pages=3)

        assert len(records) == 3
        assert len(fetcher.requested_urls) == 3


class TestChapterVerseParsingBugFix:
    """[2026-07-22 갱신] C1이 BibleReferenceParser 전체를 새 구현(4단계
    검증, confidence/kind 필드, 정규식 기반 다중 패턴)으로 교체해 이
    클래스의 옛 테스트가 낡은 계약(구 API의 정확한 dict 동등성, verse_end
    None 관례)을 검증하고 있었다 — 새 계약에 맞춰 갱신하고, 그 과정에서
    발견한 BOOK_CHAPTER_LIMITS 버그 2건(장 수를 절 상한으로 오용,
    end_ch limits dead-code)에 대한 회귀 테스트로 대체."""

    def setup_method(self):
        self.parser = BibleReferenceParser()

    def test_chapter_and_verse_range(self):
        result = self.parser.parse("고린도전서 13:4-7")
        assert result["bible_book"] == "1 Corinthians"
        assert result["chapter_start"] == 13
        assert result["verse_start"] == 4
        assert result["verse_end"] == 7
        assert result["kind"] == "confirmed"

    def test_common_verse_beyond_book_chapter_count_not_rejected(self):
        # [버그 수정 회귀 테스트] 로마서는 16장까지 있는데, 예전 버그는
        # 이 "16"을 모든 장의 절 상한으로도 잘못 재사용해 로마서 8:28
        # (실제로는 정상 구절)을 rejected 처리했다.
        result = self.parser.parse("로마서 8:28")
        assert result["chapter_start"] == 8
        assert result["verse_start"] == 28
        assert result["kind"] == "confirmed"

    def test_chapter_only_no_verse(self):
        result = self.parser.parse("고린도전서 13장")
        assert result["bible_book"] == "1 Corinthians"
        assert result["chapter_start"] == 13
        assert result["verse_start"] is None

    def test_out_of_range_chapter_number_rejected(self):
        # 로마서는 16장까지만 있다 — 17장은 존재하지 않으므로 거부돼야 함.
        result = self.parser.parse("로마서 17:1")
        assert result["kind"] == "rejected"

    def test_absurd_verse_number_rejected_by_cross_chapter_end_check(self):
        # [버그 수정 회귀 테스트] limits.get(end_ch, {})가 실제로는 dict가
        # 아니라 int라 isinstance 체크가 항상 False로 빠지던 dead-code —
        # 999절처럼 터무니없는 끝 절 번호가 통과되지 않아야 한다.
        result = self.parser.parse("창세기 1:1-2:999")
        assert result["kind"] == "rejected"

    def test_empty_input(self):
        result = self.parser.parse("")
        assert result["bible_book"] is None
        assert result["kind"] == "rejected"

    def test_genesis_still_recognized(self):
        # [2026-07-22] "창세记"(한자 오타) 별칭 여부는 C1의 전면 재작성
        # 이후 BOOK_ALIASES 구조 자체가 바뀌어 더 이상 이 클래스에서
        # 검증할 대상이 아니다 — 책명 인식 자체만 확인.
        assert self.parser.parse("창세기 1:1")["bible_book"] == "Genesis"
        assert "창세记" not in BibleReferenceParser.BOOK_ALIASES
