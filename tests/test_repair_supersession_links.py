"""Regression test — scripts/repair_supersession_links.py
(NAE-SUPERSESSION-REGISTRY-REPAIR-001). tmp_path only: never touches the
real registry, TSU dataset or backups directory.
"""

import copy
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts import repair_supersession_links as rsl

CYCLE_IDS = [r for r in rsl.REPAIRS if r[2] in {
    "ab67ca69f34ee13d51326a72d4515083", "d7b9cbf96c2c9b3013001d765711054f",
    "bdd4b58cc4ea23ff902590b18d424da0", "762dc710e9e0112dd03373e530b070f5"}]


def _build_registry() -> dict:
    """Production-shaped subset: 4 cycle pairs (Vol10~13) + 3 dangling (Vol51~53)."""
    docs = {}
    for i, (old_id, _f, cur_id, _t) in enumerate(rsl.REPAIRS):
        src = f"Spurgeon_MTP_Vol{i}.txt"
        if cur_id in {r[2] for r in CYCLE_IDS}:
            # old (superseded, bogus supersedes -> current), current (supersedes -> old)
            docs[old_id] = {"document_id": old_id, "source_file": src,
                            "supersedes": cur_id, "superseded_by": cur_id}
            docs[cur_id] = {"document_id": cur_id, "source_file": src,
                            "supersedes": old_id, "superseded_by": None}
        else:
            docs[old_id] = {"document_id": old_id, "source_file": src,
                            "supersedes": cur_id, "superseded_by": None}  # cur_id absent
    docs["unrelated"] = {"document_id": "unrelated", "source_file": "x.txt",
                         "supersedes": None, "superseded_by": None, "title": "T"}
    return {"schema_version": "2.0", "updated_at": "t0", "documents": docs, "_meta": {}}


def _write(tmp_path, reg=None):
    p = tmp_path / "registry" / "documents.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(reg or _build_registry(), indent=2, ensure_ascii=False), encoding="utf-8")
    return str(p)


def _read(p):
    return json.loads(open(p, encoding="utf-8").read())


def test_dry_run_reports_seven_and_writes_nothing(tmp_path, capsys):
    p = _write(tmp_path)
    before = open(p, "rb").read()
    assert rsl.run(p, execute=False, backup_root=str(tmp_path / "bk")) == 0
    assert open(p, "rb").read() == before
    assert not (tmp_path / "bk").exists()
    assert "정정 대상 7" in capsys.readouterr().out


def test_execute_changes_exactly_seven_fields_and_backs_up(tmp_path):
    p = _write(tmp_path)
    before = _read(p)
    pre = rsl.scan_integrity(before)
    assert pre["two_cycle"] == 4 and pre["dangling"] == 3
    assert rsl.run(p, execute=True, backup_root=str(tmp_path / "bk")) == 0
    after = _read(p)
    changed = rsl._diff_fields(before, after)
    assert sorted(changed) == sorted(f".documents.{d}.{f}" for d, f, _e, _t in rsl.REPAIRS)
    post = rsl.scan_integrity(after)
    assert (post["dangling"], post["asymmetric"], post["two_cycle"], post["multi_current"]) == (0, 0, 0, 0)
    assert post["current_ids"] == pre["current_ids"]
    # normal links kept: current.supersedes -> old, old.superseded_by -> current
    for old_id, _f, cur_id, _t in CYCLE_IDS:
        assert after["documents"][cur_id]["supersedes"] == old_id
        assert after["documents"][old_id]["superseded_by"] == cur_id
    backups = list((tmp_path / "bk").iterdir())
    assert len(backups) == 1 and _read(str(backups[0] / "documents.json")) == before


def test_idempotent_second_run_is_noop(tmp_path, capsys):
    p = _write(tmp_path)
    assert rsl.run(p, execute=True, backup_root=str(tmp_path / "bk")) == 0
    once = open(p, "rb").read()
    capsys.readouterr()
    assert rsl.run(p, execute=True, backup_root=str(tmp_path / "bk")) == 0
    assert open(p, "rb").read() == once
    assert "이미 정정됨" in capsys.readouterr().out
    assert len(list((tmp_path / "bk").iterdir())) == 1  # no second backup


def test_precondition_mismatch_aborts_without_writing(tmp_path, capsys):
    reg = _build_registry()
    reg["documents"][rsl.REPAIRS[0][0]]["supersedes"] = "somethingelse"
    p = _write(tmp_path, reg)
    before = open(p, "rb").read()
    assert rsl.run(p, execute=True, backup_root=str(tmp_path / "bk")) == 2
    assert open(p, "rb").read() == before
    assert not (tmp_path / "bk").exists()
    assert "사전조건 불일치" in capsys.readouterr().out


def test_missing_record_aborts(tmp_path):
    reg = _build_registry()
    del reg["documents"][rsl.REPAIRS[-1][0]]
    p = _write(tmp_path, reg)
    assert rsl.run(p, execute=False) == 2


def test_failed_postcheck_restores_backup(tmp_path, monkeypatch):
    p = _write(tmp_path)
    before = open(p, "rb").read()
    monkeypatch.setattr(rsl, "apply_repairs", lambda reg, ch: reg["documents"]["unrelated"].update(title="X"))
    assert rsl.run(p, execute=True, backup_root=str(tmp_path / "bk")) == 3
    assert open(p, "rb").read() == before


def test_watch_paths_must_be_unchanged(tmp_path):
    p = _write(tmp_path)
    w = tmp_path / "tsu.jsonl"
    w.write_text("x")
    assert rsl.run(p, execute=True, backup_root=str(tmp_path / "bk"), watch_paths=[str(w)]) == 0
    assert w.read_text() == "x"
