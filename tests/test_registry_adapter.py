"""Tests for scripts/adapters/registry_adapter.py
(NAE-METADATA-MIGRATION-PILOT-IMPLEMENTATION-001).

All tests use Pilot Fixtures under tmp_path only — never the real
Production/Pilot Registry under resources/theological_sources/.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from scripts.adapters.registry_adapter import (
    build_all_backfill_units,
    build_canonical_id_backfill_unit,
    canonical_id_lookup,
    legacy_id_lookup,
    load_entity_file,
    load_registry,
)
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


def _write_fixture_registry(tmp_path: Path) -> Path:
    root = tmp_path / "registry_fixture"
    root.mkdir(parents=True, exist_ok=True)
    (root / "authors.yaml").write_text(_AUTHORS_YAML, encoding="utf-8")
    return root


class TestLoad:
    def test_load_entity_file(self, tmp_path):
        root = _write_fixture_registry(tmp_path)
        entity_file = load_entity_file(root, "authors")
        assert entity_file is not None
        assert len(entity_file.entries) == 2
        assert entity_file.id_field == "author_id"

    def test_load_missing_entity_file_returns_none(self, tmp_path):
        root = tmp_path / "empty_registry"
        root.mkdir()
        assert load_entity_file(root, "works") is None

    def test_load_registry_only_returns_existing_files(self, tmp_path):
        root = _write_fixture_registry(tmp_path)
        registry = load_registry(root)
        assert set(registry.keys()) == {"authors"}


class TestLookup:
    def test_canonical_id_lookup_found(self, tmp_path):
        root = _write_fixture_registry(tmp_path)
        entity_file = load_entity_file(root, "authors")
        assert canonical_id_lookup(entity_file, "dagg_john_l") == "dagg_john_l"

    def test_canonical_id_lookup_missing_field_returns_none(self, tmp_path):
        root = _write_fixture_registry(tmp_path)
        entity_file = load_entity_file(root, "authors")
        assert canonical_id_lookup(entity_file, "FULLER-ANDREW-001") is None

    def test_canonical_id_lookup_unknown_id_returns_none(self, tmp_path):
        root = _write_fixture_registry(tmp_path)
        entity_file = load_entity_file(root, "authors")
        assert canonical_id_lookup(entity_file, "nonexistent") is None

    def test_legacy_id_lookup_empty_when_absent(self, tmp_path):
        root = _write_fixture_registry(tmp_path)
        entity_file = load_entity_file(root, "authors")
        assert legacy_id_lookup(entity_file, "dagg_john_l") == []


class TestCanonicalIdBackfill:
    def test_backfill_fills_missing_canonical_id_only(self, tmp_path):
        root = _write_fixture_registry(tmp_path)
        entity_file = load_entity_file(root, "authors")
        unit = build_canonical_id_backfill_unit(
            entity_file,
            migration_version="1.0.0",
            canonical_id_map={"FULLER-ANDREW-001": "fuller_andrew"},
            legacy_id_map={"FULLER-ANDREW-001": ["FULLER-ANDREW-001"]},
        )
        engine = MigrationEngine(
            checkpoint_dir=tmp_path / "cp", lock_path=tmp_path / "lock.json", audit_path=tmp_path / "audit.jsonl"
        )
        report = engine.execute(unit)
        assert report.fail_count == 0

        reloaded = load_entity_file(root, "authors")
        assert canonical_id_lookup(reloaded, "FULLER-ANDREW-001") == "fuller_andrew"
        assert legacy_id_lookup(reloaded, "FULLER-ANDREW-001") == ["FULLER-ANDREW-001"]
        # 이미 canonical_id가 있던 entry는 그대로 유지(불변)
        assert canonical_id_lookup(reloaded, "dagg_john_l") == "dagg_john_l"

    def test_backfill_is_noop_when_nothing_to_fill(self, tmp_path):
        root = tmp_path / "all_canonical"
        root.mkdir()
        (root / "authors.yaml").write_text(
            "schema_version: '1.0'\nauthors:\n  - author_id: dagg_john_l\n    canonical_id: dagg_john_l\n",
            encoding="utf-8",
        )
        entity_file = load_entity_file(root, "authors")
        unit = build_canonical_id_backfill_unit(
            entity_file, migration_version="1.0.0", canonical_id_map={}, legacy_id_map=None
        )
        engine = MigrationEngine(
            checkpoint_dir=tmp_path / "cp", lock_path=tmp_path / "lock.json", audit_path=tmp_path / "audit.jsonl"
        )
        report = engine.execute(unit)
        assert report.skipped_count == 1
        assert report.pass_count == 0

    def test_backfill_rejects_non_canonical_format(self, tmp_path):
        root = _write_fixture_registry(tmp_path)
        entity_file = load_entity_file(root, "authors")
        unit = build_canonical_id_backfill_unit(
            entity_file,
            migration_version="1.0.0",
            canonical_id_map={"FULLER-ANDREW-001": "FULLER_ANDREW"},  # ADR-017 위반(대문자)
        )
        engine = MigrationEngine(
            checkpoint_dir=tmp_path / "cp", lock_path=tmp_path / "lock.json", audit_path=tmp_path / "audit.jsonl"
        )
        report = engine.execute(unit)
        assert report.fail_count == 1

    def test_backfill_does_not_touch_existing_fk_fields(self, tmp_path):
        root = tmp_path / "registry_with_works"
        root.mkdir()
        (root / "authors.yaml").write_text(_AUTHORS_YAML, encoding="utf-8")
        (root / "works.yaml").write_text(
            "schema_version: '1.0'\nworks:\n  - work_id: FULLER-COMPLETE-WORKS-001\n    author_id: FULLER-ANDREW-001\n",
            encoding="utf-8",
        )
        engine = MigrationEngine(
            checkpoint_dir=tmp_path / "cp", lock_path=tmp_path / "lock.json", audit_path=tmp_path / "audit.jsonl"
        )
        units = build_all_backfill_units(
            root, "1.0.0", canonical_id_map={"FULLER-ANDREW-001": "fuller_andrew", "FULLER-COMPLETE-WORKS-001": "fuller_andrew_complete_works"}
        )
        for unit in units:
            report = engine.execute(unit)
            assert report.fail_count == 0

        works = load_entity_file(root, "works")
        # author_id FK는 그대로(Option B — 기존 FK 불변)
        assert works.entries[0]["author_id"] == "FULLER-ANDREW-001"
        assert works.entries[0]["canonical_id"] == "fuller_andrew_complete_works"


class TestBuildAllBackfillUnits:
    def test_one_unit_per_entity_file(self, tmp_path):
        root = tmp_path / "multi_entity"
        root.mkdir()
        (root / "authors.yaml").write_text(_AUTHORS_YAML, encoding="utf-8")
        (root / "works.yaml").write_text("schema_version: '1.0'\nworks: []\n", encoding="utf-8")
        units = build_all_backfill_units(root, "1.0.0", canonical_id_map={})
        assert len(units) == 2
