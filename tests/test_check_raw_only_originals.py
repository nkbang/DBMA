"""Regression test — scripts/check_raw_only_originals.py::
find_output_only_originals() (2026-07-21).

가드 스크립트: RAW에 원본이 없고 output(.batch_state.json의 processed
목록 기준)에만 존재하는 파일을 찾는다 — output 정리/재처리 전 데이터
소실을 막기 위한 사전 점검용.
"""

import json
import sys
import unicodedata
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


def test_file_in_raw_subfolder_is_not_falsely_flagged(tmp_path):
    """[버그 수정 2026-08-24] os.listdir(RAW_DIR)이 최상위만 봐서
    RAW/설교_분리/ 같은 하위 폴더의 원본을 "RAW에 없음"으로 오탐했다
    (실측: 2026-08-24, 처리 완료된 문서 다수가 이 가드에 false
    positive로 걸림). rglob() 재귀 탐색으로 수정."""
    raw_dir = tmp_path / "RAW"
    sub = raw_dir / "설교_분리"
    sub.mkdir(parents=True)
    (sub / "sermon.md").write_text("x", encoding="utf-8")

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / ".batch_state.json").write_text(
        json.dumps({"processed": ["sermon.md"], "timestamp": ""}, ensure_ascii=False),
        encoding="utf-8",
    )
    guard.RAW_DIR = raw_dir
    guard.OUTPUT_DIR = output_dir
    guard.BATCH_STATE_PATH = output_dir / ".batch_state.json"

    assert guard.find_output_only_originals() == []


def test_nfd_vs_nfc_filename_is_not_falsely_flagged(tmp_path):
    """[버그 수정 2026-08-24] 정규화 없이 비교해서, RAW 파일시스템의
    NFD 자모분리 파일명과 batch_state.json에 NFC로 기록된 이름이
    시각적으로 동일해도 다른 파일로 오탐했다(ui/pages/dashboard.py 등
    반복 확인된 근본원인과 동일)."""
    raw_dir = tmp_path / "RAW"
    raw_dir.mkdir()
    nfd_name = unicodedata.normalize("NFD", "고린도전서.pdf")
    nfc_name = unicodedata.normalize("NFC", "고린도전서.pdf")
    (raw_dir / nfd_name).write_text("x", encoding="utf-8")

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / ".batch_state.json").write_text(
        json.dumps({"processed": [nfc_name], "timestamp": ""}, ensure_ascii=False),
        encoding="utf-8",
    )
    guard.RAW_DIR = raw_dir
    guard.OUTPUT_DIR = output_dir
    guard.BATCH_STATE_PATH = output_dir / ".batch_state.json"

    assert guard.find_output_only_originals() == []


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
