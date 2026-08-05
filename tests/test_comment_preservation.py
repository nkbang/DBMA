"""tests/test_comment_preservation.py (NAE-ADAPTER-REFACTOR-001).

Verifies that the ruamel.yaml round-trip rewrite of
scripts/adapters/{registry_adapter,manifest_adapter}.py preserves
comments, quote style, key ordering, and blank lines — the defect
found in NAE_PILOT_MIGRATION_VALIDATION_REPORT_001.md §4 (PyYAML
safe_load/safe_dump destroyed all of these on real Pilot Manifest
files).

All fixtures below are synthetic copies of the real file's *shape*
(same comment style, quoting, blank-line placement) — never the real
Registry/Manifest/RAW files themselves.
"""

import filecmp
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.adapters.manifest_adapter import build_touch_unit, load_manifest
from scripts.adapters.registry_adapter import build_canonical_id_backfill_unit, load_entity_file
from scripts.migration_engine import MigrationEngine

# 실제 Pilot Manifest(dagg)와 동일한 모양(주석/따옴표/빈 줄/들여쓰기)의 fixture.
_MANIFEST_FIXTURE = '''# NAE Manifest Pilot — Dagg (monograph) — NAE-MANIFEST-PILOT-IMPLEMENTATION-001
#
# Pilot namespace(resources/theological_sources/manifest/pilot/) — 실제
# 운영 Manifest 위치가 아니다. Authority Registry(authority/*.yaml)를
# 참조만 하고 그 파일들은 수정하지 않는다.
#
# Manifest Schema v1.0.0 정본: docs/NAE_CORPUS_MANIFEST_SCHEMA_DESIGN_v1.md
schema_version: "1.0.0"

manifests:
  - manifest_id: BAP-CHURCH-DAGG-001
    source_id: BAP-CHURCH-DAGG-001
    author_id: dagg_john_l
    work_id: WORK-DAGG-CHURCH-ORDER-001
    edition_id: WORK-DAGG-CHURCH-ORDER-001-1871
    volume_id: null    # monograph — 값 없음
    issue_id: null      # monograph — 값 없음
    acquisition_status: acquired
    ocr_status: complete
    metadata_status: verified
    tsu_status: not_ready
    embedding_status: not_started
    processing_status: metadata_complete   # 5필드 요약 파생값
    created_at: "2026-08-03T00:00:00Z"
    updated_at: "2026-08-03T00:00:00Z"
    verified_by: cue
'''

# 실제 authors.yaml과 동일한 모양의 fixture(주석 + 비표준 ID + notes 블록).
_AUTHORS_FIXTURE = '''# NAE Authority Registry — Authors (PRODUCTION)
#
# NAE-AUTHORITY-REGISTRY-BUILD-001: Pilot-001/002에서 검증된 데이터를
# 복사 승격한 최초의 Production 데이터.
#
# 스키마 정본: docs/NAE_AUTHORITY_REGISTRY_DESIGN_v1.md §2.1
schema_version: "1.0"

authors:
  - author_id: dagg_john_l
    canonical_id: dagg_john_l
    canonical_name: "John L. Dagg"
    aliases: ["John Dagg", "J. L. Dagg, D.D.", "J.L. Dagg"]
    birth_year: 1794
    death_year: 1884
    tradition: "Particular Baptist (American, Southern)"

  - author_id: FULLER-ANDREW-001
    canonical_name: "Andrew Fuller"
    aliases: ["Rev. Andrew Fuller", "Andrew Fuller, Kettering"]
    birth_year: 1754
    death_year: 1815
    tradition: "Particular Baptist"
    notes: >
      Pilot-002 승격분, 값 변경 없음. [ID Governance 주의] 이 author_id는
      대문자-하이픈 표기(FULLER-ANDREW-001)로 다른 표기 관례를 따른다.
'''


def _make_engine(tmp_path: Path) -> MigrationEngine:
    return MigrationEngine(
        checkpoint_dir=tmp_path / "cp", lock_path=tmp_path / "lock.json", audit_path=tmp_path / "audit.jsonl"
    )


class TestCommentPreservation:
    def test_manifest_touch_preserves_header_comments(self, tmp_path):
        path = tmp_path / "manifest.yaml"
        path.write_text(_MANIFEST_FIXTURE, encoding="utf-8")
        unit = build_touch_unit(path, "1.0.0", updated_at="2026-08-05T00:00:00+09:00")
        engine = _make_engine(tmp_path)
        report = engine.execute(unit)
        assert report.fail_count == 0

        new_text = path.read_text(encoding="utf-8")
        assert "# NAE Manifest Pilot — Dagg (monograph)" in new_text
        assert "# 운영 Manifest 위치가 아니다" in new_text
        assert "# monograph — 값 없음" in new_text  # 인라인 주석도 보존

    def test_registry_backfill_preserves_header_and_notes_comments(self, tmp_path):
        root = tmp_path / "registry"
        root.mkdir()
        (root / "authors.yaml").write_text(_AUTHORS_FIXTURE, encoding="utf-8")
        entity_file = load_entity_file(root, "authors")
        unit = build_canonical_id_backfill_unit(
            entity_file, "1.0.0", canonical_id_map={"FULLER-ANDREW-001": "fuller_andrew"}
        )
        engine = _make_engine(tmp_path)
        report = engine.execute(unit)
        assert report.fail_count == 0

        new_text = (root / "authors.yaml").read_text(encoding="utf-8")
        assert "# NAE Authority Registry — Authors (PRODUCTION)" in new_text
        assert "# 스키마 정본: docs/NAE_AUTHORITY_REGISTRY_DESIGN_v1.md §2.1" in new_text
        assert "[ID Governance 주의]" in new_text  # notes 블록 스칼라 보존


