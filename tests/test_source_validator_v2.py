"""Regression + dual-schema tests for scripts/source_validator.py.

NAE-VALIDATOR-IMPLEMENTATION-001: source_validator.py now supports both
v1.2 (NAE-PD) and v2.1.0 (NAE-MODERN, ADR-016) manifests, branching on the
top-level `schema_version` field. These tests cover:
  - Test 1: existing v1.2 manifest -> PASS (no regression)
  - Test 2: valid v2.1.0 sample -> PASS
  - Test 3: invalid `category` (missing, required field) -> FAIL
  - Test 4: invalid `source_type` enum value -> FAIL
  - Test 5: missing `edition_id` -> FAIL (required per schema v2.1.0)
  - Test 6: invalid `volume_number` -> FAIL
  - Regression: real repo manifest (resources/theological_sources/baptist/
    source_manifest.yaml) still validates identically to the pre-change
    baseline (21 PASS / 0 WARNING / 0 FAIL).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import scripts.source_validator as sv


def _write_manifest(tmp_path: Path, subdir: str, content: str) -> Path:
    d = tmp_path / subdir
    d.mkdir(parents=True, exist_ok=True)
    p = d / "source_manifest.yaml"
    p.write_text(content, encoding="utf-8")
    return p


_V1_MANIFEST = """
schema_version: "1.2"
sources:
  - source_id: TEST-V1-001
    title: "Test Work"
    license: public_domain_original
    content_genre: [theology]
    status: approved_for_acquisition
"""

_V2_VALID_MANIFEST = """
schema_version: "2.1.0"
sources:
  - source_id: TEST-V2-001
    author_id: test_author
    work_id: test_author-test_work
    edition_id: test_author-test_work-ed1
    title: "Test Modern Work"
    publication_year: 2020
    category: theology
    source_type: public_archive
    copyright_status: public_domain
    usage_permission: research
    access_control: public
    citation_policy: "Test Author, Test Modern Work (2020)."
    status: approved_for_acquisition
