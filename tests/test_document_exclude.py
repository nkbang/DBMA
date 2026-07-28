"""Regression test — 문서 처리 제외(exclude) 기능.

Covers: identity_registry.exclude_document()/unexclude_document()/
classify_ingest_decision() EXCLUDED branch, and
index_orchestrator.exclude_document_from_index() (TSU 레코드 purge +
chunk 파일 backups/ 이동, dry-run vs execute).
Uses tmp_path throughout — no production data touched.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.identity_registry import (
    classify_ingest_decision,
    exclude_document,
    unexclude_document,
)
from core.index_orchestrator import exclude_document_from_index


class TestExcludeDocument:
    def test_sets_ingest_status_and_reason(self):
        registry = {"documents": {
            "d1": {"document_id": "d1", "ingest_status": "PROCESSED"},
        }}
        record = exclude_document(registry, "d1", reason="중복 자료")
        assert record["ingest_status"] == "EXCLUDED"
        assert record["exclude_reason"] == "중복 자료"
        assert record["excluded_at"] is not None

    def test_missing_document_returns_none(self):
        registry = {"documents": {}}
        assert exclude_document(registry, "missing") is None

    def test_unexclude_restores_processed(self):
        registry = {"documents": {
            "d1": {"document_id": "d1", "ingest_status": "EXCLUDED",
                    "excluded_at": "2026-07-28T00:00:00", "exclude_reason": "x"},
        }}
        record = unexclude_document(registry, "d1")
        assert record["ingest_status"] == "PROCESSED"
        assert record["excluded_at"] is None
        assert record["exclude_reason"] is None


class TestClassifyIngestDecisionExcluded:
    def test_excluded_status_skips_even_on_hash_change(self):
        registry = {"documents": {
            "d1": {"document_id": "d1", "ingest_status": "EXCLUDED",
                    "file_hash": "old_hash", "last_content_hash": "old_hash"},
        }}
        decision, record = classify_ingest_decision(registry, "d1", "new_hash")
        assert decision == "SKIP"
        assert record["document_id"] == "d1"


class TestExcludeDocumentFromIndex:
    def _seed(self, tmp_path, monkeypatch):
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_DATASET_PATH", str(tmp_path / "tsu.jsonl"))
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_MANIFEST_PATH", str(tmp_path / "manifest.json"))
        monkeypatch.setattr("core.index_orchestrator.BACKUP_ROOT", tmp_path / "backups")

        reg_dir = tmp_path / "registry"
        reg_dir.mkdir()
        (reg_dir / "documents.json").write_text(json.dumps({"documents": {
            "d1": {"document_id": "d1", "source_file": "a.md", "chunk_count": 1,
                   "ingest_status": "PROCESSED", "book": None, "title": None, "author": None,
                   "chapter": None, "page": None, "language": "ko", "source_type": "md"},
        }}), encoding="utf-8")

        dataset_path = tmp_path / "tsu.jsonl"
        dataset_path.write_text(
            json.dumps({"document_id": "d1", "chunk_id": "d1_chunk_00000",
                        "content": "stale", "tsu_id": "TSU-UNK-d1_chunk_00000"}) + "\n",
            encoding="utf-8",
        )
        # make_safe_stem("a.md") == "a_md" — output stem includes the
        # lowercased extension suffix, distinct from the source filename.
        (tmp_path / "a_md.md").write_text("content", encoding="utf-8")
        (tmp_path / "a_md_chunks.txt").write_text("chunk text", encoding="utf-8")
        return dataset_path

    def test_dry_run_leaves_files_and_dataset_untouched(self, tmp_path, monkeypatch):
        dataset_path = self._seed(tmp_path, monkeypatch)
        result = exclude_document_from_index("d1", output_dir=str(tmp_path), execute=False)

        assert result["executed"] is False
        assert result["purged_tsu_records"] == 1  # computed, not yet applied
        assert (tmp_path / "a_md.md").exists()
        assert (tmp_path / "a_md_chunks.txt").exists()
        records = [json.loads(l) for l in dataset_path.read_text().splitlines() if l.strip()]
        assert any(r["document_id"] == "d1" for r in records)

    def test_execute_purges_dataset_and_moves_files(self, tmp_path, monkeypatch):
        dataset_path = self._seed(tmp_path, monkeypatch)
        result = exclude_document_from_index("d1", output_dir=str(tmp_path), execute=True)

        assert result["executed"] is True
        assert result["purged_tsu_records"] == 1
        assert not (tmp_path / "a_md.md").exists()
        assert not (tmp_path / "a_md_chunks.txt").exists()
        assert len(result["moved_files"]) == 2
        for f in result["moved_files"]:
            assert os.path.exists(f)

        records = [json.loads(l) for l in dataset_path.read_text().splitlines() if l.strip()]
        assert all(r["document_id"] != "d1" for r in records)

    def test_missing_document_id_raises(self, tmp_path, monkeypatch):
        self._seed(tmp_path, monkeypatch)
        try:
            exclude_document_from_index("missing", output_dir=str(tmp_path), execute=False)
            assert False, "expected KeyError"
        except KeyError:
            pass
