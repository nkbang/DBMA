"""Tests for scripts/authority_validator.py (NAE-AUTHORITY-VALIDATOR-IMPLEMENTATION-001).

Covers: FK integrity, duplicate IDs, legacy alias conflicts, canonical
ID format (WARNING only), orphan entities, circular references
(continues_work_id), duplicate canonical names, and a regression check
against the real production Authority Registry.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import scripts.authority_validator as av


def _write_registry(tmp_path: Path, **files: str) -> Path:
    d = tmp_path / "authority"
    d.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (d / f"{name}.yaml").write_text(content, encoding="utf-8")
    return d


_GOOD_AUTHORS = """
schema_version: "1.0"
authors:
  - author_id: test_author
    canonical_id: test_author
    canonical_name: "Test Author"
    aliases: ["T. Author"]
"""

_GOOD_WORKS = """
schema_version: "1.0"
works:
  - work_id: test_author_test_work
    canonical_id: test_author_test_work
    author_id: test_author
    canonical_title: "Test Work"
"""

_GOOD_EDITIONS = """
schema_version: "1.0"
editions:
  - edition_id: test_author_test_work_1900
    canonical_id: test_author_test_work_1900
    work_id: test_author_test_work
"""

_GOOD_VOLUMES = "schema_version: '1.0'\nvolumes: []\n"

_GOOD_SOURCES = """
schema_version: "1.0"
sources:
  - source_id: test_source_001
    canonical_id: test_source_001
    edition_id: test_author_test_work_1900
"""


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


class TestNormalRegistry:
    def test_valid_registry_has_no_fail(self, tmp_path):
        registry = _write_good_registry(tmp_path)
        result = av.validate(registry)
        assert result.fail_count == 0


class TestFkIntegrity:
    def test_broken_work_author_fk_fails(self, tmp_path):
        bad_works = _GOOD_WORKS.replace("author_id: test_author", "author_id: nonexistent_author")
        registry = _write_good_registry(tmp_path, works=bad_works)
        result = av.validate(registry)
        assert result.fail_count >= 1
        assert any("author_id='nonexistent_author'" in line and "Broken Reference" in line for line in result.lines)

    def test_broken_edition_work_fk_fails(self, tmp_path):
        bad_editions = _GOOD_EDITIONS.replace("work_id: test_author_test_work", "work_id: nonexistent_work")
        registry = _write_good_registry(tmp_path, editions=bad_editions)
        result = av.validate(registry)
        assert result.fail_count >= 1

    def test_broken_source_volume_fk_fails(self, tmp_path):
        bad_sources = _GOOD_SOURCES.rstrip() + "\n    volume_id: nonexistent_volume\n"
        registry = _write_good_registry(tmp_path, sources=bad_sources)
        result = av.validate(registry)
        assert result.fail_count >= 1
        assert any("volume_id='nonexistent_volume'" in line for line in result.lines)


class TestDuplicateIds:
    def test_duplicate_author_id_fails(self, tmp_path):
        dup_authors = """
schema_version: "1.0"
authors:
  - author_id: test_author
    canonical_name: "Test Author"
  - author_id: test_author
    canonical_name: "Test Author Duplicate"
"""
        registry = _write_good_registry(tmp_path, authors=dup_authors)
        result = av.validate(registry)
        assert result.fail_count >= 1
        assert any("author_id 중복" in line for line in result.lines)

    def test_duplicate_source_id_fails(self, tmp_path):
        dup_sources = _GOOD_SOURCES + """  - source_id: test_source_001
    edition_id: test_author_test_work_1900
"""
        registry = _write_good_registry(tmp_path, sources=dup_sources)
        result = av.validate(registry)
        assert result.fail_count >= 1
        assert any("source_id 중복" in line for line in result.lines)


class TestLegacyAlias:
    def test_alias_colliding_with_other_canonical_id_fails(self, tmp_path):
        authors = """
schema_version: "1.0"
authors:
  - author_id: author_a
    canonical_name: "Author A"
    aliases: ["author_b"]
  - author_id: author_b
    canonical_name: "Author B"
"""
        registry = _write_good_registry(tmp_path, authors=authors)
        result = av.validate(registry)
        assert result.fail_count >= 1
        assert any("canonical author_id와 충돌" in line for line in result.lines)

    def test_alias_reused_across_two_authors_fails(self, tmp_path):
        authors = """
schema_version: "1.0"
authors:
  - author_id: author_a
    canonical_name: "Author A"
    aliases: ["Shared Alias"]
  - author_id: author_b
    canonical_name: "Author B"
    aliases: ["Shared Alias"]
