"""Regression test — ui/pages/research.py session lifecycle (SPRINT27-E).
Verifies one research session_id persists across multiple "세션에 저장"
clicks within the same st.session_state (ADR-005 §1) instead of minting a
new session per save, using a monkeypatched st + a real
core/research_workspace.py-backed sessions.json (isolated tmp_path).
"""

import sys
import os
from contextlib import contextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import core.research_workspace as rw


class _Recorder:
    def __init__(self, session_state=None, button_return=True):
        self.session_state = session_state if session_state is not None else {}
        self._button_return = button_return
        self.success_calls = []
        self.error_calls = []
        self.warning_calls = []

    def divider(self):
        pass

    def subheader(self, msg):
        pass

    def caption(self, msg):
        pass

    def success(self, msg):
        self.success_calls.append(msg)

    def error(self, msg):
        self.error_calls.append(msg)

    def warning(self, msg):
        self.warning_calls.append(msg)

    def info(self, msg):
        pass

    def selectbox(self, label, options=None, key=None, **kw):
        options = options or []
        return options[0] if options else None

    def button(self, label, key=None, **kw):
        return self._button_return

    def columns(self, spec):
        n = len(spec) if hasattr(spec, "__len__") else spec
        return [_NullCtx() for _ in range(n)]

    def table(self, data):
        pass

    @contextmanager
    def expander(self, label):
        yield None


class _NullCtx:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeResponse:
    def __init__(self, top_k_results, citations=None):
        self._top_k_results = top_k_results
        self._citations = citations or []

    def to_dict(self):
        return {"top_k_results": self._top_k_results, "citations": self._citations}


def _seed_mod(tmp_path, monkeypatch):
    monkeypatch.setattr(rw, "DEFAULT_OUTPUT_DIR", str(tmp_path))
    import ui.pages.research as mod
    monkeypatch.setattr(mod, "add_query_result", rw.add_query_result)
    monkeypatch.setattr(mod, "search_results_table", lambda **kw: None)
    return mod


def test_session_id_persists_across_renders_and_saves(tmp_path, monkeypatch):
    mod = _seed_mod(tmp_path, monkeypatch)

    session_state = {}
    rec = _Recorder(session_state=session_state)
    monkeypatch.setattr(mod, "st", rec)

    # First page render — session_id is created once.
    if "research_session_id" not in session_state:
        session_state["research_session_id"] = rw.create_session()
    first_session_id = session_state["research_session_id"]

    # First save.
    session_state["research_results"] = [{"title": "a"}]
    session_state["research_query"] = "q1"
    session_state["research_response"] = _FakeResponse([{"tsu_id": "T1"}])
    mod._render_search_results()

    # Simulate a second render pass (Streamlit rerun) — session_id must be
    # reused, not recreated, since it's already in session_state.
    if "research_session_id" not in session_state:
        session_state["research_session_id"] = rw.create_session()
    assert session_state["research_session_id"] == first_session_id

    # Second save, different query.
    session_state["research_query"] = "q2"
    session_state["research_response"] = _FakeResponse([{"tsu_id": "T2"}])
    mod._render_search_results()

    save_confirmations = [m for m in rec.success_calls if m.startswith("세션 저장 완료")]
    assert len(save_confirmations) == 2

    session = rw.load_session(first_session_id)
    assert session is not None
    assert [q["query"] for q in session["queries"]] == ["q1", "q2"]
