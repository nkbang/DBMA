"""Regression test — ui/pages/library.py column-header sort."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ui.pages import library

DOCS = [
    {"title": "b.pdf", "type": "PDF", "_mtime_epoch": 2, "_size_bytes": 10},
    {"title": "A.epub", "type": "EPUB", "_mtime_epoch": 3, "_size_bytes": 5},
    {"title": "c.docx", "type": "DOCX", "_mtime_epoch": 1, "_size_bytes": 20},
]


def _titles(by, desc=None):
    return [d["title"] for d in library._sort_documents(list(DOCS), by, desc)]


def test_default_directions():
    assert _titles("name") == ["A.epub", "b.pdf", "c.docx"]  # case-insensitive asc
    assert _titles("date") == ["A.epub", "b.pdf", "c.docx"]  # newest first
    assert _titles("size") == ["c.docx", "b.pdf", "A.epub"]  # largest first
    assert _titles("type") == ["c.docx", "A.epub", "b.pdf"]  # DOCX, EPUB, PDF


def test_explicit_direction_overrides_default():
    assert _titles("name", True) == ["c.docx", "b.pdf", "A.epub"]
    assert _titles("size", False) == ["A.epub", "b.pdf", "c.docx"]


def test_unknown_key_falls_back_to_name():
    assert _titles("bogus") == _titles("name")


def test_header_click_toggles_same_column_and_resets_new_column():
    assert library._next_sort_state("name", None, "name") == ("name", True)
    assert library._next_sort_state("name", True, "name") == ("name", False)
    assert library._next_sort_state("date", None, "date") == ("date", False)
    assert library._next_sort_state("name", True, "size") == ("size", True)
    assert library._next_sort_state("size", False, "name") == ("name", False)