class TestQuotePreservation:
    def test_schema_version_quote_style_unchanged(self, tmp_path):
        path = tmp_path / "manifest.yaml"
        path.write_text(_MANIFEST_FIXTURE, encoding="utf-8")
        unit = build_touch_unit(path, "1.0.0", updated_at="2026-08-05T00:00:00+09:00")
        engine = _make_engine(tmp_path)
        engine.execute(unit)

        new_text = path.read_text(encoding="utf-8")
        assert 'schema_version: "1.0.0"' in new_text  # 큰따옴표 유지(안 바뀜)

    def test_new_updated_at_value_keeps_double_quote_style(self, tmp_path):
        path = tmp_path / "manifest.yaml"
        path.write_text(_MANIFEST_FIXTURE, encoding="utf-8")
        unit = build_touch_unit(path, "1.0.0", updated_at="2026-08-05T00:00:00+09:00")
        engine = _make_engine(tmp_path)
        engine.execute(unit)

        new_text = path.read_text(encoding="utf-8")
        assert 'updated_at: "2026-08-05T00:00:00+09:00"' in new_text

    def test_registry_untouched_fields_keep_quotes(self, tmp_path):
        root = tmp_path / "registry"
        root.mkdir()
        (root / "authors.yaml").write_text(_AUTHORS_FIXTURE, encoding="utf-8")
        entity_file = load_entity_file(root, "authors")
        unit = build_canonical_id_backfill_unit(
            entity_file, "1.0.0", canonical_id_map={"FULLER-ANDREW-001": "fuller_andrew"}
        )
        engine = _make_engine(tmp_path)
        engine.execute(unit)

        new_text = (root / "authors.yaml").read_text(encoding="utf-8")
        assert 'canonical_name: "Andrew Fuller"' in new_text
        assert 'schema_version: "1.0"' in new_text


class TestOrderPreservation:
    def test_manifest_field_order_unchanged(self, tmp_path):
        path = tmp_path / "manifest.yaml"
        path.write_text(_MANIFEST_FIXTURE, encoding="utf-8")
        unit = build_touch_unit(path, "1.0.0", updated_at="2026-08-05T00:00:00+09:00")
        engine = _make_engine(tmp_path)
        engine.execute(unit)

        new_text = path.read_text(encoding="utf-8")
        idx_created = new_text.index("created_at:")
        idx_updated = new_text.index("updated_at:")
        idx_verified = new_text.index("verified_by:")
        assert idx_created < idx_updated < idx_verified  # 원본 순서(created_at -> updated_at -> verified_by) 유지

    def test_registry_new_field_inserted_right_after_id_field(self, tmp_path):
        """canonical_id는 신규 필드이므로 원본에 없던 위치지만, id_field
        바로 다음(가독성)에 삽입되고 그 뒤 필드 순서는 유지되어야 한다."""
        root = tmp_path / "registry"
        root.mkdir()
        (root / "authors.yaml").write_text(_AUTHORS_FIXTURE, encoding="utf-8")
        entity_file = load_entity_file(root, "authors")
        unit = build_canonical_id_backfill_unit(
            entity_file, "1.0.0", canonical_id_map={"FULLER-ANDREW-001": "fuller_andrew"}
        )
        engine = _make_engine(tmp_path)
        engine.execute(unit)

        new_text = (root / "authors.yaml").read_text(encoding="utf-8")
        idx_author_id = new_text.index("author_id: FULLER-ANDREW-001")
        idx_canonical_id = new_text.index("canonical_id: fuller_andrew")
        idx_canonical_name = new_text.index('canonical_name: "Andrew Fuller"')
        assert idx_author_id < idx_canonical_id < idx_canonical_name


class TestWhitespacePreservation:
    def test_blank_lines_preserved(self, tmp_path):
        path = tmp_path / "manifest.yaml"
        path.write_text(_MANIFEST_FIXTURE, encoding="utf-8")
        unit = build_touch_unit(path, "1.0.0", updated_at="2026-08-05T00:00:00+09:00")
        engine = _make_engine(tmp_path)
        engine.execute(unit)

        new_text = path.read_text(encoding="utf-8")
        original_blank_lines = _MANIFEST_FIXTURE.count("\n\n")
        new_blank_lines = new_text.count("\n\n")
        assert new_blank_lines == original_blank_lines

    def test_registry_blank_line_between_entries_preserved(self, tmp_path):
        root = tmp_path / "registry"
        root.mkdir()
        (root / "authors.yaml").write_text(_AUTHORS_FIXTURE, encoding="utf-8")
        entity_file = load_entity_file(root, "authors")
        unit = build_canonical_id_backfill_unit(
            entity_file, "1.0.0", canonical_id_map={"FULLER-ANDREW-001": "fuller_andrew"}
        )
        engine = _make_engine(tmp_path)
        engine.execute(unit)

        new_text = (root / "authors.yaml").read_text(encoding="utf-8")
        # 두 author entry 사이 빈 줄(원본에 존재)이 유지되는지
        assert "\n\n  - author_id: FULLER-ANDREW-001" in new_text


