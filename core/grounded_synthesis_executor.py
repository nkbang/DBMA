"""core/grounded_synthesis_executor.py — GS modules orchestration layer.

역할:
    SynthesisInput + raw_claims -> (grounded_claims, grounded_answer, grounded_citation)
    -> GroundedAnswer 의 orchestration.

ADR-036 B9 boundary 준수:
    - Ollama 호출 금지
    - Qdrant/Tantivy 검색 금지
    - retrieval 구현 금지
    - semantic judge 금지
    - UI rendering 금지
    - GenerationService import 금지

GS modules만 사용:
    core.grounded_synthesis_input.SynthesisInput
    core.grounded_claims.Claim, bind_claims
    core.grounded_answer.GroundedAnswer, assemble_grounded_answer
    core.grounded_citation.CitationCheckReport, check_citation_provenance
    core.evidence_model.Evidence
    core.evidence_pool.EvidencePool
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from core.grounded_answer import GroundedAnswer, assemble_grounded_answer
from core.grounded_claims import Claim, bind_claims
from core.grounded_citation import CitationCheckReport, check_citation_provenance
from core.grounded_synthesis_input import SynthesisInput
from core.evidence_pool import EvidencePool

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecutionResult:
    """GS executor의 단일 실행 결과.

    기존 GenerationResult와 분리된 독립 구조.
    """
    synthesis_input: SynthesisInput
    claims: list[Claim]
    grounded_answer: GroundedAnswer
    citation_check: CitationCheckReport
    status: str  # "complete" | "incomplete" | "failed"


class GroundedSynthesisExecutor:
    """GS modules orchestration layer.

    생성된 답변의 (출처: ...) 인용을 검증하고,
    GroundedAnswer를 조립한다.

    ADR-036 B1: 기존 GenerationService를 대체하지 않는다.
    ADR-036 B9: prohibited import 없음.
    """

    def execute(
        self,
        synthesis_input: SynthesisInput,
        raw_claims: list[tuple[str, list[str]]],
        evidence_pool: EvidencePool,
    ) -> ExecutionResult:
        """SynthesisInput + raw_claims -> GroundedAnswer orchestration.

        1. claims 결속 (bind_claims -- evidence_id 소속 검사)
        2. GroundedAnswer 조립 (assemble_grounded_answer)
        3. citation provenance 검증 (check_citation_provenance)
        4. status 판정

        Parameters
        ----------
        synthesis_input : SynthesisInput
            P4에서 구성한 synthesis input.
        raw_claims : list[tuple[str, list[str]]]
            (claim_text, cited_evidence_ids) 쌍의 리스트.
            LLM(또는 stub)이 생성한 원시 claim 목록.
        evidence_pool : EvidencePool
            P2/P3가 채운 증거 풀. check_citation_provenance에 필요.

        Returns
        -------
        ExecutionResult
            ADR-036 B8 시그니처에 따른 orchestration 결과.
        """
        # Step 1: claims 결속 (evidence_id subset included_evidence_ids 검사)
        claims = bind_claims(raw_claims, synthesis_input)

        # Step 2: GroundedAnswer 조립
        grounded_answer = assemble_grounded_answer(claims, synthesis_input)

        # Step 3: citation provenance 검증 (GroundedAnswer 기반)
        citation_report = check_citation_provenance(
            grounded_answer=grounded_answer,
            synthesis_input=synthesis_input,
            evidence_pool=evidence_pool,
        )

        # Step 4: status 판정
        status = self._determine_status(claims, citation_report)

        return ExecutionResult(
            synthesis_input=synthesis_input,
            claims=claims,
            grounded_answer=grounded_answer,
            citation_check=citation_report,
            status=status,
        )

    @staticmethod
    def _determine_status(
        claims: list[Claim],
        citation_report: CitationCheckReport,
    ) -> str:
        """claims + citation检查结果로 status 판정."""
        valid_count = sum(1 for c in claims if c.valid)
        invalid_count = sum(1 for c in claims if not c.valid)

        if valid_count == 0 and invalid_count > 0:
            return "incomplete"
        if citation_report.span_not_found_count > 0:
            return "incomplete"
        return "complete"


# Module-level convenience function (P5-D wiring용)
def execute_synthesis(
    synthesis_input: SynthesisInput,
    raw_claims: list[tuple[str, list[str]]],
    evidence_pool: EvidencePool,
) -> ExecutionResult:
    """GS executor orchestration -- module-level entry point."""
    executor = GroundedSynthesisExecutor()
    return executor.execute(synthesis_input, raw_claims, evidence_pool)
