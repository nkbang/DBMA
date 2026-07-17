"""Regression test — core/index_orchestrator.py::reindex_document()

SPRINT20-I-C-3: document 단위 partial re-index. 대상 문서 TSU만 갱신되고
다른 문서 TSU는 불변, manifest 정상 생성됨을 검증한다.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.index_orchestrator import rebuild_tsu_index, reindex_document


def _make_registry(tmp_path, docs):
    reg_dir = tmp_path / "registry"
    reg_dir.mkdir(parents=True, exist_ok=True)
    documents = {}
    for doc_id, (src, chunks) in docs.items():
        documents[doc_id] = {
            "source_file": src, "chunk_count": chunks, "book": None,
            "title": None, "author": None, "chapter": None, "page": None,
            "language": "ko", "source_type": "md",
        }
        (tmp_path / src).write_text(f"content {doc_id}", encoding="utf-8")
    (reg_dir / "documents.json").write_text(json.dumps({"documents": documents}), encoding="utf-8")


def _patch_paths(tmp_path, monkeypatch):
    monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_DATASET_PATH", str(tmp_path / "tsu.jsonl"))
    monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_MANIFEST_PATH", str(tmp_path / "manifest.json"))


def test_reindex_only_target_changes(tmp_path, monkeypatch):
    _make_registry(tmp_path, {"A": ("a.md", 2), "B": ("b.md", 3)})
    _patch_paths(tmp_path, monkeypatch)

    rebuild_tsu_index(output_dir=str(tmp_path))
    ds = tmp_path / "tsu.jsonl"
    before = [json.loads(l) for l in open(ds)]
    b_before = [r for r in before if r["document_id"] == "B"]

    res = reindex_document("A", output_dir=str(tmp_path))
    after = [json.loads(l) for l in open(ds)]
    b_after = [r for r in after if r["document_id"] == "B"]

    assert res["replaced"] == 2 and res["new"] == 2
    assert res["records"] == 5  # 2(A) + 3(B)
    assert b_before == b_after  # 다른 문서 불변
    assert (tmp_path / "manifest.json").exists()


def test_reindex_missing_document_raises(tmp_path, monkeypatch):
    _make_registry(tmp_path, {"A": ("a.md", 1)})
    _patch_paths(tmp_path, monkeypatch)
    rebuild_tsu_index(output_dir=str(tmp_path))
    try:
        reindex_document("ZZZ", output_dir=str(tmp_path))
        assert False, "expected KeyError"
    except KeyError:
        pass


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
