"""Regression: the "원본이 사라진 문서" (orphan) notice on the Library page.

[2026-09-07 UX fix] The old notice put a "정리" button on every row and
called cleanup_orphaned_document() + st.rerun() on click — the success
message was wiped by the immediate rerun and the list kept reappearing, so
a review turned into 70 rapid single clicks (70 documents were excluded
that way). The notice now uses checkboxes + a confirm checkbox + one
"선택 정리" batch action, and a result panel that stays until dismissed.
"""
from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from ui.pages import library


def _fake_orphans():
    return [
        {"document_id": "d1", "source_file": "a.pdf", "chunk_count": 10},
        {"document_id": "d2", "source_file": "b.pdf", "chunk_count": 20},
        {"document_id": "d3", "source_file": "c.pdf", "chunk_count": 5},
    ]


@pytest.fixture
def notice(monkeypatch):
    calls: list[str] = []

    def fake_cleanup(document_id):
        calls.append(document_id)
        return {
            "document_id": document_id,
            "purged_tsu_records": 7,
            "moved_files": ["chunks.txt", "doc.md"],
            "backup_dir": "backups/excluded_documents_X",
            "executed": True,
        }

    monkeypatch.setattr(library, "find_orphaned_processed_documents", _fake_orphans)
    monkeypatch.setattr(library, "cleanup_orphaned_document", fake_cleanup)

    at = AppTest.from_string(
        "from ui.pages.library import _render_orphaned_documents_notice\n"
        "_render_orphaned_documents_notice()\n",
        default_timeout=10,
    )
    at.run()
    return at, calls


# --- pure aggregation helper ---------------------------------------------

def test_run_batch_aggregates_and_captures_errors():
    def cleanup(document_id):
        if document_id == "bad":
            raise RuntimeError("registry locked")
        return {"purged_tsu_records": 3, "moved_files": ["x", "y", "z"]}

    out = library._run_orphan_cleanup_batch(
        [("g1", "g1.pdf"), ("bad", "bad.pdf"), ("g2", "g2.pdf")],
        cleanup_fn=cleanup,
    )
    assert out["count"] == 2
    assert out["purged"] == 6
    assert out["moved"] == 6
    assert out["errors"] == [("bad.pdf", "registry locked")]


# --- notice behaviour ---------------------------------------------------

def test_render_does_not_clean_anything(notice):
    at, calls = notice
    assert calls == []
    assert not at.exception
    # one checkbox per orphan, plus the confirm checkbox
    keys = {cb.key for cb in at.checkbox}
    assert {"orphan_sel_d1", "orphan_sel_d2", "orphan_sel_d3", "orphan_batch_confirm"} <= keys
    # batch button present and disabled with nothing selected
    btn = at.button(key="orphan_batch_cleanup")
    assert btn.disabled


def test_batch_cleans_only_selected_once(notice):
    at, calls = notice
    at.session_state["orphan_sel_d1"] = True
    at.session_state["orphan_sel_d3"] = True
    at.run()
    at.checkbox(key="orphan_batch_confirm").check().run()
    at.button(key="orphan_batch_cleanup").click().run()

    assert calls == ["d1", "d3"]  # selected only, in list order, once each
    assert "_orphan_do_cleanup" not in at.session_state  # deferred action consumed
    assert any("2건 정리 완료" in s.value for s in at.success)
    assert at.button(key="orphan_done_ack")  # dismissable result panel


def test_result_panel_persists_across_reruns_then_dismisses(notice):
    at, calls = notice
    at.session_state["orphan_sel_d2"] = True
    at.run()
    at.checkbox(key="orphan_batch_confirm").check().run()
    at.button(key="orphan_batch_cleanup").click().run()
    assert calls == ["d2"]

    at.run()  # an unrelated rerun must not re-clean or drop the panel
    assert calls == ["d2"]
    assert any("1건 정리 완료" in s.value for s in at.success)

    at.button(key="orphan_done_ack").click().run()
    assert not at.success
    assert "_orphan_cleanup_done" not in at.session_state


def test_select_all_button_checks_every_row(notice):
    at, calls = notice
    at.button(key="orphan_sel_all_on").click().run()
    assert at.session_state["orphan_sel_d1"] is True
    assert at.session_state["orphan_sel_d2"] is True
    assert at.session_state["orphan_sel_d3"] is True
    assert calls == []  # selecting is not cleaning
