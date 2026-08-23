"""Regression test — SPRINT21-G-2 Option C: same-source_file content edits
link old/new records via supersedes/superseded_by instead of orphaning the
old one, and reconcile_pending() purges superseded documents' TSU records.

Covers: identity_registry.find_by_source_file()/mark_superseded(), the
migration backfill, and index_orchestrator.reconcile_pending()'s purge step.
Uses tmp_path throughout — no production data touched.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.identity_registry import (
    find_by_source_file,
    mark_superseded,
    migrate_registry_schema,
    register_document,
)
from core.index_orchestrator import reconcile_pending


class TestFindBySourceFile:
    def test_finds_non_superseded_record(self):
        registry = {"documents": {
            "d1": {"document_id": "d1", "source_file": "a.pdf", "superseded_by": None},
        }}
        found = find_by_source_file(registry, "a.pdf")
        assert found is not None and found["document_id"] == "d1"

    def test_skips_superseded_record(self):
        registry = {"documents": {
            "d1": {"document_id": "d1", "source_file": "a.pdf", "superseded_by": "d2"},
            "d2": {"document_id": "d2", "source_file": "a.pdf", "superseded_by": None},
        }}
        found = find_by_source_file(registry, "a.pdf")
        assert found is not None and found["document_id"] == "d2"

    def test_no_match_returns_none(self):
        registry = {"documents": {}}
        assert find_by_source_file(registry, "missing.pdf") is None


class TestMarkSuperseded:
    def test_links_both_records(self):
        registry = {"documents": {
            "d1": {"document_id": "d1", "supersedes": None, "superseded_by": None},
            "d2": {"document_id": "d2", "supersedes": None, "superseded_by": None},
        }}
        mark_superseded(registry, "d1", "d2")
        assert registry["documents"]["d1"]["superseded_by"] == "d2"
        assert registry["documents"]["d2"]["supersedes"] == "d1"
        # content/identity fields untouched (none exist to touch — proves no side effects)


class TestMigrationBackfill:
    def test_legacy_record_gets_supersession_fields(self):
        registry = {"schema_version": "1.0", "documents": {
            "d1": {"document_id": "d1", "file_hash": "h1", "source_file": "a.pdf"},
        }}
        changed = migrate_registry_schema(registry)
        assert changed is True
        assert registry["documents"]["d1"]["superseded_by"] is None
        assert registry["documents"]["d1"]["supersedes"] is None


class TestRegisterDocumentDefaults:
    def test_new_document_has_no_supersession_by_default(self):
        registry = {"documents": {}, "_meta": {"total_documents": 0}}
        metadata = {"document_id": "d1", "file_hash": "h1", "source_file": "a.pdf"}
        record, is_new = register_document(registry, metadata)
        assert record["superseded_by"] is None
        assert record["supersedes"] is None


class TestReconcilePurge:
    def _patch_paths(self, tmp_path, monkeypatch):
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_DATASET_PATH", str(tmp_path / "tsu.jsonl"))
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_MANIFEST_PATH", str(tmp_path / "manifest.json"))
        # See tests/test_reindex_document.py::_patch_paths for why these two
        # also need patching — the purge path touches DEFAULT_BIBLE_INDEX_PATH/
        # DEFAULT_CANDIDATE_INDEX_DIR directly.
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_BIBLE_INDEX_PATH", str(tmp_path / "bible_index.sqlite3"))
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_CANDIDATE_INDEX_DIR", str(tmp_path / "tantivy_index"))

    def test_purges_superseded_document_records(self, tmp_path, monkeypatch):
        self._patch_paths(tmp_path, monkeypatch)
        reg_dir = tmp_path / "registry"
        reg_dir.mkdir()
        (reg_dir / "documents.json").write_text(json.dumps({"documents": {
            "old": {"source_file": "a.md", "chunk_count": 1, "pipeline_state": "INDEXED",
                    "superseded_by": "new", "book": None, "title": None, "author": None,
                    "chapter": None, "page": None, "language": "ko", "source_type": "md"},
            "new": {"source_file": "a.md", "chunk_count": 1, "pipeline_state": "PROCESSED",
                    "superseded_by": None, "book": None, "title": None, "author": None,
                    "chapter": None, "page": None, "language": "ko", "source_type": "md"},
        }}), encoding="utf-8")
        (tmp_path / "a.md").write_text("new content", encoding="utf-8")

        # Seed the TSU dataset with a stale record for "old" that must be purged.
        dataset_path = tmp_path / "tsu.jsonl"
        dataset_path.write_text(json.dumps({"document_id": "old", "chunk_id": "old_chunk_00000",
                                             "content": "stale", "tsu_id": "TSU-UNK-old_chunk_00000"}) + "\n",
                                 encoding="utf-8")

        result = reconcile_pending(output_dir=str(tmp_path))

        assert result["purged"] == 1
        records = [json.loads(l) for l in dataset_path.read_text().splitlines() if l.strip()]
        assert all(r["document_id"] != "old" for r in records)
        assert any(r["document_id"] == "new" for r in records)

    def test_no_superseded_documents_purges_nothing(self, tmp_path, monkeypatch):
        self._patch_paths(tmp_path, monkeypatch)
        reg_dir = tmp_path / "registry"
        reg_dir.mkdir()
        (reg_dir / "documents.json").write_text(json.dumps({"documents": {
            "a": {"source_file": "a.md", "chunk_count": 0, "pipeline_state": "INDEXED", "superseded_by": None},
        }}), encoding="utf-8")

        result = reconcile_pending(output_dir=str(tmp_path))
        assert result["purged"] == 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
