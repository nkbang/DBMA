"""core/grounded_synthesis_input.py — Grounded Synthesis Phase 4: SynthesisInput Boundary.

P3A에서 만든 EvidencePool + AssemblyManifest를 받아, LLM에 실제로 전달할 입력
(SynthesisInput, ADR-036 B8)을 **새 점수 계산이나 재정렬 없이** 결정적 규칙으로 구성한다.

이 Phase는 LLM을 호출하지 않는다 — 입력을 구성하는 순수 함수만 만든다.

Architecture:
    EvidencePool (P2/P3) + AssemblyManifest (P3A)
                    ↓
        build_synthesis_input() (this module, P4)
                    ↓
        SynthesisInput (ADR-036 B8 시그니처)

ABSOLUTE RULES:
- 점수 계산·재정렬·비교 금지 (STOP #20)
- EvidencePool/Evidence 모델 수정 금지 (STOP #2/#3)
- 가짜 provenance 생성 금지 (Evidence 모델 규칙 계승)
- ADR-036 B9 금지 import 없음
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from core.evidence_assembly import AssemblyManifest, QuerySpec
from core.evidence_model import Evidence
from core.evidence_pool import EvidencePool

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SynthesisInput:
    """LLM에 전달할 합성 입력의 결정적 구조 (ADR-036 B8)."""

    query_specs: list[QuerySpec]
    included_evidence_ids: list[str]
    excluded_evidence_ids: list[str]
    truncated: bool
    prompt_text: str


def build_synthesis_input(
    pool: EvidencePool,
    manifest: AssemblyManifest,
    max_evidence: int,
) -> SynthesisInput:
    """EvidencePool + AssemblyManifest로부터 SynthesisInput을 구성한다.

    절단 규칙 (ADR-036 B3):
        질의 순서(manifest.by_query_order) → 각 질의 내부 원 순위 순서로
        라운드로빈하며 evidence_id를 채운다. 이미 included에 들어간 evidence_id는
        건너뛴다(중복 방지, 순서는 최초 등장 기준). max_evidence에 도달하면
        멈추고 나머지는 전부 excluded_evidence_ids에 담는다.
        점수를 읽거나 비교하지 않는다 — evidence_id 자체의 존재 여부와 순서만 사용한다.

    prompt_text는 included_evidence_ids 순서대로 EvidencePool.get(id).text를
    이어붙여 만든다. 각 항목 앞에 "[출처: {source_file 또는 document_title 또는
    '미상'}]"을 붙인다 (가짜 출처를 만들지 않는다 — 값이 없으면 '미상'이라고
    명시적으로 쓴다. ADR-036 B2, Evidence 모델의 '가짜 provenance 금지' 원칙 계승).

    Parameters
    ----------
    pool : EvidencePool
        P3A assembly 결과. 수정하지 않는다.
    manifest : AssemblyManifest
        P3A manifest. by_query_order와 evidence_to_queries를 읽기 전용으로 사용.
    max_evidence : int
        LLM 컨텍스트 예산 상한. 이 개수까지 evidence를 포함한다.

    Returns
    -------
    SynthesisInput
        ADR-036 B8 시그니처에 따른 결정적 입력 구조체.

    Raises
    ------
    ValueError
        max_evidence <= 0 인 경우.
    """
    if max_evidence <= 0:
        raise ValueError(f"max_evidence must be > 0, got {max_evidence}")

    # --- Step 1: 라운드로빈으로 included/excluded evidence_id 결정 ---
    # manifest.by_query_order는 (QuerySpec, list[evidence_id]) 쌍의 리스트.
    # 각 질의 내부의 evidence_id는 retrieval이 반환한 원 순위 순서 그대로.
    included: list[str] = []
    excluded: list[str] = []
    seen: set[str] = set()

    # 라운드로빈: 각 round에서 모든 질의를 한 번씩 돌며 다음 evidence를 취함
    # 각 질의의 남은 evidence가 모두 소진되면 그 질의는 skip
    remaining: list[list[str]] = [list(eids) for _, eids in manifest.by_query_order]

    while len(included) < max_evidence:
        advanced_any = False
        for q_idx in range(len(remaining)):
            if len(included) >= max_evidence:
                break
            if not remaining[q_idx]:
                continue
            eid = remaining[q_idx].pop(0)
            if eid in seen:
                # 이미 included에 있으므로 excluded에도 넣지 않음 (중복 제거)
                continue
            seen.add(eid)
            included.append(eid)
            advanced_any = True
        if not advanced_any:
            # 모든 질의의 evidence가 소진되었는데도 max_evidence에 도달하지 못함
            break

    # remaining에 남아있는 것들은 excluded (seen에 없었던 것들)
    for q_remaining in remaining:
        for eid in q_remaining:
            if eid not in seen:
                seen.add(eid)
                excluded.append(eid)

    truncated = len(excluded) > 0

    # --- Step 2: prompt_text 구성 ---
    prompt_parts: list[str] = []
    for eid in included:
        ev = pool.get(eid)
        if ev is None:
            # pool에 없는 evidence_id는 manifest에 있을 수 있음 (예: overwrite 전 기록)
            # 이 경우 텍스트를 생략하고 출처도 '미상'으로 처리
            prompt_parts.append("[출처: 미상]\n(증거 ID {eid} — text 없음)")
            continue
        # 출처 결정: source_file → document_title → '미상' (가짜 생성 금지)
        if ev.source_file is not None:
            source_label = ev.source_file
        elif ev.document_title is not None:
            source_label = ev.document_title
        else:
            source_label = "미상"
        prompt_parts.append(f"[출처: {source_label}]\n{ev.text}")

    prompt_text = "\n\n".join(prompt_parts)

    return SynthesisInput(
        query_specs=[qs for qs, _ in manifest.by_query_order],
        included_evidence_ids=included,
        excluded_evidence_ids=excluded,
        truncated=truncated,
        prompt_text=prompt_text,
    )