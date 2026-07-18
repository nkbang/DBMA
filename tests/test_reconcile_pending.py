"""Regression test — core/index_orchestrator.py::reconcile_pending()
(SPRINT21-B Phase2). Verifies pull-based Processing->TSU reconciliation:
only PROCESSED documents are picked up, pipeline_state advances to
INDEXED, already-INDEXED/TSU_READY documents are left untouched
(idempotent), and ingest_status is never modified.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.index_orchestrator import reconcile_pending, rebuild_tsu_index


def _make_registry(tmp_path, docs):
    """docs: {doc_id: (source_file, chunk_count, pipeline_state)}"""
    reg_dir = tmp_path / "registry"
    reg_dir.mkdir(parents=True, exist_ok=True)
    documents = {}
    for doc_id, (src, chunks, state) in docs.items():
        documents[doc_id] = {
            "source_file": src, "chunk_count": chunks, "book": None,
            "title": None, "author": None, "chapter": None, "page": None,
            "language": "ko", "source_type": "md",
            "pipeline_state": state, "ingest_status": "PROCESSED",
        }
        (tmp_path / src).write_text(f"content {doc_id}", encoding="utf-8")
    (reg_dir / "documents.json").write_text(json.dumps({"documents": documents}), encoding="utf-8")
    return reg_dir / "documents.json"


def _patch_paths(tmp_path, monkeypatch):
    monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_DATASET_PATH", str(tmp_path / "tsu.jsonl"))
    monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_MANIFEST_PATH", str(tmp_path / "manifest.json"))


def test_only_processed_documents_are_reconciled(tmp_path, monkeypatch):
    reg_path = _make_registry(tmp_path, {
        "A": ("a.md", 2, "PROCESSED"),
        "B": ("b.md", 2, "INDEXED"),
        "C": ("c.md", 2, "TSU_READY"),
    })
    _patch_paths(tmp_path, monkeypatch)

    result = reconcile_pending(output_dir=str(tmp_path))

    assert result["pending"] == 1
    assert result["reconciled"] == 1
    assert result["failed"] == []

    registry = json.loads(reg_path.read_text())
    assert registry["documents"]["A"]["pipeline_state"] == "INDEXED"
    assert registry["documents"]["B"]["pipeline_state"] == "INDEXED"  # untouched
    assert registry["documents"]["C"]["pipeline_state"] == "TSU_READY"  # untouched (not PROCESSED)


def test_ingest_status_never_modified(tmp_path, monkeypatch):
    reg_path = _make_registry(tmp_path, {"A": ("a.md", 1, "PROCESSED")})
    _patch_paths(tmp_path, monkeypatch)

    reconcile_pending(output_dir=str(tmp_path))

    registry = json.loads(reg_path.read_text())
    assert registry["documents"]["A"]["ingest_status"] == "PROCESSED"  # unchanged value & key


def test_idempotent_second_call_no_op(tmp_path, monkeypatch):
    reg_path = _make_registry(tmp_path, {"A": ("a.md", 1, "PROCESSED")})
    _patch_paths(tmp_path, monkeypatch)

    first = reconcile_pending(output_dir=str(tmp_path))
    second = reconcile_pending(output_dir=str(tmp_path))

    assert first["reconciled"] == 1
    assert second["pending"] == 0
    assert second["reconciled"] == 0


def test_no_pending_documents_is_noop(tmp_path, monkeypatch):
    _make_registry(tmp_path, {"A": ("a.md", 1, "INDEXED")})
    _patch_paths(tmp_path, monkeypatch)

    result = reconcile_pending(output_dir=str(tmp_path))
    assert result == {"pending": 0, "reconciled": 0, "failed": [], "purged": 0}


def test_tsu_dataset_actually_contains_reconciled_document(tmp_path, monkeypatch):
    _make_registry(tmp_path, {"A": ("a.md", 2, "PROCESSED")})
    _patch_paths(tmp_path, monkeypatch)

    reconcile_pending(output_dir=str(tmp_path))

    dataset = tmp_path / "tsu.jsonl"
    assert dataset.exists()
    records = [json.loads(l) for l in dataset.read_text().splitlines() if l.strip()]
    assert len(records) == 2
    assert all(r["document_id"] == "A" for r in records)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
