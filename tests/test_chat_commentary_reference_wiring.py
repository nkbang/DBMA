"""Regression test — Baptist commentary collection reachable from chat.

Prior to this fix, `ui/pages/chat.py::_inject_smith_context` (now
`_inject_reference_context`) only ever searched `nae_ref_v1` (Smith Bible
Dictionary) and additionally filtered results to entries whose source_id/
volume contained "smith" — so `nae_ref_commentary_v1` (Gill/Broadus/Carroll/
Spurgeon, embedded under ADR-030 Amendment B,
docs/BAPTIST_COMMENTARY_EMBEDDING_PLAN_v1.md) was never queried and never
surfaced, even though the data existed in Qdrant. This locks in that both
collections are queried and both source groups can appear in the injected
context, distinguished by `content_type`.
"""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import ollama  # noqa: F401
except ImportError:
    if "ollama" not in sys.modules:
        _ollama_stub = types.ModuleType("ollama")
        _ollama_stub.generate = lambda *a, **k: {"response": ""}
        _ollama_stub.embeddings = lambda *a, **k: {"embedding": []}
        sys.modules["ollama"] = _ollama_stub

import ui.pages.chat as chat
from NAE.pipeline.reference import config as ref_config


class _FakeResponse:
    def __init__(self):
        self.llm_context_block = ""


def _fake_search_reference(query, top_k=3, collection_names=None):
    names = collection_names or [ref_config.REFERENCE_COLLECTION_NAME]
    if names == [ref_config.REFERENCE_COLLECTION_NAME]:
        return [{
            "text": "Smith entry text",
            "source_id": "BAP-REF-SMITH-VOL01",
            "volume": "vol_1",
            "page_start": 10,
            "page_end": 10,
            "heading_context": "MOSES",
            "chunk_index": 1,
            "content_type": "reference_dictionary",
        }]
    if names == [ref_config.COMMENTARY_COLLECTION_NAME]:
        return [{
            "text": "Gill commentary text on Romans 8",
            "source_id": "BAP-COMM-GILL-NT-VOL01",
            "volume": "vol_1",
            "page_start": 250,
            "page_end": 250,
            "heading_context": "Romans 8:7",
            "chunk_index": 5,
            "content_type": "reference_commentary",
        }]
    return []


def test_inject_reference_context_queries_both_collections(monkeypatch):
    monkeypatch.setattr(
        "NAE.reference_retrieval_adapter.search_reference", _fake_search_reference,
    )
    # Force activation regardless of the heuristic's own logic — this test
    # is about wiring (are both collections queried?), not activation rules.
    monkeypatch.setattr(chat, "should_activate_smith", lambda q: True)
    monkeypatch.setattr(chat, "rewrite_query_for_smith", lambda q: None)

    response = _FakeResponse()
    entries = chat._inject_reference_context(response, "로마서 8장 주석")

    assert len(entries) == 2
    assert "Smith Bible Dictionary" in response.llm_context_block
    assert "침례교 주석가 문헌" in response.llm_context_block
    assert "Gill commentary text on Romans 8" in response.llm_context_block
    assert "Smith entry text" in response.llm_context_block


def test_inject_reference_context_smith_only_still_works(monkeypatch):
    def _smith_only(query, top_k=3, collection_names=None):
        if collection_names == [ref_config.COMMENTARY_COLLECTION_NAME]:
            return []
        return _fake_search_reference(query, top_k, [ref_config.REFERENCE_COLLECTION_NAME])

    monkeypatch.setattr(
        "NAE.reference_retrieval_adapter.search_reference", _smith_only,
    )
    monkeypatch.setattr(chat, "should_activate_smith", lambda q: True)
    monkeypatch.setattr(chat, "rewrite_query_for_smith", lambda q: None)

    response = _FakeResponse()
    entries = chat._inject_reference_context(response, "모세는 누구인가")

    assert len(entries) == 1
    assert "Smith Bible Dictionary" in response.llm_context_block
    assert "침례교 주석가 문헌" not in response.llm_context_block


def test_inject_reference_context_not_activated_returns_empty(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "NAE.reference_retrieval_adapter.search_reference",
        lambda *a, **k: calls.append(1) or [],
    )
    monkeypatch.setattr(chat, "should_activate_smith", lambda q: False)

    response = _FakeResponse()
    entries = chat._inject_reference_context(response, "아무 질문")

    assert entries == []
    assert response.llm_context_block == ""
    assert calls == []
