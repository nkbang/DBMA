"""Regression test — core/retrieval.py content_refs_cache perf fix (2026-07-22).

_scripture_alignment_score() re-parsed a TSU's static content for
scripture references on every call (measured: ~4.1s/query across a
52,064-TSU corpus when the query has no English book name, since
query_refs stays empty and the code falls through to parsing tsu
content every time). Fixed via an id(tsu)-keyed cache threaded through
compute_theological_score(). This test guards:
  1. Cache is a pure performance optimization — scores must be
     identical with/without it.
  2. The cache actually gets populated and reused (not a no-op).
  3. query_refs non-empty skips tsu-content parsing entirely (short-circuit).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch

from core.retrieval import _parse_refs_from_text, _scripture_alignment_score, compute_theological_score


def _tsu(content: str, book_id: str = "GEN", chapter: int = 1) -> dict:
    return {
        "content": content,
        "verse_mapping": {"book_id": book_id, "chapter": chapter},
        "source_file": "test.pdf",
    }


class TestCacheDoesNotChangeResults:
    def test_same_score_with_and_without_cache(self):
        tsu = _tsu("태초에 하나님이 천지를 창조하시니라 (창세기 1:1 주석 내용)")
        query = "창세기 1:1 태초에"

        score_uncached, breakdown_uncached = compute_theological_score(query, tsu)
        cache: dict = {}
        score_cached, breakdown_cached = compute_theological_score(
            query, tsu, content_refs_cache=cache
        )

        assert score_uncached == score_cached
        assert breakdown_uncached == breakdown_cached


class TestCacheIsActuallyReused:
    def test_second_call_does_not_reparse_content(self):
        tsu = _tsu("Genesis 1:1 창조 기사에 대한 주석입니다.")
        cache: dict = {}

        # First call populates the cache.
        compute_theological_score("창세기 1:1 태초에", tsu, content_refs_cache=cache)
        assert len(cache) == 1

        # Second call for the SAME tsu must not re-parse its content —
        # spy on _parse_refs_from_text and assert it's never called with
        # tsu["content"] the second time (query parsing still happens,
        # that part is cheap and intentionally not cached).
        original = _parse_refs_from_text
        calls_on_content = []

        def _spy(text):
            if text == tsu["content"]:
                calls_on_content.append(text)
            return original(text)

        with patch("core.retrieval._parse_refs_from_text", side_effect=_spy):
            compute_theological_score("창세기 1:1 태초에", tsu, content_refs_cache=cache)

        assert calls_on_content == []  # cached — never re-parsed tsu.content
        assert len(cache) == 1  # no new entry added


class TestQueryRefsShortCircuit:
    def test_english_book_name_query_skips_content_parsing(self):
        tsu = _tsu("아무 성구 참조도 없는 순수 한국어 본문입니다.")
        calls = []
        original = _parse_refs_from_text

        def _spy(text):
            calls.append(text)
            return original(text)

        with patch("core.retrieval._parse_refs_from_text", side_effect=_spy):
            _scripture_alignment_score("Genesis 1:1 in the beginning", tsu)

        # Only the query itself should have been parsed — tsu["content"]
        # must never reach _parse_refs_from_text once query_refs is non-empty.
        assert tsu["content"] not in calls
