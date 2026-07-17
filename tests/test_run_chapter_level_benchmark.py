"""Regression test — Chapter-level Benchmark Runner (SPRINT18-E).

Guards ChapterEvaluator's exact book_id AND chapter match contract (HQ
decision 2 — RetrievalEngine's +/-2 chapter tolerance must never be used
here), the book_only_hits diagnostic (HQ decision: Book Correct / Chapter
Wrong counted separately as a chapter-metadata quality signal), and the
book/chapter-split failed_queries fields (HQ decision 3), independent of
BookEvaluator / run_book_level_benchmark.py (not modified this sprint).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.retrieval import RankedCandidate
from scripts.run_chapter_level_benchmark import ChapterEvaluator, run_benchmark


def _candidate(book_id, chapter) -> RankedCandidate:
    verse_mapping: dict = {}
    if book_id is not None:
        verse_mapping["book_id"] = book_id
    if chapter is not None:
        verse_mapping["chapter"] = chapter
    return RankedCandidate(tsu_id="TSU-X-000001", content="x", metadata={"verse_mapping": verse_mapping})


class TestChapterEvaluator:
    def test_book_id_of_reads_verse_mapping(self):
        assert ChapterEvaluator.book_id_of(_candidate("JHN", 3)) == "JHN"

    def test_chapter_of_reads_verse_mapping(self):
        assert ChapterEvaluator.chapter_of(_candidate("JHN", 3)) == 3

    def test_chapter_of_missing_chapter_returns_none(self):
        assert ChapterEvaluator.chapter_of(_candidate("JHN", None)) is None

    def test_is_hit_true_on_exact_book_and_chapter_match(self):
        assert ChapterEvaluator.is_hit(_candidate("MRK", 4), "MRK", 4) is True

    def test_is_hit_false_when_book_matches_but_chapter_differs(self):
        assert ChapterEvaluator.is_hit(_candidate("MRK", 4), "MRK", 5) is False

    def test_is_hit_false_when_book_differs_but_chapter_matches(self):
        assert ChapterEvaluator.is_hit(_candidate("MRK", 4), "JHN", 4) is False

    def test_is_hit_false_when_chapter_absent(self):
        """A candidate with no verse_mapping.chapter (23.77% of the corpus,
        SPRINT18-C coverage) must miss, never silently pass."""
        assert ChapterEvaluator.is_hit(_candidate("MRK", None), "MRK", 4) is False

    def test_is_book_hit_ignores_chapter(self):
        assert ChapterEvaluator.is_book_hit(_candidate("MRK", 99), "MRK") is True


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


def _gold_file(tmp_path, queries):
    import json
    gold_file = tmp_path / "gold.json"
    gold_file.write_text(json.dumps({
        "metadata": {"dataset_version": "test"},
        "queries": queries,
    }), encoding="utf-8")
    return gold_file


def _patch_processor(monkeypatch, top1_book_id, top1_chapter):
    class _FakeCandidate:
        def __init__(self, book_id, chapter):
            self.metadata = {"verse_mapping": {"book_id": book_id, "chapter": chapter}}

    class _FakeResponse:
        top_k_results = [_FakeCandidate(top1_book_id, top1_chapter)]

    class _FakeProcessor:
        def __init__(self, engine):
            pass

        def process(self, question, query_id, k):
            return _FakeResponse()

    class _FakeEngine:
        def __init__(self, tsu_dataset_path):
            self.tsus = []

    import scripts.run_chapter_level_benchmark as mod
    monkeypatch.setattr(mod, "RetrievalEngine", _FakeEngine)
    monkeypatch.setattr(mod, "QueryProcessor", _FakeProcessor)
    return mod


class TestDiagnosticBreakdowns:
    def test_result_shape_has_diagnostic_keys(self, tmp_path, monkeypatch):
        gold_file = _gold_file(tmp_path, [
            {"id": "Q1", "question": "test", "expected_book_id": "JHN", "expected_chapter": 3,
             "language": "en", "intent": "simple_lookup"},
        ])
        mod = _patch_processor(monkeypatch, "JHN", 3)

        result = mod.run_benchmark(gold_path=str(gold_file))
        for key in ("per_book", "per_chapter", "per_language", "per_intent", "failed_queries",
                    "book_only_hits", "evidence_adjustment"):
            assert key in result
        assert result["metrics"]["precision_at_1"] == 1.0
        assert result["failed_queries"] == []
        assert result["book_only_hits"] == 0
        assert result["per_chapter"] == {"JHN-3": {"queries": 1, "precision_at_1": 1.0}}

    def test_evidence_adjustment_reflects_corpus_provenance(self, tmp_path, monkeypatch):
        """evidence_adjustment is a corpus-wide diagnostic (SPRINT19-C),
        independent of query results — computed from engine.tsus."""
        gold_file = _gold_file(tmp_path, [
            {"id": "Q1", "question": "test", "expected_book_id": "JHN", "expected_chapter": 3,
             "language": "en", "intent": "simple_lookup"},
        ])

        class _FakeCandidate:
            def __init__(self, book_id, chapter):
                self.metadata = {"verse_mapping": {"book_id": book_id, "chapter": chapter}}

        class _FakeResponse:
            top_k_results = [_FakeCandidate("JHN", 3)]

        class _FakeProcessor:
            def __init__(self, engine):
                pass

            def process(self, question, query_id, k):
                return _FakeResponse()

        class _FakeEngineWithProvenance:
            def __init__(self, tsu_dataset_path):
                self.tsus = [
                    {"tsu_id": "T1", "provenance": {"confidence": 0.8}},
                    {"tsu_id": "T2", "provenance": {"confidence": 0.4}},
                    {"tsu_id": "T3"},  # no provenance
                ]

        import scripts.run_chapter_level_benchmark as mod
        monkeypatch.setattr(mod, "RetrievalEngine", _FakeEngineWithProvenance)
        monkeypatch.setattr(mod, "QueryProcessor", _FakeProcessor)

        result = mod.run_benchmark(gold_path=str(gold_file))
        assert result["evidence_adjustment"] == {
            "records_with_confidence": 2,
            "missing_confidence": 1,
            "average_confidence": 0.6,
        }

    def test_book_only_hit_counted_and_not_a_top1_hit(self, tmp_path, monkeypatch):
        """Top1 candidate has the right book but the wrong chapter — this
        must miss precision_at_1 but be tallied under book_only_hits, the
        chapter-metadata-quality diagnostic HQ specifically asked for."""
        gold_file = _gold_file(tmp_path, [
            {"id": "Q1", "question": "test", "expected_book_id": "JHN", "expected_chapter": 3,
             "language": "en", "intent": "simple_lookup"},
        ])
        mod = _patch_processor(monkeypatch, "JHN", 99)

        result = mod.run_benchmark(gold_path=str(gold_file))
        assert result["metrics"]["precision_at_1"] == 0.0
        assert result["book_only_hits"] == 1
        assert len(result["failed_queries"]) == 1
        fq = result["failed_queries"][0]
        assert fq["book_correct"] is True
        assert fq["chapter_correct"] is False
        assert fq["expected_book_id"] == "JHN"
        assert fq["expected_chapter"] == 3
        assert fq["actual_book_id"] == "JHN"
        assert fq["actual_chapter"] == 99

    def test_complete_miss_not_counted_as_book_only_hit(self, tmp_path, monkeypatch):
        gold_file = _gold_file(tmp_path, [
            {"id": "Q1", "question": "test", "expected_book_id": "JHN", "expected_chapter": 3,
             "language": "en", "intent": "simple_lookup"},
        ])
        mod = _patch_processor(monkeypatch, "MRK", 4)

        result = mod.run_benchmark(gold_path=str(gold_file))
        assert result["book_only_hits"] == 0
        fq = result["failed_queries"][0]
        assert fq["book_correct"] is False
        assert fq["chapter_correct"] is False

    def test_candidate_without_chapter_metadata_is_a_miss_not_a_crash(self, tmp_path, monkeypatch):
        """A top1 candidate whose verse_mapping has no chapter key (the
        23.77% SPRINT18-C coverage gap) must resolve to a normal miss."""
        gold_file = _gold_file(tmp_path, [
            {"id": "Q1", "question": "test", "expected_book_id": "JHN", "expected_chapter": 3,
             "language": "en", "intent": "simple_lookup"},
        ])
        mod = _patch_processor(monkeypatch, "JHN", None)

        result = mod.run_benchmark(gold_path=str(gold_file))
        assert result["metrics"]["precision_at_1"] == 0.0
        assert result["book_only_hits"] == 1
        assert result["failed_queries"][0]["actual_chapter"] is None

    def test_query_missing_expected_chapter_is_skipped(self, tmp_path, monkeypatch):
        gold_file = _gold_file(tmp_path, [
            {"id": "Q1", "question": "test", "expected_book_id": "JHN",
             "language": "en", "intent": "simple_lookup"},
        ])
        mod = _patch_processor(monkeypatch, "JHN", 3)

        result = mod.run_benchmark(gold_path=str(gold_file))
        assert result["queries_evaluated"] == 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
