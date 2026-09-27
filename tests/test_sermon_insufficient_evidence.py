"""Regression test — ui/pages/sermon_draft.py 자료 0건 시 설교 생성 차단.

[B-1, 배포 차단 항목 — docs/NAE_FREE_DISTRIBUTION_PLAN_v1.md §6 /
docs/DBMA_RELEASE_GAP_CLOSURE_PIPELINE_v1.md S1-1] 검색 결과가 0건이면
SermonDraftService.generate_outline() / expand_point()를 호출하지 않는다.
근거 없이 LLM이 설교 원고를 지어내면 목회자가 그것을 강단에서 그대로 쓸 수
있어 피해가 되돌릴 수 없다 — tests/test_sermon_no_fabricated_illustration.py
(§5.1 예화 생성 금지)와 같은 계열의 안전장치다.

기준은 ui/pages/chat.py의 P0-6 유보응답(tests/test_chat_evidence_hold.py)과
동일하게 "검색 결과 0건"을 하드 게이트로 쓴다 — 결과는 있으나 점수만 낮은
경우는 이 테스트의 범위가 아니다(막지 않는다).

Streamlit 런타임 없이 검증 — _get_processor / _get_service를 monkeypatch한다.
"""

import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import ollama  # noqa: F401
except ImportError:
    if "ollama" not in sys.modules:
        _ollama_stub = types.ModuleType("ollama")
        _ollama_stub.generate = lambda *a, **k: {"response": ""}
        _ollama_stub.embeddings = lambda *a, **k: {"embedding": []}
        sys.modules["ollama"] = _ollama_stub

import streamlit as st

import ui.pages.sermon_draft as mod
from core.generation import SermonOutline


class _FakeResponse:
    def __init__(self, top_k_results):
        self.top_k_results = top_k_results


class _FakeProcessor:
    def __init__(self, top_k_results):
        self._top_k = top_k_results
        self.calls = 0

    def process(self, *a, **k):
        self.calls += 1
        return _FakeResponse(self._top_k)


class _FakeService:
    """generate_outline/expand_point 호출 여부만 센다 — 실제로 호출되면
    곧 Ollama가 호출된다는 뜻이므로, 이 카운터가 0이면 Ollama도 0회다."""

    def __init__(self):
        self.outline_calls = 0
        self.expand_calls = 0

    def generate_outline(self, *a, **k):
        self.outline_calls += 1
        return SermonOutline(title="제목", introduction="서론", points=["대지1"]), None

    def expand_point(self, *a, **k):
        self.expand_calls += 1
        return "확장된 본문", None


def _fresh_state(**overrides) -> dict:
    from core.generation import SERMON_FORMATS

    state = {
        "status": "input",
        "scripture_and_theme": "",
        "style_files": [],
        "sermon_format": SERMON_FORMATS[0],
        "outline": None,
        "candidates": [],
        "expanded": {},
    }
    state.update(overrides)
    return state


def test_generate_outline_holds_when_no_evidence(monkeypatch):
    proc = _FakeProcessor(top_k_results=[])
    service = _FakeService()
    monkeypatch.setattr(mod, "_get_processor", lambda: proc)
    monkeypatch.setattr(mod, "_get_service", lambda: service)
    monkeypatch.setattr(mod.st, "rerun", lambda: (_ for _ in ()).throw(RuntimeError("should not rerun")))

    st.session_state["sermon_draft_state"] = _fresh_state()

    mod._generate_outline("근거 없는 본문/주제", [], "주제설교")

    assert proc.calls == 1  # 검색은 했다
    assert service.outline_calls == 0  # 그러나 개요 생성(→ Ollama)은 스킵
    state = st.session_state["sermon_draft_state"]
    assert state["outline"] is None  # 상태 전이 없음 — 여전히 input 단계
    assert state["status"] == "input"


def test_generate_outline_proceeds_when_evidence_present(monkeypatch):
    candidate = types.SimpleNamespace(content="본문 발췌", final_score=0.9)
    proc = _FakeProcessor(top_k_results=[candidate])
    service = _FakeService()
    monkeypatch.setattr(mod, "_get_processor", lambda: proc)
    monkeypatch.setattr(mod, "_get_service", lambda: service)
    monkeypatch.setattr(mod, "doctrine_check", lambda outline, ctx: types.SimpleNamespace(passed=True, warnings=[], flagged_categories=[]))
    monkeypatch.setattr(mod.st, "rerun", lambda: None)

    st.session_state["sermon_draft_state"] = _fresh_state()

    mod._generate_outline("근거 있는 본문/주제", [], "주제설교")

    assert service.outline_calls == 1
    state = st.session_state["sermon_draft_state"]
    assert state["outline"] is not None
    assert state["status"] == "outline_generated"


def test_expansion_step_holds_when_candidates_empty(monkeypatch):
    """candidates가 비면 대지 목록 루프(버튼 렌더링) 자체에 도달하지 않고
    유보 문구를 띄운 뒤 조기 반환한다 — 버튼이 클릭되지 않아서가 아니라
    가드가 먼저 막는다는 것을 st.warning 호출 인자로 직접 확인한다."""
    service = _FakeService()
    warnings: list[str] = []
    monkeypatch.setattr(mod, "_get_service", lambda: service)
    monkeypatch.setattr(mod.st, "warning", lambda msg, *a, **k: warnings.append(msg))
    monkeypatch.setattr(
        mod.st,
        "expander",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("루프에 도달하면 안 된다")),
    )

    outline = SermonOutline(title="제목", introduction="서론", points=["대지1"])
    st.session_state["sermon_draft_state"] = _fresh_state(
        outline=outline, candidates=[], status="approved"
    )

    mod._render_expansion_step()

    assert service.expand_calls == 0
    # [2026-09-26] 유보 문구 뒤에 서재 언어 고지가 덧붙는다(영문 서재일 때만) —
    # 문구가 붙었는지가 아니라 "유보 안내가 떴는지"가 이 테스트의 관심사다.
    assert len(warnings) == 1
    assert warnings[0].startswith(mod._SERMON_NO_EVIDENCE_TEXT)


def test_expansion_step_reaches_loop_when_candidates_present(monkeypatch):
    """candidates가 있으면 가드를 통과해 대지 루프까지 도달한다(=st.expander
    호출)."""
    service = _FakeService()
    expander_calls = []
    monkeypatch.setattr(mod, "_get_service", lambda: service)

    class _NullCtx:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_expander(*a, **k):
        expander_calls.append((a, k))
        return _NullCtx()

    monkeypatch.setattr(mod.st, "expander", fake_expander)

    outline = SermonOutline(title="제목", introduction="서론", points=["대지1"])
    candidate = types.SimpleNamespace(content="본문 발췌", final_score=0.9)
    st.session_state["sermon_draft_state"] = _fresh_state(
        outline=outline, candidates=[candidate], status="approved"
    )

    mod._render_expansion_step()

    assert len(expander_calls) == 1


def test_hold_text_names_the_reason():
    assert "등록" in mod._SERMON_NO_EVIDENCE_TEXT
    assert "일반 지식" in mod._SERMON_NO_EVIDENCE_TEXT
