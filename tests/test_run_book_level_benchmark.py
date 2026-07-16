"""Regression test — Book-level Benchmark Runner (SPRINT17-Phase6B-2).

Guards BookEvaluator's single-input contract (Phase6B-2-0 preflight §2:
the only thing it reads from a RankedCandidate is
metadata["verse_mapping"]["book_id"]) and the overall run_benchmark()
flow against a missing gold file, independent of core/retrieval.py.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.retrieval import RankedCandidate
from scripts.run_book_level_benchmark import BookEvaluator, run_benchmark


def _candidate(book_id) -> RankedCandidate:
    verse_mapping = {"book_id": book_id} if book_id is not None else {}
    return RankedCandidate(tsu_id="TSU-X-000001", content="x", metadata={"verse_mapping": verse_mapping})


class TestBookEvaluator:
    def test_book_id_of_reads_verse_mapping(self):
        assert BookEvaluator.book_id_of(_candidate("JHN")) == "JHN"

    def test_book_id_of_missing_verse_mapping_returns_none(self):
        assert BookEvaluator.book_id_of(_candidate(None)) is None

    def test_is_hit_true_on_match(self):
        assert BookEvaluator.is_hit(_candidate("MRK"), "MRK") is True

    def test_is_hit_false_on_mismatch(self):
        assert BookEvaluator.is_hit(_candidate("MRK"), "JHN") is False

    def test_is_hit_false_when_book_id_absent(self):
        assert BookEvaluator.is_hit(_candidate(None), "JHN") is False


class TestRunBenchmark:
    def test_missing_gold_file_returns_error_dict(self):
        result = run_benchmark(gold_path="/nonexistent/path.json")
        assert "error" in result

    def test_empty_queries_returns_error_dict(self, tmp_path):
        import json
        gold_file = tmp_path / "empty_gold.json"
        gold_file.write_text(json.dumps({"metadata": {}, "queries": []}), encoding="utf-8")
        result = run_benchmark(gold_path=str(gold_file))
        assert "error" in result


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
