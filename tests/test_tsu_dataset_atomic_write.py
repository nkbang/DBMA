"""Regression: core.tsu_builder.write_tsu_dataset() / write_manifest() must
write atomically.

[2026-09-07 incident] The old implementations opened the target with
mode "w" (truncate in place) and never fsync'd, so an interrupted write
(a Streamlit rerun killing the script) left a NUL-hole blend of new head +
unwritten middle + stale tail. Readers then raised
JSONDecodeError("Expecting value: line 1 column 1 (char 0)").
"""
from __future__ import annotations

import json
import os

import pytest

from core.tsu_builder import write_tsu_dataset, write_manifest


def _records(n, start=0):
    return [{"tsu_id": f"T-{i}", "content": f"한글 내용 {i}", "v": i}
            for i in range(start, start + n)]


def test_fresh_write_creates_parent_and_valid_jsonl(tmp_path):
    p = tmp_path / "sub" / "tsu_dataset.jsonl"
    write_tsu_dataset(_records(1000), p)

    lines = p.read_text("utf-8").splitlines()
    assert len(lines) == 1000
    assert json.loads(lines[-1])["v"] == 999
    assert p.read_bytes().count(0) == 0


def test_overwrite_with_fewer_records_leaves_no_stale_tail_or_nul(tmp_path):
    p = tmp_path / "tsu_dataset.jsonl"
    write_tsu_dataset(_records(3000), p)
    write_tsu_dataset(_records(200), p)

    raw = p.read_bytes()
    assert raw.count(0) == 0, "NUL bytes in dataset — non-atomic write regression"
    lines = p.read_text("utf-8").splitlines()
    assert len(lines) == 200
    assert all(json.loads(ln) for ln in lines)


def test_no_temp_file_left_behind(tmp_path):
    p = tmp_path / "tsu_dataset.jsonl"
    write_tsu_dataset(_records(50), p)
    assert [f.name for f in tmp_path.iterdir()] == [p.name]


def test_serialization_error_preserves_existing_file(tmp_path):
    p = tmp_path / "tsu_dataset.jsonl"
    write_tsu_dataset(_records(500), p)

    class Unserializable:
        pass

    with pytest.raises(TypeError):
        write_tsu_dataset([{"ok": 1}, {"bad": Unserializable()}], p)

    # existing good file untouched, no temp leak
    assert len(p.read_text("utf-8").splitlines()) == 500
    assert [f.name for f in tmp_path.iterdir()] == [p.name]


def test_written_dataset_reloads_line_by_line(tmp_path):
    p = tmp_path / "tsu_dataset.jsonl"
    recs = _records(1234)
    write_tsu_dataset(recs, p)

    with open(p, "r", encoding="utf-8") as f:
        back = [json.loads(line) for line in f if line.strip()]
    assert [r["tsu_id"] for r in back] == [r["tsu_id"] for r in recs]


# --- write_manifest: same atomic contract -----------------------------------

def test_write_manifest_fresh_and_valid_json(tmp_path):
    mp = tmp_path / "bench" / "tsu_manifest.json"
    out = write_manifest(_records(10), {"documents": {}}, mp)

    on_disk = json.loads(mp.read_text("utf-8"))
    assert on_disk == out
    assert on_disk["tsu_count"] == 10
    assert mp.read_bytes().count(0) == 0
    assert [f.name for f in (tmp_path / "bench").iterdir()] == [mp.name]


def test_write_manifest_overwrite_leaves_no_nul_or_temp(tmp_path):
    mp = tmp_path / "tsu_manifest.json"
    write_manifest(_records(500), {"documents": {}}, mp)
    write_manifest(_records(3), {"documents": {}}, mp)

    raw = mp.read_bytes()
    assert raw.count(0) == 0
    assert json.loads(raw)["tsu_count"] == 3
    assert [f.name for f in tmp_path.iterdir()] == [mp.name]
