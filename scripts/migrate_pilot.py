"""scripts/migrate_pilot.py — Metadata Migration Pilot Executor
(NAE-METADATA-MIGRATION-PILOT-IMPLEMENTATION-001).

Registry Adapter/Manifest Adapter가 만든 MigrationUnit을 Migration
Engine으로 실행하는 오케스트레이션 스크립트다. 이 스크립트 자체도
Registry/Manifest의 실제 스키마를 조립하지 않는다 — 그건 Adapter의
역할이고, 여기서는 순서(흐름)만 담당한다:

    Registry 로드 → MigrationUnit 생성 → Migration Engine 실행(Dry Run/
    Execute) → Manifest FK 재검증(+ Audit 필드 touch) → Verify → Report

**중요**: 이 스크립트는 어떤 실제 경로도 기본값으로 갖지 않는다
(`--registry-root`/`--manifest-root`는 필수 인자) — 실 Production/Pilot
Registry(`resources/theological_sources/authority/`)나 실 Pilot Manifest
(`resources/theological_sources/manifest/pilot/`)를 대상으로 실행하는
것은 이번 작업 명령서(§8 금지 목록)에서 금지되어 있고, 테스트도 전부
Pilot Fixture(임시 디렉토리)만 사용한다.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.adapters.manifest_adapter import ManifestFile, load_manifest, verify_fk
from scripts.adapters.registry_adapter import build_all_backfill_units, load_registry
from scripts.migration_engine import MigrationEngine


@dataclass
class PilotReport:
    registry_units: int = 0
    manifest_files: int = 0
    changed: int = 0
    skipped: int = 0
    rolled_back: int = 0
    failed: int = 0
    fk_broken: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    def print_all(self) -> None:
        print("=== Migration Report ===")
        print(f"Registry: {self.registry_units}")
        print(f"Manifest: {self.manifest_files}")
        print(f"Changed: {self.changed}")
        print(f"Skipped: {self.skipped}")
        print(f"Rollback: {self.rolled_back}")
        if self.failed:
            print(f"Failed: {self.failed}")
        if self.fk_broken:
            print(f"FK Broken: {len(self.fk_broken)}")
            for line in self.fk_broken:
                print(f"  - {line}")
        print(f"Time: {self.elapsed_seconds:.3f}s")


def run_pilot_migration(
    registry_root: Path,
    manifest_root: Path,
    engine: MigrationEngine,
    migration_version: str,
    canonical_id_map: dict[str, str],
    legacy_id_map: dict[str, list[str]] | None,
    dry_run: bool,
) -> PilotReport:
    start = time.time()
    report = PilotReport()

    registry = load_registry(registry_root)
    units = build_all_backfill_units(registry_root, migration_version, canonical_id_map, legacy_id_map)
    report.registry_units = len(units)

    for unit in units:
        result = engine.dry_run(unit) if dry_run else engine.execute(unit)
        report.changed += result.pass_count
        report.skipped += result.skipped_count
        report.failed += result.fail_count
        report.rolled_back += result.warning_count  # Rollback 발생 시 WARNING으로 기록됨(engine.execute)

    # Manifest FK 재검증(Option B — FK 자체는 안 바뀌어야 함을 재확인)
    registry_index = {
        entity_key: {e.get(entity_file.id_field) for e in entity_file.entries if e.get(entity_file.id_field)}
        for entity_key, entity_file in registry.items()
    }
    manifest_files = sorted(manifest_root.rglob("manifest.yaml"))
    report.manifest_files = len(manifest_files)
    for manifest_path in manifest_files:
        manifest = load_manifest(manifest_path)
        for ok, message in verify_fk(manifest, registry_index):
            if not ok:
                report.fk_broken.append(message)

    report.elapsed_seconds = time.time() - start
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--registry-root", required=True, help="Registry entity YAML이 있는 디렉토리(Pilot Fixture 전용)")
    parser.add_argument("--manifest-root", required=True, help="manifest.yaml들이 있는 디렉토리(Pilot Fixture 전용)")
    parser.add_argument("--checkpoint-dir", required=True)
    parser.add_argument("--lock-path", required=True)
    parser.add_argument("--audit-path", required=True)
    parser.add_argument("--migration-version", default="1.0.0")
    parser.add_argument("--canonical-id-map", required=True, help="JSON 파일(entity_id -> canonical_id)")
    parser.add_argument("--legacy-id-map", help="JSON 파일(entity_id -> [legacy_id, ...]), 선택")
    parser.add_argument("--operator", default="cue")
    parser.add_argument("--dry-run", action="store_true", help="실제 쓰기 없이 미리보기만 수행")
    args = parser.parse_args()

    canonical_id_map = json.loads(Path(args.canonical_id_map).read_text(encoding="utf-8"))
    legacy_id_map = json.loads(Path(args.legacy_id_map).read_text(encoding="utf-8")) if args.legacy_id_map else None

    engine = MigrationEngine(
        checkpoint_dir=Path(args.checkpoint_dir),
        lock_path=Path(args.lock_path),
        audit_path=Path(args.audit_path),
        operator=args.operator,
    )

    report = run_pilot_migration(
        registry_root=Path(args.registry_root),
        manifest_root=Path(args.manifest_root),
        engine=engine,
        migration_version=args.migration_version,
        canonical_id_map=canonical_id_map,
        legacy_id_map=legacy_id_map,
        dry_run=args.dry_run,
    )
    report.print_all()
    return 1 if (report.failed or report.fk_broken) else 0


if __name__ == "__main__":
    raise SystemExit(main())
