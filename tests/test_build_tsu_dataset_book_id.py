"""Regression test — TSU book_id resolution (SPRINT17-Phase6A-1).

build_tsu_records() previously tagged every TSU record "GEN" regardless
of actual document content (Dataset Quality Audit finding). This test
guards _resolve_book_id() against the two concrete regressions found
while fixing it:
  1. NFC/NFD Unicode mismatch silently failing all Korean filename matches.
  2. Single-character alias false positives (e.g. "마가복음" matching "마").
"""

import sys
import os
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.build_tsu_dataset import _resolve_book_id


class TestResolveBookId:
    def test_korean_full_name_nfc(self):
        assert _resolve_book_id("11. 고린도전서.pdf") == "1CO"
        assert _resolve_book_id("12. 고린도후서.pdf") == "2CO"

    def test_korean_full_name_nfd_matches_nfc(self):
        """macOS stores Korean filenames as NFD — must resolve the same as NFC."""
        nfd_name = unicodedata.normalize("NFD", "11. 고린도전서.pdf")
        assert nfd_name != "11. 고린도전서.pdf"  # sanity: NFD really differs byte-wise
        assert _resolve_book_id(nfd_name) == "1CO"

    def test_mark_does_not_false_positive_to_matthew(self):
        """'마가복음' (Mark) contains the single-char MAT alias '마' — must not match."""
        assert _resolve_book_id("3. 마가복음.pdf") is None

    def test_english_title_with_authors(self):
        assert _resolve_book_id(
            "2 Kings The Anchor Bible Commentary (Mordechai Cogan and Hayim Tadmor).pdf"
        ) == "2KI"
        assert _resolve_book_id(
            "2 Chronicles, Volume 15 (Word Biblical Commentary) (Raymond B. Dillard).pdf"
        ) == "2CH"

    def test_no_match_returns_none(self):
        assert _resolve_book_id("random_notes.pdf") is None


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
