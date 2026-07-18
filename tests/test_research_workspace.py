"""Regression test — core/research_workspace.py (SPRINT27-B-3).
Verifies session create/save/load/list against an isolated output dir,
and confirms result_refs are correctly extracted from ResponsePackage.to_dict()
(top_k_results key, not "results" — SPRINT27-B-3 CI fix).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.research_workspace as rw


def test_create_session_returns_unique_id():
    a = rw.create_session()
    b = rw.create_session()
    assert isinstance(a, str) and a
    assert isinstance(b, str) and b


def test_add_query_result_creates_and_persists_session(tmp_path, monkeypatch):
    monkeypatch.setattr(rw, "DEFAULT_OUTPUT_DIR", str(tmp_path))
    session_id = rw.create_session()
    response_package = {
        "top_k_results": [
            {"tsu_id": "TSU-GEN-000001", "metadata": {"document_id": "doc123"}},
            {"tsu_id": "TSU-GEN-000002", "metadata": {"document_id": "doc123"}},
        ],
        "citations": [
            {"citation_id": "CIT-1", "tsu_id": "TSU-GEN-000001"},
        ],
    }

    ok = rw.add_query_result(session_id, "창조 기사", response_package)
    assert ok is True

    session = rw.load_session(session_id)
    assert session is not None
    assert session["session_id"] == session_id
    assert len(session["queries"]) == 1
    assert session["queries"][0]["query"] == "창조 기사"
    assert session["queries"][0]["result_refs"] == [
        {"tsu_id": "TSU-GEN-000001", "document_id": "doc123", "citation_id": "CIT-1"},
        {"tsu_id": "TSU-GEN-000002", "document_id": "doc123"},
    ]


def test_add_query_result_appends_to_existing_session(tmp_path, monkeypatch):
    monkeypatch.setattr(rw, "DEFAULT_OUTPUT_DIR", str(tmp_path))
    session_id = rw.create_session()
    rw.add_query_result(session_id, "q1", {"top_k_results": [{"tsu_id": "T1"}]})
    rw.add_query_result(session_id, "q2", {"top_k_results": [{"tsu_id": "T2"}]})

    session = rw.load_session(session_id)
    assert len(session["queries"]) == 2
    assert [q["query"] for q in session["queries"]] == ["q1", "q2"]


def test_load_session_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(rw, "DEFAULT_OUTPUT_DIR", str(tmp_path))
    assert rw.load_session("nonexistent") is None


def test_list_sessions_returns_all(tmp_path, monkeypatch):
    monkeypatch.setattr(rw, "DEFAULT_OUTPUT_DIR", str(tmp_path))
    s1 = rw.create_session()
    s2 = rw.create_session()
    rw.add_query_result(s1, "q", {"top_k_results": []})
    rw.add_query_result(s2, "q", {"top_k_results": []})

    sessions = rw.list_sessions()
    ids = {s["session_id"] for s in sessions}
    assert ids == {s1, s2}
