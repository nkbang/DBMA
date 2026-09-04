"""Regression test — RetrievalEngine tolerates a missing TSU dataset file.

Before a fresh install (or right after scripts/reset_for_beta.py) has
processed its first document, output/bench/tsu_dataset.jsonl doesn't
exist yet. RetrievalEngine used to hard-crash with FileNotFoundError in
that state, which surfaced as a raw traceback on ui/pages/sermon_draft.py
(and any other page constructing QueryProcessor) the moment a pastor
tester opened the app before processing anything. Missing file should now
mean "empty corpus", not a crash — see core/retrieval.py::_load_corpus().
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.retrieval import RetrievalEngine, QueryProcessor


def test_missing_dataset_file_yields_empty_corpus(tmp_path):
    missing_path = tmp_path / "does_not_exist.jsonl"
    engine = RetrievalEngine(tsu_dataset_path=str(missing_path))
    assert engine.tsus == []
    assert engine.list_source_files() == []
    assert engine.book_coverage() == {}


def test_missing_dataset_file_query_processor_returns_empty_results(tmp_path):
    missing_path = tmp_path / "does_not_exist.jsonl"
    engine = RetrievalEngine(tsu_dataset_path=str(missing_path))
    processor = QueryProcessor(engine=engine)

    response = processor.process("로마서 8장", query_id="t1", k=5)

    assert response.top_k_results == []
