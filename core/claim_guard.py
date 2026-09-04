"""ClaimGuard — Sprint D: 위험 주장 탐지 · 절대주장 차단 · 범위 한정 문구.

검색 파이프라인에서 "이 근거로 이런 문장을 말해도 되는가"를 판정한다.
실제 LLM 응답 생성 파이프라인에 끼워 넣는 것(어디서 호출할지)은 범위 밖.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.parallel_retriever import EvidenceCandidate


# ---------------------------------------------------------------------------
# 위험 표현 사전 (지시서 원문 그대로)
# ---------------------------------------------------------------------------

ABSOLUTE_SUPERLATIVE_TERMS = [
    "최초", "처음", "가장 이른", "유일", "반드시", "전부", "항상", "절대", "명백히",
    "성경 전체에서", "정통 교리", "모든 학자", "학계의 합의",
    "성경이 가르친다", "원어의 정확한 의미는", "역사적으로 확실하다",
    # Sprint D 추가 (미탐 15건에서 실제 확인된 표현)
    # bare "가장"과 bare "모든"은 neutral fp 유발으로 제거 (Task Order 027)
    "가장 먼저", "유일하게", "가장 작은", "최초로", "절대적인",
]


# ---------------------------------------------------------------------------
# 판정 결과 모델
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    HIGH = "high"


@dataclass
class ClaimGuardResult:
    risk_level: RiskLevel
    matched_terms: list[str] = field(default_factory=list)
    scope_qualifier_required: bool = False
    absolute_claim_blocked: bool = False
    competing_candidates_found: bool = False
    reason: str = ""
    suggested_wording: str | None = None


# ---------------------------------------------------------------------------
# 핵심 클래스
# ---------------------------------------------------------------------------

class ClaimGuard:
    """위험 주장 탐지 · 절대주장 차단 · 범위 한정 문구 판정기."""

    def __init__(self, parallel_retriever_db_path: str | None = None) -> None:
        """
        Args:
            parallel_retriever_db_path: competing-candidate 탐색용
                (bible_tag_annotation 조회) — None이면 경쟁후보 탐색을 건너뛰고
                보수적으로 판정(no_full_corpus_comparison_exists=True로 취급).
        """
        self.db_path = parallel_retriever_db_path

    def detect_risk(self, claim_text: str) -> tuple[RiskLevel, list[str]]:
        """claim_text에서 ABSOLUTE_SUPERLATIVE_TERMS 매칭 검사.
        1개 이상 매칭 시 HIGH, 매칭 없으면 NONE. (LOW는 이번엔 미사용 —
        향후 확장 대비 enum에만 남겨둠)"""
        matched: list[str] = []
        for term in ABSOLUTE_SUPERLATIVE_TERMS:
            if term in claim_text:
                matched.append(term)
        if matched:
            return (RiskLevel.HIGH, matched)
        return (RiskLevel.NONE, [])

    def evaluate(
        self,
        claim_text: str,
        evidence: list["EvidenceCandidate"],
        tag_name: str | None = None,
    ) -> ClaimGuardResult:
        """
        규칙 (지시서 원문 그대로, evidence의 trust_tier 분포로 판단):

        1. detect_risk(claim_text)로 위험 표현 탐지.
           매칭 없으면 ClaimGuardResult(risk_level=NONE, ...) 바로 반환 (아래 규칙 불필요).

        2. 위험 표현이 있는 경우:
           a. evidence에 trust_tier == T1인 항목이 하나도 없으면
              → absolute_claim_blocked=True, reason="T1(본문) 근거 없이 절대·최상급 주장 불가"
           b. evidence가 전부 T2 또는 T4뿐이면 (T1/T3 없음)
              → absolute_claim_blocked=True, scope_qualifier_required=True,
                reason="T2/T4 단독 근거로는 절대 주장 불가 — 데이터셋 범위 한정 필요"
           c. tag_name이 주어졌고 parallel_retriever_db_path가 있으면:
              _find_competing_candidates(tag_name)로 동일 태그의 다른 canonical_reference가
              2개 이상 있는지 확인 → 있으면 competing_candidates_found=True.
              없으면(또는 db_path가 None이면) competing_candidates_found=False,
              → 이 경우 absolute_claim_blocked=True,
                reason="전체 코퍼스 비교 불가 — '최초/유일' 주장 차단 (no_full_corpus_comparison_exists)"
           d. a~c 모두 통과(T1 근거 있음 + T2/T4 단독 아님 + 경쟁후보 확인됨)해도
              scope_qualifier_required=True는 유지 (완전한 절대 주장은 허용하지 않음 — 항상
              범위 한정 문구를 요구하는 게 이 시스템의 기본값).

        3. suggested_wording 채우기: §2.3의 템플릿 중 근거 상태에 맞는 것을 선택.
        """
        # Rule 1: 위험 표현 탐지
        risk_level, matched_terms = self.detect_risk(claim_text)
        if risk_level == RiskLevel.NONE:
            return ClaimGuardResult(
                risk_level=RiskLevel.NONE,
                matched_terms=[],
                scope_qualifier_required=False,
                absolute_claim_blocked=False,
                competing_candidates_found=False,
                reason="",
                suggested_wording=None,
            )

        # Rule 2: 위험 표현이 있는 경우 — 순서: 2b → 2a → 2c → 2d
        # TrustTier 분석
        has_t1 = False
        has_t3 = False
        only_t2_or_t4 = True
        for cand in evidence:
            if cand.trust_tier.value == "T1":
                has_t1 = True
                only_t2_or_t4 = False
            elif cand.trust_tier.value == "T3":
                has_t3 = True
                only_t2_or_t4 = False
            elif cand.trust_tier.value in ("T2", "T4"):
                pass  # only_t2_or_t4는 이미 True일 수 있음

        result = ClaimGuardResult(
            risk_level=risk_level,
            matched_terms=matched_terms,
            scope_qualifier_required=False,
            absolute_claim_blocked=False,
            competing_candidates_found=False,
            reason="",
            suggested_wording=None,
        )

        # Rule 2b: T2/T4 단독 근거 (먼저 검사 — T1 없으면 2a로 감)
        if only_t2_or_t4:
            result.absolute_claim_blocked = True
            result.scope_qualifier_required = True
            result.reason = "T2/T4 단독 근거로는 절대 주장 불가 — 데이터셋 범위 한정 필요"
            # suggested_wording 채우기
            if evidence:
                first = evidence[0]
                if first.dataset_id and first.tag_name and first.canonical_reference:
                    result.suggested_wording = self._scope_statement(
                        first.dataset_id, first.tag_name, first.canonical_reference
                    )
            return result

        # Rule 2c: 경쟁 후보 탐색
        competing_count = 0
        if tag_name and self.db_path:
            competing_count = self._find_competing_candidates(tag_name)

        if competing_count >= 2:
            result.competing_candidates_found = True
            # a~c 모두 통과 — scope_qualifier만 요구
            result.scope_qualifier_required = True
            result.absolute_claim_blocked = False
            result.reason = "경쟁 후보 확인됨 — 범위 한정 문구 필요"
            # suggested_wording 채우기
            if evidence:
                first = evidence[0]
                if first.dataset_id and first.tag_name and first.canonical_reference:
                    result.suggested_wording = self._scoped_conclusion_statement(
                        first.canonical_reference, first.scope or "정의 없음"
                    )
        else:
            # db_path가 None이거나 competing_count < 2
            result.absolute_claim_blocked = True
            result.reason = "전체 코퍼스 비교 불가 — '최초/유일' 주장 차단 (no_full_corpus_comparison_exists)"
            # suggested_wording 채우기
            if evidence:
                first = evidence[0]
                if first.dataset_id and first.tag_name and first.canonical_reference:
                    result.suggested_wording = self._scope_statement(
                        first.dataset_id, first.tag_name, first.canonical_reference
                    )

        # Rule 2d: scope_qualifier_required 기본값 유지
        if not result.absolute_claim_blocked:
            result.scope_qualifier_required = True

        return result

    def _find_competing_candidates(self, tag_name: str) -> int:
        """bible_tag_annotation에서 tag_name으로 조회했을 때 서로 다른
        canonical_reference가 몇 개인지 반환 (SELECT DISTINCT). db_path가
        없으면 0 반환."""
        if not self.db_path:
            return 0

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT COUNT(DISTINCT canonical_reference)
                FROM bible_tag_annotation
                WHERE tag_name = ?
                """,
                (tag_name,),
            )
            row = cursor.fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    # -----------------------------------------------------------------------
    # 문장 템플릿 (§2.3)
    # -----------------------------------------------------------------------

    def _scope_statement(self, dataset_id: str, tag_name: str, canonical_reference: str) -> str:
        return f"해당 데이터셋({dataset_id})의 `{tag_name}` 태그 검색에서 {canonical_reference}가 결과로 나타난다."

    def _textual_observation_statement(self, canonical_reference: str, observation: str) -> str:
        return f"{canonical_reference}는 {observation}."

    def _scoped_conclusion_statement(self, canonical_reference: str, definition_note: str) -> str:
        return f"이 정의({definition_note}) 아래 {canonical_reference}는 가장 이른 사례 중 하나로 볼 수 있다."