"""


class TestV1Regression:
    """Test 1: 기존 v1.2 Manifest PASS."""

    def test_valid_v1_entry_passes(self, tmp_path):
        manifest_path = _write_manifest(tmp_path, "baptist", _V1_MANIFEST)
        result = sv.validate(tmp_path)
        assert result.fail_count == 0
        assert result.pass_count > 0

    def test_real_repo_manifest_unchanged(self):
        """실제 저장소 baptist manifest가 이번 변경 전후로 동일하게 통과하는지 확인."""
        root = Path("resources/theological_sources")
        result = sv.validate(root)
        assert result.fail_count == 0
        assert result.pass_count == 21
        assert result.warn_count == 0


class TestV2ValidManifest:
    """Test 2: 신규 v2.1.0 Sample PASS."""

    def test_valid_v2_entry_passes(self, tmp_path):
        _write_manifest(tmp_path, "modern/theology", _V2_VALID_MANIFEST)
        result = sv.validate(tmp_path)
        assert result.fail_count == 0
        assert result.pass_count > 0


class TestV2InvalidCategory:
    """Test 3: 잘못된(누락된) category FAIL."""

    def test_missing_category_fails(self, tmp_path):
        bad = _V2_VALID_MANIFEST.replace("    category: theology\n", "")
        _write_manifest(tmp_path, "modern/theology", bad)
        result = sv.validate(tmp_path)
        assert result.fail_count >= 1
        assert any("필수 필드 누락" in line and "category" in line for line in result.lines)


class TestV2InvalidSourceType:
    """Test 4: 잘못된 source_type FAIL."""

    def test_invalid_source_type_fails(self, tmp_path):
        bad = _V2_VALID_MANIFEST.replace("source_type: public_archive", "source_type: bogus_value")
        _write_manifest(tmp_path, "modern/theology", bad)
        result = sv.validate(tmp_path)
        assert result.fail_count >= 1
        assert any("source_type 값 비정상" in line for line in result.lines)

    def test_all_valid_source_type_values_pass(self, tmp_path):
        for value in ("licensed", "purchased", "personal", "reference", "public_archive"):
            manifest = _V2_VALID_MANIFEST.replace("source_type: public_archive", f"source_type: {value}")
            sub_root = tmp_path / value
            _write_manifest(sub_root, "modern/theology", manifest)
            result = sv.validate(sub_root)
            assert result.fail_count == 0, f"source_type={value} should PASS"


class TestV2MissingEditionId:
    """Test 5: edition_id 누락 — Schema v2.1.0 정책상 required -> FAIL."""

    def test_missing_edition_id_fails(self, tmp_path):
        bad = _V2_VALID_MANIFEST.replace("    edition_id: test_author-test_work-ed1\n", "")
        _write_manifest(tmp_path, "modern/theology", bad)
        result = sv.validate(tmp_path)
        assert result.fail_count >= 1
        assert any("edition_id" in line and "필수 필드 누락" in line for line in result.lines)


class TestV2VolumeNumber:
    """Test 6: volume_number 오류 FAIL."""

    def test_negative_volume_number_fails(self, tmp_path):
        bad = _V2_VALID_MANIFEST.rstrip() + "\n    volume_number: -1\n"
        _write_manifest(tmp_path, "modern/theology", bad)
        result = sv.validate(tmp_path)
        assert result.fail_count >= 1
        assert any("volume_number 값 비정상" in line for line in result.lines)

    def test_non_integer_volume_number_fails(self, tmp_path):
        bad = _V2_VALID_MANIFEST.rstrip() + '\n    volume_number: "one"\n'
        _write_manifest(tmp_path, "modern/theology", bad)
        result = sv.validate(tmp_path)
        assert result.fail_count >= 1
        assert any("volume_number 값 비정상" in line for line in result.lines)

    def test_valid_volume_number_passes(self, tmp_path):
        good = _V2_VALID_MANIFEST.rstrip() + "\n    volume_number: 2\n"
        _write_manifest(tmp_path, "modern/theology", good)
        result = sv.validate(tmp_path)
        assert result.fail_count == 0


class TestUnrecognizedSchemaVersion:
    def test_unrecognized_schema_version_fails(self, tmp_path):
        bad = _V2_VALID_MANIFEST.replace('schema_version: "2.1.0"', 'schema_version: "9.9.9"')
        _write_manifest(tmp_path, "modern/theology", bad)
        result = sv.validate(tmp_path)
        assert result.fail_count >= 1
        assert any("schema_version 인식 불가" in line for line in result.lines)


class TestArchiveSourceOptional:
    def test_missing_archive_source_passes(self, tmp_path):
        _write_manifest(tmp_path, "modern/theology", _V2_VALID_MANIFEST)
        result = sv.validate(tmp_path)
        assert result.fail_count == 0

    def test_string_archive_source_passes(self, tmp_path):
        good = _V2_VALID_MANIFEST.rstrip() + '\n    archive_source: "https://archive.org/details/example"\n'
        _write_manifest(tmp_path, "modern/theology", good)
        result = sv.validate(tmp_path)
        assert result.fail_count == 0

    def test_non_string_archive_source_fails(self, tmp_path):
        bad = _V2_VALID_MANIFEST.rstrip() + "\n    archive_source: 12345\n"
        _write_manifest(tmp_path, "modern/theology", bad)
        result = sv.validate(tmp_path)
        assert result.fail_count >= 1
        assert any("archive_source 형식 오류" in line for line in result.lines)


class TestSourceIdDedupAcrossSchemas:
    def test_duplicate_source_id_across_v1_and_v2_fails(self, tmp_path):
        v1 = _V1_MANIFEST.replace("TEST-V1-001", "SHARED-ID")
        v2 = _V2_VALID_MANIFEST.replace("TEST-V2-001", "SHARED-ID")
        _write_manifest(tmp_path, "baptist", v1)
        _write_manifest(tmp_path, "modern/theology", v2)
        result = sv.validate(tmp_path)
        assert any("source_id 중복" in line for line in result.lines)
