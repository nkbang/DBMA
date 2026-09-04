"""Tests for source_validator.py v2.2.x support (NAE-VALIDATOR-V2.2-IMPLEMENTATION-001).

Covers: schema_version routing (1.x/2.1.x/2.2.x), work_type conditional
field rules (edition_id/volume_id/issue_id), Authority Reference FK
checks (--registry-path), and Manifest Layer field validation
(manifest_id/processing_status, optional/opt-in).

Test 1/2 (v1.2 and v2.1 regression) are covered by
tests/test_source_validator_v2.py — not duplicated here.
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


def _write_registry(tmp_path: Path, **files: str) -> Path:
    d = tmp_path / "registry"
    d.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (d / f"{name}.yaml").write_text(content, encoding="utf-8")
    return d


_V22_BASE = """
schema_version: "2.2.0"
sources:
  - source_id: TEST-V22-{sid}
    author_id: test_author
    work_id: test_author-test_work
    title: "Test Work"
    publication_year: 2020
    category: theology
    source_type: public_archive
    copyright_status: public_domain
    usage_permission: research
    access_control: public
    citation_policy: "Test Author, Test Work (2020)."
    status: approved_for_acquisition
    work_type: {work_type}
{extra_fields}
"""


def _manifest(sid: str, work_type: str, extra: dict[str, str] | None = None) -> str:
    extra = extra or {}
    extra_lines = "\n".join(f"    {k}: {v}" for k, v in extra.items())
    return _V22_BASE.format(sid=sid, work_type=work_type, extra_fields=extra_lines)


class TestSchemaVersionRouting:
    """Phase 2: schema_version routing (1.x / 2.1.x / 2.2.x)."""

    def test_v1_routes_to_legacy(self, tmp_path):
        content = """
schema_version: "1.2"
sources:
  - source_id: TEST-ROUTE-V1
    title: "Test"
    license: public_domain_original
    content_genre: [theology]
    status: approved_for_acquisition