class TestTouchMigrationOnlyChangesUpdatedAt:
    def test_diff_is_exactly_one_line(self, tmp_path):
        path = tmp_path / "manifest.yaml"
        path.write_text(_MANIFEST_FIXTURE, encoding="utf-8")
        unit = build_touch_unit(path, "1.0.0", updated_at="2026-08-05T00:00:00+09:00")
        engine = _make_engine(tmp_path)
        engine.execute(unit)

        before_lines = _MANIFEST_FIXTURE.splitlines()
        after_lines = path.read_text(encoding="utf-8").splitlines()
        assert len(before_lines) == len(after_lines)  # 줄 수 자체가 안 바뀜

        diff_lines = [
            (i, b, a) for i, (b, a) in enumerate(zip(before_lines, after_lines)) if b != a
        ]
        assert len(diff_lines) == 1
        _, before_line, after_line = diff_lines[0]
        assert "updated_at:" in before_line
        assert "updated_at:" in after_line


class TestIdempotency:
    def test_second_touch_run_yields_zero_changes(self, tmp_path):
        path = tmp_path / "manifest.yaml"
        path.write_text(_MANIFEST_FIXTURE, encoding="utf-8")
        unit = build_touch_unit(path, "1.0.0", updated_at="2026-08-05T00:00:00+09:00")
        engine = _make_engine(tmp_path)
        first = engine.execute(unit)
        assert first.pass_count == 1

        text_after_first = path.read_text(encoding="utf-8")
        second = engine.execute(unit)
        assert second.skipped_count == 1
        assert second.pass_count == 0
        assert path.read_text(encoding="utf-8") == text_after_first  # 0 changes

    def test_registry_backfill_idempotent(self, tmp_path):
        root = tmp_path / "registry"
        root.mkdir()
        (root / "authors.yaml").write_text(_AUTHORS_FIXTURE, encoding="utf-8")
        entity_file = load_entity_file(root, "authors")
        unit = build_canonical_id_backfill_unit(
            entity_file, "1.0.0", canonical_id_map={"FULLER-ANDREW-001": "fuller_andrew"}
        )
        engine = _make_engine(tmp_path)
        engine.execute(unit)
        text_after_first = (root / "authors.yaml").read_text(encoding="utf-8")

        second = engine.execute(unit)
        assert second.skipped_count == 1
        assert (root / "authors.yaml").read_text(encoding="utf-8") == text_after_first


class TestRollback:
    def test_rollback_restores_byte_identical_file(self, tmp_path):
        path = tmp_path / "manifest.yaml"
        path.write_text(_MANIFEST_FIXTURE, encoding="utf-8")
        original_copy = tmp_path / "manifest.yaml.original"
        original_copy.write_text(_MANIFEST_FIXTURE, encoding="utf-8")

        def failing_hook():
            return False, "forced VERIFY failure(test)"

        engine = MigrationEngine(
            checkpoint_dir=tmp_path / "cp",
            lock_path=tmp_path / "lock.json",
            audit_path=tmp_path / "audit.jsonl",
            verify_hooks=[failing_hook],
        )
        unit = build_touch_unit(path, "1.0.0", updated_at="2026-08-05T00:00:00+09:00")
        report = engine.execute(unit)
        assert report.fail_count == 1
        assert report.warning_count == 1  # Rollback 완료

        assert filecmp.cmp(path, original_copy, shallow=False)  # cmp byte-identical

    def test_registry_rollback_restores_byte_identical_file(self, tmp_path):
        root = tmp_path / "registry"
        root.mkdir()
        (root / "authors.yaml").write_text(_AUTHORS_FIXTURE, encoding="utf-8")
        original_copy = tmp_path / "authors.yaml.original"
        original_copy.write_text(_AUTHORS_FIXTURE, encoding="utf-8")

        def failing_hook():
            return False, "forced VERIFY failure(test)"

        entity_file = load_entity_file(root, "authors")
        engine = MigrationEngine(
            checkpoint_dir=tmp_path / "cp",
            lock_path=tmp_path / "lock.json",
            audit_path=tmp_path / "audit.jsonl",
            verify_hooks=[failing_hook],
        )
        unit = build_canonical_id_backfill_unit(
            entity_file, "1.0.0", canonical_id_map={"FULLER-ANDREW-001": "fuller_andrew"}
        )
        report = engine.execute(unit)
        assert report.fail_count == 1
        assert report.warning_count == 1

        assert filecmp.cmp(root / "authors.yaml", original_copy, shallow=False)
