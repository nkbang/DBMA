"""NAE/pipeline/tsu/gate_adapter.py — Crosswalk Gate Wiring Adapter
(NAE-TSU-PIPELINE-WIRING-IMPLEMENTATION-001 Phase 1).

Decides *which* identifiers are eligible for TSU generation by routing
Manifest entries through Crosswalk Resolver -> TSU Gate. This module
never builds TSU records itself — `builder.build_tsu_for_identifier`/
`build_tsu_for_all` are not imported here (구현 금지: "Builder 호출
금지", 작업 명령서 Phase 1). `builder.py` is untouched by this task
(0 lines changed) — the only wiring point is in `runner.py`.

Reuses `scripts/manifest_validator.py`'s existing TSU_ELIGIBLE
computation (`compute_tsu_eligible`, FK verification, registry/corpus
manifest indices) rather than re-implementing it — that module is not
modified by this task, only imported and called (read-only use).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.crosswalk.gate_orchestrator import GateOrchestrator, ManifestEntryInput
from scripts.crosswalk.storage.yaml_repository import YamlCrosswalkRepository
from scripts.crosswalk.tsu_gate import TsuGateStatus
from scripts.manifest_validator import (
    ValidationResult,
    _validate_authority_fk,
    compute_tsu_eligible,
    find_manifest_files,
    load_corpus_manifest_index,
    load_manifest_file,
    load_registry_index,
)

DEFAULT_MANIFEST_ROOT = _REPO_ROOT / "resources" / "theological_sources" / "manifest" / "pilot"
DEFAULT_REGISTRY_PATH = _REPO_ROOT / "resources" / "theological_sources" / "authority"
DEFAULT_CORPUS_MANIFEST_ROOT = _REPO_ROOT / "resources" / "theological_sources"
DEFAULT_CROSSWALK_YAML = _REPO_ROOT / "NAE" / "metadata" / "crosswalk" / "crosswalk.yaml"
DEFAULT_CROSSWALK_INDEX = _REPO_ROOT / "NAE" / "metadata" / "crosswalk" / "index.json"


@dataclass
class GateWiringSummary:
    """Phase 5(Summary Report)가 필요로 하는 PASS/BLOCK/ERROR 집계.

    설계 문서(`NAE_TSU_PIPELINE_WIRING_DESIGN_001.md` §Phase4)는
    `iter_eligible_identifiers`가 `Iterator[str]`만 반환하는 것으로
    스케치했으나, 구현 과정에서 Runner의 Summary Report(Phase 5, PASS/
    BLOCK/ERROR 건수 + BLOCK/ERROR 상세 출력 요구)가 단순 문자열
    스트림만으로는 불가능하다는 것이 확인되어, PASS된 identifier
    목록과 집계를 함께 담는 이 dataclass로 반환하도록 구체화했다
    (인터페이스 확장 — 설계 의도 위반 아님, PASS 목록도 여전히
    포함되어 있어 "eligible identifier만 추려 넘긴다"는 원래 계약은
    그대로 유지).
    """

    pass_identifiers: list[str] = field(default_factory=list)
    pass_count: int = 0
    block_count: int = 0
    block_details: list[tuple[str, str]] = field(default_factory=list)
    error_count: int = 0
    error_details: list[tuple[str, str]] = field(default_factory=list)


def load_manifest_entries(
    manifest_root: Path = DEFAULT_MANIFEST_ROOT,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    corpus_manifest_root: Path | None = DEFAULT_CORPUS_MANIFEST_ROOT,
) -> list[ManifestEntryInput]:
    """Manifest 파일(들)을 읽어 Gate 입력(`ManifestEntryInput`)으로
    변환한다. `manifest_validator.py`의 기존 함수를 그대로 재사용할
    뿐, 그 파일은 이번 작업에서 전혀 수정하지 않는다(읽기 전용 호출)."""
    registry_index = load_registry_index(registry_path)
    corpus_manifest_index = load_corpus_manifest_index(corpus_manifest_root) if corpus_manifest_root else None

    entries_input: list[ManifestEntryInput] = []
    for manifest_path in find_manifest_files(manifest_root):
        entries, _schema_version, error = load_manifest_file(manifest_path)
        if error is not None:
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            source_id = entry.get("source_id")
            if not source_id:
                continue

            throwaway_result = ValidationResult()  # FK 검사 로그를 버릴 그릇 — 판정 결과(bool)만 사용
            authority_verified = _validate_authority_fk(entry, "gate-wiring", registry_index, throwaway_result)
            corpus_entry = corpus_manifest_index.get(source_id) if corpus_manifest_index else None
            verdict, _reasons = compute_tsu_eligible(entry, authority_verified, corpus_entry)

            entries_input.append(
                ManifestEntryInput(source_identifier=source_id, tsu_eligible=(verdict == "READY"))
            )
    return entries_input


def build_default_orchestrator() -> GateOrchestrator:
    """실제 Production Crosswalk Storage(Option B, `NAE/metadata/
    crosswalk/`)를 대상으로 하는 기본 `GateOrchestrator`를 만든다."""
    repository = YamlCrosswalkRepository(DEFAULT_CROSSWALK_YAML, DEFAULT_CROSSWALK_INDEX)
    return GateOrchestrator(repository)


def iter_eligible_identifiers(
    manifest_entries: list[ManifestEntryInput],
    orchestrator: GateOrchestrator,
) -> GateWiringSummary:
    """PASS 판정된 entry의 target_identifier만 모아 반환한다 — Builder를
    호출하지 않는다(identifier 계산만, 작업 명령서 Phase 1 "Builder
    호출 금지"). BLOCK/ERROR 상세도 함께 집계한다."""
    summary = GateWiringSummary()

    for entry in manifest_entries:
        result = orchestrator.evaluate(entry)

        if result.status == TsuGateStatus.PASS:
            target_identifier = orchestrator.resolver.resolve(entry.source_identifier)
            if target_identifier is not None:
                summary.pass_identifiers.append(target_identifier)
                summary.pass_count += 1
            else:
                # PASS 판정에는 반드시 Gate-eligible 레코드가 있어야 하므로
                # (tsu_gate.check_tsu_gate 로직상) 이 분기는 이론상 도달
                # 불가능하다 — 그래도 방어적으로 ERROR 처리(무음 실패 금지).
                summary.error_count += 1
                summary.error_details.append(
                    (entry.source_identifier, "PASS 판정이나 target_identifier 조회 실패(불일치 상태)")
                )
        elif result.status == TsuGateStatus.BLOCK:
            summary.block_count += 1
            summary.block_details.append((entry.source_identifier, result.reason))
        else:  # TsuGateStatus.ERROR
            summary.error_count += 1
            summary.error_details.append((entry.source_identifier, result.reason))

    return summary
