"""Regression test — core/extraction_failures.py (SPRINT21-H-1).
Verifies the append-only failure log is separate from documents.json,
uses the same atomic-write pattern, and never raises.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.extraction_failures import load_extraction_failures, record_extraction_failure


def test_load_returns_empty_when_missing(tmp_path):
    data = load_extraction_failures(str(tmp_path))
    assert data == {"failures": []}


def test_record_persists_and_is_readable(tmp_path):
    ok = record_extraction_failure(str(tmp_path), "broken.pdf", stage="extract", reason="추출 텍스트 없음")
    assert ok is True

    data = load_extraction_failures(str(tmp_path))
    assert len(data["failures"]) == 1
    entry = data["failures"][0]
    assert entry["source_file"] == "broken.pdf"
    assert entry["stage"] == "extract"
    assert entry["reason"] == "추출 텍스트 없음"
    assert "failed_at" in entry


def test_multiple_failures_append(tmp_path):
    record_extraction_failure(str(tmp_path), "a.pdf", stage="extract", reason="r1")
    record_extraction_failure(str(tmp_path), "b.pdf", stage="noise", reason="r2")
    data = load_extraction_failures(str(tmp_path))
    assert [f["source_file"] for f in data["failures"]] == ["a.pdf", "b.pdf"]


def test_written_file_is_separate_from_documents_json(tmp_path):
    record_extraction_failure(str(tmp_path), "a.pdf", stage="exception", reason="boom", retry_count=3)
    failures_path = tmp_path / "registry" / "extraction_failures.json"
    documents_path = tmp_path / "registry" / "documents.json"
    assert failures_path.exists()
    assert not documents_path.exists()  # never touched


def test_retry_count_recorded(tmp_path):
    record_extraction_failure(str(tmp_path), "a.pdf", stage="exception", reason="boom", retry_count=3)
    data = load_extraction_failures(str(tmp_path))
    assert data["failures"][0]["retry_count"] == 3


def test_corrupt_file_recovers_to_empty(tmp_path):
    reg_dir = tmp_path / "registry"
    reg_dir.mkdir()
    (reg_dir / "extraction_failures.json").write_text("{not valid json", encoding="utf-8")
    data = load_extraction_failures(str(tmp_path))
    assert data == {"failures": []}


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
