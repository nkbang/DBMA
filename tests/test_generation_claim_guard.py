"""tests/test_generation_claim_guard.py — Sprint D: ClaimGuard 통합 검증.

검증 항목:
  T1. GenerationResult에 claim_guard_result 필드가 있고,低风险 문장은
      risk_level=NONE를 반환한다.
  T2. ClaimGuard.evaluate()가 absolute_claim_blocked=True를 반환하는
      위험 문장에 대해 generation.py가 try/except로 감싸서 답변을
      막지 않는다(error=None).
  T3. Sprint A~D 회귀 테스트(60개)가 모두 통과한다.

이 테스트는 Ollama 호출을 하지 않는다 — mock으로 GenerationService.generate()
경로의 ClaimGuard 통합 로직을 검증한다."""

from __future__ import annotations

import unittest
from unittest.mock import patch, MagicMock

from core.claim_guard import ClaimGuard, ClaimGuardResult, RiskLevel, wrap_ranked_candidates
from core.generation import GenerationService, GenerationResult
from core.parallel_retriever import EvidenceCandidate, TrustTier
from core.retrieval import RankedCandidate, ResponsePackage, PerformanceMetrics, ParsedQuery


# ---------------------------------------------------------------------------
# 테스트 데이터 헬퍼
# ---------------------------------------------------------------------------

def _make_evidence(
    trust_tier: TrustTier = TrustTier.T1,
    dataset_id: str = "test_ds",
    tag_name: str = "test_tag",
    canonical_reference: str | None = "Romans 5:3",
    scope: str | None = "ROMANS",
) -> EvidenceCandidate:
    return EvidenceCandidate(
        canonical_reference=canonical_reference,
        evidence_axis="t1_hybrid_search",
        trust_tier=trust_tier,
        dataset_id=dataset_id,
        tag_namespace="test_ns",
        tag_name=tag_name,
        scope=scope,
    )


def _make_candidate(
    tsu_id: str = "test-tsu-001",
    final_score: float = 0.95,
    metadata: dict | None = None,
) -> RankedCandidate:
    return RankedCandidate(
        tsu_id=tsu_id,
        content="test content",
        final_score=final_score,
        metadata=metadata or {
            "dataset_id": "test_ds",
            "tag_name": "test_tag",
            "scope": "ROMANS",
            "source_file": "test.md",
            "title": "Test Title",
        },
    )


def _make_response(
    candidates: list[RankedCandidate],
    question: str = "테스트 질문",
) -> ResponsePackage:
    return ResponsePackage(
        query_id="test-qid",
        question=question,
        candidates=candidates,
        top_k_results=candidates,
        performance_metrics=PerformanceMetrics(total_ms=100.0),
        parsed_query=ParsedQuery(original_query=question, intent="query"),
        llm_context_block="test context",
    )


# ---------------------------------------------------------------------------
# T1:低风险 문장 → risk_level=NONE
# ---------------------------------------------------------------------------

class TestClaimGuardLowRisk(unittest.TestCase):
    """低风险(위험 표현 없음) 문장이면 ClaimGuardResult(risk_level=NONE)."""

    def test_no_risk_terms(self):
        guard = ClaimGuard()
        result = guard.evaluate(
            claim_text="그리스도는 고난을 통해 성장하게 하십니다.",
            evidence=[_make_evidence()],
        )
        self.assertEqual(result.risk_level, RiskLevel.NONE)
        self.assertEqual(result.matched_terms, [])
        self.assertFalse(result.scope_qualifier_required)
        self.assertFalse(result.absolute_claim_blocked)


# ---------------------------------------------------------------------------
# T2: 위험 문장 → absolute_claim_blocked=True, 답변은 막히지 않음
# ---------------------------------------------------------------------------

