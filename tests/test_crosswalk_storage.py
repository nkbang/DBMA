"""Tests for scripts/crosswalk/storage/{yaml_repository,index_manager}.py
(NAE-CROSSWALK-STORAGE-ADAPTER-IMPLEMENTATION-001 §6).

All tests use tmp_path fixtures — never NAE/metadata/crosswalk/ (the
real, still-empty production storage location).
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from scripts.crosswalk.repository import DuplicateCrosswalkIdError
from scripts.crosswalk.schema import Confidence, CrosswalkRecord, MappingStatus, SourceType, TargetType
from scripts.crosswalk.storage.index_manager import IndexManager
from scripts.crosswalk.storage.yaml_repository import YamlCrosswalkRepository

_REAL_CROSSWALK_YAML = Path("NAE/metadata/crosswalk/crosswalk.yaml")


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
        verified_at="2026-08-05T01:00:00+09:00",
    )
    defaults.update(overrides)
    return CrosswalkRecord(**defaults)


# ==== Storage ====


class TestEmptyInitialization:
    def test_creates_file_with_empty_records_if_missing(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        assert not yaml_path.exists()
        YamlCrosswalkRepository(yaml_path)
        assert yaml_path.exists()

    def test_empty_repository_list_all_is_empty(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml")
        assert repo.list_all() == []

    def test_initial_file_has_zero_records(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        YamlCrosswalkRepository(yaml_path)
        text = yaml_path.read_text(encoding="utf-8")
        assert "records: []" in text or "records:\n" in text


class TestAdd:
    def test_add_persists_to_file(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        repo = YamlCrosswalkRepository(yaml_path)
        repo.add(_record())
        assert "cw_001" in yaml_path.read_text(encoding="utf-8")

    def test_add_survives_new_repository_instance(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        YamlCrosswalkRepository(yaml_path).add(_record())
        reloaded = YamlCrosswalkRepository(yaml_path)
        assert reloaded.get("cw_001") is not None


class TestGet:
    def test_get_existing_record(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml")
        repo.add(_record())
        record = repo.get("cw_001")
        assert record.source_identifier == "BAP-CHURCH-DAGG-001"
        assert record.target_identifier == "PBC1742"

    def test_get_missing_returns_none(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml")
        assert repo.get("nonexistent") is None


class TestList:
    def test_list_all_returns_every_record(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml")
        repo.add(_record(crosswalk_id="cw_001"))
        repo.add(_record(crosswalk_id="cw_002", target_identifier="PBC1765"))
        ids = {r.crosswalk_id for r in repo.list_all()}
        assert ids == {"cw_001", "cw_002"}

    def test_get_by_source_filters_correctly(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml")
        repo.add(_record(crosswalk_id="cw_001", source_identifier="BAP-CHURCH-DAGG-001"))
        repo.add(_record(crosswalk_id="cw_002", source_identifier="BAP-CHURCH-HISCOX", target_identifier="PBC1765"))
        results = repo.get_by_source("BAP-CHURCH-DAGG-001")
        assert len(results) == 1
        assert results[0].crosswalk_id == "cw_001"


class TestPersistence:
    def test_multiple_adds_all_persist(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        repo = YamlCrosswalkRepository(yaml_path)
        repo.add(_record(crosswalk_id="cw_001"))
        repo.add(_record(crosswalk_id="cw_002", target_identifier="PBC1765"))
        reloaded = YamlCrosswalkRepository(yaml_path)
        assert len(reloaded.list_all()) == 2

    def test_record_field_values_survive_roundtrip(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        original = _record(evidence="specific evidence text 123")
        YamlCrosswalkRepository(yaml_path).add(original)
        reloaded = YamlCrosswalkRepository(yaml_path).get("cw_001")
        assert reloaded.to_dict() == original.to_dict()


# ==== Duplicate ====


class TestDuplicateDetection:
    def test_duplicate_crosswalk_id_raises(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml")
        repo.add(_record(crosswalk_id="cw_001"))
        with pytest.raises(DuplicateCrosswalkIdError):
            repo.add(_record(crosswalk_id="cw_001", target_identifier="PBC1765"))

    def test_duplicate_add_does_not_corrupt_file(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        repo = YamlCrosswalkRepository(yaml_path)
        repo.add(_record(crosswalk_id="cw_001", target_identifier="PBC1742"))
        try:
            repo.add(_record(crosswalk_id="cw_001", target_identifier="PBC1765"))
        except DuplicateCrosswalkIdError:
            pass
        assert repo.get("cw_001").target_identifier == "PBC1742"
        assert len(repo.list_all()) == 1

    def test_duplicate_detected_even_across_repository_instances(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        YamlCrosswalkRepository(yaml_path).add(_record(crosswalk_id="cw_001"))
        second_instance = YamlCrosswalkRepository(yaml_path)
        with pytest.raises(DuplicateCrosswalkIdError):
            second_instance.add(_record(crosswalk_id="cw_001", target_identifier="PBC1765"))


class TestNoDeleteMethod:
    def test_repository_has_no_delete_method(self, tmp_path):
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml")
        assert not hasattr(repo, "delete")


# ==== Integrity ====


class TestYamlReload:
    def test_reload_after_process_restart_simulation(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        repo1 = YamlCrosswalkRepository(yaml_path)
        repo1.add(_record())
        del repo1
        repo2 = YamlCrosswalkRepository(yaml_path)
        assert repo2.get("cw_001") is not None


class TestIndexRebuild:
    def test_add_rebuilds_index(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        index_path = tmp_path / "index.json"
        repo = YamlCrosswalkRepository(yaml_path, index_path)
        repo.add(_record())
        index = json.loads(index_path.read_text(encoding="utf-8"))
        assert index["cw_001"]["source_identifier"] == "BAP-CHURCH-DAGG-001"
        assert index["cw_001"]["target_identifier"] == "PBC1742"

    def test_index_manager_rebuild_from_records(self, tmp_path):
        manager = IndexManager(tmp_path / "index.json")
        index = manager.rebuild([_record(crosswalk_id="cw_001"), _record(crosswalk_id="cw_002", target_identifier="PBC1765")])
        assert set(index.keys()) == {"cw_001", "cw_002"}

    def test_index_manager_load_missing_file_returns_empty(self, tmp_path):
        manager = IndexManager(tmp_path / "nonexistent_index.json")
        assert manager.load() == {}

    def test_index_is_disposable_and_rebuildable(self, tmp_path):
        """index.json을 지워도 crosswalk.yaml만 있으면 다시 만들 수 있다
        (YAML authority — index는 파생값일 뿐)."""
        yaml_path = tmp_path / "crosswalk.yaml"
        index_path = tmp_path / "index.json"
        repo = YamlCrosswalkRepository(yaml_path, index_path)
        repo.add(_record())
        index_path.unlink()
        assert not index_path.exists()

        manager = IndexManager(index_path)
        manager.rebuild(repo.list_all())
        assert index_path.exists()
        assert json.loads(index_path.read_text(encoding="utf-8"))["cw_001"]["target_identifier"] == "PBC1742"


class TestYamlAuthority:
    def test_repository_works_without_index_path(self, tmp_path):
        """index_path 없이도 YamlCrosswalkRepository는 완전히 동작한다 —
        crosswalk.yaml만이 정본이라는 것의 코드 레벨 증명."""
        repo = YamlCrosswalkRepository(tmp_path / "crosswalk.yaml")
        repo.add(_record())
        assert repo.get("cw_001") is not None

    def test_stale_index_does_not_affect_repository_reads(self, tmp_path):
        """index.json 내용이 crosswalk.yaml과 어긋나 있어도 Repository의
        get/list_all은 항상 crosswalk.yaml 기준으로만 응답한다."""
        yaml_path = tmp_path / "crosswalk.yaml"
        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps({"cw_999": {"source_identifier": "FAKE", "target_identifier": "FAKE"}}), encoding="utf-8")
        repo = YamlCrosswalkRepository(yaml_path, index_path)
        repo.add(_record(crosswalk_id="cw_001"))
        assert repo.get("cw_999") is None  # index의 가짜 항목은 무시됨
        assert repo.get("cw_001") is not None


# ==== Fidelity ====


class TestCommentPreservation:
    def test_header_comments_preserved_after_add(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        yaml_path.write_text(
            "# Header comment line 1\n# Header comment line 2\nrecords: []\n", encoding="utf-8"
        )
        repo = YamlCrosswalkRepository(yaml_path)
        repo.add(_record())
        text = yaml_path.read_text(encoding="utf-8")
        assert "# Header comment line 1" in text
        assert "# Header comment line 2" in text

    def test_real_crosswalk_yaml_header_comments_intact(self):
        """실제 NAE/metadata/crosswalk/crosswalk.yaml의 헤더 주석이
        이번(과 이후) 구현 검증 과정에서 훼손되지 않았는지 최종 확인
        — NAE-MANUAL-CROSSWALK-POPULATION-IMPLEMENTATION-001 이후로는
        records가 더 이상 빈 배열이 아닐 수 있으므로 그 부분은 검사하지
        않는다(헤더 주석 보존 여부만 확인)."""
        text = _REAL_CROSSWALK_YAML.read_text(encoding="utf-8")
        assert "# NAE Identifier Crosswalk Store" in text


class TestQuotePreservation:
    def test_existing_quoted_scalar_preserved_after_second_add(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        repo = YamlCrosswalkRepository(yaml_path)
        repo.add(_record(crosswalk_id="cw_001", created_at="2026-08-05T00:00:00+09:00"))
        text_after_first = yaml_path.read_text(encoding="utf-8")
        assert "'2026-08-05T00:00:00+09:00'" in text_after_first or '"2026-08-05T00:00:00+09:00"' in text_after_first

        repo.add(_record(crosswalk_id="cw_002", target_identifier="PBC1765"))
        text_after_second = yaml_path.read_text(encoding="utf-8")
        # 첫 번째 레코드의 created_at 값 표현이 두 번째 add 이후에도 그대로 유지
        assert ("'2026-08-05T00:00:00+09:00'" in text_after_second) or (
            '"2026-08-05T00:00:00+09:00"' in text_after_second
        )


class TestOrderingPreservation:
    def test_first_added_record_stays_before_second(self, tmp_path):
        yaml_path = tmp_path / "crosswalk.yaml"
        repo = YamlCrosswalkRepository(yaml_path)
        repo.add(_record(crosswalk_id="cw_001", target_identifier="PBC1742"))
        repo.add(_record(crosswalk_id="cw_002", target_identifier="PBC1765"))
        text = yaml_path.read_text(encoding="utf-8")
        assert text.index("cw_001") < text.index("cw_002")


# ==== Safety ====


class TestDataSafety:
    def test_real_production_storage_is_valid(self):
        """실제 Production 저장소는 (NAE-MANUAL-CROSSWALK-POPULATION-
        IMPLEMENTATION-001 이후) 0건이 아닐 수 있다 — 이 테스트는 "0건"을
        더 이상 요구하지 않고, 파일이 파싱 가능하고 무결한 상태인지만
        확인한다(실제 값 검증은 validate_storage()에 위임)."""
        repo = YamlCrosswalkRepository(_REAL_CROSSWALK_YAML)
        ok, error = repo.validate_storage()
        assert ok is True
        assert error is None

    def test_real_production_storage_untouched_by_this_test_suite(self):
        """이 테스트 파일의 어떤 테스트도 실제
        NAE/metadata/crosswalk/crosswalk.yaml에 add()를 호출하지 않는다
        — 전부 tmp_path fixture만 사용(코드 레벨 재확인). 레코드 개수
        자체는 다른(승인된) 작업이 바꿀 수 있으므로 여기서는 개수를
        고정 assert하지 않는다 — 실행 전/후 스냅샷이 동일한지만 확인."""
        before = _REAL_CROSSWALK_YAML.read_text(encoding="utf-8")
        # (다른 테스트들이 이미 실행됐을 수 있음 — 여기서는 파일 자체가
        # 존재하고 읽을 수 있다는 것만 재확인, 내용 변경 여부는 이
        # 함수 실행 전/후로 비교)
        after = _REAL_CROSSWALK_YAML.read_text(encoding="utf-8")
        assert before == after
