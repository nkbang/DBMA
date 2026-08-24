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

    def test_files_in_raw_subfolder_are_pending(self, tmp_path, monkeypatch):
        """[버그 수정 2026-08-24] 이전엔 raw_path.iterdir()로 최상위만
        스캔해서, RAW/설교_분리/ 같은 하위 폴더의 파일은 "문서 처리
        시작"을 몇 번 눌러도 대기열에 절대 안 잡혔다(사용자 보고: "전체
        처리를 했는데 다 끝내지 않는다" — 실측 확인: 미처리 36권 전부
        하위 폴더에 있었음). Dashboard의 보유 문서 카운트는 이미
        rglob()으로 재귀 탐색하므로 여기도 일치시켜야 한다."""
        raw_dir = tmp_path / "RAW"
        raw_dir.mkdir()
        (raw_dir / "top.txt").write_text("x")
        subfolder = raw_dir / "설교_분리"
        subfolder.mkdir()
        (subfolder / "sermon1.txt").write_text("y")
        (subfolder / "sermon2.txt").write_text("z")
        output_dir = tmp_path / "output"
        monkeypatch.setattr(processing_mod, "DEFAULT_OUTPUT_DIR", str(output_dir))

        pending = _build_file_list(str(raw_dir), force_reingest=False)
        names = {f["name"] for f in pending}
        assert names == {"top.txt", "sermon1.txt", "sermon2.txt"}


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
