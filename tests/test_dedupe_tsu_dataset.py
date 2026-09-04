"""Regression test — scripts/dedupe_tsu_dataset.py::plan()/execute()
(2026-07-21).

get_remove_source_files()는 scripts/cleanup_duplicate_outputs.py의
find_size_duplicates()/_pick_duplicate_keep_and_remove()를 그대로
재사용하므로 여기서는 mock으로 대체해 plan()/execute()의 자체 로직
(TSU jsonl 필터링 + 백업)만 검증한다.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import scripts.dedupe_tsu_dataset as dedupe


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def test_plan_counts_matched_records_per_source_file(tmp_path):
    tsu_path = tmp_path / "tsu_dataset.jsonl"
    _write_jsonl(tsu_path, [
        {"tsu_id": "1", "source_file": "dup_a.pdf"},
        {"tsu_id": "2", "source_file": "dup_a.pdf"},
        {"tsu_id": "3", "source_file": "keep.pdf"},
    ])
    dedupe.TSU_DATASET_PATH = tsu_path

    with patch.object(dedupe, "get_remove_source_files", return_value=["dup_a.pdf"]):
        p = dedupe.plan()

    assert p["total"] == 3
    assert p["matched_records"] == {"dup_a.pdf": 2}


def test_plan_empty_when_no_overlap(tmp_path):
    tsu_path = tmp_path / "tsu_dataset.jsonl"
    _write_jsonl(tsu_path, [{"tsu_id": "1", "source_file": "keep.pdf"}])
    dedupe.TSU_DATASET_PATH = tsu_path

    with patch.object(dedupe, "get_remove_source_files", return_value=["dup_a.pdf"]):
        p = dedupe.plan()

    assert p["matched_records"] == {}


def test_execute_backs_up_and_filters_records(tmp_path, monkeypatch):
    tsu_path = tmp_path / "tsu_dataset.jsonl"
    _write_jsonl(tsu_path, [
        {"tsu_id": "1", "source_file": "dup_a.pdf"},
        {"tsu_id": "2", "source_file": "keep.pdf"},
    ])
    dedupe.TSU_DATASET_PATH = tsu_path
    dedupe.BACKUP_ROOT = tmp_path / "backups"

    with patch.object(dedupe, "get_remove_source_files", return_value=["dup_a.pdf"]):
        p = dedupe.plan()
        dedupe.execute(p)

    remaining = [json.loads(l) for l in tsu_path.read_text(encoding="utf-8").splitlines()]
    assert [r["tsu_id"] for r in remaining] == ["2"]

    backups = list((tmp_path / "backups").glob("dedupe_tsu_dataset_*/tsu_dataset.jsonl"))
    assert len(backups) == 1
    backed_up = [json.loads(l) for l in backups[0].read_text(encoding="utf-8").splitlines()]
    assert len(backed_up) == 2


def test_execute_noop_when_nothing_to_remove(tmp_path):
    tsu_path = tmp_path / "tsu_dataset.jsonl"
    _write_jsonl(tsu_path, [{"tsu_id": "1", "source_file": "keep.pdf"}])
    dedupe.TSU_DATASET_PATH = tsu_path
    dedupe.BACKUP_ROOT = tmp_path / "backups"

    with patch.object(dedupe, "get_remove_source_files", return_value=["dup_a.pdf"]):
        p = dedupe.plan()
        dedupe.execute(p)

    assert not (tmp_path / "backups").exists()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
