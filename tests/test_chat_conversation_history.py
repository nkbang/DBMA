"""Regression test — ui/pages/chat.py::_build_conversation_history()
(2026-07-24, "Plan B" session-scoped continuity). Verifies it reads
chat_messages correctly (window size, truncation, empty state) without a
live Streamlit runtime — st.session_state is monkeypatched to a plain dict.
"""

import sys
import os
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

if "ollama" not in sys.modules:
    _ollama_stub = types.ModuleType("ollama")
    _ollama_stub.generate = lambda *a, **k: {"response": ""}
    sys.modules["ollama"] = _ollama_stub


class _FakeSessionState(dict):
    pass


class _FakeSt:
    def __init__(self):
        self.session_state = _FakeSessionState()


def _msg(role, content):
    return {"role": role, "content": content}


def test_empty_history_returns_empty_string(monkeypatch):
    import ui.pages.chat as mod
    fake_st = _FakeSt()
    fake_st.session_state["chat_messages"] = []
    monkeypatch.setattr(mod, "st", fake_st)

    assert mod._build_conversation_history() == ""


def test_formats_recent_turns_with_role_labels(monkeypatch):
    import ui.pages.chat as mod
    fake_st = _FakeSt()
    fake_st.session_state["chat_messages"] = [
        _msg("user", "질문1"),
        _msg("assistant", "답변1"),
    ]
    monkeypatch.setattr(mod, "st", fake_st)

    result = mod._build_conversation_history()
    assert result == "사용자: 질문1\n어시스턴트: 답변1"


def test_only_last_n_turns_are_kept(monkeypatch):
    import ui.pages.chat as mod
    fake_st = _FakeSt()
    messages = []
    for i in range(10):
        messages.append(_msg("user", f"질문{i}"))
        messages.append(_msg("assistant", f"답변{i}"))
    fake_st.session_state["chat_messages"] = messages
    monkeypatch.setattr(mod, "st", fake_st)

    result = mod._build_conversation_history()
    # _HISTORY_MAX_TURNS=3 -> last 6 messages (turns 7,8,9)
    assert "질문7" in result
    assert "질문9" in result
    assert "질문0" not in result


def test_long_message_is_truncated(monkeypatch):
    import ui.pages.chat as mod
    fake_st = _FakeSt()
    long_text = "x" * 1000
    fake_st.session_state["chat_messages"] = [_msg("user", long_text)]
    monkeypatch.setattr(mod, "st", fake_st)

    result = mod._build_conversation_history()
    assert len(result) < 400
