"""Regression test — ui/pages/research.py::_render_saved_sessions() (SPRINT27-C).
Verifies the read-only session list/load panel against a real
core/research_workspace.py-backed sessions.json (isolated tmp_path), without
a live Streamlit runtime — st.* calls are monkeypatched to no-ops/recorders.
No retrieval call is made; list_sessions()/load_session() are used as-is.
"""

import sys
import os
from contextlib import contextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import core.research_workspace as rw


class _Recorder:
    def __init__(self, selectbox_return=None, button_return=False):
        self.caption_calls = []
        self.subheader_calls = []
        self.table_calls = []
        self.success_calls = []
        self.divider_calls = 0
        self._selectbox_return = selectbox_return
        self._button_return = button_return
        self.session_state = {}

    def divider(self):
        self.divider_calls += 1

    def subheader(self, msg):
        self.subheader_calls.append(msg)

    def caption(self, msg):
        self.caption_calls.append(msg)

    def table(self, data):
        self.table_calls.append(data)

    def success(self, msg):
        self.success_calls.append(msg)

    def selectbox(self, label, options=None, key=None, **kw):
        options = options or []
        return self._selectbox_return if self._selectbox_return is not None else (options[0] if options else None)

    def button(self, label, key=None, **kw):
        return self._button_return

    @contextmanager
    def expander(self, label):
        yield None


def _seed(tmp_path, monkeypatch):
    monkeypatch.setattr(rw, "DEFAULT_OUTPUT_DIR", str(tmp_path))
    import ui.pages.research as mod
    monkeypatch.setattr(mod, "list_sessions", rw.list_sessions)
    monkeypatch.setattr(mod, "load_session", rw.load_session)
    return mod


def test_empty_state_shows_caption(tmp_path, monkeypatch):
    mod = _seed(tmp_path, monkeypatch)
    rec = _Recorder()
    monkeypatch.setattr(mod, "st", rec)

    mod._render_saved_sessions()

    assert rec.caption_calls == ["저장된 세션이 없습니다."]
    assert rec.table_calls == []


def test_lists_and_loads_session_with_result_refs(tmp_path, monkeypatch):
    mod = _seed(tmp_path, monkeypatch)
    session_id = rw.create_session()
    rw.add_query_result(
        session_id,
        "창조 기사",
        {
            "top_k_results": [{"tsu_id": "TSU-GEN-000001", "metadata": {"document_id": "doc1"}}],
            "citations": [{"citation_id": "CIT-1", "tsu_id": "TSU-GEN-000001"}],
        },
    )

    label = f"{rw.load_session(session_id)['created_at']} · 검색 1건"
    rec = _Recorder(selectbox_return=label)
    monkeypatch.setattr(mod, "st", rec)

    mod._render_saved_sessions()

    assert rec.subheader_calls == ["저장된 세션"]
    assert len(rec.table_calls) == 1
    assert rec.table_calls[0] == [
        {"tsu_id": "TSU-GEN-000001", "document_id": "doc1", "citation_id": "CIT-1"}
    ]


def test_load_query_button_fills_query_into_session_state(tmp_path, monkeypatch):
    mod = _seed(tmp_path, monkeypatch)
    session_id = rw.create_session()
    rw.add_query_result(session_id, "은혜란 무엇인가", {"top_k_results": []})

    label = f"{rw.load_session(session_id)['created_at']} · 검색 1건"
    rec = _Recorder(selectbox_return=label, button_return=True)
    monkeypatch.setattr(mod, "st", rec)

    mod._render_saved_sessions()

    assert rec.session_state.get("research_query") == "은혜란 무엇인가"
    assert rec.success_calls
