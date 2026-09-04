"""Tests for scripts/migration_engine.py (NAE-METADATA-MIGRATION-IMPLEMENTATION-001).

Covers MigrationEngine (dry_run/execute/resume/verify/rollback), and
exercises migration_audit.py/migration_report.py indirectly (Audit Log
records, PASS/WARNING/FAIL/SKIPPED reporting).

All tests operate on tmp_path fixture files only — no Registry/Manifest/
RAW path is ever referenced, matching the implementation-scope
restriction (Migration Engine itself only, no real migration executed).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.migration_engine import (
    MigrationEngine,
    MigrationUnit,
    compute_migration_unit_id,
    sha256_of,
)


def _make_engine(tmp_path: Path, verify_hooks=None) -> MigrationEngine:
    return MigrationEngine(
        checkpoint_dir=tmp_path / "checkpoints",
        lock_path=tmp_path / "lock.json",
        audit_path=tmp_path / "audit.jsonl",
        operator="test",
        verify_hooks=verify_hooks,
    )


def _upper_transform(old_contents: dict) -> dict:
    return {k: v.upper() for k, v in old_contents.items()}


class TestMigrationUnitId:
    def test_deterministic(self):
        id1 = compute_migration_unit_id("1.0.0", "author:fuller_andrew")
        id2 = compute_migration_unit_id("1.0.0", "author:fuller_andrew")
        assert id1 == id2

    def test_differs_by_version_or_target(self):
        base = compute_migration_unit_id("1.0.0", "author:fuller_andrew")
        assert base != compute_migration_unit_id("1.0.1", "author:fuller_andrew")
        assert base != compute_migration_unit_id("1.0.0", "author:dagg_john_l")


class TestDryRun:
    def test_dry_run_previews_change_without_writing(self, tmp_path):
        f = tmp_path / "f1.txt"
        f.write_text("hello", encoding="utf-8")
        engine = _make_engine(tmp_path)
        unit = MigrationUnit(
            target_key="demo", migration_version="1.0.0", target_files=[f], transform=_upper_transform
        )
        report = engine.dry_run(unit)
        assert report.fail_count == 0
        assert report.pass_count == 1
        assert f.read_text(encoding="utf-8") == "hello"  # 실제 쓰기 없음

    def test_dry_run_no_op_when_already_target_state(self, tmp_path):
        f = tmp_path / "f1.txt"
        f.write_text("HELLO", encoding="utf-8")
        engine = _make_engine(tmp_path)
        unit = MigrationUnit(
            target_key="demo", migration_version="1.0.0", target_files=[f], transform=_upper_transform
        )
        report = engine.dry_run(unit)
        assert report.skipped_count == 1
        assert report.pass_count == 0


class TestExecute:
    def test_execute_writes_files_and_checkpoints(self, tmp_path):
        f = tmp_path / "f1.txt"
        f.write_text("hello", encoding="utf-8")
        engine = _make_engine(tmp_path)
        unit = MigrationUnit(
            target_key="demo", migration_version="1.0.0", target_files=[f], transform=_upper_transform
        )
        report = engine.execute(unit)
        assert report.fail_count == 0
        assert f.read_text(encoding="utf-8") == "HELLO"
        assert engine.checkpoints.has(unit.unit_id, "before")
        assert engine.checkpoints.has(unit.unit_id, "after")

    def test_execute_logs_audit_record(self, tmp_path):
        f = tmp_path / "f1.txt"
        f.write_text("hello", encoding="utf-8")
        engine = _make_engine(tmp_path)
        unit = MigrationUnit(
            target_key="demo", migration_version="1.0.0", target_files=[f], transform=_upper_transform
        )
        engine.execute(unit)
        records = engine.audit.find_by_unit(unit.unit_id)
        assert len(records) == 1
        assert records[0]["result"] == "PASS"
        assert records[0]["before_checksum"] is not None
        assert records[0]["after_checksum"] is not None
        assert records[0]["before_checksum"] != records[0]["after_checksum"]

    def test_execute_already_target_state_is_noop(self, tmp_path):
        f = tmp_path / "f1.txt"
        f.write_text("HELLO", encoding="utf-8")
        engine = _make_engine(tmp_path)
        unit = MigrationUnit(
            target_key="demo", migration_version="1.0.0", target_files=[f], transform=_upper_transform
        )
        report = engine.execute(unit)
        assert report.skipped_count == 1
        # no-op이므로 Checkpoint를 새로 만들지 않음
        assert not engine.checkpoints.has(unit.unit_id, "before")


class TestIdempotency:
    def test_execute_100_times_same_result(self, tmp_path):
        f = tmp_path / "f1.txt"
        f.write_text("hello", encoding="utf-8")
        engine = _make_engine(tmp_path)
        unit = MigrationUnit(
            target_key="demo", migration_version="1.0.0", target_files=[f], transform=_upper_transform
        )

        for _ in range(100):
            report = engine.execute(unit)
            assert report.fail_count == 0

        assert f.read_text(encoding="utf-8") == "HELLO"
        # 첫 실행만 실제 변경, 나머지 99회는 no-op(Checkpoint 파일이 1세트만 존재)
        after = engine.checkpoints.load(unit.unit_id, "after")
        assert after is not None
        # Audit Log에는 최초 1건의 PASS(실질 변경) + 99건의 no-op PASS가 기록됨
        records = engine.audit.find_by_unit(unit.unit_id)
        assert len(records) == 100
        assert all(r["result"] == "PASS" for r in records)


class TestVerify:
    def test_verify_passes_when_unchanged_since_complete(self, tmp_path):
        f = tmp_path / "f1.txt"
        f.write_text("hello", encoding="utf-8")
        engine = _make_engine(tmp_path)
        unit = MigrationUnit(
            target_key="demo", migration_version="1.0.0", target_files=[f], transform=_upper_transform
        )
        engine.execute(unit)
        report = engine.verify(unit)
        assert report.fail_count == 0
        assert report.pass_count == 1

    def test_verify_fails_when_externally_modified(self, tmp_path):
        f = tmp_path / "f1.txt"
        f.write_text("hello", encoding="utf-8")
        engine = _make_engine(tmp_path)
        unit = MigrationUnit(
            target_key="demo", migration_version="1.0.0", target_files=[f], transform=_upper_transform
        )
        engine.execute(unit)
        f.write_text("TAMPERED", encoding="utf-8")
        report = engine.verify(unit)
        assert report.fail_count == 1

    def test_verify_fails_when_not_yet_complete(self, tmp_path):
        f = tmp_path / "f1.txt"
        f.write_text("hello", encoding="utf-8")
        engine = _make_engine(tmp_path)
        unit = MigrationUnit(
            target_key="demo", migration_version="1.0.0", target_files=[f], transform=_upper_transform
        )
        report = engine.verify(unit)
        assert report.fail_count == 1


class TestResume:
    def test_resume_completes_interrupted_migration(self, tmp_path):
        f = tmp_path / "f1.txt"
        f.write_text("hello", encoding="utf-8")
        engine = _make_engine(tmp_path)
        unit = MigrationUnit(
            target_key="demo", migration_version="1.0.0", target_files=[f], transform=_upper_transform
        )

        # MIGRATING 도중 중단된 상황을 시뮬레이션: before checkpoint만 존재
        from scripts.migration_checkpoint import Checkpoint

        engine.checkpoints.save(
            Checkpoint(
                migration_unit_id=unit.unit_id,
                stage="before",
                files={str(f): sha256_of("hello")},
                contents={str(f): "hello"},
            )
        )

        assert unit.unit_id in engine.checkpoints.resume_candidates()
        report = engine.resume(unit)
        assert report.fail_count == 0
        assert f.read_text(encoding="utf-8") == "HELLO"
        assert engine.checkpoints.has(unit.unit_id, "after")

    def test_resume_without_interruption_warns(self, tmp_path):
        f = tmp_path / "f1.txt"
        f.write_text("hello", encoding="utf-8")
        engine = _make_engine(tmp_path)
        unit = MigrationUnit(
            target_key="demo", migration_version="1.0.0", target_files=[f], transform=_upper_transform
        )
        report = engine.resume(unit)
        assert report.warning_count == 1


class TestRollbackInterface:
    def test_verifying_failure_triggers_automatic_rollback(self, tmp_path):
        def failing_hook():
            return False, "simulated post-write validation failure"

        engine = _make_engine(tmp_path / "engine_state", verify_hooks=[failing_hook])
        f = tmp_path / "f2.txt"
        f.write_text("hello", encoding="utf-8")
        unit = MigrationUnit(
            target_key="demo2", migration_version="1.0.0", target_files=[f], transform=_upper_transform
        )
        report = engine.execute(unit)
        assert report.fail_count == 1
        # VERIFYING 실패 시 자동 Rollback이 시도되어 원본으로 복원됨
        assert f.read_text(encoding="utf-8") == "hello"

    def test_rollback_not_supported_after_complete(self, tmp_path):
        f = tmp_path / "f1.txt"
        f.write_text("hello", encoding="utf-8")
        engine = _make_engine(tmp_path)
        unit = MigrationUnit(
            target_key="demo", migration_version="1.0.0", target_files=[f], transform=_upper_transform
        )
        engine.execute(unit)
        assert engine.rollback_supported(unit) is False
        assert "COMPLETE 이후" in engine.rollback_reason(unit)
        assert engine.rollback(unit) is False

    def test_rollback_not_supported_when_no_checkpoint(self, tmp_path):
        f = tmp_path / "f1.txt"
        f.write_text("hello", encoding="utf-8")
        engine = _make_engine(tmp_path)
        unit = MigrationUnit(
            target_key="demo", migration_version="1.0.0", target_files=[f], transform=_upper_transform
        )
        assert engine.rollback_supported(unit) is False
        assert engine.rollback(unit) is False

    def test_explicit_rollback_restores_before_state(self, tmp_path):
        f = tmp_path / "f1.txt"
        f.write_text("hello", encoding="utf-8")
        engine = _make_engine(tmp_path)
        unit = MigrationUnit(
            target_key="demo", migration_version="1.0.0", target_files=[f], transform=_upper_transform
        )

        from scripts.migration_checkpoint import Checkpoint

        engine.checkpoints.save(
            Checkpoint(
                migration_unit_id=unit.unit_id,
                stage="before",
                files={str(f): sha256_of("hello")},
                contents={str(f): "hello"},
            )
        )
        f.write_text("SOMETHING_ELSE", encoding="utf-8")
        assert engine.rollback_supported(unit) is True
        assert engine.rollback(unit) is True
        assert f.read_text(encoding="utf-8") == "hello"


class TestMigrationLockPreventsConcurrentExecution:
    def test_concurrent_execute_on_locked_engine_fails(self, tmp_path):
        f = tmp_path / "f1.txt"
        f.write_text("hello", encoding="utf-8")
        engine = _make_engine(tmp_path)
        unit = MigrationUnit(
            target_key="demo", migration_version="1.0.0", target_files=[f], transform=_upper_transform
        )
        # Lock을 다른 소유자 이름으로 선점
        engine.lock.acquire(owner="someone_else")
        report = engine.execute(unit)
        assert report.fail_count == 1
        assert "Lock" in report.lines[0]
