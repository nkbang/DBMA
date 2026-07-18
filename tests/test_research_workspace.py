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


def test_create_session_no_collision_within_same_second(monkeypatch):
    """SPRINT27-E — same-second calls must not produce the same session_id
    (ADR-005 §2: timestamp+uuid4 suffix)."""

    class _FrozenDatetime(rw.datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 7, 18, 12, 0, 0)

    monkeypatch.setattr(rw.datetime, "datetime", _FrozenDatetime)

    a = rw.create_session()
    b = rw.create_session()
    assert a != b
    assert a.startswith("2026-07-18T12:00:00-")
    assert b.startswith("2026-07-18T12:00:00-")


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


def test_missing_file_defaults_to_current_schema_version(tmp_path, monkeypatch):
    monkeypatch.setattr(rw, "DEFAULT_OUTPUT_DIR", str(tmp_path))
    data = rw.load_sessions()
    assert data["schema_version"] == rw.SCHEMA_VERSION


def test_saved_file_includes_schema_version(tmp_path, monkeypatch):
    monkeypatch.setattr(rw, "DEFAULT_OUTPUT_DIR", str(tmp_path))
    session_id = rw.create_session()
    rw.add_query_result(session_id, "q", {"top_k_results": []})

    import json
    path = rw._sessions_path()
    with open(path, "r", encoding="utf-8") as f:
        on_disk = json.load(f)
    assert on_disk["schema_version"] == rw.SCHEMA_VERSION


def test_legacy_file_without_schema_version_loads(tmp_path, monkeypatch):
    """SPRINT27-E — a sessions.json shaped like the pre-ADR-005 production
    file (no schema_version key) must load without error and be treated
    as version 1 (ADR-005 §4/§5 additive migration, read-time only)."""
    monkeypatch.setattr(rw, "DEFAULT_OUTPUT_DIR", str(tmp_path))
    research_dir = tmp_path / "research"
    research_dir.mkdir()
    legacy_payload = {
        "sessions": [
            {
                "session_id": "2026-07-18T01:47:35",
                "created_at": "2026-07-18T01:47:35",
                "queries": [
                    {
                        "query": "test query",
                        "timestamp": "2026-07-18T01:47:35",
                        "result_refs": [{"tsu_id": "test123", "document_id": "doc456"}],
                    }
                ],
            }
        ]
    }
    import json
    (research_dir / "sessions.json").write_text(
        json.dumps(legacy_payload, ensure_ascii=False), encoding="utf-8"
    )

    data = rw.load_sessions()
    assert data["schema_version"] == rw.SCHEMA_VERSION
    assert len(data["sessions"]) == 1

    sessions = rw.list_sessions()
    assert sessions[0]["session_id"] == "2026-07-18T01:47:35"

    session = rw.load_session("2026-07-18T01:47:35")
    assert session is not None
    assert session["queries"][0]["query"] == "test query"
