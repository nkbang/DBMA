"""scripts/migration_engine.py — Metadata Migration Engine
(NAE-METADATA-MIGRATION-IMPLEMENTATION-001).

이번 구현은 Migration Engine "자체"만 다룬다 — 이 파일을 포함해 이번
작업으로 만든 어떤 모듈에도 Registry/Manifest/RAW/TSU/Embedding 경로가
하드코딩되어 있지 않다. 어떤 파일을 어떻게 바꿀지는 호출자가
`MigrationUnit`으로 넘겨준다 — 이 엔진은 State Machine/Checkpoint/
Lock/Audit/Idempotency/Rollback Hook만 담당하는 순수 인프라다.

설계 근거:
  docs/NAE_METADATA_MIGRATION_ENGINE_DESIGN_001.md (전체)
  docs/NAE_METADATA_MIGRATION_STATE_MACHINE.md (State Machine)
  docs/NAE_METADATA_MIGRATION_SEQUENCE.md (실행 시퀀스)

State Machine(설계 §2):
  PENDING -> VALIDATING -> MIGRATING -> VERIFYING -> COMPLETE
                  \\-> FAILED -> ROLLED_BACK(가능한 경우만, 설계 §4)

실제 Migration(Pilot/Corpus-wide)은 이번 작업에서 수행하지 않는다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.migration_audit import AuditLogger, AuditRecord
from scripts.migration_checkpoint import Checkpoint, CheckpointManager
from scripts.migration_lock import MigrationLock
from scripts.migration_report import MigrationReport

# State Machine 상태 상수(설계 §2) — 이번 구현에서는 실행 로그/리포트
# 메시지에만 사용, 별도 영속 상태 필드로 저장하지 않는다(Checkpoint
# 존재 여부 자체가 상태를 함의한다: before만 있음=중단, after까지
# 있음=COMPLETE).
PENDING = "PENDING"
VALIDATING = "VALIDATING"
MIGRATING = "MIGRATING"
VERIFYING = "VERIFYING"
COMPLETE = "COMPLETE"
FAILED = "FAILED"
ROLLED_BACK = "ROLLED_BACK"


def sha256_of(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_migration_unit_id(migration_version: str, target_key: str) -> str:
    """결정적 Migration Unit ID(설계 §5-1) — 같은 대상·같은 버전이면
    몇 번을 계산해도 항상 동일한 값(우연/타임스탬프 기반 ID 금지)."""
    return hashlib.sha256(f"{migration_version}:{target_key}".encode("utf-8")).hexdigest()[:16]


@dataclass
class MigrationUnit:
    """설계 §1 Migration Unit.

    target_files: 이 Unit이 원자적으로 함께 바뀌어야 하는 폐쇄 집합
    (파일 경로들) — 더 잘게 쪼개 실행하지 않는다.
    transform: old_contents(dict[str,str]) -> new_contents(dict[str,str])를
    계산하는 순수 함수. 파일에 직접 쓰지 않는다(부작용 없음) — 실제
    쓰기는 MigrationEngine.execute()만 수행한다.
    """

    target_key: str
    migration_version: str
    target_files: list[Path]
    transform: Callable[[dict[str, str]], dict[str, str]]

    @property
    def unit_id(self) -> str:
        return compute_migration_unit_id(self.migration_version, self.target_key)


class MigrationEngine:
    def __init__(
        self,
        checkpoint_dir: Path,
        lock_path: Path,
        audit_path: Path,
        operator: str = "cue",
        verify_hooks: list[Callable[[], tuple[bool, str]]] | None = None,
    ) -> None:
        self.checkpoints = CheckpointManager(checkpoint_dir)
        self.lock = MigrationLock(lock_path)
        self.audit = AuditLogger(audit_path)
        self.operator = operator
        # verify_hooks: MIGRATING 완료 후 VERIFYING 단계에서 실행할 검증
        # 콜백 목록(설계 §13 post-flight의 통합 지점 — 예: 3-Validator
        # 재실행). 이번 구현은 실제 Validator를 연결하지 않는다(Registry/
        # Manifest를 건드리는 실제 Migration이 이번 작업 범위 밖이므로
        # 검증 대상 데이터 자체가 없음) — 테스트/향후 Pilot Migration
        # 단계에서 주입하는 확장점으로만 존재.
        self.verify_hooks = verify_hooks or []

    def _read_current(self, files: list[Path]) -> dict[str, str]:
        return {str(p): (p.read_text(encoding="utf-8") if p.exists() else "") for p in files}

    def _checksum_map(self, contents: dict[str, str]) -> dict[str, str]:
        return {path: sha256_of(content) for path, content in contents.items()}

    # ---- Dry Run(설계 §9) ----
    def dry_run(self, unit: MigrationUnit) -> MigrationReport:
        report = MigrationReport()
        old_contents = self._read_current(unit.target_files)
        try:
            new_contents = unit.transform(dict(old_contents))
        except Exception as exc:  # noqa: BLE001
            report.add("FAIL", f"{unit.unit_id}: transform 실행 실패 — {exc}")
            self.audit.log(
                AuditRecord(
                    timestamp=time.time(),
                    operator=self.operator,
                    migration_version=unit.migration_version,
                    migration_unit=unit.unit_id,
                    before_checksum=None,
                    after_checksum=None,
                    result="DRY_RUN",
                    reason=f"transform 실패: {exc}",
                )
            )
            return report

        if old_contents == new_contents:
            report.add("SKIPPED", f"{unit.unit_id}: 이미 목표 상태와 동일(no-op)")
        else:
            for path in unit.target_files:
                key = str(path)
                if old_contents.get(key) != new_contents.get(key):
                    report.add(
                        "PASS",
                        f"{unit.unit_id}: {key} 변경 예정 "
                        f"(old sha256={sha256_of(old_contents.get(key, ''))[:12]}.. -> "
                        f"new sha256={sha256_of(new_contents.get(key, ''))[:12]}..)",
                    )

        self.audit.log(
            AuditRecord(
                timestamp=time.time(),
                operator=self.operator,
                migration_version=unit.migration_version,
                migration_unit=unit.unit_id,
                before_checksum=None,
                after_checksum=None,
                result="DRY_RUN",
                reason=None,
            )
        )
        return report

    # ---- Execute(설계 §2 State Machine 정상/실패 경로) ----
    def execute(self, unit: MigrationUnit) -> MigrationReport:
        report = MigrationReport()

        if not self.lock.acquire(owner=unit.unit_id):
            report.add("FAIL", f"{unit.unit_id}: Migration Lock 획득 실패(다른 Migration 실행 중)")
            return report

        try:
            # VALIDATING
            old_contents = self._read_current(unit.target_files)
            try:
                new_contents = unit.transform(dict(old_contents))
            except Exception as exc:  # noqa: BLE001
                report.add("FAIL", f"{unit.unit_id}: VALIDATING 실패 — transform 오류: {exc}")
                self.audit.log(
                    AuditRecord(
                        timestamp=time.time(),
                        operator=self.operator,
                        migration_version=unit.migration_version,
                        migration_unit=unit.unit_id,
                        before_checksum=None,
                        after_checksum=None,
                        result="FAIL",
                        reason=str(exc),
                    )
                )
                return report

            # Idempotency(설계 §5-2): 이미 목표 상태와 동일하면 no-op COMPLETE
            if old_contents == new_contents:
                report.add("SKIPPED", f"{unit.unit_id}: 이미 목표 상태(no-op COMPLETE)")
                self.audit.log(
                    AuditRecord(
                        timestamp=time.time(),
                        operator=self.operator,
                        migration_version=unit.migration_version,
                        migration_unit=unit.unit_id,
                        before_checksum=None,
                        after_checksum=None,
                        result="PASS",
                        reason="no-op(이미 목표 상태)",
                    )
                )
                return report

            # Checkpoint A(before, 설계 §3)
            before_checksums = self._checksum_map(old_contents)
            self.checkpoints.save(
                Checkpoint(
                    migration_unit_id=unit.unit_id,
                    stage="before",
                    files=before_checksums,
                    contents=old_contents,
                    extra={"migration_version": unit.migration_version, "target_key": unit.target_key},
                )
            )

            # MIGRATING: 폐쇄 집합 전체를 한 번에 쓴다(설계 §1)
            for path in unit.target_files:
                key = str(path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(new_contents.get(key, ""), encoding="utf-8")

            # VERIFYING: verify_hooks 실행(설계 §13 post-flight 통합 지점)
            for hook in self.verify_hooks:
                ok, message = hook()
                if not ok:
                    report.add("FAIL", f"{unit.unit_id}: VERIFYING 실패 — {message}")
                    rolled_back = self._rollback(unit, reason=f"VERIFYING 실패: {message}")
                    report.add(
                        "WARNING" if rolled_back else "FAIL",
                        f"{unit.unit_id}: Rollback {'완료' if rolled_back else '불가(사람 개입 필요)'}",
                    )
                    return report

            # COMPLETE: Checkpoint B(after)
            after_checksums = self._checksum_map(new_contents)
            self.checkpoints.save(
                Checkpoint(
                    migration_unit_id=unit.unit_id,
                    stage="after",
                    files=after_checksums,
                    contents={},
                    extra={"migration_version": unit.migration_version, "target_key": unit.target_key},
                )
            )
            report.add("PASS", f"{unit.unit_id}: COMPLETE")
            self.audit.log(
                AuditRecord(
                    timestamp=time.time(),
                    operator=self.operator,
                    migration_version=unit.migration_version,
                    migration_unit=unit.unit_id,
                    before_checksum=",".join(sorted(before_checksums.values())),
                    after_checksum=",".join(sorted(after_checksums.values())),
                    result="PASS",
                    reason=None,
                )
            )
            return report
        finally:
            self.lock.release(owner=unit.unit_id)

    # ---- Resume(설계 §8 Failure Recovery) ----
    def resume(self, unit: MigrationUnit) -> MigrationReport:
        """Checkpoint 'before'는 있는데 'after'가 없는(=중단된) Migration
        Unit을 재개한다. execute() 내부의 Idempotency 체크에 의해 안전하게
        재실행 가능하므로 별도의 Resume 전용 쓰기 로직을 두지 않는다
        (설계 §12 Performance — "별도 Resume 전용 로직 불필요")."""
        report = MigrationReport()
        if unit.unit_id not in self.checkpoints.resume_candidates():
            report.add(
                "WARNING",
                f"{unit.unit_id}: Resume 대상 아님(중단된 Checkpoint 없음) — execute()로 새로 실행하세요",
            )
            return report
        return self.execute(unit)

    # ---- Verify(설계 §13 post-flight 재검증) ----
    def verify(self, unit: MigrationUnit) -> MigrationReport:
        report = MigrationReport()
        after = self.checkpoints.load(unit.unit_id, "after")
        if after is None:
            report.add("FAIL", f"{unit.unit_id}: Checkpoint(after) 없음 — 아직 COMPLETE 아님")
            return report

        current_checksums = self._checksum_map(self._read_current(unit.target_files))
        if current_checksums == after.files:
            report.add("PASS", f"{unit.unit_id}: 현재 파일 상태가 Checkpoint(after)와 일치")
        else:
            report.add("FAIL", f"{unit.unit_id}: 현재 파일 상태가 Checkpoint(after)와 불일치(외부 변경 의심)")
        return report

    # ---- Rollback Interface(설계 §4 — 이번 단계는 Hook만 구현) ----
    def rollback_supported(self, unit: MigrationUnit) -> bool:
        """COMPLETE 이후는 자동 Rollback 대상이 아니다(설계 §2 역행 규칙,
        §4 Rollback 불가능한 경우 1번)."""
        if self.checkpoints.has(unit.unit_id, "after"):
            return False
        return self.checkpoints.has(unit.unit_id, "before")

    def rollback_reason(self, unit: MigrationUnit) -> str | None:
        if self.rollback_supported(unit):
            return None
        if self.checkpoints.has(unit.unit_id, "after"):
            return "COMPLETE 이후 Rollback 불가(설계 §4) — 새 역방향 Migration Unit 필요"
        return "Checkpoint(before) 없음 — Rollback 대상 상태 아님"

    def rollback(self, unit: MigrationUnit) -> bool:
        return self._rollback(unit, reason="명시적 rollback() 호출")

    def _rollback(self, unit: MigrationUnit, reason: str) -> bool:
        if not self.rollback_supported(unit):
            self.audit.log(
                AuditRecord(
                    timestamp=time.time(),
                    operator=self.operator,
                    migration_version=unit.migration_version,
                    migration_unit=unit.unit_id,
                    before_checksum=None,
                    after_checksum=None,
                    result="FAIL",
                    reason=f"Rollback 불가: {self.rollback_reason(unit)}",
                )
            )
            return False

        before = self.checkpoints.load(unit.unit_id, "before")
        assert before is not None
        for path in unit.target_files:
            key = str(path)
            if key in before.contents:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(before.contents[key], encoding="utf-8")

        restored = self._checksum_map(self._read_current(unit.target_files))
        ok = restored == before.files
        self.audit.log(
            AuditRecord(
                timestamp=time.time(),
                operator=self.operator,
                migration_version=unit.migration_version,
                migration_unit=unit.unit_id,
                before_checksum=",".join(sorted(before.files.values())),
                after_checksum=",".join(sorted(restored.values())),
                result="ROLLED_BACK" if ok else "FAIL",
                reason=reason,
            )
        )
        return ok


def _make_unit_from_args(args: argparse.Namespace) -> MigrationUnit:
    """CLI 전용 헬퍼 — 새 콘텐츠는 호출자가 준 JSON 파일(path -> content)에서
    읽어온다. 이 모듈은 어떤 도메인 변환 로직도 내장하지 않는다(Registry/
    Manifest 필드를 아는 코드가 전혀 없음) — CLI는 순수하게 엔진 동작을
    시연/테스트하기 위한 얇은 래퍼일 뿐이다."""
    target_files = [Path(p) for p in args.target]
    new_contents: dict[str, str] = {}
    if args.content_file:
        new_contents = json.loads(Path(args.content_file).read_text(encoding="utf-8"))

    def transform(old_contents: dict[str, str]) -> dict[str, str]:
        merged = dict(old_contents)
        merged.update(new_contents)
        return merged

    return MigrationUnit(
        target_key=args.target_key,
        migration_version=args.migration_version,
        target_files=target_files,
        transform=transform,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Metadata Migration Engine CLI(설계 §9 Dry Run/§8 Resume/§13 Verify) — "
        "이번 구현은 Migration Engine 자체만 다루며 실제 Registry/Manifest/RAW를 대상으로 하지 않는다."
    )
    parser.add_argument("--checkpoint-dir", required=True)
    parser.add_argument("--lock-path", required=True)
    parser.add_argument("--audit-path", required=True)
    parser.add_argument("--target", nargs="+", required=True, help="Migration Unit이 다룰 파일 경로들")
    parser.add_argument("--target-key", required=True)
    parser.add_argument("--migration-version", default="1.0.0")
    parser.add_argument("--content-file", help="새 콘텐츠(JSON: path -> content)")
    parser.add_argument("--operator", default="cue")

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--resume", action="store_true")
    mode.add_argument("--verify", action="store_true")

    args = parser.parse_args()

    engine = MigrationEngine(
        checkpoint_dir=Path(args.checkpoint_dir),
        lock_path=Path(args.lock_path),
        audit_path=Path(args.audit_path),
        operator=args.operator,
    )
    unit = _make_unit_from_args(args)

    if args.dry_run:
        report = engine.dry_run(unit)
    elif args.execute:
        report = engine.execute(unit)
    elif args.resume:
        report = engine.resume(unit)
    else:
        report = engine.verify(unit)

    report.print_all()
    return 1 if report.fail_count > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