"""
        _write_manifest(tmp_path, "baptist", content)
        result = sv.validate(tmp_path)
        assert result.fail_count == 0

    def test_v21_routes_to_modern_without_conditional_rules(self, tmp_path):
        # v2.1.x still requires edition_id unconditionally (old behavior).
        content = _manifest("ROUTE-V21", "periodical").replace(
            'schema_version: "2.2.0"', 'schema_version: "2.1.0"'
        )
        _write_manifest(tmp_path, "modern/theology", content)
        result = sv.validate(tmp_path)
        # v2.1.x: edition_id missing -> FAIL (no conditional exemption for periodical)
        assert result.fail_count >= 1
        assert any("필수 필드 누락/공백(v2.1" in line for line in result.lines)

    def test_v22_detected_for_2_2_0(self, tmp_path):
        content = _manifest("ROUTE-V22", "monograph", {"edition_id": "test_author-test_work-ed1"})
        _write_manifest(tmp_path, "modern/theology", content)
        result = sv.validate(tmp_path)
        assert any("v2.2.x" in line for line in result.lines)

    def test_unrecognized_schema_version_fails(self, tmp_path):
        content = _manifest("ROUTE-BAD", "monograph").replace('schema_version: "2.2.0"', 'schema_version: "9.9"')
        _write_manifest(tmp_path, "modern/theology", content)
        result = sv.validate(tmp_path)
        assert result.fail_count >= 1


class TestWorkTypeConditionalFields:
    """Phase 3/4/5: work_type -> edition_id/volume_id/issue_id rules."""

    def test_monograph_with_edition_passes(self, tmp_path):
        content = _manifest("MONO-OK", "monograph", {"edition_id": "test_author-test_work-ed1"})
        _write_manifest(tmp_path, "modern/theology", content)
        result = sv.validate(tmp_path)
        assert result.fail_count == 0

    def test_monograph_missing_edition_fails(self, tmp_path):
        content = _manifest("MONO-NOED", "monograph")
        _write_manifest(tmp_path, "modern/theology", content)
        result = sv.validate(tmp_path)
        assert result.fail_count >= 1
        assert any("edition_id 누락" in line for line in result.lines)

    def test_periodical_with_issue_passes(self, tmp_path):
        content = _manifest("PER-ISSUE", "periodical", {"issue_id": "bmm_v001_i001"})
        _write_manifest(tmp_path, "modern/missions", content)
        result = sv.validate(tmp_path)
        assert result.fail_count == 0

    def test_monograph_with_issue_fails(self, tmp_path):
        content = _manifest(
            "MONO-ISSUE", "monograph",
            {"edition_id": "test_author-test_work-ed1", "issue_id": "i001"},
        )
        _write_manifest(tmp_path, "modern/theology", content)
        result = sv.validate(tmp_path)
        assert result.fail_count >= 1
        assert any("issue_id 존재" in line and "금지" in line for line in result.lines)

    def test_multi_volume_with_edition_and_volume_passes(self, tmp_path):
        content = _manifest(
            "MULTIVOL-OK", "multi_volume",
            {"edition_id": "test_author-test_work-ed1", "volume_id": "test_author-test_work-ed1-v01"},
        )
        _write_manifest(tmp_path, "modern/missions", content)
        result = sv.validate(tmp_path)
        assert result.fail_count == 0

    def test_unknown_work_type_fails(self, tmp_path):
        content = _manifest("BADTYPE", "not_a_real_type")
        _write_manifest(tmp_path, "modern/theology", content)
        result = sv.validate(tmp_path)
        assert result.fail_count >= 1
        assert any("work_type 값 비정상" in line for line in result.lines)

    def test_periodical_missing_both_volume_and_issue_fails(self, tmp_path):
        content = _manifest("PER-NEITHER", "periodical")
        _write_manifest(tmp_path, "modern/missions", content)
        result = sv.validate(tmp_path)
        assert result.fail_count >= 1
        assert any("periodical 최소 요구 미충족" in line for line in result.lines)

    def test_missing_work_type_defaults_to_monograph(self, tmp_path):
        content = _manifest("NOTYPE", "monograph").replace("    work_type: monograph\n", "")
        _write_manifest(tmp_path, "modern/theology", content)
        result = sv.validate(tmp_path)
        # defaults to monograph -> edition_id required -> missing -> FAIL
        assert result.fail_count >= 1
        assert any("monograph로 간주" in line for line in result.lines)


class TestAuthorityReferenceFK:
    """Phase 6: --registry-path optional FK validation."""

    def test_no_registry_path_skips_fk_check(self, tmp_path):
        content = _manifest("FK-SKIP", "monograph", {"edition_id": "nonexistent-edition"})
        _write_manifest(tmp_path, "modern/theology", content)
        result = sv.validate(tmp_path)  # no registry_path
        assert result.fail_count == 0  # FK not checked at all

    def test_registry_path_catches_missing_fk(self, tmp_path):
        content = _manifest("FK-MISSING", "monograph", {"edition_id": "nonexistent-edition"})
        _write_manifest(tmp_path, "modern/theology", content)
        registry = _write_registry(
            tmp_path,
            authors="schema_version: '1.0'\nauthors: [{author_id: test_author}]\n",
            works="schema_version: '1.0'\nworks: [{work_id: test_author-test_work}]\n",
            editions="schema_version: '1.0'\neditions: []\n",
        )
        result = sv.validate(tmp_path, registry_path=registry)
        assert result.fail_count >= 1
        assert any("nonexistent-edition" in line and "존재하지 않음" in line for line in result.lines)

    def test_registry_path_passes_when_fk_present(self, tmp_path):
        content = _manifest("FK-OK", "monograph", {"edition_id": "test_author-test_work-ed1"})
        _write_manifest(tmp_path, "modern/theology", content)
        registry = _write_registry(
            tmp_path,
            authors="schema_version: '1.0'\nauthors: [{author_id: test_author}]\n",
            works="schema_version: '1.0'\nworks: [{work_id: test_author-test_work}]\n",
            editions="schema_version: '1.0'\neditions: [{edition_id: test_author-test_work-ed1}]\n",
        )
        result = sv.validate(tmp_path, registry_path=registry)
        assert result.fail_count == 0


class TestManifestLayerFields:
    """Phase 7: manifest_id/processing_status — opt-in, only when present."""

    def test_entry_without_manifest_id_unaffected(self, tmp_path):
        content = _manifest("NOMANIFEST", "monograph", {"edition_id": "test_author-test_work-ed1"})
        _write_manifest(tmp_path, "modern/theology", content)
        result = sv.validate(tmp_path)
        assert result.fail_count == 0

    def test_manifest_status_valid_passes(self, tmp_path):
        content = _manifest(
            "MANIFEST-OK", "monograph",
            {
                "edition_id": "test_author-test_work-ed1",
                "manifest_id": "TEST-V22-MANIFEST-OK",
                "processing_status": "acquired",
                "verified_by": "cue",
            },
        )
        _write_manifest(tmp_path, "modern/theology", content)
        result = sv.validate(tmp_path)
        assert result.fail_count == 0
        assert any("processing_status=acquired" in line for line in result.lines)

    def test_manifest_status_invalid_fails(self, tmp_path):
        content = _manifest(
            "MANIFEST-BAD", "monograph",
            {
                "edition_id": "test_author-test_work-ed1",
                "manifest_id": "TEST-V22-MANIFEST-BAD",
                "processing_status": "bogus_status",
            },
        )
        _write_manifest(tmp_path, "modern/theology", content)
        result = sv.validate(tmp_path)
        assert result.fail_count >= 1
        assert any("processing_status 값 비정상" in line for line in result.lines)

    def test_manifest_without_verified_by_warns_not_fails(self, tmp_path):
        content = _manifest(
            "MANIFEST-NOAUDIT", "monograph",
            {
                "edition_id": "test_author-test_work-ed1",
                "manifest_id": "TEST-V22-MANIFEST-NOAUDIT",
            },
        )
        _write_manifest(tmp_path, "modern/theology", content)
        result = sv.validate(tmp_path)
        assert result.fail_count == 0
        assert result.warn_count >= 1
        assert any("verified_by" in line and "WARNING" in line for line in result.lines)
