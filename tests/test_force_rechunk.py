"""Regression test — core/processing.py force_rechunk (2026-07-21).

force_rechunk is a separate operation from force_reingest
(tests/test_process_batch_force_reingest.py) — the two must not be
conflated (explicit contract from that file's docstring, preserved
here):

- force_reingest bypasses the .batch_state.json *filename* gate
  (process_batch level) — "try this filename again".
- force_rechunk bypasses classify_ingest_decision()'s *content-hash*
  SKIP (process_one_file level) — "re-run chunking even though the
  content is identical to what's already registered", needed after a
  chunking algorithm change (e.g. the 2026-07-21
  _merge_sentence_fragments() fix) to re-chunk already-ingested
  documents.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.processing import process_one_file, build_converter, build_splitter, get_processed_files


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_force_rechunk_reruns_chunking_on_duplicate_content(tmp_path):
    output_dir = str(tmp_path / "output")
    os.makedirs(output_dir, exist_ok=True)
    converter = build_converter()
    splitter = build_splitter(1200, 200)

    same_content = "이것은 회귀 테스트를 위한 동일한 본문 내용입니다. " * 30

    original_path = _write(tmp_path, "original.txt", same_content)
    duplicate_path = _write(tmp_path, "duplicate_rescan.txt", same_content)

    first = process_one_file(
        {"name": "original.txt", "path": original_path, "ext": "txt", "use_ocr": False},
        converter, splitter, output_dir, 1200, 200,
    )
    assert first["success"] is True

    # Without force_rechunk: SKIP path, no chunk files written for this name.
    plain = process_one_file(
        {"name": "duplicate_rescan.txt", "path": duplicate_path, "ext": "txt", "use_ocr": False},
        converter, splitter, output_dir, 1200, 200,
    )
    assert plain.get("skipped") is True
    assert plain.get("ingest_decision") == "SKIP"
    assert not os.path.exists(os.path.join(output_dir, "duplicate_rescan_txt_chunks_meta.json"))

    # With force_rechunk: same duplicate content, but chunking actually runs.
    forced = process_one_file(
        {"name": "duplicate_rescan.txt", "path": duplicate_path, "ext": "txt", "use_ocr": False},
        converter, splitter, output_dir, 1200, 200,
        force_rechunk=True,
    )
    assert forced.get("skipped") is not True
    assert os.path.exists(os.path.join(output_dir, "duplicate_rescan_txt_chunks_meta.json"))
    # mark_processed() must still fire on this path too (reuses REPROCESS's
    # existing fall-through, which already calls it — asserted for safety).
    assert "duplicate_rescan.txt" in get_processed_files(output_dir)


def test_force_rechunk_false_by_default_preserves_skip_behavior(tmp_path):
    """force_reingest tests (test_process_batch_force_reingest.py) must keep
    passing unchanged — force_rechunk defaults to False and does not alter
    SKIP behavior unless explicitly requested."""
    output_dir = str(tmp_path / "output")
    os.makedirs(output_dir, exist_ok=True)
    converter = build_converter()
    splitter = build_splitter(1200, 200)

    same_content = "짧은 반복 콘텐츠. " * 20
    original_path = _write(tmp_path, "o2.txt", same_content)
    duplicate_path = _write(tmp_path, "d2.txt", same_content)

    process_one_file(
        {"name": "o2.txt", "path": original_path, "ext": "txt", "use_ocr": False},
        converter, splitter, output_dir, 1200, 200,
    )
    result = process_one_file(
        {"name": "d2.txt", "path": duplicate_path, "ext": "txt", "use_ocr": False},
        converter, splitter, output_dir, 1200, 200,
    )
    assert result.get("skipped") is True


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
