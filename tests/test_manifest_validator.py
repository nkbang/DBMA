"""Tests for scripts/manifest_validator.py (NAE-MANIFEST-VALIDATOR-IMPLEMENTATION-001).

Covers: Identity/Lifecycle/Audit schema validation, Authority Registry
FK checks (mandatory --registry-path), work_type conditional field
rules (via Registry work_type lookup), TSU_ELIGIBLE computation
(READY/BLOCKED), and corpus-manifest cross-reference for
copyright_status (--corpus-manifest-root, optional).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import scripts.manifest_validator as mv


def _write_manifest(tmp_path: Path, subdir: str, content: str) -> Path:
    d = tmp_path / "manifest" / subdir
    d.mkdir(parents=True, exist_ok=True)
    p = d / "manifest.yaml"
    p.write_text(content, encoding="utf-8")
    return p


def _write_registry(tmp_path: Path) -> Path:
    d = tmp_path / "registry"
    d.mkdir(parents=True, exist_ok=True)
    (d / "authors.yaml").write_text(
        "schema_version: '1.0'\nauthors: [{author_id: test_author}]\n", encoding="utf-8"
    )
    (d / "works.yaml").write_text(
        "schema_version: '1.0'\nworks: [{work_id: test_work, author_id: test_author, work_type: monograph}]\n",
        encoding="utf-8",
    )
    (d / "editions.yaml").write_text(
        "schema_version: '1.0'\neditions: [{edition_id: test_edition, work_id: test_work}]\n", encoding="utf-8"
    )
    (d / "volumes.yaml").write_text("schema_version: '1.0'\nvolumes: []\n", encoding="utf-8")
    (d / "issues.yaml").write_text("schema_version: '1.0'\nissues: []\n", encoding="utf-8")
    (d / "sources.yaml").write_text(
        "schema_version: '1.0'\nsources: [{source_id: TEST-SRC-001, edition_id: test_edition}]\n",
        encoding="utf-8",
    )
    return d


def _write_corpus_manifest(tmp_path: Path, copyright_status: str = "public_domain") -> Path:
    d = tmp_path / "corpus" / "baptist"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "source_manifest.yaml"
    p.write_text(
        f"""
schema_version: "1.2"
sources:
  - source_id: TEST-SRC-001
    title: "Test"
    license: public_domain_original
    content_genre: [theology]
    status: approved_for_acquisition
    copyright_status: {copyright_status}
""",
        encoding="utf-8",
    )
    return d.parent


_VALID_ENTRY = """
schema_version: "1.0.0"
manifests:
  - manifest_id: TEST-SRC-001
    source_id: TEST-SRC-001
    author_id: test_author
    work_id: test_work
    edition_id: test_edition
    volume_id: null
    issue_id: null
    acquisition_status: acquired
    ocr_status: complete
    metadata_status: verified
    tsu_status: not_ready
    embedding_status: not_started
    created_at: "2026-08-03T00:00:00Z"
    updated_at: "2026-08-03T00:00:00Z"
    verified_by: cue
