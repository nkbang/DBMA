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
