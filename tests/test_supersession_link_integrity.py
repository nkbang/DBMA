"""Regression test — core/identity_registry.py::mark_superseded() link integrity
(NAE-SUPERSESSION-LINK-INTEGRITY-001).

document_id is a content hash, so A -> B -> A (same ID returning) must not
leave supersedes/superseded_by cycles or dangling references, and each
source_file must keep exactly one current record. Pure dict-based: never
touches a real registry path.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.identity_registry import (
    find_by_source_file,
    get_supersession_chain,
    mark_superseded,
)


def _registry(*ids, source_file="a.txt", **overrides) -> dict:
    docs = {
        i: {"document_id": i, "source_file": source_file, "supersedes": None, "superseded_by": None}
        for i in ids
    }
    for i, fields in overrides.items():
        docs[i].update(fields)
    return {"documents": docs}


def _docs(reg):
    return reg["documents"]


def _assert_invariants(reg, current_id):
    docs = _docs(reg)
    # Invariant 2 + single current record per source_file
    assert docs[current_id]["superseded_by"] is None
    assert [d for d, r in docs.items() if r["superseded_by"] is None] == [current_id]
    # Invariant 4: every link resolves inside the registry
    for r in docs.values():
        for key in ("supersedes", "superseded_by"):
            assert r[key] is None or r[key] in docs
    # #6: chain walker terminates without duplicates from any starting node
    for start in docs:
        chain_ids = [r["document_id"] for r in get_supersession_chain(reg, start)]
        assert len(chain_ids) == len(set(chain_ids))
    # #7: current record is what lookup by source_file returns
    assert find_by_source_file(reg, "a.txt")["document_id"] == current_id


def test_1_normal_two_version_chain_unchanged():
    reg = _registry("A", "B")
    mark_superseded(reg, "A", "B")
    assert _docs(reg)["A"]["superseded_by"] == "B"
    assert _docs(reg)["B"]["supersedes"] == "A"
    _assert_invariants(reg, "B")


def test_2_same_id_A_becomes_current_again_after_A_to_B():
    reg = _registry("A", "B")
    mark_superseded(reg, "A", "B")
    mark_superseded(reg, "B", "A")  # A requested current again
    d = _docs(reg)
    assert d["A"]["superseded_by"] is None
    assert d["A"]["supersedes"] == "B"
    assert d["B"]["superseded_by"] == "A"
    assert d["B"]["supersedes"] is None  # Invariant 3: no B -> A back-link
    _assert_invariants(reg, "A")


def test_3_same_id_A_becomes_current_again_from_A_B_C_state():
    reg = _registry("A", "B", "C")
    mark_superseded(reg, "A", "B")
    mark_superseded(reg, "B", "C")
    mark_superseded(reg, "C", "A")  # A requested current again
    d = _docs(reg)
    assert (d["B"]["supersedes"], d["B"]["superseded_by"]) == (None, "C")
    assert (d["C"]["supersedes"], d["C"]["superseded_by"]) == ("B", "A")
    assert (d["A"]["supersedes"], d["A"]["superseded_by"]) == ("C", None)
    _assert_invariants(reg, "A")  # A -> C -> B, exactly one current


def test_3b_vol10_shape_dangling_link_revived_by_reregistration():
    # a337c5's supersedes pointed at ab67ca while ab67ca was deleted (dangling);
    # ab67ca re-registered under the same ID, healing the link into a cycle.
    reg = _registry("A", "B", B={"supersedes": "A"})
    mark_superseded(reg, "B", "A")
    d = _docs(reg)
    assert d["B"]["supersedes"] is None
    assert d["B"]["superseded_by"] == "A"
    assert d["A"]["supersedes"] == "B"
    _assert_invariants(reg, "A")


def test_4_dangling_supersedes_is_cleared():
    # Vol51 shape: 9aa798.supersedes -> 189da5 (deleted from registry)
    reg = _registry("A", "B", A={"supersedes": "ghost"})
    mark_superseded(reg, "A", "B")
    assert _docs(reg)["A"]["supersedes"] is None
    _assert_invariants(reg, "B")


def test_4b_dangling_superseded_by_on_new_is_cleared():
    reg = _registry("A", "B", B={"superseded_by": "ghost"})
    mark_superseded(reg, "A", "B")
    assert _docs(reg)["B"]["superseded_by"] is None
    _assert_invariants(reg, "B")


def test_5_same_id_is_noop():
    reg = _registry("A", A={"supersedes": "ghost"})
    before = {k: dict(v) for k, v in _docs(reg).items()}
    mark_superseded(reg, "A", "A")
    assert _docs(reg) == before


def test_missing_record_ids_do_not_raise():
    reg = _registry("A")
    mark_superseded(reg, "A", "missing")  # one-sided write, as before
    assert _docs(reg)["A"]["superseded_by"] == "missing"
