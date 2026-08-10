"""Regression test — GenerationService conversation_history parameter
(2026-07-24, DBMA Chat "Plan B" session-scoped continuity).

conversation_history is additive/optional: existing callers (Research,
SermonDraft) that never pass it must see byte-identical prompts to before.
Only Chat opts in by passing recent turns, and only the ANSWER-GENERATION
prompt changes — the retrieval query (response.question) is untouched.
"""

import sys
import os
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import ollama  # noqa: F401
except ImportError:
    if "ollama" not in sys.modules:
        _ollama_stub = types.ModuleType("ollama")
        _ollama_stub.generate = lambda *args, **kwargs: {"response": ""}
        _ollama_stub.embeddings = lambda *args, **kwargs: {"embedding": []}
        sys.modules["ollama"] = _ollama_stub

from core.generation import GenerationService
from core.retrieval import ResponsePackage, ParsedQuery, PerformanceMetrics


def _make_response(context: str = "some context") -> ResponsePackage:
    return ResponsePackage(
        query_id="q1",
        question="후속 질문입니다",
        candidates=[],
        top_k_results=[],
        performance_metrics=PerformanceMetrics(),
        parsed_query=ParsedQuery(original_query="후속 질문입니다", intent="unknown"),
        llm_context_block=context,
        citations=[],
    )


class TestConversationHistoryPrompt:
    def test_omitted_history_is_byte_identical_to_before(self):
        response = _make_response()
        prompt, context_used = GenerationService._build_prompt(response)
        assert prompt == "문맥:\nsome context\n\n질문:\n후속 질문입니다"
        assert context_used is True

    def test_empty_string_history_is_same_as_omitted(self):
        response = _make_response()
        prompt, _ = GenerationService._build_prompt(response, conversation_history="")
        assert prompt == "문맥:\nsome context\n\n질문:\n후속 질문입니다"

    def test_history_is_prepended_before_context(self):
        response = _make_response()
        history = "사용자: 첫 질문\n어시스턴트: 첫 답변"
        prompt, context_used = GenerationService._build_prompt(response, conversation_history=history)
        assert prompt == (
            "이전 대화:\n사용자: 첫 질문\n어시스턴트: 첫 답변\n\n"
            "문맥:\nsome context\n\n질문:\n후속 질문입니다"
        )
        assert context_used is True

    def test_history_with_no_retrieval_context_still_prepends(self):
        response = _make_response(context="")
        history = "사용자: 첫 질문\n어시스턴트: 첫 답변"
        prompt, context_used = GenerationService._build_prompt(response, conversation_history=history)
        assert prompt == "이전 대화:\n사용자: 첫 질문\n어시스턴트: 첫 답변\n\n질문:\n후속 질문입니다"
        assert context_used is False

    def test_generate_stream_accepts_conversation_history(self):
        response = _make_response()
        service = GenerationService()
        stream = service.generate_stream(response, conversation_history="사용자: 이전\n어시스턴트: 답")
        assert "이전 대화:" in stream._prompt
