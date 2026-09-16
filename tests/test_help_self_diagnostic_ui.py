"""tests/test_help_self_diagnostic_ui.py — 도움말 페이지 자가 진단 UI 회귀.

[S5-3] "자가 진단 실행" 버튼을 누르면 run_self_diagnostic()이 호출되고
결과가 세션 상태에 저장되는지, 버튼을 누르지 않으면 호출되지 않는지
확인한다. 실제 렌더 HTML 검사보다는 상태 전이(호출 여부·저장 위치)에
집중한다 — 스타일은 회귀 대상이 아니다.
"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import ui.pages.help as help_mod
from core.self_diagnostic import DiagnosticResult


def _fake_results():
    return [
        DiagnosticResult("ollama", "Ollama 연결", "정상", "정상 응답"),
        DiagnosticResult("models", "필수 모델", "오류", "누락됨"),
    ]


def test_button_not_clicked_does_not_call_diagnostic(monkeypatch):
    calls = []
    monkeypatch.setattr(help_mod, "run_self_diagnostic", lambda: calls.append(1) or _fake_results())
    monkeypatch.setattr(help_mod.st, "button", lambda *a, **k: False)
    st.session_state.pop("help_diagnostic_results", None)

    help_mod._render_self_diagnostic_section()

    assert calls == []


def test_button_clicked_runs_diagnostic_and_stores_results(monkeypatch):
    calls = []

    def fake_run():
        calls.append(1)
        return _fake_results()

    monkeypatch.setattr(help_mod, "run_self_diagnostic", fake_run)
    monkeypatch.setattr(help_mod.st, "button", lambda *a, **k: True)
    st.session_state.pop("help_diagnostic_results", None)

    help_mod._render_self_diagnostic_section()

    assert calls == [1]
    assert st.session_state["help_diagnostic_results"] == _fake_results()


def test_results_persist_across_reruns_without_button_click(monkeypatch):
    """버튼을 다시 안 눌러도 이전 결과가 세션 상태에 남아 화면에 계속
    표시돼야 한다(Streamlit rerun마다 진단을 다시 돌리지 않음)."""
    calls = []
    monkeypatch.setattr(help_mod, "run_self_diagnostic", lambda: calls.append(1) or _fake_results())
    monkeypatch.setattr(help_mod.st, "button", lambda *a, **k: False)
    st.session_state["help_diagnostic_results"] = _fake_results()

    help_mod._render_self_diagnostic_section()

    assert calls == []  # 재실행 안 됨
    assert st.session_state["help_diagnostic_results"] == _fake_results()  # 이전 결과 유지
