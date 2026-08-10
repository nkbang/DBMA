"""scripts/crosswalk/gate_orchestrator.py — TSU Gate Orchestrator
(NAE-TSU-GATE-RELIABILITY-IMPLEMENTATION-001 Phase 3).

Resolver → Storage Validation → TSU Gate를 연결하는 오케스트레이션
계층이다. `docs/NAE_TSU_GATE_CONNECTION_DESIGN_001.md` §3의 "미구현"
표시 부분을 채운다.

**이 모듈이 하지 않는 것**(작업 명령서 §Phase3 "금지" 그대로):
TSU 생성, Manifest 수정, RAW 접근, Retrieval 호출, Embedding 생성 —
이 파일은 위 5가지 중 어느 것도 import하지 않는다(아래 import 목록이
그 증거): `scripts.crosswalk.resolver`, `scripts.crosswalk.tsu_gate`,
`scripts.crosswalk.repository`뿐.
"""

from __future__ import annotations

from dataclasses import dataclass

from .repository import CrosswalkRepository
from .resolver import CrosswalkResolver
from .tsu_gate import TsuGateResult, check_tsu_gate


@dataclass
class ManifestEntryInput:
    """Gate 판정에 필요한 최소 입력(NAE_TSU_GATE_CONNECTION_DESIGN_001.md
    §1 Gate Contract의 `source_id`/`tsu_eligible` 부분 — `canonical_id`/
    `legacy_id`는 판정에 쓰이지 않으므로 이 입력 구조에 포함하지 않는다,
    Contract 문서와 동일 결론)."""

    source_identifier: str
    tsu_eligible: bool


class GateOrchestrator:
    """Manifest Entry 하나를 받아 Resolver→Storage Validation→TSU Gate
    순서로 평가해 최종 `TsuGateResult`(PASS/BLOCK/ERROR)를 반환한다.

    `repository`가 `validate_storage()`를 제공하면(예:
    `YamlCrosswalkRepository`) 매 평가 전에 저장소 무결성을 먼저
    확인한다 — 제공하지 않는 저장소(예: `InMemoryCrosswalkRepository`)
    라면 이 단계를 건너뛴다(구조적으로 손상될 수 없는 저장소이므로).
    """

    def __init__(self, repository: CrosswalkRepository, resolver: CrosswalkResolver | None = None) -> None:
        self.repository = repository
        self.resolver = resolver or CrosswalkResolver(repository)

    def evaluate(self, entry: ManifestEntryInput) -> TsuGateResult:
        validate_storage = getattr(self.repository, "validate_storage", None)
        if callable(validate_storage):
            ok, error = validate_storage()
            if not ok:
                return check_tsu_gate(entry.tsu_eligible, None, storage_error=error)

        try:
            record = self.resolver.resolve_record(entry.source_identifier)
        except Exception as exc:  # noqa: BLE001 — Resolver/Repository 예외를 ERROR로 흡수
            return check_tsu_gate(entry.tsu_eligible, None, storage_error=str(exc))

        return check_tsu_gate(entry.tsu_eligible, record)
