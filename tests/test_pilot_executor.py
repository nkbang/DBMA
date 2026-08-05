"""Tests for scripts/migrate_pilot.py (NAE-METADATA-MIGRATION-PILOT-IMPLEMENTATION-001).

All tests use Pilot Fixtures under tmp_path only — never the real
Production/Pilot Registry or Manifest under resources/theological_sources/.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.migrate_pilot import run_pilot_migration
from scripts.migration_engine import MigrationEngine


_AUTHORS_YAML = """
schema_version: "1.0"
authors:
  - author_id: dagg_john_l
    canonical_id: dagg_john_l
    canonical_name: "John L. Dagg"
  - author_id: FULLER-ANDREW-001
    canonical_name: "Andrew Fuller"
"""

_MANIFEST_YAML = """
manifests:
  - manifest_id: m1
    author_id: FULLER-ANDREW-001
"""


def _make_fixture(tmp_path: Path) -> tuple[Path, Path]:
    registry_root = tmp_path / "registry"
    registry_root.mkdir()
    (registry_root / "authors.yaml").write_text(_AUTHORS_YAML, encoding="utf-8")

    manifest_root = tmp_path / "manifest" / "fuller"
    manifest_root.mkdir(parents=True)
    (manifest_root / "manifest.yaml").write_text(_MANIFEST_YAML, encoding="utf-8")

    return registry_root, manifest_root


def _make_engine(tmp_path: Path) -> MigrationEngine:
    return MigrationEngine(
        checkpoint_dir=tmp_path / "cp",
        lock_path=tmp_path / "lock.json",
        audit_path=tmp_path / "audit.jsonl",
    )


class TestDryRun:
    def test_dry_run_does_not_write_registry(self, tmp_path):
        registry_root, manifest_root = _make_fixture(tmp_path)
        engine = _make_engine(tmp_path)
        report = run_pilot_migration(
            registry_root=registry_root,
            manifest_root=manifest_root,
            engine=engine,
            migration_version="1.0.0",
            canonical_id_map={"FULLER-ANDREW-001": "fuller_andrew"},
            legacy_id_map={"FULLER-ANDREW-001": ["FULLER-ANDREW-001"]},
            dry_run=True,
        )
        assert report.registry_units == 1
        assert report.manifest_files == 1
        assert report.changed == 1  # dry_run PASS(변경 예정 diff)
        # 실제 파일은 변경되지 않아야 함
        assert "canonical_id: fuller_andrew" not in (registry_root / "authors.yaml").read_text(encoding="utf-8")

    def test_dry_run_reports_no_fk_broken(self, tmp_path):
        registry_root, manifest_root = _make_fixture(tmp_path)
        engine = _make_engine(tmp_path)
        report = run_pilot_migration(
            registry_root=registry_root,
            manifest_root=manifest_root,
            engine=engine,
            migration_version="1.0.0",
            canonical_id_map={"FULLER-ANDREW-001": "fuller_andrew"},
            legacy_id_map=None,
            dry_run=True,
        )
        assert report.fk_broken == []


class TestExecute:
    def test_execute_writes_registry_and_preserves_manifest_fk(self, tmp_path):
        registry_root, manifest_root = _make_fixture(tmp_path)
        engine = _make_engine(tmp_path)
        report = run_pilot_migration(
            registry_root=registry_root,
            manifest_root=manifest_root,
            engine=engine,
            migration_version="1.0.0",
            canonical_id_map={"FULLER-ANDREW-001": "fuller_andrew"},
            legacy_id_map={"FULLER-ANDREW-001": ["FULLER-ANDREW-001"]},
            dry_run=False,
        )
        assert report.changed == 1
        assert report.failed == 0
        assert report.fk_broken == []

        registry_text = (registry_root / "authors.yaml").read_text(encoding="utf-8")
        assert "canonical_id: fuller_andrew" in registry_text

        manifest_text = (manifest_root / "manifest.yaml").read_text(encoding="utf-8")
        # Option B — Manifest의 FK 값(author_id)은 그대로여야 함
        assert "author_id: FULLER-ANDREW-001" in manifest_text

    def test_execute_detects_fk_broken_when_registry_incomplete(self, tmp_path):
        registry_root, manifest_root = _make_fixture(tmp_path)
        # dagg_john_l만 있고 FULLER-ANDREW-001을 완전히 제거해 broken FK 유도
        (registry_root / "authors.yaml").write_text(
            "schema_version: '1.0'\nauthors:\n  - author_id: dagg_john_l\n    canonical_id: dagg_john_l\n",
            encoding="utf-8",
        )
        engine = _make_engine(tmp_path)
        report = run_pilot_migration(
            registry_root=registry_root,
            manifest_root=manifest_root,
            engine=engine,
            migration_version="1.0.0",
            canonical_id_map={},
            legacy_id_map=None,
            dry_run=False,
        )
        assert len(report.fk_broken) == 1
        assert "author_id='FULLER-ANDREW-001'" in report.fk_broken[0]


class TestCheckpointAndRollback:
    def test_checkpoint_created_for_changed_unit(self, tmp_path):
        registry_root, manifest_root = _make_fixture(tmp_path)
        engine = _make_engine(tmp_path)
        run_pilot_migration(
            registry_root=registry_root,
            manifest_root=manifest_root,
            engine=engine,
            migration_version="1.0.0",
            canonical_id_map={"FULLER-ANDREW-001": "fuller_andrew"},
            legacy_id_map=None,
            dry_run=False,
        )
        # Migration Unit ID는 registry_adapter의 target_key 규칙(registry:authors)에서 유도됨
        from scripts.migration_engine import compute_migration_unit_id

        unit_id = compute_migration_unit_id("1.0.0", "registry:authors")
        assert engine.checkpoints.has(unit_id, "before")
        assert engine.checkpoints.has(unit_id, "after")

    def test_verifying_failure_rolls_back_registry_file(self, tmp_path):
        registry_root, manifest_root = _make_fixture(tmp_path)

        def failing_hook():
            return False, "simulated verify failure"

        engine = MigrationEngine(
            checkpoint_dir=tmp_path / "cp",
            lock_path=tmp_path / "lock.json",
            audit_path=tmp_path / "audit.jsonl",
            verify_hooks=[failing_hook],
        )
        original_text = (registry_root / "authors.yaml").read_text(encoding="utf-8")

        report = run_pilot_migration(
            registry_root=registry_root,
            manifest_root=manifest_root,
            engine=engine,
            migration_version="1.0.0",
            canonical_id_map={"FULLER-ANDREW-001": "fuller_andrew"},
            legacy_id_map=None,
            dry_run=False,
        )
        assert report.failed >= 1
        assert report.rolled_back >= 1
        # 파일이 원래 상태로 복원됐어야 함
        assert (registry_root / "authors.yaml").read_text(encoding="utf-8") == original_text


class TestIdempotency:
    def test_running_pilot_twice_is_idempotent(self, tmp_path):
        registry_root, manifest_root = _make_fixture(tmp_path)
        engine = _make_engine(tmp_path)
        args = dict(
            registry_root=registry_root,
            manifest_root=manifest_root,
            engine=engine,
            migration_version="1.0.0",
            canonical_id_map={"FULLER-ANDREW-001": "fuller_andrew"},
            legacy_id_map=None,
            dry_run=False,
        )
        first = run_pilot_migration(**args)
        second = run_pilot_migration(**args)
        assert first.changed == 1
        assert second.changed == 0
        assert second.skipped == 1
