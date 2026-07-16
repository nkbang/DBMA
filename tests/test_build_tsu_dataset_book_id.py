"""Regression test — TSU book_id resolution (SPRINT17-Phase6A-1).

build_tsu_records() previously tagged every TSU record "GEN" regardless
of actual document content (Dataset Quality Audit finding). This test
guards _resolve_book_id() against the regressions found while fixing it:
  1. NFC/NFD Unicode mismatch silently failing all Korean filename matches.
  2. Single-character alias false positives (a raw substring match would
     resolve any "마"-containing filename to MAT).
  3. (Follow-up) "마가복음" (Mark) originally had no matching alias at all
     in core.retrieval.NAME_TO_BOOK_ID — only "마르코복음" was listed —
     so real Mark documents fell back to "UNK". "마가복음"/"마가" were
     added as MRK aliases; this must resolve to MRK now, not None and
     not MAT.
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

    def test_mark_resolves_correctly_not_matthew(self):
        """'마가복음' (Mark) must resolve to MRK, not fall through to the
        single-char MAT alias '마' (the original false-positive bug) and
        not fall back to None (the subsequent missing-alias gap)."""
        assert _resolve_book_id("3. 마가복음.pdf") == "MRK"

    def test_single_char_alias_alone_does_not_match(self):
        """A filename containing only a single-character alias substring
        (with no real 2+ char book name present) must not resolve —
        single-char aliases are excluded from filename matching entirely."""
        assert _resolve_book_id("마제문서.pdf") is None  # contains "마" only

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
