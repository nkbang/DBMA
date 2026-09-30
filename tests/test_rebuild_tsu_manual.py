"""Regression — scripts/rebuild_tsu_manual.py 링크 정리 (NAE-REBUILD-TSU-LINK-CLEANUP-001).
tmp_path only."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.identity_registry import remove_document
from scripts import rebuild_tsu_manual as rtm


def _doc(i, src, ts="2026-01-01", sup=None, by=None):
    return {"document_id": i, "source_file": src, "last_processed_at": ts,
            "supersedes": sup, "superseded_by": by}


def _reg():
    return {"schema_version": "2.0", "documents": {
        # dup group: a(old ts), b(new ts) both current
        "a": _doc("a", "x.txt", "2026-01-01"),
        "b": _doc("b", "x.txt", "2026-02-01", sup="c"),
        # c is superseded history sharing source_file with b? (different file to isolate)
        "c": _doc("c", "y.txt", by="b"),
        # legit chain on same source: old superseded, new current -> NOT a duplicate
        "o": _doc("o", "z.txt", by="n"),
        "n": _doc("n", "z.txt", sup="o"),
    }}


def _write(tmp_path, reg=None):
    p = tmp_path / "registry" / "documents.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(reg or _reg()), encoding="utf-8")
    return p


def test_remove_document_clears_links():
    reg = _reg()
    assert remove_document(reg, "b")["document_id"] == "b"
    assert reg["documents"]["c"]["superseded_by"] is None
    assert remove_document(reg, "nope") is None


def test_supersession_chain_is_not_a_duplicate():
    assert rtm.find_duplicates(_reg()["documents"]) == {"x.txt": ["a", "b"]}


def test_winner_prefers_current_then_latest():
    docs = _reg()["documents"]
    assert rtm.pick_winner(docs, ["a", "b"]) == "b"
    docs["b"]["superseded_by"] = "a"  # b no longer current -> a wins despite older ts
    assert rtm.pick_winner(docs, ["a", "b"]) == "a"


def test_dry_run_changes_nothing(tmp_path):
    p = _write(tmp_path)
    before = p.read_bytes()
    assert rtm.main(["--registry", str(p)]) == 0
    assert p.read_bytes() == before


def test_remove_losers_leaves_no_dangling_and_backs_up(tmp_path):
    reg = _reg()
    reg["documents"]["a"]["supersedes"] = None
    reg["documents"]["c"]["superseded_by"] = "a"  # link to the soon-removed loser
    reg["documents"]["a"]["supersedes"] = "c"
    reg["documents"]["b"]["supersedes"] = None
    p = _write(tmp_path, reg)
    n, code = rtm.remove_losers(p, tmp_path / "bk")
    assert (n, code) == (1, 0)
    after = json.loads(p.read_text(encoding="utf-8"))
    assert "a" not in after["documents"]
    assert rtm.link_problems(after)["dangling"] == 0
    assert len(list((tmp_path / "bk").iterdir())) == 1


def test_idempotent(tmp_path):
    p = _write(tmp_path)
    assert rtm.remove_losers(p, tmp_path / "bk")[0] == 1
    once = p.read_bytes()
    assert rtm.remove_losers(p, tmp_path / "bk") == (0, 0)
    assert p.read_bytes() == once
    assert len(list((tmp_path / "bk").iterdir())) == 1
