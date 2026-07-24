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


class _FakeCandidate:
    def __init__(self, final_score):
        self.final_score = final_score


class TestLowConfidenceWarning:
    """[2026-07-24] Soft, provisional relevance-floor warning — see
    _LOW_CONFIDENCE_SCORE_THRESHOLD docstring. Never blocks/alters the
    answer, only adds a caption."""

    def test_empty_results_is_low_confidence(self):
        import ui.pages.chat as mod
        assert mod._is_low_confidence([]) is True

    def test_score_below_threshold_is_low_confidence(self):
        import ui.pages.chat as mod
        assert mod._is_low_confidence([_FakeCandidate(0.40)]) is True

    def test_score_at_or_above_threshold_is_not_low_confidence(self):
        import ui.pages.chat as mod
        assert mod._is_low_confidence([_FakeCandidate(0.45)]) is False
        assert mod._is_low_confidence([_FakeCandidate(0.51)]) is False

    def test_only_top_result_score_matters(self):
        import ui.pages.chat as mod
        # top_k_results[0] is the ranking-sorted best match; a weak second
        # result must not flip a genuinely strong top match to "low".
        assert mod._is_low_confidence([_FakeCandidate(0.51), _FakeCandidate(0.10)]) is False
