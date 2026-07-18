"""Regression test — core/processing.py::process_batch(force_reingest=)
(SPRINT21-G-3-B Gap#3 fix). Verifies the .batch_state.json filename gate
is bypassed when force_reingest=True, while the separate content-hash
SKIP layer (classify_ingest_decision) still correctly detects unchanged
content — the two must not be conflated.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.processing import process_batch, get_processed_files, mark_processed


def test_force_reingest_bypasses_batch_state_gate(tmp_path):
    output_dir = str(tmp_path)
    mark_processed(output_dir, "already_marked.txt")
    assert "already_marked.txt" in get_processed_files(output_dir)

    file_list = [{"path": "/nonexistent/already_marked.txt", "name": "already_marked.txt", "ext": "txt", "use_ocr": False}]

    # force_reingest=False (default): batch-level gate skips before
    # process_one_file() is ever called — no attempt to open the (missing)
    # file, so this must not raise.
    results = process_batch(file_list, converter=None, splitter=None, output_dir=output_dir,
                             chunk_size=1200, chunk_overlap=200, force_reingest=False)
    assert results[0]["skipped"] is True
    assert "이미 처리됨" in results[0]["logs"][0]["msg"]


def test_force_reingest_true_reaches_process_one_file(tmp_path):
    output_dir = str(tmp_path)
    mark_processed(output_dir, "already_marked.txt")

    file_list = [{"path": "/nonexistent/already_marked.txt", "name": "already_marked.txt", "ext": "txt", "use_ocr": False}]

    # force_reingest=True: batch-level gate must not fire. The file path
    # doesn't exist, so process_one_file() will fail inside — but that
    # failure proves the batch-level skip was bypassed (a real skip would
    # never touch the filesystem at all).
    results = process_batch(file_list, converter=None, splitter=None, output_dir=output_dir,
                             chunk_size=1200, chunk_overlap=200, force_reingest=True)
    assert results[0].get("skipped") is not True
    assert "이미 처리됨" not in str(results[0].get("logs", []))


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
