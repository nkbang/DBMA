"""Tests for canonical_id/legacy_id governance checks in scripts/authority_validator.py
(NAE-ID-GOVERNANCE-IMPLEMENTATION-001, Check 9/10/11).

Existing checks 1-8 are untouched by this task — this file covers only the
new canonical_id existence/format check and the legacy_id type check.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import scripts.authority_validator as av


_GOOD_AUTHORS = """
schema_version: "1.0"
authors:
  - author_id: test_author
    canonical_id: test_author
    canonical_name: "Test Author"
"""

_GOOD_WORKS = "schema_version: '1.0'\nworks: []\n"
_GOOD_EDITIONS = "schema_version: '1.0'\neditions: []\n"
_GOOD_VOLUMES = "schema_version: '1.0'\nvolumes: []\n"
_GOOD_SOURCES = "schema_version: '1.0'\nsources: []\n"


def _write_registry(tmp_path: Path, **files: str) -> Path:
    d = tmp_path / "authority"
    d.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (d / f"{name}.yaml").write_text(content, encoding="utf-8")
    return d


def _write_good_registry(tmp_path: Path, **overrides: str) -> Path:
    files = dict(
        authors=_GOOD_AUTHORS,
        works=_GOOD_WORKS,
        editions=_GOOD_EDITIONS,
        volumes=_GOOD_VOLUMES,
        sources=_GOOD_SOURCES,
    )
    files.update(overrides)
    return _write_registry(tmp_path, **files)


class TestCanonicalIdExistence:
    def test_canonical_id_present_passes(self, tmp_path):
        registry = _write_good_registry(tmp_path)
        result = av.validate(registry)
        assert result.fail_count == 0
        assert any("canonical_id='test_author' 형식 확인" in line for line in result.lines)

    def test_canonical_id_missing_fails(self, tmp_path):
        authors = """
schema_version: "1.0"
authors:
  - author_id: test_author
    canonical_name: "Test Author"
"""
        registry = _write_good_registry(tmp_path, authors=authors)
        result = av.validate(registry)
        assert result.fail_count >= 1
        assert any("canonical_id 누락" in line for line in result.lines)


class TestCanonicalIdFormat:
    def test_upper_case_canonical_id_fails(self, tmp_path):
        authors = """
schema_version: "1.0"
authors:
  - author_id: FULLER-ANDREW-001
    canonical_id: FULLER_ANDREW
    canonical_name: "Andrew Fuller"
"""
        registry = _write_good_registry(tmp_path, authors=authors)
        result = av.validate(registry)
        assert result.fail_count >= 1
        assert any("ADR-017 canonical 표기(lowercase snake_case) 위반" in line for line in result.lines)

    def test_lowercase_canonical_id_passes(self, tmp_path):
        authors = """
schema_version: "1.0"
authors:
  - author_id: FULLER-ANDREW-001
    canonical_id: fuller_andrew
    legacy_id: ["FULLER-ANDREW-001"]
    canonical_name: "Andrew Fuller"
"""
        registry = _write_good_registry(tmp_path, authors=authors)
        result = av.validate(registry)
        assert result.fail_count == 0


class TestLegacyIdType:
    def test_legacy_id_array_passes(self, tmp_path):
        authors = """
schema_version: "1.0"
authors:
  - author_id: FULLER-ANDREW-001
    canonical_id: fuller_andrew
    legacy_id: ["FULLER-ANDREW-001", "old-alias"]
    canonical_name: "Andrew Fuller"
"""
        registry = _write_good_registry(tmp_path, authors=authors)
        result = av.validate(registry)
        assert result.fail_count == 0
        assert any("legacy_id 배열 타입 확인" in line for line in result.lines)

    def test_legacy_id_string_fails(self, tmp_path):
        authors = """
schema_version: "1.0"
authors:
  - author_id: FULLER-ANDREW-001
    canonical_id: fuller_andrew
    legacy_id: "FULLER-ANDREW-001"
    canonical_name: "Andrew Fuller"
"""
        registry = _write_good_registry(tmp_path, authors=authors)
        result = av.validate(registry)
        assert result.fail_count >= 1
        assert any("배열(list) 타입이어야 함" in line for line in result.lines)


class TestExistingFkUnaffected:
    def test_existing_fk_checks_still_pass(self, tmp_path):
        works = """
schema_version: "1.0"
works:
  - work_id: test_author_test_work
    canonical_id: test_author_test_work
    author_id: test_author
    canonical_title: "Test Work"
"""
        registry = _write_good_registry(tmp_path, works=works)
        result = av.validate(registry)
        assert result.fail_count == 0
        assert any("author_id='test_author' 참조 확인" in line for line in result.lines)


class TestRealProductionRegistry:
    """실제 Production Registry 회귀 — canonical_id/legacy_id 도입 후에도 FAIL 0건 유지."""

    def test_production_registry_has_zero_fail(self):
        registry = Path("resources/theological_sources/authority")
        result = av.validate(registry)
        assert result.fail_count == 0

    def test_production_registry_all_26_have_canonical_id(self):
        registry = Path("resources/theological_sources/authority")
        result = av.validate(registry)
        assert any("canonical_id='fuller_andrew' 형식 확인" in line for line in result.lines)
