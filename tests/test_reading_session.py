"""Regression tests for UX-007 §13 Tier C — core/reading_session.py
(last-read-position persistence, docs/DBMA-UX-007-SessionState-Design.md §3.1)
and its Dashboard "이어서 읽기" card integration.
"""

import importlib
import os

from streamlit.testing.v1 import AppTest

APP_PATH = os.path.join(os.path.dirname(__file__), "..", "ui", "app.py")


def _run_app(session_state: dict | None = None) -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.session_state["show_onboarding"] = False
    for key, value in (session_state or {}).items():
        at.session_state[key] = value
    at.run()
    return at


def test_save_and_load_last_read_roundtrip(tmp_path, monkeypatch):
    import core.reading_session as rs

    monkeypatch.setattr(rs, "_READING_DIR", str(tmp_path / "reading"))
    monkeypatch.setattr(rs, "_LAST_POSITION_FILE", str(tmp_path / "reading" / "last_position.json"))

    assert rs.load_last_read() is None

    rs.save_last_read("doc-1", "로마서 강해", "roma.md")
    loaded = rs.load_last_read()
    assert loaded["document_id"] == "doc-1"
    assert loaded["title"] == "로마서 강해"
    assert loaded["source_label"] == "roma.md"
    assert "read_at" in loaded

    # Overwrite, not append — single latest value.
    rs.save_last_read("doc-2", "요한복음 강해", "yohan.md")
    loaded2 = rs.load_last_read()
    assert loaded2["document_id"] == "doc-2"


def test_save_last_read_noop_when_no_identifiers(tmp_path, monkeypatch):
    import core.reading_session as rs

    monkeypatch.setattr(rs, "_READING_DIR", str(tmp_path / "reading"))
    monkeypatch.setattr(rs, "_LAST_POSITION_FILE", str(tmp_path / "reading" / "last_position.json"))

    rs.save_last_read("", "제목만 있음", "")
    assert rs.load_last_read() is None


def test_dashboard_continue_reading_card_hidden_when_none(monkeypatch):
    monkeypatch.setattr("core.reading_session.load_last_read", lambda: None)
    at = _run_app()
    assert not at.exception
    assert not any("이어서 읽기" in m.value for m in at.markdown)


def test_dashboard_continue_reading_card_shown_and_navigates(monkeypatch):
    monkeypatch.setattr(
        "core.reading_session.load_last_read",
        lambda: {
            "document_id": "doc-1",
            "title": "로마서 강해",
            "source_label": "roma.md",
            "read_at": "2026-08-19T00:00:00",
        },
    )
    at = _run_app()
    assert not at.exception
    assert any("로마서 강해" in m.value for m in at.markdown)

    btn = [b for b in at.button if b.key == "continue_reading_btn"]
    assert len(btn) == 1
    btn[0].click().run()
    assert not at.exception
    assert at.session_state["research_detail_selection"] == {
        "source_file": "roma.md",
        "document_id": "doc-1",
        "query_terms": [],
    }
    assert at.session_state["nav_page"] == "Research"
