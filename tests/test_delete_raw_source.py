"""Regression test — core/index_orchestrator.py::delete_raw_source()
(2026-08-24, 사용자 요청: "필요없는 자기 자료를 제거하는 기능").

RAW 원본을 os.remove()가 아니라 backups/deleted_raw_{날짜}/로 이동한다
("원본 절대 삭제 안 함" 정책을 지키면서도 목록/검색에서는 완전히 빠짐).
이미 처리된 문서면 registry EXCLUDED 처리 + TSU 레코드 정리까지 함께
한다. 모든 경로(BACKUP_ROOT 포함)를 tmp_path로 override해 실제 repo의
backups/를 절대 건드리지 않는다.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
from core.identity_registry import save_identity_registry, _empty_registry
from core.index_orchestrator import delete_raw_source


def _write_registry(path: Path, documents: dict) -> None:
    registry = _empty_registry()
    registry["documents"] = documents
    save_identity_registry(registry, str(path))


def _patch_paths(monkeypatch, tmp_path):
    monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_DATASET_PATH", str(tmp_path / "tsu.jsonl"))
    monkeypatch.setattr("core.index_orchestrator.DEFAULT_TSU_MANIFEST_PATH", str(tmp_path / "manifest.json"))
    monkeypatch.setattr("core.index_orchestrator.DEFAULT_CANDIDATE_INDEX_DIR", str(tmp_path / "tantivy_index"))
    monkeypatch.setattr("core.index_orchestrator.DEFAULT_BIBLE_INDEX_PATH", str(tmp_path / "bible_index.sqlite3"))
    monkeypatch.setattr("core.index_orchestrator.BACKUP_ROOT", tmp_path / "backups")


class TestDeleteRawSourceUnprocessed:
    def test_dry_run_does_not_move_file(self, tmp_path, monkeypatch):
        _patch_paths(monkeypatch, tmp_path)
        raw_dir = tmp_path / "RAW"
        raw_dir.mkdir()
        (raw_dir / "a.md").write_text("x")
        registry_path = tmp_path / "output" / "registry" / "documents.json"
        registry_path.parent.mkdir(parents=True)
        _write_registry(registry_path, {})

        result = delete_raw_source("a.md", raw_dir=str(raw_dir), output_dir=str(tmp_path / "output"), execute=False)

        assert result["found"] is True
        assert result["executed"] is False
        assert result["trash_path"] is None
        assert (raw_dir / "a.md").exists()  # untouched

    def test_execute_moves_unprocessed_file_to_trash(self, tmp_path, monkeypatch):
        _patch_paths(monkeypatch, tmp_path)
        raw_dir = tmp_path / "RAW"
        raw_dir.mkdir()
        (raw_dir / "a.md").write_text("x")
        registry_path = tmp_path / "output" / "registry" / "documents.json"
        registry_path.parent.mkdir(parents=True)
        _write_registry(registry_path, {})

        result = delete_raw_source("a.md", raw_dir=str(raw_dir), output_dir=str(tmp_path / "output"), execute=True)

        assert result["found"] is True
        assert result["document_id"] is None  # never processed, no registry record
        assert not (raw_dir / "a.md").exists()  # gone from RAW
        assert Path(result["trash_path"]).exists()  # recoverable in trash

    def test_finds_file_in_raw_subfolder(self, tmp_path, monkeypatch):
        """[동일 근본원인] processing.py의 하위 폴더 스캔 수정(2026-08-24)과
        같은 기준 — 삭제 기능도 RAW 최상위만 봐서는 안 된다."""
        _patch_paths(monkeypatch, tmp_path)
        raw_dir = tmp_path / "RAW"
        sub = raw_dir / "설교_분리"
        sub.mkdir(parents=True)
        (sub / "sermon.md").write_text("x")
        registry_path = tmp_path / "output" / "registry" / "documents.json"
        registry_path.parent.mkdir(parents=True)
        _write_registry(registry_path, {})

        result = delete_raw_source("sermon.md", raw_dir=str(raw_dir), output_dir=str(tmp_path / "output"), execute=True)
        assert result["found"] is True
        assert not (sub / "sermon.md").exists()

    def test_file_not_found_returns_found_false(self, tmp_path, monkeypatch):
        _patch_paths(monkeypatch, tmp_path)
        raw_dir = tmp_path / "RAW"
        raw_dir.mkdir()
        registry_path = tmp_path / "output" / "registry" / "documents.json"
        registry_path.parent.mkdir(parents=True)
        _write_registry(registry_path, {})

        result = delete_raw_source("nope.md", raw_dir=str(raw_dir), output_dir=str(tmp_path / "output"), execute=True)
        assert result["found"] is False
        assert result["trash_path"] is None


class TestDeleteRawSourceProcessed:
    def test_execute_excludes_registry_record_and_purges_tsu(self, tmp_path, monkeypatch):
        _patch_paths(monkeypatch, tmp_path)
        raw_dir = tmp_path / "RAW"
        raw_dir.mkdir()
        (raw_dir / "book.pdf").write_text("x")

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        registry_path = output_dir / "registry" / "documents.json"
        registry_path.parent.mkdir(parents=True)
        _write_registry(registry_path, {
            "doc-1": {
                "document_id": "doc-1",
                "file_hash": "h1",
                "source_file": "book.pdf",
                "chunk_count": 2,
                "ingest_status": "PROCESSED",
                "superseded_by": None,
            },
        })

        tsu_path = tmp_path / "tsu.jsonl"
        with open(tsu_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"document_id": "doc-1", "source_file": "book.pdf", "content": "c1"}, ensure_ascii=False) + "\n")
            f.write(json.dumps({"document_id": "doc-1", "source_file": "book.pdf", "content": "c2"}, ensure_ascii=False) + "\n")
            f.write(json.dumps({"document_id": "doc-2", "source_file": "other.pdf", "content": "c3"}, ensure_ascii=False) + "\n")

        result = delete_raw_source("book.pdf", raw_dir=str(raw_dir), output_dir=str(output_dir), execute=True)

        assert result["found"] is True
        assert result["document_id"] == "doc-1"
        assert result["purged_tsu_records"] == 2
        assert not (raw_dir / "book.pdf").exists()
        assert Path(result["trash_path"]).exists()

        remaining = [json.loads(l) for l in tsu_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert [r["document_id"] for r in remaining] == ["doc-2"]

        from core.identity_registry import load_identity_registry
        reg = load_identity_registry(str(registry_path))
        assert reg["documents"]["doc-1"]["ingest_status"] == "EXCLUDED"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
