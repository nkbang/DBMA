"""Regression test — core/index_orchestrator.py::rebuild_tsu_index()

SPRINT20-I: rebuild_tsu_index()는 scripts/build_tsu_dataset.py의 배치
로직(build_tsu_records/write_tsu_dataset/write_manifest)을 그대로 감싸는
얇은 wrapper다. 새 파싱/스코어링 로직이 없으므로, 이 테스트는 wrapper가
그 함수들을 올바른 인자로 호출하고 반환 계약을 지키는지만 검증한다.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.index_orchestrator import rebuild_tsu_index


def _make_registry(tmp_path, doc_count=2, chunks_per_doc=3):
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    documents = {}
    for i in range(doc_count):
        source_file = f"doc{i}.md"
        documents[f"DOC-{i}"] = {
            "source_file": source_file,
            "chunk_count": chunks_per_doc,
            "book": None,
            "title": f"Title {i}",
            "author": None,
            "chapter": None,
            "page": None,
            "language": "ko",
            "source_type": "md",
        }
        (tmp_path / f"doc{i}.md").write_text(f"content for doc {i}", encoding="utf-8")
    registry = {"documents": documents}
    (registry_dir / "documents.json").write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    return registry_dir / "documents.json"


class TestRebuildTsuIndex:
    def test_returns_expected_contract(self, tmp_path, monkeypatch):
        _make_registry(tmp_path, doc_count=2, chunks_per_doc=3)

        dataset_path = tmp_path / "tsu_dataset.jsonl"
        manifest_path = tmp_path / "tsu_manifest.json"
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_DATASET_PATH", str(dataset_path))
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_MANIFEST_PATH", str(manifest_path))

        result = rebuild_tsu_index(output_dir=str(tmp_path))

        assert result["documents"] == 2
        assert result["records"] == 6  # 2 docs * 3 chunks
        assert result["dataset_path"] == str(dataset_path)
        assert result["manifest_path"] == str(manifest_path)
        assert dataset_path.exists()
        assert manifest_path.exists()

        lines = dataset_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 6
        first_record = json.loads(lines[0])
        assert "tsu_id" in first_record
        assert "content" in first_record

    def test_empty_registry_produces_zero_records(self, tmp_path, monkeypatch):
        registry_dir = tmp_path / "registry"
        registry_dir.mkdir(parents=True, exist_ok=True)
        (registry_dir / "documents.json").write_text(
            json.dumps({"documents": {}}), encoding="utf-8"
        )

        dataset_path = tmp_path / "tsu_dataset.jsonl"
        manifest_path = tmp_path / "tsu_manifest.json"
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_DATASET_PATH", str(dataset_path))
        monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_MANIFEST_PATH", str(manifest_path))

        result = rebuild_tsu_index(output_dir=str(tmp_path))

        assert result["documents"] == 0
        assert result["records"] == 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
