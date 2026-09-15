"""Regression test — ui/pages/chat.py::generate_answer() 근거 부족 시 유보.

[PM 정렬 감사 P0-6 / 위험 R6] 검색이 근거를 하나도 반환하지 못하면
(top_k_results 비었고 Smith 사전 컨텍스트도 없음) GenerationService를
호출하지 않고 _NO_EVIDENCE_HOLD_TEXT를 돌려준다. 결과가 있으면(점수가
낮더라도) 평소처럼 생성한다.

Streamlit 런타임 없이 검증 — _get_processor / _get_generation_service /
_inject_smith_context / _settings_overrides를 monkeypatch한다.
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


class _FakeResponse:
    def __init__(self, top_k_results):
        self.top_k_results = top_k_results
        self.llm_context_block = ""
        self.question = "q"
        self.citations = None


class _FakeProcessor:
    def __init__(self, top_k_results):
        self._top_k = top_k_results
        self.calls = 0

    def process(self, *a, **k):
        self.calls += 1
        return _FakeResponse(self._top_k)


class _FakeStream:
    def __iter__(self):
        return iter([])

    def to_result(self):
        return types.SimpleNamespace(answer="생성된 답변", error=None)


class _FakeGenerationService:
    def __init__(self):
        self.calls = 0

    def generate_stream(self, *a, **k):
        self.calls += 1
        return _FakeStream()


def _patch(monkeypatch, *, top_k_results, smith_results):
    import ui.pages.chat as mod

    proc = _FakeProcessor(top_k_results)
    gen = _FakeGenerationService()
    monkeypatch.setattr(mod, "_get_processor", lambda: proc)
    monkeypatch.setattr(mod, "_get_generation_service", lambda: gen)
    monkeypatch.setattr(mod, "_inject_smith_context", lambda response, question: smith_results)
    monkeypatch.setattr(mod, "_settings_overrides", lambda: {})
    return mod, proc, gen


def test_holds_when_no_evidence_at_all(monkeypatch):
    mod, proc, gen = _patch(monkeypatch, top_k_results=[], smith_results=[])

    answer, sources = mod.generate_answer("등록되지 않은 주제 질문")

    assert answer == mod._NO_EVIDENCE_HOLD_TEXT
    assert sources == []
    assert gen.calls == 0  # 생성 자체를 건너뛴다


def test_proceeds_when_smith_context_present(monkeypatch):
    # 검색 0건이라도 Smith 사전 컨텍스트가 있으면 근거가 있는 것으로 본다.
    mod, proc, gen = _patch(monkeypatch, top_k_results=[], smith_results=[{"term": "은혜"}])

    answer, sources = mod.generate_answer("은혜란 무엇인가")

    assert answer == "생성된 답변"
    assert gen.calls == 1


def test_proceeds_when_results_present_even_if_weak(monkeypatch):
    weak = types.SimpleNamespace(
        final_score=0.05, theological_score=0.05, passage_score=0.0
    )
    mod, proc, gen = _patch(monkeypatch, top_k_results=[weak], smith_results=[])

    answer, sources = mod.generate_answer("느슨하게 관련된 질문")

    assert answer == "생성된 답변"
    assert gen.calls == 1
    assert sources == [weak]


def test_hold_text_names_the_reason(monkeypatch):
    import ui.pages.chat as mod

    assert "등록" in mod._NO_EVIDENCE_HOLD_TEXT
    assert "일반 지식" in mod._NO_EVIDENCE_HOLD_TEXT