"""


class TestIdentityAndSchema:
    def test_valid_manifest_passes_schema_checks(self, tmp_path):
        _write_manifest(tmp_path, "ok", _VALID_ENTRY)
        registry = _write_registry(tmp_path)
        result = mv.validate(tmp_path / "manifest", registry, None)
        assert result.fail_count == 0

    def test_missing_schema_version_fails(self, tmp_path):
        bad = _VALID_ENTRY.replace('schema_version: "1.0.0"\n', "")
        _write_manifest(tmp_path, "noschema", bad)
        registry = _write_registry(tmp_path)
        result = mv.validate(tmp_path / "manifest", registry, None)
        assert result.fail_count >= 1
        assert any("Identity 필수 필드 누락" in line and "schema_version" in line for line in result.lines)

    def test_missing_manifest_id_fails(self, tmp_path):
        bad = _VALID_ENTRY.replace(
            "  - manifest_id: TEST-SRC-001\n    source_id: TEST-SRC-001\n",
            "  - source_id: TEST-SRC-001\n",
        )
        _write_manifest(tmp_path, "noid", bad)
        registry = _write_registry(tmp_path)
        result = mv.validate(tmp_path / "manifest", registry, None)
        assert result.fail_count >= 1


class TestEnumValidation:
    def test_invalid_metadata_status_fails(self, tmp_path):
        bad = _VALID_ENTRY.replace("metadata_status: verified", "metadata_status: validated")
        _write_manifest(tmp_path, "badenum", bad)
        registry = _write_registry(tmp_path)
        result = mv.validate(tmp_path / "manifest", registry, None)
        assert result.fail_count >= 1
        assert any("metadata_status 값 비정상" in line for line in result.lines)

    def test_invalid_ocr_status_fails(self, tmp_path):
        bad = _VALID_ENTRY.replace("ocr_status: complete", "ocr_status: done")
        _write_manifest(tmp_path, "badocr", bad)
        registry = _write_registry(tmp_path)
        result = mv.validate(tmp_path / "manifest", registry, None)
        assert result.fail_count >= 1
        assert any("ocr_status 값 비정상" in line for line in result.lines)


class TestAuthorityFK:
    def test_missing_fk_fails(self, tmp_path):
        bad = _VALID_ENTRY.replace("work_id: test_work", "work_id: nonexistent_work")
        _write_manifest(tmp_path, "badfk", bad)
        registry = _write_registry(tmp_path)
        result = mv.validate(tmp_path / "manifest", registry, None)
        assert result.fail_count >= 1
        assert any("work_id='nonexistent_work'" in line and "존재하지 않음" in line for line in result.lines)

    def test_present_fk_passes(self, tmp_path):
        _write_manifest(tmp_path, "goodfk", _VALID_ENTRY)
        registry = _write_registry(tmp_path)
        result = mv.validate(tmp_path / "manifest", registry, None)
        assert any("work_id='test_work' Registry 참조 확인" in line for line in result.lines)

    def test_work_type_conditional_rule_via_registry_lookup(self, tmp_path):
        """monograph(Registry work_type)인데 volume_id가 있으면 FAIL."""
        bad = _VALID_ENTRY.replace("volume_id: null", "volume_id: some_volume")
        _write_manifest(tmp_path, "badworktype", bad)
        registry = _write_registry(tmp_path)  # test_work.work_type = monograph
        result = mv.validate(tmp_path / "manifest", registry, None)
        assert result.fail_count >= 1
        assert any("volume_id 존재" in line and "금지" in line for line in result.lines)


class TestTsuEligible:
    def test_ready_when_all_conditions_met(self, tmp_path):
        _write_manifest(tmp_path, "ready", _VALID_ENTRY)
        registry = _write_registry(tmp_path)
        corpus_root = _write_corpus_manifest(tmp_path, copyright_status="public_domain")
        result = mv.validate(tmp_path / "manifest", registry, corpus_root)
        assert any("TSU_ELIGIBLE=READY" in line for line in result.lines)

    def test_blocked_when_metadata_not_verified(self, tmp_path):
        bad = _VALID_ENTRY.replace("metadata_status: verified", "metadata_status: in_progress")
        _write_manifest(tmp_path, "blocked-meta", bad)
        registry = _write_registry(tmp_path)
        corpus_root = _write_corpus_manifest(tmp_path)
        result = mv.validate(tmp_path / "manifest", registry, corpus_root)
        assert any("TSU_ELIGIBLE=BLOCKED" in line and "metadata_status" in line for line in result.lines)

    def test_blocked_when_copyright_not_public_domain(self, tmp_path):
        _write_manifest(tmp_path, "blocked-copyright", _VALID_ENTRY)
        registry = _write_registry(tmp_path)
        corpus_root = _write_corpus_manifest(tmp_path, copyright_status="unknown")
        result = mv.validate(tmp_path / "manifest", registry, corpus_root)
        assert any("TSU_ELIGIBLE=BLOCKED" in line and "copyright_status" in line for line in result.lines)

    def test_blocked_without_corpus_manifest_root(self, tmp_path):
        """--corpus-manifest-root 미지정 시 copyright_status 조회 불가 -> BLOCKED."""
        _write_manifest(tmp_path, "no-corpus-root", _VALID_ENTRY)
        registry = _write_registry(tmp_path)
        result = mv.validate(tmp_path / "manifest", registry, None)
        assert any("TSU_ELIGIBLE=BLOCKED" in line and "조회 불가" in line for line in result.lines)

    def test_blocked_when_cross_reference_source_missing(self, tmp_path):
        """corpus-manifest-root는 있지만 해당 source_id가 그 안에 없으면 BLOCKED."""
        _write_manifest(tmp_path, "xref-miss", _VALID_ENTRY)
        registry = _write_registry(tmp_path)
        corpus_root = tmp_path / "empty_corpus"
        (corpus_root / "baptist").mkdir(parents=True)
        (corpus_root / "baptist" / "source_manifest.yaml").write_text(
            "schema_version: '1.2'\nsources: []\n", encoding="utf-8"
        )
        result = mv.validate(tmp_path / "manifest", registry, corpus_root)
        assert any("TSU_ELIGIBLE=BLOCKED" in line and "조회 불가" in line for line in result.lines)


class TestSourceManifest1to1:
    def test_duplicate_source_id_across_manifests_fails(self, tmp_path):
        entry_a = _VALID_ENTRY
        entry_b = _VALID_ENTRY.replace("manifest_id: TEST-SRC-001", "manifest_id: TEST-SRC-001-DUP")
        _write_manifest(tmp_path, "dup-a", entry_a)
        _write_manifest(tmp_path, "dup-b", entry_b)
        registry = _write_registry(tmp_path)
        result = mv.validate(tmp_path / "manifest", registry, None)
        assert any("Source:Manifest 1:1 위반" in line for line in result.lines)


class TestRealPilotData:
    """실제 저장소 Manifest Pilot(10건) 재검증 — 회귀 확인용."""

    def test_real_pilot_manifests_fk_and_reference_integrity_pass(self):
        root = Path("resources/theological_sources/manifest")
        registry = Path("resources/theological_sources/authority")
        result = mv.validate(root, registry, None)
        # FK/Reference Integrity 자체는 깨지지 않아야 함(Manifest Pilot Report-001의
        # Reference Integrity 10/10 PASS와 일치) — enum 값 불일치(기존에 발견된
        # 별도 이슈)는 이 테스트의 관심사가 아니므로 FK 관련 메시지만 확인.
        fk_failures = [line for line in result.lines if "Registry" in line and "존재하지 않음" in line]
        assert fk_failures == []
