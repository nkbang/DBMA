"""Regression test — QueryParser._detect_books_standalone() alias
resolution stabilization (SPRINT18-Phase18-B-1).

Root cause (confirmed via SPRINT17 Book-level Benchmark + live Chat UI
reproduction): the method sorted alias candidates longest-first but never
stopped at the first (longest) match — it kept scanning the full alias
list and appended every book whose alias appeared anywhere in the query,
including single-character aliases (e.g. "마" inside "마가복음" wrongly
added MAT; "요" inside "필요한가" wrongly added JHN/JOEL).

Fix: (1) exclude aliases shorter than 2 characters from standalone
detection, (2) suppress a shorter alias match if its span overlaps a
span already claimed by a longer match, (3) reject a match whose
preceding character is alphanumeric (catches a legitimate 2+ char alias
embedded mid-word, e.g. "요한" inside "필요한가", which (1)/(2) alone do
not filter).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.retrieval import QueryParser


class TestAliasContaminationFixed:
    """Test A (PM spec) — single-syllable alias contamination removed."""

    def setup_method(self):
        self.parser = QueryParser()

    def test_mark_sermon_query_no_longer_pulls_in_matthew(self):
        result = self.parser._detect_books_standalone(
            "마가복음 본문으로 설교를 준비하려면 어떤 자료가 필요한가?"
        )
        assert result == ["MRK"]
        assert "MAT" not in result
        assert "JHN" not in result
        assert "JOEL" not in result

    def test_acts_sermon_query_no_longer_pulls_in_john(self):
        result = self.parser._detect_books_standalone(
            "사도행전 본문으로 설교를 준비하려면 어떤 자료가 필요한가?"
        )
        assert result == ["ACT"]
        assert "JHN" not in result

    def test_romans_content_query_stays_clean(self):
        result = self.parser._detect_books_standalone("로마서의 주요 내용은 무엇인가?")
        assert result == ["ROM"]


class TestMultiBookQueryStillWorks:
    """Test B (PM spec) — removing single-syllable aliases must not break
    legitimate multi-book queries built from valid 2+ char aliases."""

    def setup_method(self):
        self.parser = QueryParser()

    def test_matthew_and_john_comparison(self):
        result = self.parser._detect_books_standalone("마태복음과 요한복음을 비교하라")
        assert result == ["MAT", "JHN"]

    def test_john_with_trailing_particle_still_detected(self):
        """"요한복음을" (John + object particle 을, no space) must still
        resolve — the leading-boundary check must not reject valid
        particle-attached phrasing."""
        result = self.parser._detect_books_standalone("요한복음을 읽어라")
        assert result == ["JHN"]


class TestMidWordEmbeddingSuppressed:
    """The specific new failure mode found beyond simple length filtering:
    a legitimate 2+ char alias ("요한") coincidentally appearing inside an
    unrelated Korean word ("필요한가")."""

    def setup_method(self):
        self.parser = QueryParser()

    def test_yohan_inside_pilyohan_is_not_a_john_reference(self):
        result = self.parser._detect_books_standalone("이것은 필요한 자료입니다")
        assert "JHN" not in result


class TestSingleCharacterAliasExcluded:
    def setup_method(self):
        self.parser = QueryParser()

    def test_short_aliases_absent_from_cache(self):
        self.parser._detect_books_standalone("")  # trigger lazy cache build
        short_aliases = [alias for alias, _ in self.parser._alias_cache if len(alias) < 2]
        assert short_aliases == []


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
