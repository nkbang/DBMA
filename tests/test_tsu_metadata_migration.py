"""Tests for NAE/pipeline/tsu/metadata_migration.py
(NAE-METADATA-SCHEMA-2.0.0-MIGRATION-IMPLEMENTATION-001).

All tests use tmp_path / in-memory objects — Production files
(NAE/corpus/tsu/, resources/theological_sources/, NAE/metadata/crosswalk/)
are never written by this suite.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from NAE.pipeline.tsu import metadata_migration as mm
from scripts.crosswalk.schema import Confidence, CrosswalkRecord, MappingStatus, SourceType, TargetType


def _crosswalk(target_identifier="Dagg_Church_Order", source_identifier="BAP-CHURCH-DAGG-001",
                mapping_status=MappingStatus.MANUAL_CONFIRMED, confidence=Confidence.HIGH):
    return CrosswalkRecord(
        crosswalk_id="cw1",
        source_identifier=source_identifier,
        source_type=SourceType.REGISTRY_SOURCE_ID,
        target_identifier=target_identifier,
        target_type=TargetType.CORPUS_CANONICAL_ID,
        mapping_status=mapping_status,
        confidence=confidence,
        evidence="test evidence",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def _sources(crosswalk_records=None, registry=None, editions=None, works=None):
    crosswalk_records = crosswalk_records if crosswalk_records is not None else [_crosswalk()]
    by_target: dict = {}
    for r in crosswalk_records:
        by_target.setdefault(r.target_identifier, []).append(r)

    registry = registry if registry is not None else {
        "BAP-CHURCH-DAGG-001": {
            "source_id": "BAP-CHURCH-DAGG-001",
            "edition_id": "ED-1871",
            "volume_id": None,
            "source_type": "reference",
            "copyright_status": "public_domain",
            "usage_permission": "research",
            "access_control": "public",
        }
    }
    editions = editions if editions is not None else {
        "ED-1871": {"edition_id": "ED-1871", "work_id": "WORK-DAGG-001", "publication_year": 1871}
    }
    works = works if works is not None else {
        "WORK-DAGG-001": {"work_id": "WORK-DAGG-001", "author_id": "dagg_john_l"}
    }
    return mm.MigrationSources(
        crosswalk_by_target=by_target, registry_by_source_id=registry,
        editions_by_id=editions, works_by_id=works,
    )


def _tsu_record(**overrides):
    defaults = dict(
        id="TSU-0000001", tsu_schema_version="1", book="Church Order", author="John L. Dagg",
        identifier="Dagg_Church_Order", source_identifier="Dagg_Church_Order",
        collector_version="", canonical_version="2.0.0", page=8, paragraph=8, sentence=0,
        source_text="source text", claim="a claim", doctrine="Ecclesiology",
        scriptures=[], citations=[], confidence=0.8, extraction_method="llm",
        review_status="generated", model="my-theology-bot-v2:latest",
    )
    defaults.update(overrides)
    return defaults


class TestProvenanceChainSuccess:
    def test_resolve_metadata_full_chain(self):
        result = mm.resolve_metadata("Dagg_Church_Order", _sources())
        assert not isinstance(result, mm.MigrationSkip)
        assert result["source_id"] == "BAP-CHURCH-DAGG-001"
        assert result["author_id"] == "dagg_john_l"
        assert result["work_id"] == "WORK-DAGG-001"
        assert result["edition_id"] == "ED-1871"
        assert result["publication_year"] == 1871

    def test_resolve_metadata_volume_id_null_for_monograph(self):
        result = mm.resolve_metadata("Dagg_Church_Order", _sources())
        assert result["volume_id"] is None

    def test_resolve_metadata_tsu_access_full_for_public_domain(self):
        result = mm.resolve_metadata("Dagg_Church_Order", _sources())
        assert result["tsu_access"] == "full"

    def test_resolve_metadata_schema_version_stamped(self):
        result = mm.resolve_metadata("Dagg_Church_Order", _sources())
        assert result["metadata_schema_version"] == "1.1.0"

    def test_resolve_metadata_provenance_includes_crosswalk_id(self):
        result = mm.resolve_metadata("Dagg_Church_Order", _sources())
        assert result["metadata_provenance"]["crosswalk_id"] == "cw1"


class TestProvenanceChainFailure:
    def test_no_crosswalk_record_skips(self):
        result = mm.resolve_metadata("Unknown_Book", _sources())
        assert isinstance(result, mm.MigrationSkip)
        assert "no eligible crosswalk" in result.reason

    def test_low_confidence_crosswalk_skips(self):
        cw = _crosswalk(confidence=Confidence.LOW)
        result = mm.resolve_metadata("Dagg_Church_Order", _sources(crosswalk_records=[cw]))
        assert isinstance(result, mm.MigrationSkip)

    def test_unmapped_status_skips(self):
        cw = _crosswalk(mapping_status=MappingStatus.UNMAPPED, confidence=None)
        result = mm.resolve_metadata("Dagg_Church_Order", _sources(crosswalk_records=[cw]))
        assert isinstance(result, mm.MigrationSkip)

    def test_missing_registry_record_skips(self):
        result = mm.resolve_metadata("Dagg_Church_Order", _sources(registry={}))
        assert isinstance(result, mm.MigrationSkip)
        assert "no registry record" in result.reason

    def test_missing_edition_record_skips(self):
        result = mm.resolve_metadata("Dagg_Church_Order", _sources(editions={}))
        assert isinstance(result, mm.MigrationSkip)
        assert "no edition record" in result.reason

    def test_missing_work_record_skips(self):
        result = mm.resolve_metadata("Dagg_Church_Order", _sources(works={}))
        assert isinstance(result, mm.MigrationSkip)
        assert "no work record" in result.reason


class TestMissingAuthoritativeMetadata:
    def test_category_is_null_with_explicit_status(self):
        result = mm.resolve_metadata("Dagg_Church_Order", _sources())
        assert result["category"] is None
        assert result["category_status"] == "AUTHORITATIVE_SOURCE_MISSING"

    def test_citation_policy_is_null_with_explicit_status(self):
        result = mm.resolve_metadata("Dagg_Church_Order", _sources())
        assert result["citation_policy"] is None
        assert result["citation_policy_status"] == "AUTHORITATIVE_SOURCE_MISSING"

    def test_no_guessed_values_ever_present(self):
        result = mm.resolve_metadata("Dagg_Church_Order", _sources())
        assert result["category"] != ""
        assert result["citation_policy"] != ""


class TestExistingFieldImmutability:
    def test_migrate_record_preserves_all_immutable_fields(self):
        record = _tsu_record()
        new_record, status = mm.migrate_record(record, _sources())
        assert status == "migrated"
        for f in mm.IMMUTABLE_FIELDS:
            assert new_record[f] == record[f]

    def test_migrate_record_does_not_mutate_original(self):
        record = _tsu_record()
        original_copy = dict(record)
        mm.migrate_record(record, _sources())
        assert record == original_copy

    def test_verify_invariant_raises_on_claim_change(self):
        before = _tsu_record()
        after = dict(before)
        after["claim"] = "a DIFFERENT claim"
        with pytest.raises(mm.InvariantViolation):
            mm.verify_invariant(before, after)

    def test_verify_invariant_raises_on_review_status_change(self):
        before = _tsu_record()
        after = dict(before)
        after["review_status"] = "verified"
        with pytest.raises(mm.InvariantViolation):
            mm.verify_invariant(before, after)

    def test_verify_invariant_raises_on_key_removed(self):
        before = _tsu_record()
        after = dict(before)
        del after["doctrine"]
        with pytest.raises(mm.InvariantViolation):
            mm.verify_invariant(before, after)

    def test_verify_invariant_passes_on_pure_addition(self):
        before = _tsu_record()
        after = dict(before)
        after["new_field"] = "value"
        mm.verify_invariant(before, after)  # should not raise


class TestIdempotency:
    def test_second_run_skips_already_migrated(self):
        record = _tsu_record()
        migrated, status1 = mm.migrate_record(record, _sources())
        assert status1 == "migrated"
        result2, status2 = mm.migrate_record(migrated, _sources())
        assert status2 == "skipped_already_migrated"
        assert result2 is None

    def test_repeated_migrate_file_stable(self, tmp_path):
        item_dir = tmp_path / "Dagg_Church_Order"
        item_dir.mkdir()
        tsu_path = item_dir / "tsu.json"
        tsu_path.write_text(json.dumps([_tsu_record()]), encoding="utf-8")

        summary1, results1 = mm.migrate_file(tsu_path, _sources(), dry_run=False, backup_root=tmp_path / "backup")
        assert summary1.migrated == 1

        summary2, results2 = mm.migrate_file(tsu_path, _sources(), dry_run=False, backup_root=tmp_path / "backup")
        assert summary2.migrated == 0
        assert summary2.skipped_already_migrated == 1


class TestForceBehavior:
    def test_force_reprocesses_already_migrated(self):
        record = _tsu_record()
        migrated, _ = mm.migrate_record(record, _sources())
        result, status = mm.migrate_record(migrated, _sources(), force=True)
        assert status == "migrated"
        assert result is not None

    def test_without_force_never_overwrites(self):
        record = _tsu_record()
        migrated, _ = mm.migrate_record(record, _sources())
        result, status = mm.migrate_record(migrated, _sources(), force=False)
        assert status == "skipped_already_migrated"
        assert result is None


class TestRollback:
    def test_backup_written_before_overwrite(self, tmp_path):
        item_dir = tmp_path / "Dagg_Church_Order"
        item_dir.mkdir()
        tsu_path = item_dir / "tsu.json"
        original_content = json.dumps([_tsu_record()])
        tsu_path.write_text(original_content, encoding="utf-8")

        backup_root = tmp_path / "backup"
        mm.migrate_file(tsu_path, _sources(), dry_run=False, backup_root=backup_root)

        backup_file = backup_root / "Dagg_Church_Order" / "tsu.json"
        assert backup_file.exists()
        assert backup_file.read_text(encoding="utf-8") == original_content

    def test_rollback_restores_original_byte_for_byte(self, tmp_path):
        item_dir = tmp_path / "Dagg_Church_Order"
        item_dir.mkdir()
        tsu_path = item_dir / "tsu.json"
        original_content = json.dumps([_tsu_record()])
        tsu_path.write_text(original_content, encoding="utf-8")

        backup_root = tmp_path / "backup"
        mm.migrate_file(tsu_path, _sources(), dry_run=False, backup_root=backup_root)
        assert tsu_path.read_text(encoding="utf-8") != original_content  # migrated, changed

        backup_file = backup_root / "Dagg_Church_Order" / "tsu.json"
        tsu_path.write_text(backup_file.read_text(encoding="utf-8"), encoding="utf-8")  # rollback
        assert tsu_path.read_text(encoding="utf-8") == original_content


class TestAtomicWrite:
    def test_dry_run_never_writes_file(self, tmp_path):
        item_dir = tmp_path / "Dagg_Church_Order"
        item_dir.mkdir()
        tsu_path = item_dir / "tsu.json"
        original_content = json.dumps([_tsu_record()])
        tsu_path.write_text(original_content, encoding="utf-8")

        mm.migrate_file(tsu_path, _sources(), dry_run=True)
        assert tsu_path.read_text(encoding="utf-8") == original_content

    def test_dry_run_leaves_no_tmp_file(self, tmp_path):
        item_dir = tmp_path / "Dagg_Church_Order"
        item_dir.mkdir()
        tsu_path = item_dir / "tsu.json"
        tsu_path.write_text(json.dumps([_tsu_record()]), encoding="utf-8")

        mm.migrate_file(tsu_path, _sources(), dry_run=True)
        assert not (item_dir / "tsu.json.tmp").exists()

    def test_real_write_leaves_no_tmp_file_after_completion(self, tmp_path):
        item_dir = tmp_path / "Dagg_Church_Order"
        item_dir.mkdir()
        tsu_path = item_dir / "tsu.json"
        tsu_path.write_text(json.dumps([_tsu_record()]), encoding="utf-8")

        mm.migrate_file(tsu_path, _sources(), dry_run=False, backup_root=tmp_path / "backup")
        assert not (item_dir / "tsu.json.tmp").exists()
        assert tsu_path.exists()


class TestMalformedRecord:
    def test_missing_identifier_field_skips(self):
        record = _tsu_record()
        del record["identifier"]
        new_record, status = mm.migrate_record(record, _sources())
        assert new_record is None
        assert status.startswith("skipped_no_provenance")

    def test_malformed_json_file_reports_error_not_raise(self, tmp_path):
        item_dir = tmp_path / "Broken"
        item_dir.mkdir()
        tsu_path = item_dir / "tsu.json"
        tsu_path.write_text("{not valid json[[[", encoding="utf-8")

        summary, results = mm.migrate_file(tsu_path, _sources(), dry_run=True)
        assert summary.errors
        assert results == []

    def test_non_list_json_reports_error(self, tmp_path):
        item_dir = tmp_path / "Broken"
        item_dir.mkdir()
        tsu_path = item_dir / "tsu.json"
        tsu_path.write_text(json.dumps({"not": "a list"}), encoding="utf-8")

        summary, results = mm.migrate_file(tsu_path, _sources(), dry_run=True)
        assert summary.errors

    def test_empty_records_list_handled(self, tmp_path):
        item_dir = tmp_path / "Empty"
        item_dir.mkdir()
        tsu_path = item_dir / "tsu.json"
        tsu_path.write_text(json.dumps([]), encoding="utf-8")

        summary, results = mm.migrate_file(tsu_path, _sources(), dry_run=True)
        assert summary.total == 0
        assert summary.migrated == 0
        assert not summary.errors


class TestBatchAndDuplicateScenarios:
    def test_mixed_batch_migrated_and_skipped(self, tmp_path):
        item_dir = tmp_path / "Dagg_Church_Order"
        item_dir.mkdir()
        tsu_path = item_dir / "tsu.json"
        records = [_tsu_record(id="TSU-1"), _tsu_record(id="TSU-2", identifier="Unknown_Book")]
        tsu_path.write_text(json.dumps(records), encoding="utf-8")

        summary, results = mm.migrate_file(tsu_path, _sources(), dry_run=True)
        assert summary.total == 2
        assert summary.migrated == 1
        assert summary.skipped_no_provenance == 1

    def test_reexecution_after_partial_migration_is_stable(self, tmp_path):
        item_dir = tmp_path / "Dagg_Church_Order"
        item_dir.mkdir()
        tsu_path = item_dir / "tsu.json"
        records = [_tsu_record(id="TSU-1"), _tsu_record(id="TSU-2")]
        tsu_path.write_text(json.dumps(records), encoding="utf-8")

        mm.migrate_file(tsu_path, _sources(), dry_run=False, backup_root=tmp_path / "backup")
        summary2, _ = mm.migrate_file(tsu_path, _sources(), dry_run=False, backup_root=tmp_path / "backup")
        assert summary2.migrated == 0
        assert summary2.skipped_already_migrated == 2


class TestTsuAccessComputation:
    def test_public_domain_is_full(self):
        assert mm.compute_tsu_access("public_domain", "research") == "full"

    def test_licensed_research_is_full(self):
        assert mm.compute_tsu_access("licensed", "research") == "full"

    def test_citation_only_permission_is_citation_only(self):
        assert mm.compute_tsu_access("copyrighted", "citation_only") == "citation_only"

    def test_no_redistribution_is_restricted(self):
        assert mm.compute_tsu_access("copyrighted", "no_redistribution") == "restricted"

    def test_unknown_copyright_status_returns_none(self):
        assert mm.compute_tsu_access("unknown", "research") is None


class TestLoadMigrationSources:
    def test_load_from_real_looking_yaml_files(self, tmp_path):
        crosswalk_path = tmp_path / "crosswalk.yaml"
        crosswalk_path.write_text(
            "records:\n"
            "  - crosswalk_id: cw1\n"
            "    source_identifier: BAP-CHURCH-DAGG-001\n"
            "    source_type: registry_source_id\n"
            "    target_identifier: Dagg_Church_Order\n"
            "    target_type: corpus_canonical_id\n"
            "    mapping_status: manual-confirmed\n"
            "    confidence: high\n"
            "    evidence: 'test'\n"
            "    created_at: '2026-08-08T00:00:00+00:00'\n",
            encoding="utf-8",
        )
        registry_path = tmp_path / "sources.yaml"
        registry_path.write_text(
            "sources:\n"
            "  - source_id: BAP-CHURCH-DAGG-001\n"
            "    edition_id: ED-1871\n"
            "    volume_id: null\n"
            "    source_type: reference\n"
            "    copyright_status: public_domain\n"
            "    usage_permission: research\n"
            "    access_control: public\n",
            encoding="utf-8",
        )
        editions_path = tmp_path / "editions.yaml"
        editions_path.write_text(
            "editions:\n  - edition_id: ED-1871\n    work_id: WORK-1\n    publication_year: 1871\n",
            encoding="utf-8",
        )
        works_path = tmp_path / "works.yaml"
        works_path.write_text(
            "works:\n  - work_id: WORK-1\n    author_id: dagg_john_l\n",
            encoding="utf-8",
        )

        sources = mm.load_migration_sources(
            crosswalk_path=crosswalk_path, registry_path=registry_path,
            editions_path=editions_path, works_path=works_path,
        )
        result = mm.resolve_metadata("Dagg_Church_Order", sources)
        assert not isinstance(result, mm.MigrationSkip)
        assert result["author_id"] == "dagg_john_l"

    def test_missing_files_produce_empty_maps(self, tmp_path):
        sources = mm.load_migration_sources(
            crosswalk_path=tmp_path / "nope.yaml",
            registry_path=tmp_path / "nope2.yaml",
            editions_path=tmp_path / "nope3.yaml",
            works_path=tmp_path / "nope4.yaml",
        )
        assert sources.registry_by_source_id == {}
        assert sources.editions_by_id == {}
        assert sources.works_by_id == {}


class TestRegression:
    def test_metadata_schema_version_constant(self):
        assert mm.METADATA_SCHEMA_VERSION == "1.1.0"

    def test_immutable_fields_count_matches_builder_schema(self):
        assert len(mm.IMMUTABLE_FIELDS) == 20
