"""scripts/crosswalk/tsu_gate.py — TSU Gate Adapter interface
(NAE-CROSSWALK-ADAPTER-IMPLEMENTATION-001 §7,
NAE-TSU-GATE-RELIABILITY-IMPLEMENTATION-001 Phase 1 — TSU_GATE_ERROR).

**Interface만** — `NAE/pipeline/tsu/`, Manifest, Migration Engine 코드는
전혀 수정하지 않는다. 이 모듈은 이미 계산된 값(TSU_ELIGIBLE 여부,
CrosswalkRecord, 저장소 오류 여부)을 인자로 받아 최종 판정만 내린다 —
저장소 조회/검증 자체는 `GateOrchestrator`(`gate_orchestrator.py`)가
수행하고 그 결과만 이 함수에 넘긴다.

3-상태 모델(`docs/NAE_TSU_GATE_CONNECTION_DESIGN_001.md` §4):

- `TSU_GATE_PASS`  — Gate 통과, TSU 생성 가능
- `TSU_GATE_BLOCK` — 정상적인 대기 상태(사람 확인 전, confidence 부족 등)
- `TSU_GATE_ERROR` — Crosswalk Storage 자체를 신뢰할 수 없는 상태
  (YAML 파싱 실패, 스키마 검증 실패, 저장소 접근 불가 등) — BLOCK과
  절대 같은 것으로 취급하지 않는다("아직 매핑 안 됨"과 "저장소가
  고장났다"는 다른 문제).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .schema import CrosswalkRecord, MappingStatus


class TsuGateStatus(str, Enum):
    PASS = "TSU_GATE_PASS"
    BLOCK = "TSU_GATE_BLOCK"
    ERROR = "TSU_GATE_ERROR"


@dataclass
class TsuGateResult:
    status: TsuGateStatus
    reason: str

    @property
    def eligible(self) -> bool:
        """하위 호환: 기존 호출자(`result.eligible`)가 이전 2-상태
        모델과 동일하게 계속 동작하도록 유지한다 — `PASS`일 때만 True."""
        return self.status == TsuGateStatus.PASS


def check_tsu_gate(
    tsu_eligible: bool,
    crosswalk_record: CrosswalkRecord | None,
    storage_error: str | None = None,
) -> TsuGateResult:
    """TSU_ELIGIBLE == READY AND crosswalk mapping_status == manual-confirmed
    (NAE_TSU_IDENTIFIER_CONTRACT_001.md §4 Gate 정의)을 판정한다.

    `crosswalk_record`는 호출자가 `CrosswalkResolver.resolve_record()`로
    이미 조회해 넘긴다 — 이 함수는 조회를 수행하지 않는다(순수 판정
    함수, 부작용 없음).

    `storage_error`가 주어지면(저장소 검증 실패 메시지) 다른 조건과
    무관하게 즉시 `TSU_GATE_ERROR`를 반환한다 — ERROR는 BLOCK보다
    우선 판정되는 최상위 상태다(저장소를 신뢰할 수 없으면 그 안의
    어떤 판정도 신뢰할 수 없으므로).
    """
    if storage_error is not None:
        return TsuGateResult(status=TsuGateStatus.ERROR, reason=f"Crosswalk Storage 오류: {storage_error}")

    if not tsu_eligible:
        return TsuGateResult(status=TsuGateStatus.BLOCK, reason="TSU_ELIGIBLE != READY")

    if crosswalk_record is None:
        return TsuGateResult(status=TsuGateStatus.BLOCK, reason="Crosswalk mapping 없음")

    if crosswalk_record.mapping_status != MappingStatus.MANUAL_CONFIRMED:
        return TsuGateResult(
            status=TsuGateStatus.BLOCK,
            reason=f"mapping_status={crosswalk_record.mapping_status.value!r} != 'manual-confirmed'",
        )

    if not crosswalk_record.is_gate_eligible():
        return TsuGateResult(
            status=TsuGateStatus.BLOCK,
            reason="Crosswalk Record가 Gate 조건(confidence/evidence)을 만족하지 않음",
        )

    return TsuGateResult(
        status=TsuGateStatus.PASS, reason="TSU_ELIGIBLE=READY AND mapping_status=manual-confirmed"
    )
