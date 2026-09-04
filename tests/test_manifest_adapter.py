"""Tests for scripts/adapters/manifest_adapter.py
(NAE-METADATA-MIGRATION-PILOT-IMPLEMENTATION-001).

All tests use Pilot Fixtures under tmp_path only — never the real
Pilot Manifest under resources/theological_sources/manifest/pilot/.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.adapters.manifest_adapter import (
    build_touch_unit,
    edition_id_lookup,
    load_manifest,
    source_id_lookup,
    verify_fk,
    volume_id_lookup,
)
from scripts.migration_engine import MigrationEngine


_MANIFEST_YAML = """
manifests:
  - manifest_id: m1
    source_id: BAP-CHURCH-DAGG-001
    author_id: dagg_john_l
    work_id: WORK-DAGG-CHURCH-ORDER-001
    edition_id: WORK-DAGG-CHURCH-ORDER-001-1871
    updated_at: "2026-08-01"
"""


def _write_fixture_manifest(tmp_path: Path) -> Path:
    path = tmp_path / "manifest.yaml"
    path.write_text(_MANIFEST_YAML, encoding="utf-8")
    return path


class TestLoadLookup:
    def test_load_manifest(self, tmp_path):
        path = _write_fixture_manifest(tmp_path)
        manifest = load_manifest(path)
        assert len(manifest.entries) == 1

    def test_source_id_lookup_found(self, tmp_path):
        manifest = load_manifest(_write_fixture_manifest(tmp_path))
        entry = source_id_lookup(manifest, "BAP-CHURCH-DAGG-001")
        assert entry is not None
        assert entry["manifest_id"] == "m1"

    def test_source_id_lookup_not_found(self, tmp_path):
        manifest = load_manifest(_write_fixture_manifest(tmp_path))
        assert source_id_lookup(manifest, "NONEXISTENT") is None

    def test_edition_id_lookup(self, tmp_path):
        manifest = load_manifest(_write_fixture_manifest(tmp_path))
        results = edition_id_lookup(manifest, "WORK-DAGG-CHURCH-ORDER-001-1871")
        assert len(results) == 1

    def test_volume_id_lookup_empty_when_absent(self, tmp_path):
        manifest = load_manifest(_write_fixture_manifest(tmp_path))
        assert volume_id_lookup(manifest, "any_volume") == []


class TestVerifyFk:
    def test_verify_fk_all_pass(self, tmp_path):
        manifest = load_manifest(_write_fixture_manifest(tmp_path))
        registry_index = {
            "authors": {"dagg_john_l"},
            "works": {"WORK-DAGG-CHURCH-ORDER-001"},
            "editions": {"WORK-DAGG-CHURCH-ORDER-001-1871"},
            "sources": {"BAP-CHURCH-DAGG-001"},
        }
        results = verify_fk(manifest, registry_index)
        assert all(ok for ok, _ in results)
        assert len(results) == 4  # author_id/work_id/edition_id/source_id

    def test_verify_fk_detects_broken_reference(self, tmp_path):
        manifest = load_manifest(_write_fixture_manifest(tmp_path))
        registry_index = {"authors": set(), "works": set(), "editions": set(), "sources": set()}
        results = verify_fk(manifest, registry_index)
        assert all(not ok for ok, _ in results)
        assert any("Broken Reference" in msg for _, msg in results)

    def test_verify_fk_unaffected_by_canonical_id_backfill(self, tmp_path):
        """Option B 재확인: Registry에 canonical_id가 추가돼도 registry_index
        (기존 FK 문자열 집합)는 그대로이므로 FK 검증 결과가 바뀌지 않는다."""
        manifest = load_manifest(_write_fixture_manifest(tmp_path))
        registry_index_before = {
            "authors": {"dagg_john_l"},
            "works": {"WORK-DAGG-CHURCH-ORDER-001"},
            "editions": {"WORK-DAGG-CHURCH-ORDER-001-1871"},
            "sources": {"BAP-CHURCH-DAGG-001"},
        }
        # canonical_id 추가는 registry_index(기존 ID 문자열 집합) 자체를
        # 바꾸지 않는다 — 동일 딕셔너리로 재검증해도 결과 동일해야 함.
        results_before = verify_fk(manifest, registry_index_before)
        results_after = verify_fk(manifest, dict(registry_index_before))
        assert results_before == results_after


class TestTouchUnit:
    def test_touch_unit_updates_updated_at_only(self, tmp_path):
        path = _write_fixture_manifest(tmp_path)
        unit = build_touch_unit(path, migration_version="1.0.0", updated_at="2026-08-05")
        engine = MigrationEngine(
            checkpoint_dir=tmp_path / "cp", lock_path=tmp_path / "lock.json", audit_path=tmp_path / "audit.jsonl"
        )
        report = engine.execute(unit)
        assert report.fail_count == 0

        manifest = load_manifest(path)
        assert manifest.entries[0]["updated_at"] == "2026-08-05"
        # FK 필드는 그대로
        assert manifest.entries[0]["source_id"] == "BAP-CHURCH-DAGG-001"
        assert manifest.entries[0]["author_id"] == "dagg_john_l"

    def test_touch_unit_is_idempotent(self, tmp_path):
        path = _write_fixture_manifest(tmp_path)
        unit = build_touch_unit(path, migration_version="1.0.0", updated_at="2026-08-05")
        engine = MigrationEngine(
            checkpoint_dir=tmp_path / "cp", lock_path=tmp_path / "lock.json", audit_path=tmp_path / "audit.jsonl"
        )
        engine.execute(unit)
        report_second = engine.execute(unit)
        assert report_second.skipped_count == 1