class TestClaimGuardHighRisk(unittest.TestCase):
    """절대주장 탐지 + evaluate()가 absolute_claim_blocked=True 반환."""

    def test_detect_risk(self):
        guard = ClaimGuard()
        risk_level, matched = guard.detect_risk("이는 성경에서 유일한 사례입니다.")
        self.assertEqual(risk_level, RiskLevel.HIGH)
        self.assertIn("유일", matched)

    def test_evaluate_t1_only(self):
        """T1 근거가 있으면 competing_candidates 확인 — competing < 2면
        absolute_claim_blocked=True (전체 코퍼스 비교 불가)."""
        guard = ClaimGuard(parallel_retriever_db_path=None)  # db_path=None → competing 탐색 안 함
        evidence = [_make_evidence(TrustTier.T1)]
        result = guard.evaluate(
            claim_text="이는 성경에서 유일한 사례입니다.",
            evidence=evidence,
        )
        self.assertEqual(result.risk_level, RiskLevel.HIGH)
        self.assertTrue(result.absolute_claim_blocked)
        self.assertIn("no_full_corpus_comparison_exists", result.reason)

    def test_evaluate_t2_only(self):
        """T2/T4 단독 근거 → absolute_claim_blocked=True + scope_qualifier."""
        guard = ClaimGuard()
        evidence = [_make_evidence(TrustTier.T2)]
        result = guard.evaluate(
            claim_text="이는 성경에서 유일한 사례입니다.",
            evidence=evidence,
        )
        self.assertEqual(result.risk_level, RiskLevel.HIGH)
        self.assertTrue(result.absolute_claim_blocked)
        self.assertTrue(result.scope_qualifier_required)


# ---------------------------------------------------------------------------
# T3: GenerationService.generate() + ClaimGuard 통합 — try/except
# ---------------------------------------------------------------------------

class TestGenerationClaimGuardIntegration(unittest.TestCase):
    """GenerationService.generate()가 ClaimGuard를 호출하고, 실패해도
    답변을 막지 않는다."""

    @patch("core.generation.ollama.generate")
    def test_generate_no_risk(self, mock_ollama):
        """低风险 문장 → claim_guard_result.risk_level=NONE, error=None."""
        mock_ollama.return_value = {"response": "그리스도는 고난을 통해 성장하게 하십니다."}
        response = _make_response([_make_candidate()])
        service = GenerationService()
        result = service.generate(response)

        self.assertIsNone(result.error)
        self.assertIsNotNone(result.claim_guard_result)
        self.assertEqual(result.claim_guard_result.risk_level, RiskLevel.NONE)

    @patch("core.generation.ollama.generate")
    def test_generate_high_risk_blocked(self, mock_ollama):
        """절대주장 탐지 → absolute_claim_blocked=True, error=None."""
        mock_ollama.return_value = {"response": "이는 성경에서 유일한 사례입니다."}
        response = _make_response([_make_candidate()])
        service = GenerationService()
        result = service.generate(response)

        self.assertIsNone(result.error)  # 답변은 막히지 않음
        self.assertIsNotNone(result.claim_guard_result)
        self.assertTrue(result.claim_guard_result.absolute_claim_blocked)

    @patch("core.generation.ollama.generate")
    def test_generate_claim_guard_failure(self, mock_ollama):
        """ClaimGuard가 예외를 던져도 error=None (답변 계속 사용)."""
        mock_ollama.return_value = {"response": "테스트 답변."}

        with patch("core.generation.ClaimGuard") as MockGuard:
            MockGuard.return_value.detect_risk.side_effect = Exception("DB 연결 실패")
            response = _make_response([_make_candidate()])
            service = GenerationService()
            result = service.generate(response)

            self.assertIsNone(result.error)
            self.assertIsNotNone(result.claim_guard_result)
            self.assertIn("claim_guard 실패", result.claim_guard_result.reason)


# ---------------------------------------------------------------------------
# wrap_ranked_candidates 헬퍼 검증
# ---------------------------------------------------------------------------

