"""교단 신학 관점 지시문 회귀 테스트 (ADR-009 Amendment A, 2026-09-10).

배경: ADR-009(Accepted, 2026-07-22)는 사용자의 전통을 개혁파 침례교로
확정하고 doctrine_filter를 **설교 초안 경로**에 연결했다. 그러나 목회자가
실제로 답을 얻는 주 경로인 질의응답(Chat/Research)에는 교단 신호가 전혀
없었다 — 모델 SYSTEM 프롬프트의 "복음주의 및 개혁주의"는 개혁파 침례교와
모순되지 않지만 신자세례·회중교회론·1689 언약신학을 특정하지 못한다.

이 파일이 지키는 것은 두 가지다.

1. 교단 관점이 답변 프롬프트에 실제로 들어간다.
2. **그것이 근거 강제를 무너뜨리지 않는다.** "교단에 맞는 답"을 요구하면
   모델은 자료에 없는 교리를 보충해 전통에 맞추려는 유혹을 받는데, 그건
   이 앱이 막으려는 바로 그 행동이다. 지시문의 우선순위와 배치가 이
   테스트의 핵심 검증 대상이다.
"""
import pytest

from core import generation
from core.generation import GenerationService
from core.retrieval import ResponsePackage, ParsedQuery, PerformanceMetrics
from core.sermon.doctrine_vocabulary import DENOMINATION_PROFILE


def _response(context: str = "some context") -> ResponsePackage:
    return ResponsePackage(
        query_id="q1",
        question="유아세례를 어떻게 보아야 합니까?",
        candidates=[],
        top_k_results=[],
        performance_metrics=PerformanceMetrics(),
        parsed_query=ParsedQuery(original_query="유아세례", intent="theological"),
        llm_context_block=context,
        citations=[],
    )


class TestDirectivePresent:
    def test_present_when_context_exists(self):
        prompt, used = GenerationService._build_prompt(_response())
        assert used is True
        assert generation._DENOMINATION_DIRECTIVE in prompt

    def test_present_when_no_context(self):
        """자료가 없어도 교단 관점은 유지된다 — 답변의 성격을 정하는 것이지
        자료를 해석하는 지시만은 아니기 때문이다."""
        prompt, used = GenerationService._build_prompt(_response(context=""))
        assert used is False
        assert generation._DENOMINATION_DIRECTIVE in prompt

    def test_profile_text_reaches_the_prompt(self):
        prompt, _ = GenerationService._build_prompt(_response())
        assert DENOMINATION_PROFILE in prompt
        assert "개혁파 침례교" in prompt


class TestGroundingStillWins:
    """근거 강제가 교단 관점보다 우선한다는 것이 프롬프트에 남아 있어야 한다."""

    def test_grounding_directive_still_present(self):
        prompt, _ = GenerationService._build_prompt(_response())
        assert generation._GROUNDING_DIRECTIVE in prompt

    def test_grounding_comes_before_denomination(self):
        """순서가 곧 우선순위 신호다 — 근거 지시가 먼저 와야 한다."""
        prompt, _ = GenerationService._build_prompt(_response())
        assert prompt.index(generation._GROUNDING_DIRECTIVE) < prompt.index(
            generation._DENOMINATION_DIRECTIVE
        )

    def test_directive_states_grounding_precedence(self):
        """전통에 맞추려 자료에 없는 내용을 보태지 말라는 조항이 있어야 한다."""
        assert "자료에 없는 내용을 보태지 마라" in generation._DENOMINATION_DIRECTIVE
        assert "우선한다" in generation._DENOMINATION_DIRECTIVE

    def test_both_directives_precede_the_question(self):
        prompt, _ = GenerationService._build_prompt(_response())
        q_at = prompt.index("질문:")
        assert prompt.index(generation._GROUNDING_DIRECTIVE) < q_at
        assert prompt.index(generation._DENOMINATION_DIRECTIVE) < q_at


class TestAdr009Principles:
    """ADR-009 §Decision-4의 원칙이 프롬프트 수준에서도 지켜지는지."""

    def test_no_condemnation_of_other_traditions(self):
        assert "정죄하지 마라" in generation._DENOMINATION_DIRECTIVE

    def test_final_judgement_left_to_the_pastor(self):
        """자동 차단 없음 — 최종 신학적 판단 권한은 목회자에게 있다."""
        assert "최종 판단은" in generation._DENOMINATION_DIRECTIVE

    def test_conflicting_evidence_must_be_surfaced_not_hidden(self):
        """전통과 다른 견해를 감추면 그건 검열이지 신학이 아니다."""
        assert "감추지 마라" in generation._DENOMINATION_DIRECTIVE

    def test_no_numeric_scoring_language(self):
        """ADR-009는 백분율 점수 같은 거짓 정밀도를 명시적으로 금지한다."""
        assert "%" not in generation._DENOMINATION_DIRECTIVE


class TestProfileIsSingleSourced:
    def test_profile_matches_adr009_wording(self):
        """전통 표현은 지어내지 않고 ADR-009 §Decision 원문을 인용한다."""
        assert DENOMINATION_PROFILE == (
            "개혁파 침례교(Reformed Baptist) — 1689 런던신앙고백 계열, "
            "신자세례·회중교회론"
        )

    def test_directive_does_not_hardcode_the_tradition(self):
        """프로파일을 바꾸면 지시문도 따라 바뀌어야 한다 — 두 곳에 각각
        적어두면 언젠가 서로 어긋난다."""
        import re
        src_line = [
            l for l in generation._DENOMINATION_DIRECTIVE.splitlines()
            if "다음 전통에 서 있는" in l
        ]
        assert src_line, "전통을 소개하는 문장을 찾지 못했다"
        assert DENOMINATION_PROFILE in src_line[0]
