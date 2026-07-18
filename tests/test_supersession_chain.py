"""Regression test — core/identity_registry.py::get_supersession_chain()
(SPRINT24-2). Pure read-only chain walker over supersedes/superseded_by.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.identity_registry import get_supersession_chain


def _registry(docs: dict) -> dict:
    return {"documents": docs}


def test_single_document_no_chain():
    reg = _registry({"a": {"document_id": "a", "supersedes": None, "superseded_by": None}})
    chain = get_supersession_chain(reg, "a")
    assert [r["document_id"] for r in chain] == ["a"]


def test_three_version_chain_oldest_to_newest():
    reg = _registry({
        "v1": {"document_id": "v1", "supersedes": None, "superseded_by": "v2"},
        "v2": {"document_id": "v2", "supersedes": "v1", "superseded_by": "v3"},
        "v3": {"document_id": "v3", "supersedes": "v2", "superseded_by": None},
    })
    # querying from the middle version must still return the full chain
    chain = get_supersession_chain(reg, "v2")
    assert [r["document_id"] for r in chain] == ["v1", "v2", "v3"]


def test_query_from_oldest_returns_full_chain():
    reg = _registry({
        "v1": {"document_id": "v1", "supersedes": None, "superseded_by": "v2"},
        "v2": {"document_id": "v2", "supersedes": "v1", "superseded_by": None},
    })
    chain = get_supersession_chain(reg, "v1")
    assert [r["document_id"] for r in chain] == ["v1", "v2"]


def test_unknown_document_id_returns_empty():
    reg = _registry({"a": {"document_id": "a"}})
    assert get_supersession_chain(reg, "missing") == []


def test_cycle_does_not_infinite_loop():
    # Malformed/corrupt data (should never occur via mark_superseded(), but
    # the walker must not hang if it does).
    reg = _registry({
        "a": {"document_id": "a", "supersedes": "b", "superseded_by": None},
        "b": {"document_id": "b", "supersedes": "a", "superseded_by": None},
    })
    chain = get_supersession_chain(reg, "a")
    assert len(chain) <= 2  # terminates, no crash


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
