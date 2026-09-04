"""Tests for core/query_planner.py (DBMA-SEARCH-INFRA-001 Query Planner, HQ 제안 ④)."""

import pytest

from core.query_planner import classify
from core.retrieval import QueryParser

_parser = QueryParser()


def _classify(query: str):
    parsed = _parser.parse(query)
    return classify(query, parsed)


class TestHQExamples:
    """The exact examples from the HQ directive."""

    def test_bible_reference_korean_no_space(self):
        plan = _classify("롬8:28")
        assert plan.route == "bible"

    def test_bible_reference_korean_spaced(self):
        plan = _classify("롬 8:28")
        assert plan.route == "bible"

    def test_metadata_author_name(self):
        plan = _classify("Calvin")
        assert plan.route == "metadata"

    def test_greek_word(self):
        plan = _classify("λόγος")
        assert plan.route == "greek"

    def test_thematic_short_phrase_is_hybrid_not_metadata(self):
        # HQ's own example — 3 Korean words, must NOT be misrouted to metadata.
        plan = _classify("고난 속 소망")
        assert plan.route == "hybrid"


class TestBibleRoute:
    def test_english_full_reference(self):
        plan = _classify("Romans 8:28")
        assert plan.route == "bible"

    def test_reference_with_range(self):
        plan = _classify("Romans 5:1-10")
        assert plan.route == "bible"
        assert plan.reason == "scripture reference detected"

    def test_bible_takes_priority_over_everything_else(self):
        # Quoted AND contains a scripture ref — bible wins.
        plan = _classify('"Romans 8:28 is amazing"')
        assert plan.route == "bible"


class TestGreekRoute:
    def test_hebrew_word(self):
        plan = _classify("בְּרֵאשִׁית")
        assert plan.route == "greek"

    def test_greek_takes_priority_over_metadata_shape(self):
        plan = _classify("Λόγος")  # capitalized, would look proper-noun-like
        assert plan.route == "greek"


class TestExactRoute:
    def test_double_quoted_phrase(self):
        plan = _classify('"하나님의 나라"')
        assert plan.route == "exact"
        assert plan.exact_phrase == "하나님의 나라"

    def test_single_quoted_phrase(self):
        plan = _classify("'grace and law'")
        assert plan.route == "exact"
        assert plan.exact_phrase == "grace and law"

    def test_curly_quotes(self):
        plan = _classify("“하나님의 은혜”")
        assert plan.route == "exact"
        assert plan.exact_phrase == "하나님의 은혜"

    def test_unquoted_is_not_exact(self):
        plan = _classify("하나님의 나라")
        assert plan.route != "exact"


class TestMetadataRoute:
    def test_single_capitalized_word(self):
        plan = _classify("Luther")
        assert plan.route == "metadata"

    def test_lowercase_single_word_is_hybrid(self):
        # No gazetteer to confirm this is a name — stays conservative.
        plan = _classify("grace")
        assert plan.route == "hybrid"

    def test_multi_word_english_is_hybrid(self):
        plan = _classify("Calvin Institutes")
        assert plan.route == "hybrid"

    def test_korean_single_word_is_hybrid(self):
        # No Latin-script gazetteer match possible — falls through, not invented.
        plan = _classify("칼빈")
        assert plan.route == "hybrid"


class TestHybridRoute:
    def test_natural_language_question(self):
        plan = _classify("고난 중의 소망에 관한 설교 자료를 찾아줘")
        assert plan.route == "hybrid"

    def test_english_sentence(self):
        plan = _classify("What does the Bible say about grace?")
        assert plan.route == "hybrid"

    def test_route_priority_order_bible_greek_exact_metadata_hybrid(self):
        # Sanity: every branch is reachable and mutually exclusive on these inputs.
        routes = {
            _classify("롬8:28").route,
            _classify("λόγος").route,
            _classify('"exact phrase"').route,
            _classify("Calvin").route,
            _classify("이것은 자연어 문장입니다").route,
        }
        assert routes == {"bible", "greek", "exact", "metadata", "hybrid"}
