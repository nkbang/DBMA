"""Regression tests for UX-007 §13 Tier A/B session state work.

Covers:
- Dashboard "최근 검색" card (Tier A, core/research_workspace.py read-only)
- Sermon Research Hub end-to-end flow (Tier B): search result ->
  "설교 연구에 추가" -> hub absorbs into sermon_research_state ->
  notes/outline editable -> "설교 작성으로 이어가기" navigates.
- §7 어댑터: sermon_research_state -> sermon_draft_state 프리필,
  진행 중인 초안은 덮어쓰지 않음.

Design reference: docs/DBMA-UX-007-SessionState-Design.md
"""

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


def test_sidebar_has_sermon_research_menu_item():
    at = _run_app()
    at.sidebar.radio[0].set_value("설교 연구").run()
    assert not at.exception


def test_sermon_research_hub_empty_state():
    at = _run_app()
    at.sidebar.radio[0].set_value("설교 연구").run()
    assert not at.exception
    texts = [m.value for m in at.markdown] + [m.value for m in at.info]
    assert any("아직 담긴 자료가 없습니다" in t for t in texts)


def test_send_to_sermon_research_from_search_result():
    at = _run_app({
        "research_results": [{
            "tsu_id": "res-1",
            "title": "테스트 결과",
            "snippet": "발췌문",
            "source": "출처.md",
            "score": 0.8,
            "document_id": "doc-x",
            "source_file": "출처.md",
        }],
    })
    at.sidebar.radio[0].set_value("Research").run()
    assert not at.exception

    send_buttons = [b for b in at.button if b.key and b.key.startswith("send_sermon_")]
    assert len(send_buttons) == 1
    send_buttons[0].click().run()
    assert not at.exception
    assert at.session_state["sermon_research_selection"][0]["tsu_id"] == "res-1"


def test_hub_absorbs_selection_buffer_and_dedupes():
    at = _run_app({
        "sermon_research_selection": [{
            "tsu_id": "t1",
            "document_id": "d1",
            "excerpt": "e1",
            "source_label": "s1.md",
            "added_at": "2026-08-19T00:00:00",
        }],
    })
    at.sidebar.radio[0].set_value("설교 연구").run()
    assert not at.exception
    assert at.session_state["sermon_research_state"]["materials"][0]["tsu_id"] == "t1"
    assert at.session_state["sermon_research_selection"] == []


def test_hub_outline_and_continue_button_navigates_to_sermon_draft():
    at = _run_app({
        "sermon_research_state": {
            "status": "collecting",
            "materials": [{
                "tsu_id": "t1", "document_id": "d1",
                "excerpt": "e1", "source_label": "s1.md", "added_at": "x",
            }],
            "notes": {},
            "outline_draft": [],
        },
    })
    at.sidebar.radio[0].set_value("설교 연구").run()
    assert not at.exception

    outline_widgets = [ta for ta in at.text_area if ta.key == "sermon_outline_draft_input"]
    assert len(outline_widgets) == 1
    outline_widgets[0].set_value("1. 본문 소개\n2. 적용").run()
    assert at.session_state["sermon_research_state"]["outline_draft"] == ["1. 본문 소개", "2. 적용"]

    continue_buttons = [b for b in at.button if b.label == "설교 작성으로 이어가기"]
    assert len(continue_buttons) == 1
    continue_buttons[0].click().run()
    assert not at.exception
    assert at.session_state["nav_page"] == "설교문 작성"


def test_hub_remove_material():
    at = _run_app({
        "sermon_research_state": {
            "status": "collecting",
            "materials": [{
                "tsu_id": "t1", "document_id": "d1",
                "excerpt": "e1", "source_label": "s1.md", "added_at": "x",
            }],
            "notes": {},
            "outline_draft": [],
        },
    })
    at.sidebar.radio[0].set_value("설교 연구").run()
    remove_buttons = [b for b in at.button if b.key and b.key.startswith("sermon_remove_")]
    assert len(remove_buttons) == 1
    remove_buttons[0].click().run()
    assert not at.exception
    assert at.session_state["sermon_research_state"]["materials"] == []


def test_dashboard_recent_search_card_hidden_when_no_sessions(monkeypatch):
    monkeypatch.setattr(
        "core.research_workspace.list_sessions",
        lambda: [],
    )
    at = _run_app()
    assert not at.exception
    assert not any("최근 검색" in m.value for m in at.markdown)


