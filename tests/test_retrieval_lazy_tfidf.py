"""Regression test — RetrievalEngine lazy TF-IDF index (SPRINT28-C).

TF-IDF (self.vectors/self.tfidf_vectorizer) is a fallback-only path used
by retrieve() STEP 3 when the BGE-M3 embedding backend is unavailable
(embedding_cache=None or a failed lookup). Building it eagerly at
__init__ accounted for ~80% of RetrievalEngine's memory footprint even
when never read (SPRINT28-C Preflight, measured). This guards the new
lazy-build contract: unbuilt at __init__, built exactly once on first
actual fallback need, idempotent thereafter.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.retrieval import RetrievalEngine, QueryParser


def _write_dataset(tmp_path) -> str:
    records = [
        {
            "tsu_id": "TSU-ROM-doc1_chunk_00000",
            "document_id": "doc1",
            "chunk_id": "doc1_chunk_00000",
            "content": "로마서 8장은 성령 안에서의 삶을 다룬다. 정죄함이 없다는 확신을 준다.",
            "verse_mapping": {"book_id": "ROM"},
            "source_file": "test.pdf",
        },
        {
            "tsu_id": "TSU-ROM-doc1_chunk_00001",
            "document_id": "doc1",
            "chunk_id": "doc1_chunk_00001",
            "content": "은혜와 믿음으로 의롭다 함을 받는다는 교리를 설명한다.",
            "verse_mapping": {"book_id": "ROM"},
            "source_file": "test.pdf",
        },
    ]
    path = tmp_path / "tsu_dataset.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return str(path)


def test_tfidf_index_not_built_at_init(tmp_path):
    engine = RetrievalEngine(tsu_dataset_path=_write_dataset(tmp_path))
    assert engine._tfidf_index_built is False
    assert engine.vectors == []


def test_tfidf_index_built_lazily_on_fallback_need(tmp_path):
    engine = RetrievalEngine(tsu_dataset_path=_write_dataset(tmp_path))
    parsed = QueryParser().parse("로마서 8장 성령")

    # embedding_cache=None -> semantic_embedder stays None -> every
    # candidate falls through to the TF-IDF fallback branch.
    candidates, _metrics = engine.retrieve(parsed, k_output=2, embedding_cache=None)

    assert engine._tfidf_index_built is True
    assert len(engine.vectors) == len(engine.tsus)
    assert len(candidates) > 0


def test_tfidf_index_build_is_idempotent(tmp_path):
    engine = RetrievalEngine(tsu_dataset_path=_write_dataset(tmp_path))
    engine._ensure_tfidf_index()
    vectors_first = engine.vectors
    engine._ensure_tfidf_index()
    assert engine.vectors is vectors_first  # not rebuilt, same object


def test_no_fallback_needed_leaves_index_unbuilt(tmp_path):
    """When embedding_cache is None and BM25 alone still yields results,
    the fallback path is exercised as in the previous test; this test
    instead confirms an engine that never calls retrieve() at all stays
    at the cheap post-__init__ state (no TF-IDF memory paid for a
    session that never queries)."""
    engine = RetrievalEngine(tsu_dataset_path=_write_dataset(tmp_path))
    assert engine._tfidf_index_built is False
