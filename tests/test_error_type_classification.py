"""Regression test — error_type field on extraction failures
(SPRINT25-B-1). Verifies backward compatibility with pre-existing records,
that exception failures capture type(e).__name__, and that extract/noise
failures store None (no unnecessary fields).
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.extraction_failures import load_extraction_failures, record_extraction_failure
from core.processing import process_batch, build_converter, build_splitter


class TestBackwardCompatibility:
    def test_legacy_record_without_error_type_still_readable(self, tmp_path):
        """A pre-existing record (written before this field existed) has
        no 'error_type' key at all — .get() must handle that, not crash."""
        reg_dir = tmp_path / "registry"
        reg_dir.mkdir()
        legacy = {"failures": [
            {"source_file": "old.pdf", "failed_at": "2026-01-01T00:00:00",
             "stage": "exception", "reason": "boom", "retry_count": 3},
        ]}
        (reg_dir / "extraction_failures.json").write_text(json.dumps(legacy), encoding="utf-8")

        data = load_extraction_failures(str(tmp_path))
        assert len(data["failures"]) == 1
        assert data["failures"][0].get("error_type") is None  # missing key, not an error


class TestErrorTypeCapture:
    def test_exception_failure_stores_error_type(self, tmp_path):
        ok = record_extraction_failure(str(tmp_path), "a.pdf", stage="exception",
                                        reason="boom", retry_count=3, error_type="ValueError")
        assert ok is True
        data = load_extraction_failures(str(tmp_path))
        assert data["failures"][0]["error_type"] == "ValueError"

    def test_default_error_type_is_none(self, tmp_path):
        record_extraction_failure(str(tmp_path), "a.pdf", stage="extract", reason="추출 텍스트 없음")
        data = load_extraction_failures(str(tmp_path))
        assert data["failures"][0]["error_type"] is None


class TestPipelineIntegration:
    def test_extract_and_noise_failures_have_no_error_type(self, tmp_path):
        """core/extractors.py untouched — verify via the real pipeline
        that extract_fail (empty text) records error_type=None."""
        raw = tmp_path / "RAW"; out = tmp_path / "output"
        raw.mkdir(); out.mkdir()
        (raw / "empty.txt").write_text("", encoding="utf-8")
        converter = build_converter(use_ocr=False)
        splitter = build_splitter(chunk_size=1200, chunk_overlap=200)

        process_batch(
            [{"path": str(raw / "empty.txt"), "name": "empty.txt", "ext": "txt", "use_ocr": False}],
            converter, splitter, output_dir=str(out), chunk_size=1200, chunk_overlap=200, report=None,
        )

        data = load_extraction_failures(str(out))
        assert len(data["failures"]) == 1
        assert data["failures"][0]["stage"] == "extract"
        assert data["failures"][0]["error_type"] is None

    def test_real_exception_captures_error_type(self, tmp_path):
        """A genuinely nonexistent RAW file triggers FileNotFoundError
        inside extract_text_from_file(), caught by process_one_file()'s
        outer exception handler — error_type must reflect that exact class."""
        raw = tmp_path / "RAW"; out = tmp_path / "output"
        raw.mkdir(); out.mkdir()
        converter = build_converter(use_ocr=False)
        splitter = build_splitter(chunk_size=1200, chunk_overlap=200)

        process_batch(
            [{"path": str(raw / "missing.txt"), "name": "missing.txt", "ext": "txt", "use_ocr": False}],
            converter, splitter, output_dir=str(out), chunk_size=1200, chunk_overlap=200, report=None,
        )

        data = load_extraction_failures(str(out))
        assert len(data["failures"]) == 1
        assert data["failures"][0]["stage"] == "exception"
        assert data["failures"][0]["error_type"] == "FileNotFoundError"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
