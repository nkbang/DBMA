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

from core import generation
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
    """[2026-09-10] 근거 강제 지시문(_GROUNDING_DIRECTIVE) 도입 전까지 이
    테스트들은 프롬프트 전문을 문자열 리터럴로 고정 비교했다. 지시문이
    붙으면서 전문 비교는 지시문 문구를 조금만 다듬어도 깨지는 브리틀한
    검증이 됐다 — 이 테스트가 실제로 지키려는 것은 지시문 문구가 아니라
    '대화 이력이 자료 블록보다 앞에 온다'는 순서 계약이므로, 전문 비교를
    순서/구성요소 검증으로 바꾼다. 지시문 자체의 존재는 아래
    TestGroundingDirective가 따로 검증한다."""

    def test_omitted_history_has_no_history_block(self):
        response = _make_response()
        prompt, context_used = GenerationService._build_prompt(response)
        assert "이전 대화:" not in prompt
        assert prompt.startswith("자료:\nsome context")
        assert prompt.endswith("질문:\n후속 질문입니다")
        assert context_used is True

    def test_empty_string_history_is_same_as_omitted(self):
        response = _make_response()
        omitted, _ = GenerationService._build_prompt(response)
        empty, _ = GenerationService._build_prompt(response, conversation_history="")
        assert empty == omitted

    def test_history_is_prepended_before_context(self):
        response = _make_response()
        history = "사용자: 첫 질문\n어시스턴트: 첫 답변"
        prompt, context_used = GenerationService._build_prompt(response, conversation_history=history)
        assert prompt.startswith(
            "이전 대화:\n사용자: 첫 질문\n어시스턴트: 첫 답변\n\n자료:\nsome context"
        )
        assert prompt.endswith("질문:\n후속 질문입니다")
        assert context_used is True

    def test_history_with_no_retrieval_context_still_prepends(self):
        response = _make_response(context="")
        history = "사용자: 첫 질문\n어시스턴트: 첫 답변"
        prompt, context_used = GenerationService._build_prompt(response, conversation_history=history)
        assert prompt.startswith("이전 대화:\n사용자: 첫 질문\n어시스턴트: 첫 답변\n\n")
        assert "자료:" not in prompt
        assert prompt.endswith("질문:\n후속 질문입니다")
        assert context_used is False


class TestGroundingDirective:
    """근거 강제 지시문이 두 분기 모두에 실제로 들어가는지 — 이것이
    빠지면 모델 내장 지식이 검색 근거와 섞이는 것을 막을 장치가 앱
    전체에 하나도 남지 않는다(ClaimGuard는 사후 탐지만 한다)."""

    def test_directive_present_when_context_exists(self):
        prompt, context_used = GenerationService._build_prompt(_make_response())
        assert context_used is True
        assert generation._GROUNDING_DIRECTIVE in prompt

    def test_directive_placed_between_context_and_question(self):
        prompt, _ = GenerationService._build_prompt(_make_response())
        assert prompt.index("some context") < prompt.index(generation._GROUNDING_DIRECTIVE)
        assert prompt.index(generation._GROUNDING_DIRECTIVE) < prompt.index("질문:")

    def test_no_context_branch_uses_short_directive(self):
        prompt, context_used = GenerationService._build_prompt(_make_response(context=""))
        assert context_used is False
        assert generation._GROUNDING_DIRECTIVE_NO_CONTEXT in prompt
        # 자료가 없는데 "위 자료" 운운하는 긴 지시문이 새어들면 안 된다
        assert generation._GROUNDING_DIRECTIVE not in prompt

    def test_generate_stream_accepts_conversation_history(self):
        response = _make_response()
        service = GenerationService()
        stream = service.generate_stream(response, conversation_history="사용자: 이전\n어시스턴트: 답")
        assert "이전 대화:" in stream._prompt