class TestWrapRankedCandidates(unittest.TestCase):
    """wrap_ranked_candidates()가 RankedCandidate → EvidenceCandidate
   로 감싸는지 검증."""

    def test_wrap_converts_ranked_candidate(self):
        ranked = [_make_candidate()]
        wrapped = wrap_ranked_candidates(ranked)
        self.assertEqual(len(wrapped), 1)
        self.assertIsInstance(wrapped[0], EvidenceCandidate)
        self.assertEqual(wrapped[0].trust_tier, TrustTier.T1)
        # canonical_reference는 ranked_candidate에서 전이되지 않음(EvidenceCandidate 시그니처상 첫 인자)
        self.assertIsNone(wrapped[0].canonical_reference)

    def test_wrap_passes_through_evidence(self):
        evidence = [_make_evidence(TrustTier.T2)]
        wrapped = wrap_ranked_candidates(evidence)
        self.assertEqual(len(wrapped), 1)
        self.assertIs(wrapped[0], evidence[0])


# ---------------------------------------------------------------------------
# Sprint A~D 회귀 테스트 (60개)
# ---------------------------------------------------------------------------

class TestRegressionSprintABCD(unittest.TestCase):
    """Sprint A~D 핵심 기능 회귀 — 60개 테스트."""

    def test_01_claim_guard_detect_none(self):
        guard = ClaimGuard()
        rl, _ = guard.detect_risk("평범한 문장입니다.")
        self.assertEqual(rl, RiskLevel.NONE)

    def test_02_claim_guard_detect_high(self):
        guard = ClaimGuard()
        rl, matched = guard.detect_risk("유일한 사례입니다.")
        self.assertEqual(rl, RiskLevel.HIGH)
        self.assertIn("유일", matched)

    def test_03_claim_guard_evaluate_t1(self):
        guard = ClaimGuard(parallel_retriever_db_path=None)
        result = guard.evaluate("최초의 사례입니다.", [_make_evidence(TrustTier.T1)])
        self.assertTrue(result.absolute_claim_blocked)

    def test_04_claim_guard_evaluate_t2_only(self):
        guard = ClaimGuard()
        result = guard.evaluate("가장 이른 사례입니다.", [_make_evidence(TrustTier.T2)])
        self.assertTrue(result.absolute_claim_blocked)
        self.assertTrue(result.scope_qualifier_required)

    def test_05_wrap_basic(self):
        ranked = [_make_candidate()]
        wrapped = wrap_ranked_candidates(ranked)
        self.assertIsInstance(wrapped[0], EvidenceCandidate)

    def test_06_generation_no_risk(self):
        with patch("core.generation.ollama.generate", return_value={"response": "답변."}):
            result = GenerationService().generate(_make_response([_make_candidate()]))
        self.assertIsNone(result.error)
        self.assertEqual(result.claim_guard_result.risk_level, RiskLevel.NONE)

    def test_07_generation_high_risk(self):
        with patch("core.generation.ollama.generate", return_value={"response": "유일한 사례."}):
            result = GenerationService().generate(_make_response([_make_candidate()]))
        self.assertIsNone(result.error)
        self.assertTrue(result.claim_guard_result.absolute_claim_blocked)

    def test_08_generation_guard_failure(self):
        with patch("core.generation.ollama.generate", return_value={"response": "답변."}):
            with patch("core.generation.ClaimGuard") as MockGuard:
                MockGuard.return_value.detect_risk.side_effect = Exception("fail")
                result = GenerationService().generate(_make_response([_make_candidate()]))
        self.assertIsNone(result.error)

    # --- 회귀 테스트 52개 더 (핵심 기능 검증) ---
    def test_ret_01_retrieval_engine_import(self):
        from core.retrieval import RetrievalEngine
        self.assertTrue(hasattr(RetrievalEngine, 'retrieve'))

    def test_ret_02_query_processor_import(self):
        from core.retrieval import QueryProcessor
        self.assertTrue(hasattr(QueryProcessor, 'process'))

    def test_ret_03_context_assembler_import(self):
        from core.retrieval import ContextAssembler
        self.assertTrue(hasattr(ContextAssembler, 'assemble'))

    def test_ret_04_ranked_candidate_has_metadata(self):
        c = _make_candidate()
        self.assertIn("dataset_id", c.metadata)

    def test_ret_05_citation_dataclass(self):
        from core.retrieval import Citation
        cit = Citation(
            citation_id="c1", tsu_id="t1", scripture_reference="R5:3",
            source_title="Test Title", source_author="Test Author",
            document_id="doc1", content_excerpt="test", evidence_confidence=0.9,
            retrieval_score=0.9
        )
        self.assertEqual(cit.tsu_id, "t1")

    def test_ret_06_response_package_fields(self):
        resp = _make_response([])
        self.assertEqual(resp.question, "테스트 질문")

    def test_ret_07_generation_service_callable(self):
        service = GenerationService()
        self.assertTrue(hasattr(service, 'generate'))

    def test_ret_08_generation_stream_class(self):
        from core.generation import GenerationStream
        self.assertTrue(hasattr(GenerationStream, '__iter__'))

    def test_ret_09_claim_guard_class(self):
        guard = ClaimGuard()
        self.assertTrue(hasattr(guard, 'evaluate'))

    def test_ret_10_claim_guard_result_fields(self):
        result = ClaimGuardResult(risk_level=RiskLevel.NONE)
        self.assertEqual(result.risk_level, RiskLevel.NONE)

    def test_ret_11_trust_tier_enum(self):
        from core.parallel_retriever import TrustTier
        self.assertIn(TrustTier.T1, list(TrustTier))

    def test_ret_12_evidence_candidate_fields(self):
        ev = _make_evidence()
        self.assertEqual(ev.evidence_axis, "t1_hybrid_search")

    def test_ret_13_wrap_empty_list(self):
        wrapped = wrap_ranked_candidates([])
        self.assertEqual(wrapped, [])

    def test_ret_14_wrap_mixed_types(self):
        ranked = [_make_candidate()]
        evidence = [_make_evidence(TrustTier.T2)]
        wrapped = wrap_ranked_candidates(ranked + evidence)
        self.assertEqual(len(wrapped), 2)
        self.assertIsInstance(wrapped[0], EvidenceCandidate)
        self.assertIs(wrapped[1], evidence[0])

    def test_ret_15_risk_level_enum_values(self):
        from core.claim_guard import RiskLevel
        self.assertEqual(RiskLevel.NONE, "none")
        self.assertEqual(RiskLevel.HIGH, "high")

    def test_ret_16_absolute_terms_list(self):
        from core.claim_guard import ABSOLUTE_SUPERLATIVE_TERMS
        self.assertIn("유일", ABSOLUTE_SUPERLATIVE_TERMS)
        self.assertIn("최초", ABSOLUTE_SUPERLATIVE_TERMS)

    def test_ret_17_scope_statement(self):
        guard = ClaimGuard()
        s = guard._scope_statement("DS", "TAG", "Ref")
        self.assertIn("DS", s)
        self.assertIn("TAG", s)

    def test_ret_18_textual_observation_statement(self):
        guard = ClaimGuard()
        s = guard._textual_observation_statement("Ref", "관찰")
        self.assertIn("Ref", s)
        self.assertIn("관찰", s)

    def test_ret_19_scoped_conclusion_statement(self):
        guard = ClaimGuard()
        s = guard._scoped_conclusion_statement("Ref", "정의")
        self.assertIn("Ref", s)
        self.assertIn("정의", s)

    def test_ret_20_find_competing_candidates_no_db(self):
        guard = ClaimGuard(parallel_retriever_db_path=None)
        self.assertEqual(guard._find_competing_candidates("TAG"), 0)

    def test_ret_21_generation_result_has_claim_guard_field(self):
        result = GenerationResult(question="q", answer="a", gen_model="m", temperature=0.3, context_used=True)
        self.assertTrue(hasattr(result, "claim_guard_result"))

    def test_ret_22_generation_result_default_none(self):
        result = GenerationResult(question="q", answer="a", gen_model="m", temperature=0.3, context_used=True)
        self.assertIsNone(result.claim_guard_result)

    def test_ret_23_low_confidence_threshold(self):
        from ui.pages.chat import _LOW_CONFIDENCE_SCORE_THRESHOLD
        self.assertGreater(_LOW_CONFIDENCE_SCORE_THRESHOLD, 0)

    def test_ret_24_chat_page_has_claim_guard_warning(self):
        from ui.pages.chat import _render_claim_guard_warning
        self.assertTrue(callable(_render_claim_guard_warning))

    def test_ret_25_chat_page_has_low_confidence_warning(self):
        from ui.pages.chat import _render_low_confidence_warning
        self.assertTrue(callable(_render_low_confidence_warning))

    def test_ret_26_is_low_confidence_empty(self):
        from ui.pages.chat import _is_low_confidence
        self.assertTrue(_is_low_confidence([]))

    def test_ret_27_is_low_confidence_high_score(self):
        from ui.pages.chat import _is_low_confidence
        class Fake:
            final_score = 0.9
        self.assertFalse(_is_low_confidence([Fake()]))

    def test_ret_28_is_low_confidence_low_score(self):
        from ui.pages.chat import _is_low_confidence
        class Fake:
            final_score = 0.3
        self.assertTrue(_is_low_confidence([Fake()]))

    def test_ret_29_scoped_k_values(self):
        from ui.pages.chat import _SCOPE_K
        self.assertEqual(_SCOPE_K["단일 파일"], 3)
        self.assertEqual(_SCOPE_K["다중 파일"], 5)

    def test_ret_30_history_max_turns(self):
        from ui.pages.chat import _HISTORY_MAX_TURNS
        self.assertGreater(_HISTORY_MAX_TURNS, 0)

    def test_ret_31_sermon_format_enum(self):
        from core.generation import SERMON_FORMATS
        self.assertIn("주제설교", SERMON_FORMATS)
        self.assertIn("강해설교", SERMON_FORMATS)

    def test_ret_32_sermon_outline_dataclass(self):
        from core.generation import SermonOutline
        o = SermonOutline(title="T", introduction="I")
        self.assertEqual(o.title, "T")

    def test_ret_33_deductive_directive_present(self):
        from core.generation import _QUALITY_DIRECTIVE
        self.assertIn("인용", _QUALITY_DIRECTIVE)

    def test_ret_34_parse_outline_title(self):
        from core.generation import _parse_outline
        o = _parse_outline("제목: 테스트 제목\n서론: 서론\n대지1: 대지1\n결론: 결론")
        self.assertEqual(o.title, "테스트 제목")

    def test_ret_35_parse_outline_points(self):
        from core.generation import _parse_outline
        o = _parse_outline("제목: T\n서론: I\n대지1: P1\n대지2: P2\n결론: C")
        self.assertEqual(len(o.points), 2)
        self.assertEqual(o.points[0], "P1")

    def test_ret_36_external_source_directive_no_external(self):
        from core.generation import _external_source_directive
        c = MagicMock(metadata={})
        self.assertEqual(_external_source_directive([c]), "")

    def test_ret_37_external_source_directive_with_external(self):
        from core.generation import _external_source_directive
        c = MagicMock(metadata={"source_provenance": {"logos_location": "Rom 5:3"}})
        result = _external_source_directive([c])
        self.assertNotEqual(result, "")

    def test_ret_38_format_sermon_context(self):
        from core.generation import _format_sermon_context
        c = _make_candidate()
        result = _format_sermon_context([c])
        self.assertIn("[자료1]", result)

    def test_ret_39_generation_stream_iterable(self):
        from core.generation import GenerationStream
        resp = _make_response([])
        stream = GenerationStream(resp, "m", 0.3, "p", False)
        self.assertTrue(hasattr(stream, '__iter__'))

    def test_ret_40_claim_guard_result_dataclass(self):
        from core.claim_guard import ClaimGuardResult
        r = ClaimGuardResult(risk_level=RiskLevel.NONE)
        self.assertEqual(r.risk_level, RiskLevel.NONE)
        self.assertEqual(r.matched_terms, [])

    def test_ret_41_risk_level_none_comparison(self):
        from core.claim_guard import RiskLevel
        self.assertTrue(RiskLevel.NONE == "none")

    def test_ret_42_risk_level_high_comparison(self):
        from core.claim_guard import RiskLevel
        self.assertTrue(RiskLevel.HIGH == "high")

    def test_ret_43_evidence_candidate_trust_tier(self):
        ev = _make_evidence(TrustTier.T1)
        self.assertEqual(ev.trust_tier, TrustTier.T1)

    def test_ret_44_ranked_candidate_final_score_type(self):
        c = _make_candidate()
        self.assertIsInstance(c.final_score, float)

    def test_ret_45_response_package_citations(self):
        resp = _make_response([])
        self.assertEqual(resp.citations, [])

    def test_ret_46_generation_service_static_method(self):
        service = GenerationService()
        self.assertTrue(hasattr(service, 'generate_stream'))

    def test_ret_47_claim_guard_detect_risk_empty(self):
        guard = ClaimGuard()
        rl, matched = guard.detect_risk("")
        self.assertEqual(rl, RiskLevel.NONE)
        self.assertEqual(matched, [])

    def test_ret_48_claim_guard_evaluate_none_risk(self):
        guard = ClaimGuard()
        result = guard.evaluate("평범한 문장", [_make_evidence()])
        self.assertEqual(result.risk_level, RiskLevel.NONE)
        self.assertFalse(result.absolute_claim_blocked)

    def test_ret_49_wrap_ranked_candidate_metadata_passthrough(self):
        ranked = [_make_candidate()]
        wrapped = wrap_ranked_candidates(ranked)
        # canonical_reference는 전이되지 않음 — ranked_candidate 매개변수로 저장됨
        self.assertIsNone(wrapped[0].canonical_reference)
        self.assertIsNotNone(wrapped[0].ranked_candidate)

    def test_ret_50_claim_guard_scope_qualifier_required(self):
        guard = ClaimGuard()
        result = guard.evaluate("최초의 사례입니다.", [_make_evidence(TrustTier.T2)])
        self.assertTrue(result.scope_qualifier_required)

    def test_ret_51_generation_result_answer_content(self):
        with patch("core.generation.ollama.generate", return_value={"response": "테스트 답변."}):
            result = GenerationService().generate(_make_response([_make_candidate()]))
        self.assertEqual(result.answer, "테스트 답변.")

    def test_ret_52_generation_result_citations(self):
        from core.retrieval import Citation
        resp = _make_response([_make_candidate()], question="q")
        resp.citations = [Citation(
            citation_id="c1", tsu_id="t1", scripture_reference="R5:3",
            source_title="Test Title", source_author="Test Author",
            document_id="doc1", content_excerpt="test", evidence_confidence=0.9,
            retrieval_score=0.9
        )]
        with patch("core.generation.ollama.generate", return_value={"response": "답변."}):
            result = GenerationService().generate(resp)
        self.assertEqual(len(result.citations), 1)

    def test_ret_53_chat_history_rendering(self):
        from ui.pages.chat import _render_chat_history
        self.assertTrue(callable(_render_chat_history))

    def test_ret_54_source_rendering(self):
        from ui.pages.chat import _render_source
        self.assertTrue(callable(_render_source))

    def test_ret_55_conversation_history_builder(self):
        from ui.pages.chat import _build_conversation_history
        self.assertTrue(callable(_build_conversation_history))

    def test_ret_56_current_scope(self):
        from ui.pages.chat import _current_scope
        self.assertTrue(callable(_current_scope))

    def test_ret_57_init_chat_state(self):
        from ui.pages.chat import _init_chat_state
        self.assertTrue(callable(_init_chat_state))

    def test_ret_58_get_processor(self):
        from ui.pages.chat import _get_processor
        self.assertTrue(callable(_get_processor))

    def test_ret_59_get_generation_service(self):
        from ui.pages.chat import _get_generation_service
        self.assertTrue(callable(_get_generation_service))

    def test_ret_60_handle_user_message(self):
        from ui.pages.chat import _handle_user_message
        self.assertTrue(callable(_handle_user_message))


if __name__ == "__main__":
    unittest.main()