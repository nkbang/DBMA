"""Regression test — scripts/check_raw_only_originals.py::
find_output_only_originals() (2026-07-21).

가드 스크립트: RAW에 원본이 없고 output(.batch_state.json의 processed
목록 기준)에만 존재하는 파일을 찾는다 — output 정리/재처리 전 데이터
소실을 막기 위한 사전 점검용.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import scripts.check_raw_only_originals as guard


def _setup(tmp_path, processed, raw_names):
    raw_dir = tmp_path / "RAW"
    raw_dir.mkdir()
    for name in raw_names:
        (raw_dir / name).write_text("x", encoding="utf-8")

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / ".batch_state.json").write_text(
        json.dumps({"processed": processed, "timestamp": ""}, ensure_ascii=False),
        encoding="utf-8",
    )

    guard.RAW_DIR = raw_dir
    guard.OUTPUT_DIR = output_dir
    guard.BATCH_STATE_PATH = output_dir / ".batch_state.json"


def test_flags_processed_file_missing_from_raw(tmp_path):
    _setup(tmp_path, processed=["a.pdf", "b.pdf"], raw_names=["a.pdf"])
    assert guard.find_output_only_originals() == ["b.pdf"]


def test_empty_when_all_processed_files_present_in_raw(tmp_path):
    _setup(tmp_path, processed=["a.pdf", "b.pdf"], raw_names=["a.pdf", "b.pdf"])
    assert guard.find_output_only_originals() == []


def test_no_batch_state_file_returns_empty(tmp_path):
    guard.RAW_DIR = tmp_path / "RAW"
    guard.OUTPUT_DIR = tmp_path / "output"
    guard.BATCH_STATE_PATH = tmp_path / "output" / ".batch_state.json"
    assert guard.find_output_only_originals() == []


def test_result_sorted_deterministically(tmp_path):
    _setup(tmp_path, processed=["z.pdf", "a.pdf", "m.pdf"], raw_names=[])
    assert guard.find_output_only_originals() == ["a.pdf", "m.pdf", "z.pdf"]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
