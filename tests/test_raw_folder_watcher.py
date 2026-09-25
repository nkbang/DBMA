"""Regression test — ADR-035 §3.1 항목1: RAW 폴더 신규 파일 감지.

core/raw_folder_watcher.py는 자동으로 파일을 처리하지 않고 목록만
반환한다(감지 후 원클릭 확인 유지) — 이 테스트는 그 경계를 검증한다.
"""

import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.raw_folder_watcher import find_new_raw_files, maybe_check_new_raw_files


def test_find_new_raw_files_empty_when_raw_dir_missing(tmp_path):
    raw_dir = tmp_path / "raw_does_not_exist"
    output_dir = tmp_path / "output"

    result = find_new_raw_files(str(raw_dir), str(output_dir))

    assert result == []


def test_find_new_raw_files_lists_unprocessed_supported_files(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    (raw_dir / "sermon1.pdf").write_text("dummy")
    (raw_dir / "sermon2.txt").write_text("dummy")
    (raw_dir / "notes.xyz").write_text("dummy")  # unsupported extension
    (raw_dir / ".hidden.pdf").write_text("dummy")  # dotfile — excluded

    result = find_new_raw_files(str(raw_dir), str(output_dir))

    names = {f["name"] for f in result}
    assert names == {"sermon1.pdf", "sermon2.txt"}


def test_find_new_raw_files_excludes_already_processed(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    (raw_dir / "done.pdf").write_text("dummy")
    (raw_dir / "new.pdf").write_text("dummy")

    (output_dir / ".batch_state.json").write_text(
        json.dumps({"processed": ["done.pdf"]}), encoding="utf-8"
    )

    result = find_new_raw_files(str(raw_dir), str(output_dir))

    assert [f["name"] for f in result] == ["new.pdf"]


def test_find_new_raw_files_does_not_touch_filesystem_beyond_reading(tmp_path):
    """자동 처리를 하지 않는다는 ADR-035 §3.1 조건 — 호출 전후로 RAW
    폴더 내용이 정확히 그대로 유지되는지 확인(파일 이동/삭제 없음)."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (raw_dir / "a.pdf").write_bytes(b"content")

    before = sorted(p.name for p in raw_dir.iterdir())
    find_new_raw_files(str(raw_dir), str(output_dir))
    after = sorted(p.name for p in raw_dir.iterdir())

    assert before == after == ["a.pdf"]


def test_maybe_check_throttles_to_once_per_day(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (raw_dir / "a.pdf").write_bytes(b"content")

    first = maybe_check_new_raw_files(str(raw_dir), str(output_dir))
    assert first is not None
    assert [f["name"] for f in first] == ["a.pdf"]

    # Same day, second call — marker file should suppress the re-scan.
    second = maybe_check_new_raw_files(str(raw_dir), str(output_dir))
    assert second is None

    marker = output_dir / ".raw_watcher_marker"
    assert marker.exists()
