"""Regression test — ui/pages/processing.py "처리 가능: N개" count
(2026-07-21 bug fix).

Before: _render_ingestion_form() counted every supported-extension file
in RAW, including already-processed ones — so "처리 가능: 64개 문서"
stayed at 64 even when 대기열(queue) correctly showed 0, an apparent
contradiction the user flagged. The count must use the same
already-processed filter as _build_file_list() (and therefore the same
definition of "pending" as the queue), respecting force_reingest.
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
from ui.pages import processing as processing_mod
from ui.pages.processing import _build_file_list


def _mark_processed(output_dir: Path, *names: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / ".batch_state.json").write_text(
        json.dumps({"processed": list(names)}), encoding="utf-8"
    )


class TestPendingCountMatchesQueueDefinition:
    def test_all_new_files_are_pending(self, tmp_path, monkeypatch):
        raw_dir = tmp_path / "RAW"
        raw_dir.mkdir()
        (raw_dir / "a.txt").write_text("x")
        (raw_dir / "b.txt").write_text("y")
        output_dir = tmp_path / "output"
        monkeypatch.setattr(processing_mod, "DEFAULT_OUTPUT_DIR", str(output_dir))

        assert len(_build_file_list(str(raw_dir), force_reingest=False)) == 2

    def test_already_processed_files_excluded_from_pending_count(self, tmp_path, monkeypatch):
        """The exact contradiction the user reported: a file already in
        .batch_state.json's processed set must not count toward
        "처리 가능"(pending), matching the queue's 0-count for the same file."""
        raw_dir = tmp_path / "RAW"
        raw_dir.mkdir()
        (raw_dir / "a.txt").write_text("x")
        (raw_dir / "b.txt").write_text("y")
        output_dir = tmp_path / "output"
        monkeypatch.setattr(processing_mod, "DEFAULT_OUTPUT_DIR", str(output_dir))
        _mark_processed(output_dir, "a.txt", "b.txt")

        pending = _build_file_list(str(raw_dir), force_reingest=False)
        assert pending == []

    def test_force_reingest_makes_processed_files_pending_again(self, tmp_path, monkeypatch):
        raw_dir = tmp_path / "RAW"
        raw_dir.mkdir()
        (raw_dir / "a.txt").write_text("x")
        output_dir = tmp_path / "output"
        monkeypatch.setattr(processing_mod, "DEFAULT_OUTPUT_DIR", str(output_dir))
        _mark_processed(output_dir, "a.txt")

        assert len(_build_file_list(str(raw_dir), force_reingest=False)) == 0
        assert len(_build_file_list(str(raw_dir), force_reingest=True)) == 1


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
