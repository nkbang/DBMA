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


def _doc(t, n):
    return {"path": f"p/{n}", "title": n, "type": t, "size": "1 KB", "modified": "d"}


def test_group_by_type_biggest_first_and_order_preserved():
    docs = [_doc("TXT", "a"), _doc("PDF", "b"), _doc("PDF", "c"), _doc("EPUB", "d")]
    groups = library._group_by_type(docs)
    assert [g[0] for g in groups] == ["PDF", "EPUB", "TXT"]  # size desc, then name
    assert [d["title"] for d in groups[0][1]] == ["b", "c"]


def test_grouped_view_previews_then_shows_more(monkeypatch):
    seen = {"labels": [], "buttons": []}

    class _Ctx:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    class _St:
        session_state = {}

        def container(self, **kw): return _Ctx()

        def expander(self, label, expanded=False):
            seen["labels"].append((label, expanded))
            return _Ctx()

        def button(self, label, **kw):
            seen["buttons"].append(label)

    monkeypatch.setattr(library, "st", _St())
    docs = [_doc("PDF", f"p{i}") for i in range(13)] + [_doc("TXT", "t")]
    library._render_grouped_documents(docs)

    assert seen["labels"] == [("PDF (13)", True), ("TXT (1)", False)]
    row_btns = [b for b in seen["buttons"] if " · " in b]
    assert len(row_btns) == library._GROUP_PREVIEW + 1  # 10 PDF + 1 TXT
    assert "더 보기 (3)" in seen["buttons"]
