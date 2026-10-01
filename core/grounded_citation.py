"""core/grounded_citation.py -- Grounded Synthesis Phase 7: Citation Provenance Check.

P6가 생성한 GroundedAnswer의 각 claim에 대해, 인용된 evidence_id가
(1) SynthesisInput.included_evidence_ids에 실제로 존재하는지,
(2) 해당 Evidence.text에 인용 구간(span)이 실제로 있는지,
(3) Evidence.has_provenance로 출처 추적 가능한지를 검사한다.

의미적 뒷받침(claim이 evidence를 정말로 지지하는가)은 다루지 않는다 --
구조적·사후 검증만 수행한다(ADR-036 B6 "결정적 검사").

Architecture:
    GroundedAnswer (P6) + SynthesisInput (P4) + EvidencePool (P2/P3)
                            ↓
        check_citation_provenance() (this module, P7)
                            ↓
        CitationCheckReport (pass/fail per claim×evidence pair)

ABSOLUTE RULES:
- 의미적 분석 금지 -- 구조적 존재 여부만 검사
- 가짜 provenance 생성 금지
- Evidence.text를 읽어서 span 존재 여부만 확인 (의미 해석 아님)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from core.evidence_model import Evidence
from core.evidence_pool import EvidencePool
from core.grounded_answer import GroundedAnswer
from core.grounded_synthesis_input import SynthesisInput

logger = logging.getLogger(__name__)


# ============================================================================
# Span Found Criteria (P7 결정적 기준)
# ============================================================================
# span_found_in_text 판정을 위한 명시적 기준:
#
# 1. 최소 길이: 5자 이상
#    - 5자 미만은 trivial match이므로 제외
#    - 공백 포함 계수 (trim 하지 않음 -- 원문 그대로 비교)
#
# 2. 정확 부분일치 (exact substring match)
#    - case-sensitive
#    - Evidence.text.find(span_text) >= 0 이면 True
#
# 3. claim text 전체를 span으로 사용
#    - claim.text가 5자 이상이면 그대로 사용
#    - claim.text가 5자 미만이면 span_found_in_text = False (자동 실패)
#
# 4. 중복 인용 구간 허용
#    - 같은 span이 Evidence.text에 여러 번 나타나도 한 번만 찾으면 True


@dataclass(frozen=True)
class CitationCheckResult:
    """하나의 claim×evidence pair에 대한 citation provenance 검사 결과."""

    claim_id: str
    evidence_id: str
    id_exists: bool  # evidence_id in SynthesisInput.included_evidence_ids
    span_found_in_text: bool  # Evidence.text에 claim text가 부분일치로 존재
    provenance_traceable: bool  # Evidence.has_provenance


@dataclass(frozen=True)
class CitationCheckReport:
    """전체 citation provenance 검사 보고서."""

    results: list[CitationCheckResult] = field(default_factory=list)

    @property
    def total_checks(self) -> int:
        return len(self.results)

    @property
    def id_missing_count(self) -> int:
        return sum(1 for r in self.results if not r.id_exists)

    @property
    def span_not_found_count(self) -> int:
        return sum(1 for r in self.results if not r.span_found_in_text)

    @property
    def provenance_untraceable_count(self) -> int:
        return sum(1 for r in self.results if not r.provenance_traceable)

    @property
    def all_passed(self) -> bool:
        """모든 검사가 통과했는지 (의미적 검증 아님 -- 구조적 검사만)."""
        return (
            self.id_missing_count == 0
            and self.span_not_found_count == 0
            and self.provenance_untraceable_count == 0
        )

    @property
    def claim_summary(self) -> dict[str, list[CitationCheckResult]]:
        """claim_id별 결과 그룹핑."""
        summary: dict[str, list[CitationCheckResult]] = {}
        for r in self.results:
            summary.setdefault(r.claim_id, []).append(r)
        return summary


def _check_span_in_text(claim_text: str, evidence_text: str) -> bool:
    """claim text가 evidence text에 부분일치로 존재하는지 검사.

    판정 기준:
        1. claim_text 길이가 5자 미만이면 False (trivial match 제외)
        2. case-sensitive 부분일치: evidence_text.find(claim_text) >= 0
    """
    if len(claim_text) < 5:
        return False
    return evidence_text.find(claim_text) >= 0


def check_citation_provenance(
    grounded_answer: GroundedAnswer,
    synthesis_input: SynthesisInput,
    evidence_pool: EvidencePool,
) -> CitationCheckReport:
    """GroundedAnswer의 각 claim에 대해 citation provenance를 검사한다.

    P6가 생성한 GroundedAnswer를 사후 검증 -- 의미적 뒷받침이 아닌
    구조적 존재 여부만 확인한다(ADR-036 B6 "결정적 검사").

    Parameters
    ----------
    grounded_answer : GroundedAnswer
        P6가 생성한 최종 답변. claims에 각 claim의 evidence_ids 포함.
    synthesis_input : SynthesisInput
        P4가 구성한 입력. included_evidence_ids가 기준 집합.
    evidence_pool : EvidencePool
        P2/P3가 채운 증거 풀. get(eid)로 Evidence.text 접근 가능.

    Returns
    -------
    CitationCheckReport
        각 claim×evidence pair에 대한 검사 결과와 요약 통계.
    """
    included_ids = set(synthesis_input.included_evidence_ids)
    results: list[CitationCheckResult] = []

    for claim in grounded_answer.claims:
        if not claim.evidence_ids:
            # evidence_ids가 빈 claim은 검사 대상에서 제외 (P5에서 valid=False로 표시됨)
            continue

        for eid in claim.evidence_ids:
            # --- Check 1: id_exists ---
            id_exists = eid in included_ids

            if not id_exists:
                # AC1: 존재하지 않는(이번 답변에 실제로 전달되지 않은) 근거의
                # 하위 검사를 수행하지 않는다 — 자동으로 False.
                results.append(CitationCheckResult(
                    claim_id=claim.claim_id,
                    evidence_id=eid,
                    id_exists=False,
                    span_found_in_text=False,
                    provenance_traceable=False,
                ))
                continue

            # --- Check 2: span_found_in_text ---
            ev = evidence_pool.get(eid)
            if ev is not None:
                span_found = _check_span_in_text(claim.text, ev.text)
            else:
                # pool에 없는 evidence_id -> span 검사 불가
                span_found = False

            # --- Check 3: provenance_traceable ---
            provenance_ok = ev.has_provenance if ev is not None else False

            results.append(CitationCheckResult(
                claim_id=claim.claim_id,
                evidence_id=eid,
                id_exists=True,
                span_found_in_text=span_found,
                provenance_traceable=provenance_ok,
            ))

    # 요약 통계 계산 (computed properties이므로 별도 할당 불필요)
    return CitationCheckReport(results=results)