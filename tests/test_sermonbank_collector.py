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


class TestChapterVerseParsingBugFix:
    def setup_method(self):
        self.parser = BibleReferenceParser()

    def test_chapter_and_verse_range(self):
        result = self.parser.parse("고린도전서 13:4-7")
        assert result == {
            "bible_book": "1 Corinthians",
            "chapter_start": 13,
            "chapter_end": 13,
            "verse_start": 4,
            "verse_end": 7,
        }

    def test_single_verse_no_range(self):
        result = self.parser.parse("로마서 8:28")
        assert result["chapter_start"] == 8
        assert result["verse_start"] == 28
        assert result["verse_end"] is None

    def test_chapter_only_no_verse(self):
        result = self.parser.parse("고린도전서 13")
        assert result["bible_book"] == "1 Corinthians"
        assert result["chapter_start"] == 13
        assert result["verse_start"] is None
        assert result["verse_end"] is None

    def test_english_book_name_still_extracts_chapter_verse(self):
        # 버그 수정 전에는 영어 책명으로 매칭된 경우 장/절 추출 자체가
        # 호출되지 않았다.
        result = self.parser.parse("1 Corinthians 13:4")
        assert result["bible_book"] == "1 Corinthians"
        assert result["chapter_start"] == 13
        assert result["verse_start"] == 4

    def test_empty_input(self):
        result = self.parser.parse("")
        assert result == {
            "bible_book": None,
            "chapter_start": None,
            "chapter_end": None,
            "verse_start": None,
            "verse_end": None,
        }

    def test_genesis_alias_typo_removed(self):
        # "창세记"(한자 오타)가 아니라 "창세기"로만 매칭되어야 한다.
        assert self.parser.parse("창세기 1:1")["bible_book"] == "Genesis"
        assert "창세记" not in BibleReferenceParser.BOOK_ALIASES
