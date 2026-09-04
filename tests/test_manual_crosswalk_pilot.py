"""Tests for the Manual Crosswalk Pilot flow (NAE-MANUAL-CROSSWALK-
POPULATION-IMPLEMENTATION-001) — Crosswalk creation, Resolver lookup,
YAML persistence/reload, Gate PASS, duplicate prevention, Repository
integrity, and Evidence validation, modeled on the real Dagg/Hiscox
Pilot records. All tests use tmp_path fixtures — never the real
NAE/metadata/crosswalk/crosswalk.yaml.
"""

import hashlib
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from scripts.crosswalk.gate_orchestrator import GateOrchestrator, ManifestEntryInput
from scripts.crosswalk.repository import DuplicateCrosswalkIdError
from scripts.crosswalk.resolver import CrosswalkResolver
from scripts.crosswalk.schema import Confidence, CrosswalkRecord, MappingStatus, SourceType, TargetType
from scripts.crosswalk.storage.yaml_repository import YamlCrosswalkRepository
from scripts.crosswalk.tsu_gate import TsuGateStatus, check_tsu_gate
from scripts.crosswalk.validator import validate as validate_crosswalk


def _pilot_record(source_identifier="BAP-CHURCH-DAGG-001", target_identifier="Dagg_Church_Order", **overrides):
    crosswalk_id = hashlib.sha256(f"{source_identifier}:{target_identifier}".encode()).hexdigest()[:16]
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    defaults = dict(
        crosswalk_id=crosswalk_id,
        source_identifier=source_identifier,
        source_type=SourceType.REGISTRY_SOURCE_ID,
        target_identifier=target_identifier,
        target_type=TargetType.CORPUS_CANONICAL_ID,
        mapping_status=MappingStatus.MANUAL_CONFIRMED,
        confidence=Confidence.HIGH,
        evidence=(
            "Source Evidence: Registry Edition/Author/Publisher/Year match. "
            "File Evidence: original.pdf checksum + OCR title page match. "
            "Reviewer: Human. Decision Reason: independent Source+File corroboration."
        ),
        created_at=now,
        verified_at=now,
    )
    defaults.update(overrides)
    return CrosswalkRecord(**defaults)


class TestCrosswalkCreation:
    def test_pilot_record_constructs_with_manual_confirmed(self):
        record = _pilot_record()
        assert record.mapping_status == MappingStatus.MANUAL_CONFIRMED
        assert record.confidence == Confidence.HIGH

    def test_pilot_record_id_is_deterministic(self):
        r1 = _pilot_record()
        r2 = _pilot_record()
        assert r1.crosswalk_id == r2.crosswalk_id

    def test_hiscox_record_uses_distinct_id(self):
        dagg = _pilot_record()
        hiscox = _pilot_record(source_identifier="BAP-CHURCH-HISCOX", target_identifier="Hiscox_Standard_Manual")
        assert dagg.crosswalk_id != hiscox.crosswalk_id

    def test_pilot_record_is_gate_eligible(self):
        assert _pilot_record().is_gate_eligible() is True


