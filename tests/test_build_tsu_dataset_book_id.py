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
  4. (CUE-RECONCILIATION-010) Short (2-4 char) alias substring collisions
     inside unrelated longer words — the 3-char alias "sol" (Song of
     Solomon) matched as a raw substring of "SOLAS시리즈" (a Reformation
     systematic theology series, unrelated to Scripture) in filenames like
     "5 SOLAS시리즈01 [...] 오직 믿음.pdf", silently mistagging 10 real
     registry documents as book_id=SOL. Fixed via a letter-only boundary
     lookaround (digits are still allowed to flank a match, since this
     corpus routinely appends a chapter/volume number directly after the
     book name with no separator, e.g. "사도행전1.pdf" — a plain \\b word
     boundary would incorrectly reject that case too, since Python's \\w
     treats digits and letters alike).
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

    def test_solas_series_does_not_falsely_resolve_to_song_of_solomon(self):
        """'sol' (Song of Solomon alias) must not substring-match inside
        'SOLAS시리즈' (Reformation systematic theology series title) —
        the false positive found and fixed in CUE-RECONCILIATION-010."""
        assert _resolve_book_id(
            "5 SOLAS시리즈01 [토머스슈라이너] 오직 믿음.pdf.pdf"
        ) is None

    def test_book_name_immediately_followed_by_digit_still_resolves(self):
        """Book name + volume/chapter digit with no separator (this corpus's
        actual naming convention) must still resolve — a plain \\b word
        boundary would reject this because \\w treats digits and letters
        alike; the fix uses a letter-only boundary so a following digit is
        allowed while a following letter (e.g. "solAS") is not."""
        assert _resolve_book_id("7. 사도행전1.pdf") == "ACT"
        assert _resolve_book_id("8. 사도행전2.pdf") == "ACT"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
