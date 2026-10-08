"""Regression test — ui/pages/library.py compact one-line document rows."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ui.pages import library


def test_row_label_is_single_line_with_all_fields():
    label = library._format_row_label(
        {"type": "PDF", "title": "a.pdf", "size": "1.0 KB", "modified": "2026-10-08"}
    )
    assert label == "PDF · a.pdf · 1.0 KB · 2026-10-08"
    assert "\n" not in label


def test_row_label_tolerates_missing_fields():
    assert library._format_row_label({"title": "x"}) == "? · x · ? · ?"


def test_rows_render_one_button_per_doc_in_fixed_height_box(monkeypatch):
    calls = {"buttons": [], "container": None}

    class _Ctx:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    class _St:
        session_state = {"_library_selected_path": "p/b"}

        def container(self, **kw):
            calls["container"] = kw
            return _Ctx()

        def button(self, label, **kw):
            calls["buttons"].append((label, kw))

    monkeypatch.setattr(library, "st", _St())
    docs = [
        {"path": "p/a", "title": "a", "type": "PDF", "size": "1 KB", "modified": "d"},
        {"path": "p/b", "title": "b", "type": "TXT", "size": "2 KB", "modified": "d"},
    ]
    library._render_document_rows(docs)

    assert calls["container"]["height"] == library._LIST_HEIGHT_PX
    assert len(calls["buttons"]) == 2
    assert calls["buttons"][0][1]["type"] == "secondary"
    assert calls["buttons"][1][1]["type"] == "primary"
    assert calls["buttons"][1][1]["key"].startswith("lib_row_")
