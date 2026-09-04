"""Regression test — core/sermon/bible_books.py canonical 66-book list
(2026-07-21, Sermon Draft book picker).

A separate, correct canonical list from core/query_enhancements.py's
_KOREAN_FULL_NAMES (which has 2 pre-existing typos — "예레미애" instead of
"애가"/Lamentations and "스게론" instead of "스가랴"/Zechariah — out of
scope to fix here, but not to be propagated into a new user-facing
66-button display).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.sermon.bible_books import BIBLE_BOOKS


def test_exactly_66_books():
    assert len(BIBLE_BOOKS) == 66


def test_no_duplicate_names_or_ids():
    names = [name for name, _ in BIBLE_BOOKS]
    ids = [book_id for _, book_id in BIBLE_BOOKS]
    assert len(names) == len(set(names))
    assert len(ids) == len(set(ids))


def test_first_and_last_book_in_canonical_order():
    assert BIBLE_BOOKS[0] == ("창세기", "GEN")
    assert BIBLE_BOOKS[-1] == ("요한계시록", "REV")


def test_known_typo_prone_books_are_correct():
    """The two names known to be wrong in query_enhancements.py's alias
    table — verify this canonical list does not repeat those mistakes."""
    names_by_id = {book_id: name for name, book_id in BIBLE_BOOKS}
    assert names_by_id["LAM"] == "애가"
    assert names_by_id["ZEC"] == "스가랴"


def test_old_and_new_testament_split_is_39_27():
    ot_ids = {"GEN", "EXO", "LEV", "NUM", "DEU", "JOS", "JDG", "RUT", "1SA", "2SA",
              "1KI", "2KI", "1CH", "2CH", "EZR", "NEH", "EST", "JOB", "PSA", "PRO",
              "ECC", "SOT", "ISA", "JER", "LAM", "EZE", "DAN", "HOS", "JOEL", "AMOS",
              "OBA", "JON", "MIC", "NAM", "HAB", "ZEP", "HAG", "ZEC", "MAL"}
    ids = {book_id for _, book_id in BIBLE_BOOKS}
    assert len(ot_ids & ids) == 39
    assert len(ids - ot_ids) == 27


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
