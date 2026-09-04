"""core/bible_text.py — 사용자 제공 성경 본문 JSON 로더 (ADR-031)."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.bible_text import BibleText, korean_book_name, load_bible_text, normalize_book_id


def _write(tmp_path, obj) -> str:
    p = tmp_path / "bible.json"
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return str(p)


_SAMPLE = {
    "version": "개역개정",
    "books": {
        "GEN": {"name": "창세기", "chapters": [["태초에 하나님이 천지를 창조하시니라"]]},
        "PRO": {
            "name": "잠언",
            "chapters": [
                ["1장 1절", "1장 2절"],
                ["2장 1절"],
                [],
                [],
                [],
                [],
                [],
                [f"8장 {v}절" for v in range(1, 37)],  # 잠언 8장 = 36절
            ],
        },
        "JHN": {"name": "요한복음", "chapters": [["1:1", "1:2"]]},
    },
}


class TestHappyPath:
    def test_version_label(self, tmp_path):
        bible = load_bible_text(_write(tmp_path, _SAMPLE))
        assert bible.available is True
        assert bible.version_label == "개역개정"

    def test_get_single_verse(self, tmp_path):
        bible = load_bible_text(_write(tmp_path, _SAMPLE))
        assert bible.get_verses("PRO", 8, 10, 10) == [(10, "8장 10절")]

    def test_get_verse_range(self, tmp_path):
        bible = load_bible_text(_write(tmp_path, _SAMPLE))
        verses = bible.get_verses("PRO", 8, 10, 12)
        assert [n for n, _ in verses] == [10, 11, 12]

    def test_range_clamped_to_available(self, tmp_path):
        bible = load_bible_text(_write(tmp_path, _SAMPLE))
        verses = bible.get_verses("PRO", 8, 35, 99)
        assert [n for n, _ in verses] == [35, 36]

    def test_counts(self, tmp_path):
        bible = load_bible_text(_write(tmp_path, _SAMPLE))
        assert bible.chapter_count("PRO") == 8
        assert bible.verse_count("PRO", 8) == 36
        assert bible.verse_count("PRO", 3) == 0

    def test_list_books_in_canonical_order(self, tmp_path):
        bible = load_bible_text(_write(tmp_path, _SAMPLE))
        ids = [bid for bid, _ in bible.list_books()]
        assert ids == ["GEN", "PRO", "JHN"]

    def test_book_id_normalization_alias(self, tmp_path):
        obj = {"version": "x", "books": {"잠": {"chapters": [["a"]]}, "proverbs2": {}}}
        # "잠" -> PRO, "proverbs2" 는 미해석 -> 건너뜀
        bible = load_bible_text(_write(tmp_path, obj))
        assert bible.available is True
        assert bible.has_book("PRO")
        assert bible.list_books() == [("PRO", "잠언")]


class TestFailClosed:
    def test_missing_file(self, tmp_path):
        bible = load_bible_text(str(tmp_path / "does_not_exist.json"))
        assert bible.available is False
        assert bible.reason
        # 미가용 인스턴스도 조회 API 가 안전해야 한다
        assert bible.list_books() == []
        assert bible.get_verses("PRO", 8, 10, 10) == []
        assert bible.chapter_count("PRO") == 0

    def test_top_level_not_object(self, tmp_path):
        p = tmp_path / "b.json"
        p.write_text("[]", encoding="utf-8")
        assert load_bible_text(str(p)).available is False

    def test_missing_books_key(self, tmp_path):
        assert load_bible_text(_write(tmp_path, {"version": "x"})).available is False

    def test_empty_books(self, tmp_path):
        assert load_bible_text(_write(tmp_path, {"books": {}})).available is False

    def test_no_valid_book(self, tmp_path):
        obj = {"books": {"ZZZ": {"chapters": [["a"]]}, "PRO": {"chapters": "nope"}}}
        assert load_bible_text(_write(tmp_path, obj)).available is False

    def test_invalid_json(self, tmp_path):
        p = tmp_path / "b.json"
        p.write_text("{not json", encoding="utf-8")
        assert load_bible_text(str(p)).available is False

    def test_unavailable_constructor(self):
        b = BibleText.unavailable("사유")
        assert b.available is False and b.reason == "사유"


class TestHelpers:
    def test_normalize_book_id(self):
        assert normalize_book_id("PRO") == "PRO"
        assert normalize_book_id("proverbs") == "PRO"
        assert normalize_book_id("잠언") == "PRO"
        assert normalize_book_id("없는책") is None

    def test_korean_book_name_override(self):
        assert korean_book_name("SOL") == "아가"
        assert korean_book_name("PRO") == "잠언"