class TestResolver:
    def test_resolve_returns_correct_target(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml", tmp_path / "index.json")
        repo.add(_pilot_record())
        resolver = CrosswalkResolver(repo)
        assert resolver.resolve("BAP-CHURCH-DAGG-001") == "Dagg_Church_Order"

    def test_resolve_record_returns_full_record(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml", tmp_path / "index.json")
        repo.add(_pilot_record())
        resolver = CrosswalkResolver(repo)
        record = resolver.resolve_record("BAP-CHURCH-DAGG-001")
        assert record is not None
        assert record.target_identifier == "Dagg_Church_Order"

    def test_resolve_unrelated_source_returns_none(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml", tmp_path / "index.json")
        repo.add(_pilot_record())
        resolver = CrosswalkResolver(repo)
        assert resolver.resolve("BAP-MISS-FULLER-VOL01") is None


class TestYamlPersistenceAndReload:
    def test_record_persists_to_yaml_file(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        repo = YamlCrosswalkRepository(yaml_path, tmp_path / "index.json")
        repo.add(_pilot_record())
        text = yaml_path.read_text(encoding="utf-8")
        assert "BAP-CHURCH-DAGG-001" in text
        assert "manual-confirmed" in text

    def test_reload_via_new_repository_instance(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        index_path = tmp_path / "index.json"
        YamlCrosswalkRepository(yaml_path, index_path).add(_pilot_record())

        reloaded = YamlCrosswalkRepository(yaml_path, index_path)
        record = reloaded.get(_pilot_record().crosswalk_id)
        assert record is not None
        assert record.mapping_status == MappingStatus.MANUAL_CONFIRMED

    def test_two_records_both_persist_and_reload(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        index_path = tmp_path / "index.json"
        repo = YamlCrosswalkRepository(yaml_path, index_path)
        repo.add(_pilot_record())
        repo.add(_pilot_record(source_identifier="BAP-CHURCH-HISCOX", target_identifier="Hiscox_Standard_Manual"))

        reloaded = YamlCrosswalkRepository(yaml_path, index_path)
        assert len(reloaded.list_all()) == 2


class TestGatePass:
    def test_gate_pass_for_pilot_record(self):
        result = check_tsu_gate(tsu_eligible=True, crosswalk_record=_pilot_record())
        assert result.status == TsuGateStatus.PASS
        assert result.eligible is True

    def test_orchestrator_end_to_end_pass(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml", tmp_path / "index.json")
        repo.add(_pilot_record())
        orchestrator = GateOrchestrator(repo)
        result = orchestrator.evaluate(ManifestEntryInput("BAP-CHURCH-DAGG-001", tsu_eligible=True))
        assert result.status == TsuGateStatus.PASS

    def test_second_pilot_record_also_passes(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml", tmp_path / "index.json")
        repo.add(_pilot_record(source_identifier="BAP-CHURCH-HISCOX", target_identifier="Hiscox_Standard_Manual"))
        orchestrator = GateOrchestrator(repo)
        result = orchestrator.evaluate(ManifestEntryInput("BAP-CHURCH-HISCOX", tsu_eligible=True))
        assert result.status == TsuGateStatus.PASS

    def test_unrelated_manifest_entry_still_blocked(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml", tmp_path / "index.json")
        repo.add(_pilot_record())
        orchestrator = GateOrchestrator(repo)
        result = orchestrator.evaluate(ManifestEntryInput("BAP-MISS-FULLER-VOL01", tsu_eligible=True))
        assert result.status == TsuGateStatus.BLOCK


class TestDuplicatePrevention:
    def test_duplicate_crosswalk_id_rejected(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml", tmp_path / "index.json")
        repo.add(_pilot_record())
        with pytest.raises(DuplicateCrosswalkIdError):
            repo.add(_pilot_record())  # 동일 source+target -> 동일 crosswalk_id

    def test_duplicate_add_does_not_corrupt_existing_record(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml", tmp_path / "index.json")
        repo.add(_pilot_record())
        try:
            repo.add(_pilot_record())
        except DuplicateCrosswalkIdError:
            pass
        assert len(repo.list_all()) == 1


class TestRepositoryIntegrity:
    def test_validate_storage_passes_after_pilot_records(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml", tmp_path / "index.json")
        repo.add(_pilot_record())
        repo.add(_pilot_record(source_identifier="BAP-CHURCH-HISCOX", target_identifier="Hiscox_Standard_Manual"))
        ok, error = repo.validate_storage()
        assert ok is True
        assert error is None

    def test_index_matches_yaml_after_pilot_records(self, tmp_path):
        import json

        yaml_path = tmp_path / "crosswalk.yaml"
        index_path = tmp_path / "index.json"
        repo = YamlCrosswalkRepository(yaml_path, index_path)
        repo.add(_pilot_record())
        index = json.loads(index_path.read_text(encoding="utf-8"))
        assert index[_pilot_record().crosswalk_id]["target_identifier"] == "Dagg_Church_Order"


class TestEvidenceValidation:
    def test_manual_confirmed_pilot_record_passes_evidence_check(self):
        result = validate_crosswalk([_pilot_record()])
        assert result.fail_count == 0
        assert any("evidence 존재 확인" in line for line in result.lines)

    def test_manual_confirmed_without_evidence_fails_validation(self):
        record = _pilot_record(evidence="")
        result = validate_crosswalk([record])
        assert any("evidence 누락" in line for line in result.lines)

    def test_validator_confirms_no_duplicate_pair_for_two_pilot_records(self):
        records = [
            _pilot_record(),
            _pilot_record(source_identifier="BAP-CHURCH-HISCOX", target_identifier="Hiscox_Standard_Manual"),
        ]
        result = validate_crosswalk(records)
        assert result.fail_count == 0

    def test_validator_checks_broken_reference_against_registry_source_ids(self):
        record = _pilot_record()
        result = validate_crosswalk([record], valid_source_identifiers={"BAP-CHURCH-DAGG-001", "BAP-CHURCH-HISCOX"})
        assert result.fail_count == 0
        assert any("Registry 참조 확인" in line for line in result.lines)

    def test_validator_flags_source_identifier_not_in_registry(self):
        record = _pilot_record(source_identifier="NOT-A-REAL-SOURCE")
        result = validate_crosswalk([record], valid_source_identifiers={"BAP-CHURCH-DAGG-001"})
        assert any("Broken Reference" in line for line in result.lines)


class TestIdempotency:
    def test_repeated_gate_check_stable(self):
        record = _pilot_record()
        results = {check_tsu_gate(tsu_eligible=True, crosswalk_record=record).status for _ in range(20)}
        assert results == {TsuGateStatus.PASS}

    def test_repeated_resolve_stable(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml", tmp_path / "index.json")
        repo.add(_pilot_record())
        resolver = CrosswalkResolver(repo)
        results = {resolver.resolve("BAP-CHURCH-DAGG-001") for _ in range(20)}
        assert results == {"Dagg_Church_Order"}
