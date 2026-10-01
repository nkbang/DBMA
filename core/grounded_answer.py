"""core/grounded_answer.py -- Grounded Synthesis Phase 6: GroundedAnswer Assembly.

Claim[]을 받아 최종 GroundedAnswer(ADR-036 B8)를 조립한다. 이 Phase도
**stub LLM만 사용**한다(실모델은 P9). 목표는 문장 생성 품질이 아니라
grounding integrity -- 정상/부족/충돌 세 상태를 안전하게 표현하는 구조다.

이 모듈은 core/generation.py의 grounding 상수를 import하지 않는다.
문구 스타일 참고용으로만 읽을 수 있지만, import나 값 변경은 하지 않는다.
교단 신학 관점 지시문은 사용하지 않는다(GS-00 §1 O1).

Architecture:
    Claim[] + SynthesisInput
            ↓
        assemble_grounded_answer() (this module, P6)
            ↓
        GroundedAnswer (ADR-036 B8 시그니처)

ABSOLUTE RULES:
- 자동 충돌 상태 판정(텍스트 비교, 어휘 분석 등) 금지 -- 호출자 명시 플래그만 사용
- insufficient 상태의 text가 "일반적으로", "일반적인 신학적 관점에서" 등 금지 표현 포함 안 함
- invalid claim을 폐기하지 않음 -- GroundedAnswer.claims에 그대로 남김
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, Optional

from core.grounded_claims import Claim
from core.grounded_synthesis_input import SynthesisInput

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GroundedAnswer:
    """LLM의 최종 답변 구조 (ADR-036 B5, B8)."""

    status: Literal["grounded", "insufficient_evidence", "conflicting_evidence"]
    claims: list[Claim]
    text: str
    insufficiency_reason: Optional[str]


def assemble_grounded_answer(
    claims: list[Claim],
    synthesis_input: SynthesisInput,
    conflicting: bool = False,
) -> GroundedAnswer:
    """Claim[]을 GroundedAnswer로 조립한다.

    상태 판정 규칙:
        1. included_evidence_ids가 비어 있으면 -> status="insufficient_evidence",
           insufficiency_reason="no_evidence"
        2. conflicting=True이면 -> status="conflicting_evidence"
        3. claims가 전부 valid=False이면 -> status="insufficient_evidence",
           insufficiency_reason="no_valid_claim"
        4. valid=True인 claim이 하나 이상 있으면 -> status="grounded"

    text 구성:
        - grounded: valid claim들의 text를 순서대로 이어붙임 (invalid claim text 제외)
        - insufficient: 고정 문구 ("이 질문은 현재 등록된 자료로는 답할 수 없습니다.")
        - conflicting: "자료들이 서로 다른 견해를 제시합니다." + 각 claim을 evidence_id와
          함께 병기

    자동 충돌 상태 판정(텍스트 비교, 어휘 분석 등)은 하지 않는다.
    호출자가 conflicting=True 플래그를 명시적으로 넘겨야 conflicting_evidence 상태로 진입한다.

    Parameters
    ----------
    claims : list[Claim]
        P5에서 추출·결속한 Claim 목록. valid=False인 claim도 포함될 수 있음.
    synthesis_input : SynthesisInput
        P4에서 구성한 SynthesisInput. included_evidence_ids가 기준 집합.
    conflicting : bool
        호출자가 명시하는 충돌 상태 플래그. 자동 판정하지 않음.

    Returns
    -------
    GroundedAnswer
        ADR-036 B8 시그니처에 따른 구조체.
    """
    # --- 상태 1: included_evidence_ids가 비어 있음 ---
    if len(synthesis_input.included_evidence_ids) == 0:
        return GroundedAnswer(
            status="insufficient_evidence",
            claims=claims,
            text="이 질문은 현재 등록된 자료로는 답할 수 없습니다.",
            insufficiency_reason="no_evidence",
        )

    # --- 상태 2: 호출자가 충돌 플래그 설정 ---
    if conflicting:
        valid_claims = [c for c in claims if c.valid]
        invalid_claims = [c for c in claims if not c.valid]

        parts = ["자료들이 서로 다른 견해를 제시합니다."]
        for c in claims:
            eid_str = ", ".join(c.evidence_ids) if c.evidence_ids else "근거 없음"
            parts.append(f"[{eid_str}] {c.text}")

        return GroundedAnswer(
            status="conflicting_evidence",
            claims=claims,
            text="\n\n".join(parts),
            insufficiency_reason=None,
        )

    # --- 상태 3: 모든 claim이 valid=False ---
    valid_claims = [c for c in claims if c.valid]
    if len(valid_claims) == 0 and len(claims) > 0:
        return GroundedAnswer(
            status="insufficient_evidence",
            claims=claims,
            text="이 질문은 현재 등록된 자료로는 답할 수 없습니다.",
            insufficiency_reason="no_valid_claim",
        )

    # --- 상태 4: valid=True claim 존재 -> grounded ---
    if len(valid_claims) > 0:
        text_parts = [c.text for c in valid_claims]
        return GroundedAnswer(
            status="grounded",
            claims=claims,
            text="\n\n".join(text_parts),
            insufficiency_reason=None,
        )

    # --- claims가 아예 빈 경우 ---
    return GroundedAnswer(
        status="insufficient_evidence",
        claims=claims,
        text="이 질문은 현재 등록된 자료로는 답할 수 없습니다.",
        insufficiency_reason="no_claims",
    )
