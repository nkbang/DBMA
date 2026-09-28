"""core/grounded_claims.py — Grounded Synthesis Phase 5: Claim–Evidence Binding.

LLM(이 Phase에서는 stub만 사용 — 실모델은 P9)이 생성한 답변 텍스트에서
Claim을 추출하고, 각 Claim이 어떤 evidence_id에 근거하는지 결속한다.
그리고 그 evidence_id가 SynthesisInput.included_evidence_ids의 부분집합인지 검사한다.

이 모듈은 어휘 기반 위험 탐지 모듈(별도 운영 경로)을 import하지 않는다 —
이름이 비슷하지만 목적이 다르다:
  - 위험 탐지 모듈(ClaimGuard): 어휘 기반 위험 탐지 (운영 경로)
  - 이 모듈: 구조적 근거 결속 검증 계층 (Grounded Synthesis 신규 계층)
두 모듈은 import하지도, 서로 호출하지도 않는다(ADR-036 B1).

Architecture:
    SynthesisInput (P4) + raw_claims [(claim_text, cited_evidence_ids)]
                    ↓
        bind_claims() (this module, P5)
                    ↓
        list[Claim] (ADR-036 B8 시그니처)

ABSOLUTE RULES:
- 위험 탐지 모듈 import 금지 (별도 운영 모듈)
- 프롬프트 텍스트나 Evidence.text를 읽어 인용 구간 실재 여부 검사하지 않음 (P7 책임)
- 유효하지 않은 evidence_id를 포함해도 Claim을 폐기하지 않음 — valid=False로 표시만 함
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from core.grounded_synthesis_input import SynthesisInput

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Claim:
    """하나의 주장과 그 근거 evidence_id의 결속 (ADR-036 B4, B8)."""

    claim_id: str
    text: str
    evidence_ids: list[str]
    valid: bool  # evidence_ids ⊆ synthesis_input.included_evidence_ids


class ClaimExtractor(Protocol):
    """P5 stub 구현 + P9 실모델 구현이 공유하는 인터페이스.

    stub은 미리 정한 (claim_text, evidence_ids) 목록을 그대로 반환하는
    결정적 함수(네트워크·LLM 호출 없음).
    """

    def extract(self, answer_text: str, synthesis_input: SynthesisInput) -> list[Claim]: ...


def bind_claims(
    raw_claims: list[tuple[str, list[str]]],
    synthesis_input: SynthesisInput,
) -> list[Claim]:
    """raw_claims을 SynthesisInput.included_evidence_ids와 결속한다.

    cited_evidence_ids ⊆ included_evidence_ids 여부로 valid를 결정한다.
    유효하지 않은 evidence_id를 포함해도 Claim을 폐기하지 않는다 — valid=False로
    표시만 한다(정보 손실 금지, ADR-036 B4).

    이 함수는 SynthesisInput의 프롬프트 텍스트나 Evidence.text를 읽어
    인용 구간이 실제로 텍스트에 있는지 검사하지 않는다(그건 P7의 책임).
    ID 소속 여부만 본다.

    Parameters
    ----------
    raw_claims : list[tuple[str, list[str]]]
        (claim_text, cited_evidence_ids) 쌍의 리스트.
        cited_evidence_ids는 이 Claim이 근거로 제시하는 evidence_id 목록.
    synthesis_input : SynthesisInput
        P4에서 구성한 SynthesisInput. included_evidence_ids가 기준 집합.

    Returns
    -------
    list[Claim]
        각 Claim은 valid 필드에 결속 결과를 포함.
        유효하지 않은 Claim도 리스트에 남아 있음 (폐기 없음).
    """
    included_set = set(synthesis_input.included_evidence_ids)
    claims: list[Claim] = []

    for idx, (claim_text, cited_eids) in enumerate(raw_claims):
        claim_id = f"claim_{idx:03d}"

        # valid: cited_eids가 전부 included_set의 부분집합이고, 비어있지 않을 때 True
        if len(cited_eids) == 0:
            valid = False
        else:
            valid = all(eid in included_set for eid in cited_eids)

        claims.append(Claim(
            claim_id=claim_id,
            text=claim_text,
            evidence_ids=cited_eids,
            valid=valid,
        ))

    return claims


class StubClaimExtractor:
    """P5용 stub ClaimExtractor — 미리 정한 목록을 결정적으로 반환.

    네트워크·LLM 호출 없음. 같은 입력에 항상 같은 출력.
    P9에서 실제 LLM 기반 구현으로 교체된다.
    """

    def __init__(self, claims_map: dict[str, list[tuple[str, list[str]]]] | None = None) -> None:
        """claims_map: answer_text의 부분 문자열 → (claim_text, cited_evidence_ids) 매핑.

        extract()는 answer_text에서 claims_map의 키(부분 문자열)를 찾아
        해당하는 raw_claims을 반환한다. 여러 키가 매치하면 모두 수집.
        """
        self.claims_map = claims_map or {}

    def extract(self, answer_text: str, synthesis_input: SynthesisInput) -> list[Claim]:
        """answer_text에서 미리 정한 claim 목록을 추출하고 결속한다."""
        raw_claims: list[tuple[str, list[str]]] = []
        for pattern, claims_list in self.claims_map.items():
            if pattern in answer_text:
                raw_claims.extend(claims_list)

        return bind_claims(raw_claims, synthesis_input)