# ---------------------------------------------------------------------------
# 헬퍼: RankedCandidate → EvidenceCandidate 감싸기
# ---------------------------------------------------------------------------

from core.parallel_retriever import EvidenceCandidate  # noqa: E402
from core.parallel_retriever import TrustTier  # noqa: E402


def wrap_ranked_candidates(
    candidates: list["RankedCandidate"],
) -> list["EvidenceCandidate"]:
    """core.retrieval.RankedCandidate 리스트를 core.parallel_retriever.EvidenceCandidate
    리스트로 감싼다 (evidence_axis="t1_hybrid_search", trust_tier=T1).
    GenerationService가 ParallelRetriever 없이도(현재 QueryProcessor는
    ParallelRetriever를 쓰지 않음) response.candidates만으로 ClaimGuard를
    호출할 수 있게 하는 어댑터."""
    from core.retrieval import RankedCandidate  # noqa: F811

    result: list[EvidenceCandidate] = []
    for c in candidates:
        if isinstance(c, RankedCandidate):
            evidence = EvidenceCandidate(
                canonical_reference=c.metadata.get("canonical_reference"),
                evidence_axis="t1_hybrid_search",
                trust_tier=TrustTier.T1,
                ranked_candidate=c,
                dataset_id=c.metadata.get("dataset_id"),
                tag_namespace=c.metadata.get("tag_namespace"),
                tag_name=c.metadata.get("tag_name"),
                scope=c.metadata.get("scope"),
            )
            result.append(evidence)
        else:
            # 이미 EvidenceCandidate인 것은 그대로 통과
            result.append(c)  # type: ignore[list-item]
    return result
