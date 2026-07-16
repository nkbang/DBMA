"""Regression test — EnhancedBookDetector.detect_books() Step 4 alias
guard (SPRINT18-B-1, scope extension).

core/retrieval.py's QueryParser name is monkey-patched at module load
time (bottom of the file) to core.query_enhancements.EnhancedQueryParser
— the actual production import path. EnhancedQueryParser.parse() calls
super().parse() (fixed separately in
tests/test_alias_resolution_stabilization.py) and then layers
EnhancedBookDetector.detect_books() on top. Step 4 of that method had no
minimum-length guard at all (unlike Step 5, a few lines below it in the
same method, which already had min_len=6/3), reintroducing the exact
same single-character alias contamination bug independently.

These tests exercise the production import path directly
(`from core.retrieval import QueryParser`) so a regression in either
detector — or a future divergence between their policies — is caught.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.retrieval import QueryParser
from core.query_enhancements import EnhancedQueryParser


class TestProductionPathIsEnhanced:
    def test_core_retrieval_queryparser_is_enhanced_subclass(self):
        """Guards the monkey-patch itself — if this ever silently reverts
        to the base QueryParser, EnhancedBookDetector's fixes (this file)
        stop applying in production without any other test noticing."""
        assert QueryParser is EnhancedQueryParser


class TestEnhancedBookDetectorAliasContamination:
    def setup_method(self):
        self.parser = QueryParser()

    def test_mark_sermon_query_no_longer_pulls_in_matthew(self):
        result = self.parser.parse(
            "마가복음 본문으로 설교를 준비하려면 어떤 자료가 필요한가?"
        ).detected_books
        assert result == ["MRK"]

    def test_acts_sermon_query_no_longer_pulls_in_john(self):
        result = self.parser.parse(
            "사도행전 본문으로 설교를 준비하려면 어떤 자료가 필요한가?"
        ).detected_books
        assert result == ["ACT"]

    def test_romans_content_query_stays_clean(self):
        result = self.parser.parse("로마서의 주요 내용은 무엇인가?").detected_books
        assert result == ["ROM"]

    def test_yohan_inside_pilyohan_not_detected_via_production_path(self):
        """The specific failure mode that survived the first
        (base-class-only) fix: "요한" (valid 2-char JHN alias) embedded
        inside "필요한" ("necessary") via EnhancedBookDetector Step 4,
        which had no length or boundary guard at all."""
        result = self.parser.parse("이것은 필요한 자료입니다").detected_books
        assert "JHN" not in result

    def test_multi_book_comparison_still_works(self):
        """Removing single-char aliases must not break legitimate
        multi-book detection built from valid 2+ char aliases."""
        result = self.parser.parse("마태복음과 요한복음을 비교하라").detected_books
        assert result == ["MAT", "JHN"]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
