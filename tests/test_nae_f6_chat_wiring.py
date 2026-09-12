"""F6 준비(chat.py <-> NAE bridge 배선) 회귀 테스트.

NAE_F4_F5_F6_PREPARATION_DESIGN_v1.md / ADR-024(Approved) 준수 확인:
  - §F: 게이트는 modules.nae_pd.enabled 단일 스위치 — chat.py에 별도
    플래그(NAE_BRIDGE_CHAT_ENABLED 등)를 추가하지 않았음을 소스 검사로 확인.
  - §B: NAE 결과는 채팅 답변 생성(generate_answer/_handle_user_message)에
    섞여 들어가지 않는다 — bridge_query 계열 함수가 그 경로에서 호출되지
    않음을 소스 검사로 확인.
  - disabled(기본값) 상태에서 render_nae_public_section()이 어떤 streamlit
    호출도 하지 않고 즉시 반환함(=DBMA 기본 경로 바이트 무영향)을 확인.
  - ADR-030 Amendment A §6 disclosure 텍스트 매핑.

Ollama/Qdrant 호출 없음 — 전부 mock/소스 검사.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


class TestSingleSwitchCompliance:
    """ADR-024 §F: '이 스위치 하나로 전체 bridge를 끌 수 있어야 한다 —
    별도의 두 번째 스위치를 만들지 않는다'."""

    def test_no_new_flag_introduced_anywhere(self):
        for path in ["ui/pages/chat.py", "ui/components/nae_public_section.py"]:
            src = _read(path)
            assert "NAE_BRIDGE_CHAT" not in src
            assert "NAE_BRIDGE_CHAT_ENABLED" not in src

    def test_chat_gate_is_module_registry_only(self):
        src = _read("ui/components/nae_public_section.py")
        assert 'module_registry.is_enabled("nae_pd")' in src

    def test_chat_py_calls_shared_section_not_a_private_copy(self):
        src = _read("ui/pages/chat.py")
        assert "render_nae_public_section(" in src
        # 별도 사본을 만들지 않았음 — chat.py 안에 자체 _render_nae_section 정의가 없어야 함
        assert "def _render_nae_section(" not in src


class TestNoMergeIntoGeneration:
    """ADR-024 §B: DBMA 결과와 NAE 결과를 같은 답변/랭킹에 병합하지 않는다."""

    def test_generate_answer_does_not_reference_bridge(self):
        import inspect
        import ui.pages.chat as chat

        src = inspect.getsource(chat.generate_answer)
        assert "bridge_query" not in src
        assert "NAE.retrieval_adapter" not in src

    def test_handle_user_message_does_not_reference_bridge(self):
        import inspect
        import ui.pages.chat as chat

        src = inspect.getsource(chat._handle_user_message)
        assert "bridge_query" not in src


class TestDisabledIsNoOp:
    def test_render_makes_no_streamlit_calls_when_disabled(self, monkeypatch):
        import ui.components.nae_public_section as sec
        from core import module_registry

        monkeypatch.setattr(module_registry, "is_enabled", lambda *a, **k: False)
        divider = MagicMock()
        monkeypatch.setattr(sec.st, "divider", divider)
        text_input = MagicMock()
        monkeypatch.setattr(sec.st, "text_input", text_input)

        sec.render_nae_public_section(key_prefix="chat")

        divider.assert_not_called()
        text_input.assert_not_called()


class TestKeyNamespacing:
    """chat/research가 같은 session_state를 밟지 않도록 key_prefix로 분리."""

    def test_query_key_is_prefixed(self, monkeypatch):
        import ui.components.nae_public_section as sec
        from core import module_registry

        monkeypatch.setattr(module_registry, "is_enabled", lambda *a, **k: True)
        monkeypatch.setattr(sec.st, "divider", MagicMock())
        monkeypatch.setattr(sec.st, "markdown", MagicMock())
        monkeypatch.setattr(sec.st, "caption", MagicMock())

        seen_keys = {}

        def fake_text_input(label, placeholder=None, key=None):
            seen_keys["query_key"] = key
            return ""

        monkeypatch.setattr(sec.st, "text_input", fake_text_input)
        monkeypatch.setattr(sec.st, "info", MagicMock())

        sec.render_nae_public_section(key_prefix="chat")
        assert seen_keys["query_key"] == "chat_nae_research_query"

        seen_keys.clear()
        sec.render_nae_public_section(key_prefix="research")
        assert seen_keys["query_key"] == "research_nae_research_query"


class TestDisclosure:
    def test_historical_witness_returns_fuller_text(self):
        from NAE.citation_disclosure import get_disclosure

        text = get_disclosure("historical_witness")
        assert text is not None
        assert "Andrew Fuller" in text
        assert "historical_witness" in text or "historical witness" in text

    def test_other_or_missing_authority_class_returns_none(self):
        from NAE.citation_disclosure import get_disclosure

        assert get_disclosure(None) is None
        assert get_disclosure("verified") is None
        assert get_disclosure("") is None
