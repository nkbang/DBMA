"""Regression test — Korean scripture reference no-space colon form and
duplicate-reference dedup (SPRINT18-A, Korean Scripture Reference
Stabilization).

Extends two existing parsers rather than introducing a new one (SPRINT18-A
Preflight finding: 4 of 5 PM-specified target formats already worked;
only the no-space colon form "요3:16" was a genuine gap):

  1. core/retrieval.py::QueryParser._extract_scripture_refs() Pattern 2 —
     the trailing \\b after the book alias never actually required a
     space for Korean aliases (Hangul syllables and digits are both \\w
     in Python's Unicode regex, so no boundary ever existed between them)
     — it silently only worked with a space by accident. Dropping the
     trailing \\b (kept the leading one) and making whitespace optional
     fixes the no-space form without weakening the leading-boundary
     protection against mid-word false positives.

  2. core/query_enhancements.py::EnhancedReferenceParser.parse_chapter_only()
     — three independent regex passes over the same query could each
     independently match the same reference (e.g. "요한복음" appears as
     a key in both KO_ABBR_TO_BOOK and _KOREAN_FULL_NAMES), producing
     duplicate ScriptureReference entries in this method's own return
     value even though the caller (EnhancedQueryParser.parse()) already
     deduped before exposing it via ParsedQuery.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.retrieval import QueryParser
from core.query_enhancements import EnhancedReferenceParser


class TestNoSpaceColonForm:
    """PM-specified target formats — all 5 must resolve via the
    production QueryParser (= EnhancedQueryParser)."""

    def setup_method(self):
        self.parser = QueryParser()

    def _refs(self, query):
        return self.parser.parse(query).scripture_refs

    def test_with_space(self):
        refs = self._refs("요 3:16")
        assert any(r.book_id == "JHN" and r.chapter == 3 and r.verse_start == 16 for r in refs)

    def test_without_space(self):
        refs = self._refs("요3:16")
        assert any(r.book_id == "JHN" and r.chapter == 3 and r.verse_start == 16 for r in refs)

    def test_verse_range_with_space(self):
        refs = self._refs("막 4:1-20")
        assert any(r.book_id == "MRK" and r.chapter == 4 and r.verse_start == 1 and r.verse_end == 20 for r in refs)

    def test_no_space_multi_char_abbreviation(self):
        refs = self._refs("고전13:1")
        assert any(r.book_id == "1CO" and r.chapter == 13 and r.verse_start == 1 for r in refs)

    def test_full_name_chapter_verse_korean_form(self):
        refs = self._refs("요한복음 3장 16절")
        assert any(r.book_id == "JHN" and r.chapter == 3 and r.verse_start == 16 for r in refs)


class TestNoFalsePositiveFromOptionalWhitespace:
    """Dropping the trailing \\b and making whitespace optional must not
    cause a book alias embedded mid-word to match — the leading \\b plus
    the immediate (\\d+): requirement must still reject these."""

    def setup_method(self):
        self.parser = QueryParser()

    def test_yohan_inside_unrelated_word_not_matched(self):
        refs = self.parser._extract_scripture_refs("중요3:16")
        assert refs == []

    def test_pilyohan_with_colon_not_matched(self):
        refs = self.parser._extract_scripture_refs("필요한 3:16 같은 사례")
        assert refs == []

    def test_phone_number_like_pattern_not_matched(self):
        refs = self.parser._extract_scripture_refs("전화번호는 010-1234:5678")
        assert refs == []


class TestChapterOnlyParserDedup:
    def setup_method(self):
        self.parser = EnhancedReferenceParser()

    def test_full_name_chapter_verse_not_duplicated(self):
        """"요한복음 3장 16절" matches both the abbreviation pattern
        (KO_ABBR_TO_BOOK has "요한복음") and the full-name pattern
        (_KOREAN_FULL_NAMES also has it) — must appear exactly once."""
        refs = self.parser.parse_chapter_only("요한복음 3장 16절 말씀으로 복음을 설명해줘")
        assert len(refs) == 1
        assert refs[0].book_id == "JHN"
        assert refs[0].chapter == 3
        assert refs[0].verse_start == 16

    def test_distinct_references_both_kept(self):
        """Dedup must not over-collapse genuinely distinct references."""
        refs = self.parser.parse_chapter_only("로마서 8장과 요한복음 3장을 비교하라")
        book_ids = {r.book_id for r in refs}
        assert book_ids == {"ROM", "JHN"}


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
