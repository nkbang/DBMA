"""Regression test — core/processing.py::process_one_file() SKIP path must
still call mark_processed() (2026-07-21 bug fix).

Root cause: classify_ingest_decision() returns "SKIP" when a file's
content hash matches an existing registry record under a *different*
source_file name (e.g. a re-scanned/OCR'd duplicate of an already-
ingested document). The SKIP branch rewrote the .md and returned early
without ever calling mark_processed(output_dir, source_name) — so the
duplicate filename never entered .batch_state.json's processed set and
stayed in ui/pages/processing.py's queue forever, even though its
content is already fully represented in the TSU dataset under the
original filename.

Reproduced live via manual process_one_file() call on the actual stuck
files ("5. 요한복음1clearscan_cropped.pdf" etc.) — this test reproduces
the same SKIP mechanism with synthetic .txt content so it doesn't
depend on PDF extraction or real corpus state.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.processing import process_one_file, build_converter, build_splitter, get_processed_files


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_skip_path_marks_processed(tmp_path):
    output_dir = str(tmp_path / "output")
    os.makedirs(output_dir, exist_ok=True)
    converter = build_converter()
    splitter = build_splitter(1200, 200)

    same_content = "이것은 회귀 테스트를 위한 동일한 본문 내용입니다. " * 30

    original_path = _write(tmp_path, "original.txt", same_content)
    duplicate_path = _write(tmp_path, "duplicate_rescan.txt", same_content)

    # First ingest: brand new content -> PROCESS path, populates the
    # identity registry that the second call's SKIP decision depends on.
    first = process_one_file(
        {"name": "original.txt", "path": original_path, "ext": "txt", "use_ocr": False},
        converter, splitter, output_dir, 1200, 200,
    )
    assert first["success"] is True
    assert not first.get("skipped")
    assert "original.txt" in get_processed_files(output_dir)

    # Second ingest: identical content under a different filename ->
    # must hit the SKIP path (content-hash dedup).
    second = process_one_file(
        {"name": "duplicate_rescan.txt", "path": duplicate_path, "ext": "txt", "use_ocr": False},
        converter, splitter, output_dir, 1200, 200,
    )
    assert second.get("skipped") is True
    assert second.get("ingest_decision") == "SKIP"

    # The actual bug: this filename must be marked processed even though
    # its content was a duplicate, or it stays in the UI queue forever.
    assert "duplicate_rescan.txt" in get_processed_files(output_dir)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
