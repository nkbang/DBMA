"""Tests for corruption detection in scripts/crosswalk/storage/yaml_repository.py
(NAE-TSU-GATE-RELIABILITY-IMPLEMENTATION-001 Phase 2).

Covers: invalid YAML, missing schema fields, broken index, schema
mismatch. All tests use tmp_path fixtures only.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.crosswalk.schema import Confidence, CrosswalkRecord, MappingStatus, SourceType, TargetType
from scripts.crosswalk.storage.yaml_repository import YamlCrosswalkRepository


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


class TestFreshRepositoryIsValid:
    def test_fresh_empty_repository_validates(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml", tmp_path / "index.json")
        ok, error = repo.validate_storage()
        assert ok is True
        assert error is None

    def test_fresh_repository_without_index_path_validates(self, tmp_path):
        """index_path를 아예 안 준 경우(InMemory처럼 index 미사용) —
        Check 3은 검사 대상 자체가 아니므로 통과해야 한다."""
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml")
        ok, error = repo.validate_storage()
        assert ok is True


class TestInvalidYaml:
    def test_check_parse_detects_malformed_yaml(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        yaml_path.write_text("records: [unterminated: flow: sequence: ::", encoding="utf-8")
        repo = YamlCrosswalkRepository(yaml_path)  # 파일이 이미 존재하므로 생성자가 덮어쓰지 않음
        ok, error = repo.check_parse()
        assert ok is False
        assert "parse 실패" in error

    def test_validate_storage_reports_error_for_malformed_yaml(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        repo = YamlCrosswalkRepository(yaml_path)
        yaml_path.write_text("records: [broken : yaml : here : ::", encoding="utf-8")
        ok, error = repo.validate_storage()
        assert ok is False
        assert "parse 실패" in error

    def test_get_after_corruption_raises_rather_than_silently_empty(self, tmp_path):
        """손상된 파일에서 list_all()/get()을 직접 호출하면 예외가
        전파된다 — 손상을 빈 결과로 오인하게 두지 않는다."""
        yaml_path = tmp_path / "crosswalk.yaml"
        repo = YamlCrosswalkRepository(yaml_path)
        yaml_path.write_text("records: [broken : yaml : ::", encoding="utf-8")
        try:
            repo.list_all()
            raised = False
        except Exception:
            raised = True
        assert raised is True


class TestMissingField:
    def test_check_schema_detects_missing_required_field(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        yaml_path.write_text(
            "records:\n"
            "  - crosswalk_id: cw_001\n"
            "    source_identifier: BAP-CHURCH-DAGG-001\n"
            "    # target_identifier missing\n"
            "    mapping_status: manual-confirmed\n"
            "    confidence: high\n",
            encoding="utf-8",
        )
        repo = YamlCrosswalkRepository(yaml_path)
        ok, error = repo.check_schema()
        assert ok is False
        assert "target_identifier" in error

    def test_check_schema_detects_missing_mapping_status(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        yaml_path.write_text(
            "records:\n"
            "  - crosswalk_id: cw_001\n"
            "    source_identifier: X\n"
            "    target_identifier: Y\n"
            "    confidence: high\n",
            encoding="utf-8",
        )
        repo = YamlCrosswalkRepository(yaml_path)
        ok, error = repo.check_schema()
        assert ok is False
        assert "mapping_status" in error

    def test_check_schema_passes_for_well_formed_records(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml")
        repo.add(_record())
        ok, error = repo.check_schema()
        assert ok is True
        assert error is None


class TestBrokenIndex:
    def test_missing_index_file_reported(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        index_path = tmp_path / "index.json"
        repo = YamlCrosswalkRepository(yaml_path, index_path)
        index_path.unlink()
        ok, error = repo.check_index_consistency()
        assert ok is False
        assert "rebuild" in error

    def test_index_mismatch_detected_not_silently_fixed(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        index_path = tmp_path / "index.json"
        repo = YamlCrosswalkRepository(yaml_path, index_path)
        repo.add(_record())

        # index.json을 수동으로 어긋나게 만듦(예: 실제 target과 다른 값)
        index_path.write_text(
            json.dumps({"cw_001": {"source_identifier": "BAP-CHURCH-DAGG-001", "target_identifier": "WRONG"}}),
            encoding="utf-8",
        )
        ok, error = repo.check_index_consistency()
        assert ok is False
        assert "불일치" in error

        # 자동 복구되지 않았어야 함(값이 여전히 WRONG)
        still_wrong = json.loads(index_path.read_text(encoding="utf-8"))
        assert still_wrong["cw_001"]["target_identifier"] == "WRONG"

    def test_corrupted_index_json_reported(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        index_path = tmp_path / "index.json"
        repo = YamlCrosswalkRepository(yaml_path, index_path)
        index_path.write_text("{not valid json", encoding="utf-8")
        ok, error = repo.check_index_consistency()
        assert ok is False
        assert "파싱 실패" in error


class TestSchemaMismatch:
    def test_validate_storage_surfaces_schema_error_before_index_check(self, tmp_path):
        """Check 1(parse) -> Check 2(schema) -> Check 3(index) 순서로
        실행되며, 앞 단계 실패 시 뒤 단계는 확인하지 않고 즉시 반환."""
        yaml_path = tmp_path / "crosswalk.yaml"
        index_path = tmp_path / "index.json"
        YamlCrosswalkRepository(yaml_path, index_path)  # 정상 초기화(index.json 생성됨)

        yaml_path.write_text(
            "records:\n  - crosswalk_id: cw_001\n    source_identifier: X\n",  # target_identifier/mapping_status/confidence 없음
            encoding="utf-8",
        )
        ok, error = YamlCrosswalkRepository(yaml_path, index_path).validate_storage()
        assert ok is False
        assert "필수 필드 누락" in error


class TestNoAutoRecovery:
    def test_validate_storage_never_writes_to_yaml(self, tmp_path):
        """검증 메서드(check_parse/check_schema/check_index_consistency/
        validate_storage) 어느 것도 crosswalk.yaml을 수정하지 않는다."""
        yaml_path = tmp_path / "crosswalk.yaml"
        repo = YamlCrosswalkRepository(yaml_path)
        repo.add(_record())
        before = yaml_path.read_text(encoding="utf-8")
        repo.validate_storage()
        repo.check_parse()
        repo.check_schema()
        repo.check_index_consistency()
        after = yaml_path.read_text(encoding="utf-8")
        assert before == after
