"""Regression test — ui/pages/dashboard.py::_get_effective_documents()
sample-library exclusion (2026-08-24).

"기본 자료"(ui/pages/library.py의 읽기 전용 예제 3건)는 사용자 본인이
올린 자료가 아니므로 "정리된 자료"/"유형별 문서" 카운트에서 제외해야
한다(사용자 요청). document_id 기준으로 걸러 source_file 문자열 비교의
NFC/NFD 정규화 문제를 애초에 피한다.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import ui.pages.dashboard as mod
from core.identity_registry import save_identity_registry, _empty_registry, register_document


def _make_doc(doc_id: str, source_file: str, chunk_count: int = 1) -> dict:
    return {
        "document_id": doc_id,
        "file_hash": doc_id,
        "source_file": source_file,
        "chunk_count": chunk_count,
        "ingest_status": "PROCESSED",
        "superseded_by": None,
        "doc_type": "주석",
    }


def _write_registry(path: Path, docs: dict) -> None:
    registry = _empty_registry()
    registry["documents"] = docs
    save_identity_registry(registry, str(path))


class TestSampleLibraryExclusion:
    def test_sample_documents_excluded_from_effective_count(self, tmp_path, monkeypatch):
        registry_path = tmp_path / "registry.json"
        sample_path = tmp_path / "sample_library.json"

        docs = {
            "user-doc-1": _make_doc("user-doc-1", "a.pdf"),
            "user-doc-2": _make_doc("user-doc-2", "b.pdf"),
            "sample-doc-1": _make_doc("sample-doc-1", "샘플1.md"),
        }
        _write_registry(registry_path, docs)
        sample_path.write_text(json.dumps({"document_ids": ["sample-doc-1"]}), encoding="utf-8")

        monkeypatch.setattr("core.config.DEFAULT_REGISTRY_PATH", str(registry_path))
        monkeypatch.setattr("core.config.DEFAULT_SAMPLE_LIBRARY_PATH", str(sample_path))

        effective = mod._get_effective_documents()
        assert set(effective.keys()) == {"user-doc-1", "user-doc-2"}

    def test_missing_sample_library_file_excludes_nothing(self, tmp_path, monkeypatch):
        registry_path = tmp_path / "registry.json"
        docs = {"user-doc-1": _make_doc("user-doc-1", "a.pdf")}
        _write_registry(registry_path, docs)

        monkeypatch.setattr("core.config.DEFAULT_REGISTRY_PATH", str(registry_path))
        monkeypatch.setattr("core.config.DEFAULT_SAMPLE_LIBRARY_PATH", str(tmp_path / "nonexistent.json"))

        effective = mod._get_effective_documents()
        assert set(effective.keys()) == {"user-doc-1"}


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