"""
        registry = _write_good_registry(tmp_path, authors=authors)
        result = av.validate(registry)
        assert result.fail_count >= 1
        assert any("양쪽에 중복 사용됨" in line for line in result.lines)


class TestCanonicalIdFormat:
    def test_noncanonical_id_warns_not_fails(self, tmp_path):
        authors = """
schema_version: "1.0"
authors:
  - author_id: NOT-CANONICAL-001
    canonical_id: not_canonical
    canonical_name: "Test"
"""
        registry = _write_good_registry(
            tmp_path,
            authors=authors,
            works="schema_version: '1.0'\nworks: []\n",
            editions="schema_version: '1.0'\neditions: []\n",
            sources="schema_version: '1.0'\nsources: []\n",
        )
        result = av.validate(registry)
        assert result.fail_count == 0
        assert any("canonical 표기" in line and "불일치" in line for line in result.lines)

    def test_canonical_id_passes(self, tmp_path):
        registry = _write_good_registry(tmp_path)
        result = av.validate(registry)
        assert any("'test_author' canonical 표기(ADR-017) 준수" in line for line in result.lines)


class TestOrphanEntity:
    def test_unreferenced_author_warns(self, tmp_path):
        authors = _GOOD_AUTHORS + """  - author_id: orphan_author
    canonical_id: orphan_author
    canonical_name: "Orphan Author"
"""
        registry = _write_good_registry(tmp_path, authors=authors)
        result = av.validate(registry)
        assert result.fail_count == 0
        assert any("orphan_author" in line and "Orphan Entity" in line for line in result.lines)


class TestCircularReference:
    def test_no_cycle_passes(self, tmp_path):
        registry = _write_good_registry(tmp_path)
        result = av.validate(registry)
        assert any("continues_work_id 사용 사례 없음" in line for line in result.lines)

    def test_direct_cycle_fails(self, tmp_path):
        works = """
schema_version: "1.0"
works:
  - work_id: work_a
    author_id: test_author
    continues_work_id: work_b
  - work_id: work_b
    author_id: test_author
    continues_work_id: work_a
"""
        registry = _write_good_registry(tmp_path, works=works)
        result = av.validate(registry)
        assert result.fail_count >= 1
        assert any("순환 참조 발견" in line for line in result.lines)

    def test_no_actual_cycle_with_chain_passes(self, tmp_path):
        works = """
schema_version: "1.0"
works:
  - work_id: work_a
    canonical_id: work_a
    author_id: test_author
  - work_id: work_b
    canonical_id: work_b
    author_id: test_author
    continues_work_id: work_a
"""
        registry = _write_good_registry(
            tmp_path,
            works=works,
            editions="schema_version: '1.0'\neditions: []\n",
            sources="schema_version: '1.0'\nsources: []\n",
        )
        result = av.validate(registry)
        assert result.fail_count == 0
        assert any("continues_work_id 순환 없음" in line for line in result.lines)


class TestDuplicateCanonicalName:
    def test_duplicate_canonical_name_warns(self, tmp_path):
        authors = """
schema_version: "1.0"
authors:
  - author_id: john_smith_1660
    canonical_id: john_smith_1660
    canonical_name: "John Smith"
  - author_id: john_smith_1810
    canonical_id: john_smith_1810
    canonical_name: "John Smith"
"""
        registry = _write_good_registry(
            tmp_path,
            authors=authors,
            works="schema_version: '1.0'\nworks: []\n",
            editions="schema_version: '1.0'\neditions: []\n",
            sources="schema_version: '1.0'\nsources: []\n",
        )
        result = av.validate(registry)
        assert result.fail_count == 0
        assert any("동일 인물 중복 등록 의심" in line for line in result.lines)


class TestRealProductionRegistry:
    """실제 저장소 Authority Registry(Production) 회귀 확인."""

    def test_production_registry_has_zero_fail(self):
        registry = Path("resources/theological_sources/authority")
        result = av.validate(registry)
        assert result.fail_count == 0

    def test_production_registry_known_id_format_warnings(self):
        """FULLER-ANDREW-001류 비표준 ID는 WARNING으로만 남아야 함(ID Governance v1
        결정 — 즉시 rename하지 않음)."""
        registry = Path("resources/theological_sources/authority")
        result = av.validate(registry)
        assert any("FULLER-ANDREW-001" in line and "WARNING" in line for line in result.lines)