def _hub_state(materials=None, notes=None, outline=None) -> dict:
    return {
        "status": "collecting",
        "materials": materials or [{
            "tsu_id": "t1", "document_id": "d1",
            "excerpt": "발췌문", "source_label": "로마서 주석.md", "added_at": "x",
        }],
        "notes": notes or {"t1": "이 부분 중요"},
        "outline_draft": outline if outline is not None else ["본문 소개", "적용"],
    }


def test_adapter_seeds_empty_sermon_draft_state():
    at = _run_app({"sermon_research_state": _hub_state()})
    at.sidebar.radio[0].set_value("설교 연구").run()
    btn = [b for b in at.button if b.label == "설교 작성으로 이어가기"]
    assert len(btn) == 1
    btn[0].click().run()
    assert not at.exception

    seeded = at.session_state["sermon_draft_state"]
    assert "로마서 주석.md" in seeded["scripture_and_theme"]
    assert "발췌문" in seeded["scripture_and_theme"]
    assert "이 부분 중요" in seeded["scripture_and_theme"]
    assert "본문 소개" in seeded["scripture_and_theme"]
    assert seeded["status"] == "input"
    assert seeded["style_files"] == []  # no shared_query_processor in this session
    assert at.session_state["sermon_input_text"] == seeded["scripture_and_theme"]
    assert at.session_state["nav_page"] == "설교문 작성"


def test_adapter_does_not_overwrite_in_progress_draft():
    from core.generation import SermonOutline

    existing = {
        "status": "outline_generated",
        "scripture_and_theme": "사용자가 이미 입력한 본문",
        "style_files": [],
        "sermon_format": "주제설교",
        "outline": SermonOutline(title="t", introduction="i", points=["p1"], conclusion="c"),
        "candidates": [],
        "expanded": {},
    }
    at = _run_app({
        "sermon_research_state": _hub_state(),
        "sermon_draft_state": dict(existing),
    })
    at.sidebar.radio[0].set_value("설교 연구").run()
    btn = [b for b in at.button if b.label == "설교 작성으로 이어가기"]
    btn[0].click().run()
    assert not at.exception
    assert at.session_state["sermon_draft_state"]["scripture_and_theme"] == "사용자가 이미 입력한 본문"
    assert at.session_state["sermon_draft_state"]["status"] == "outline_generated"


def test_adapter_does_not_overwrite_manually_typed_theme():
    existing = {
        "status": "input",
        "scripture_and_theme": "사용자가 직접 입력한 주제",
        "style_files": [],
        "sermon_format": "주제설교",
        "outline": None,
        "candidates": [],
        "expanded": {},
    }
    at = _run_app({
        "sermon_research_state": _hub_state(),
        "sermon_draft_state": dict(existing),
    })
    at.sidebar.radio[0].set_value("설교 연구").run()
    btn = [b for b in at.button if b.label == "설교 작성으로 이어가기"]
    btn[0].click().run()
    assert not at.exception
    assert at.session_state["sermon_draft_state"]["scripture_and_theme"] == "사용자가 직접 입력한 주제"


def test_adapter_matches_style_files_when_processor_already_loaded():
    class _FakeEngine:
        def list_source_files(self):
            return ["로마서 주석.md", "다른 자료.md"]

    class _FakeProcessor:
        engine = _FakeEngine()

    at = _run_app({
        "sermon_research_state": _hub_state(),
        "shared_query_processor": _FakeProcessor(),
    })
    at.sidebar.radio[0].set_value("설교 연구").run()
    btn = [b for b in at.button if b.label == "설교 작성으로 이어가기"]
    btn[0].click().run()
    assert not at.exception
    assert at.session_state["sermon_draft_state"]["style_files"] == ["로마서 주석.md"]


def test_dashboard_recent_search_card_shows_latest_query(monkeypatch):
    monkeypatch.setattr(
        "core.research_workspace.list_sessions",
        lambda: [{
            "session_id": "s1",
            "created_at": "2026-08-19T00:00:00",
            "queries": [
                {"query": "로마서 8장 주제", "timestamp": "2026-08-19T00:00:00", "result_refs": []},
            ],
        }],
    )
    at = _run_app()
    assert not at.exception
    assert any("로마서 8장 주제" in m.value for m in at.markdown)
