"""Tests for scripts/crosswalk/gate_orchestrator.py
(NAE-TSU-GATE-RELIABILITY-IMPLEMENTATION-001 Phase 3).

Covers the resolver -> storage validation -> gate flow, and confirms
(structurally, via import inspection) that the Orchestrator never
touches TSU generation, Manifest, RAW, Retrieval, or Embedding.
"""

import ast
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.crosswalk.gate_orchestrator import GateOrchestrator, ManifestEntryInput
from scripts.crosswalk.repository import InMemoryCrosswalkRepository
from scripts.crosswalk.resolver import CrosswalkResolver
from scripts.crosswalk.schema import Confidence, CrosswalkRecord, MappingStatus, SourceType, TargetType
from scripts.crosswalk.storage.yaml_repository import YamlCrosswalkRepository
from scripts.crosswalk.tsu_gate import TsuGateStatus


def _record(**overrides):
    defaults = dict(
        crosswalk_id="cw_001",
        source_identifier="BAP-CHURCH-DAGG-001",
        source_type=SourceType.REGISTRY_SOURCE_ID,
        target_identifier="PBC1742",
        target_type=TargetType.CORPUS_CANONICAL_ID,
        mapping_status=MappingStatus.MANUAL_CONFIRMED,
        confidence=Confidence.HIGH,
        evidence="archive.org metadata title/author cross-checked",
        created_at="2026-08-05T00:00:00+09:00",
    )
    defaults.update(overrides)
    return CrosswalkRecord(**defaults)


class TestPassFlow:
    def test_evaluate_passes_with_valid_manual_confirmed_mapping(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml", tmp_path / "index.json")
        repo.add(_record())
        orchestrator = GateOrchestrator(repo)

        result = orchestrator.evaluate(ManifestEntryInput(source_identifier="BAP-CHURCH-DAGG-001", tsu_eligible=True))
        assert result.status == TsuGateStatus.PASS

    def test_evaluate_with_in_memory_repository_also_passes(self):
        """InMemoryCrosswalkRepository는 validate_storage()가 없으므로
        저장소 검증 단계를 건너뛰고 바로 Resolver -> Gate로 간다."""
        repo = InMemoryCrosswalkRepository()
        repo.add(_record())
        orchestrator = GateOrchestrator(repo)
        result = orchestrator.evaluate(ManifestEntryInput("BAP-CHURCH-DAGG-001", tsu_eligible=True))
        assert result.status == TsuGateStatus.PASS


class TestBlockFlow:
    def test_evaluate_blocks_when_no_mapping_exists(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml", tmp_path / "index.json")
        orchestrator = GateOrchestrator(repo)
        result = orchestrator.evaluate(ManifestEntryInput("UNKNOWN-SOURCE", tsu_eligible=True))
        assert result.status == TsuGateStatus.BLOCK

    def test_evaluate_blocks_when_tsu_not_eligible(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml", tmp_path / "index.json")
        repo.add(_record())
        orchestrator = GateOrchestrator(repo)
        result = orchestrator.evaluate(ManifestEntryInput("BAP-CHURCH-DAGG-001", tsu_eligible=False))
        assert result.status == TsuGateStatus.BLOCK

    def test_evaluate_blocks_when_mapping_status_insufficient(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml", tmp_path / "index.json")
        repo.add(_record(mapping_status=MappingStatus.EVIDENCE_BACKED))
        orchestrator = GateOrchestrator(repo)
        result = orchestrator.evaluate(ManifestEntryInput("BAP-CHURCH-DAGG-001", tsu_eligible=True))
        assert result.status == TsuGateStatus.BLOCK


class TestErrorFlow:
    def test_evaluate_errors_on_corrupted_yaml(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        index_path = tmp_path / "index.json"
        repo = YamlCrosswalkRepository(yaml_path, index_path)
        repo.add(_record())
        yaml_path.write_text("records: [broken : yaml : ::", encoding="utf-8")

        orchestrator = GateOrchestrator(repo)
        result = orchestrator.evaluate(ManifestEntryInput("BAP-CHURCH-DAGG-001", tsu_eligible=True))
        assert result.status == TsuGateStatus.ERROR

    def test_evaluate_errors_on_missing_index(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        index_path = tmp_path / "index.json"
        repo = YamlCrosswalkRepository(yaml_path, index_path)
        repo.add(_record())
        index_path.unlink()

        orchestrator = GateOrchestrator(repo)
        result = orchestrator.evaluate(ManifestEntryInput("BAP-CHURCH-DAGG-001", tsu_eligible=True))
        assert result.status == TsuGateStatus.ERROR

    def test_evaluate_errors_on_index_mismatch(self, tmp_path):
        import json

        yaml_path = tmp_path / "crosswalk.yaml"
        index_path = tmp_path / "index.json"
        repo = YamlCrosswalkRepository(yaml_path, index_path)
        repo.add(_record())
        index_path.write_text(json.dumps({"cw_001": {"source_identifier": "X", "target_identifier": "WRONG"}}), encoding="utf-8")

        orchestrator = GateOrchestrator(repo)
        result = orchestrator.evaluate(ManifestEntryInput("BAP-CHURCH-DAGG-001", tsu_eligible=True))
        assert result.status == TsuGateStatus.ERROR

    def test_error_result_reason_mentions_storage(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        index_path = tmp_path / "index.json"
        repo = YamlCrosswalkRepository(yaml_path, index_path)
        index_path.unlink()
        orchestrator = GateOrchestrator(repo)
        result = orchestrator.evaluate(ManifestEntryInput("ANY", tsu_eligible=True))
        assert "Storage" in result.reason


class TestResolverIntegration:
    def test_orchestrator_uses_provided_resolver(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml", tmp_path / "index.json")
        repo.add(_record())
        resolver = CrosswalkResolver(repo)
        orchestrator = GateOrchestrator(repo, resolver=resolver)
        assert orchestrator.resolver is resolver

    def test_orchestrator_creates_default_resolver_if_not_given(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml", tmp_path / "index.json")
        orchestrator = GateOrchestrator(repo)
        assert isinstance(orchestrator.resolver, CrosswalkResolver)


class TestArchitectureBoundary:
    """구조적 검증(코드 실행이 아니라 AST 분석) — Orchestrator가
    TSU 생성/Manifest/RAW/Retrieval/Embedding을 절대 import하지 않는다."""

    _FORBIDDEN_MODULE_FRAGMENTS = ("nae.pipeline.tsu", "core.retrieval", "core.tsu_builder", "nae.pipeline.embed")

    def test_no_forbidden_imports(self):
        source = Path("scripts/crosswalk/gate_orchestrator.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.append(node.module)

        lowered = [m.lower() for m in imported_modules]
        for forbidden in self._FORBIDDEN_MODULE_FRAGMENTS:
            assert not any(forbidden in m for m in lowered), f"forbidden import found matching {forbidden!r}: {imported_modules}"

    def test_only_crosswalk_internal_imports(self):
        source = Path("scripts/crosswalk/gate_orchestrator.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        relative_imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.level > 0]
        # 전부 상대 import(.repository/.resolver/.tsu_gate)만 있어야 함
        assert all(m in {"repository", "resolver", "tsu_gate"} for m in relative_imports)


class TestIdempotency:
    def test_evaluate_called_twice_same_result(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml", tmp_path / "index.json")
        repo.add(_record())
        orchestrator = GateOrchestrator(repo)
        entry = ManifestEntryInput("BAP-CHURCH-DAGG-001", tsu_eligible=True)
        first = orchestrator.evaluate(entry)
        second = orchestrator.evaluate(entry)
        assert first.status == second.status == TsuGateStatus.PASS
