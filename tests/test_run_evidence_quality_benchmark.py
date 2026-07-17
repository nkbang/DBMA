"""Regression test — Evidence Quality Benchmark Runner (SPRINT19-D).

Guards the independence from Retrieval Accuracy judgment (no
expected_book_id/expected_chapter hit/miss anywhere in this runner —
SPRINT19-D Preflight's core architectural decision) and the three
metric groups: Evidence Coverage, Citation Reliability (missing
confidence excluded from the average, never treated as 0 — HQ
requirement), and Metadata Completeness (diagnostic breakdown, no
combined score).
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.run_evidence_quality_benchmark import run_benchmark


def _gold_file(tmp_path, questions):
    gold_file = tmp_path / "gold.json"
    queries = [
        {"id": f"Q{i}", "question": q, "expected_book_id": "JHN", "expected_chapter": 3,
         "language": "en", "intent": "simple_lookup"}
        for i, q in enumerate(questions)
    ]
    gold_file.write_text(json.dumps({"metadata": {"dataset_version": "test"}, "queries": queries}), encoding="utf-8")
    return gold_file


class _FakeCandidate:
    def __init__(self, book_id=None, chapter=None, verse_start=None, confidence=None):
        vm = {}
        if book_id is not None:
            vm["book_id"] = book_id
        if chapter is not None:
            vm["chapter"] = chapter
        if verse_start is not None:
            vm["verse_start"] = verse_start
        metadata = {"verse_mapping": vm}
        if confidence is not None:
            metadata["provenance"] = {"confidence": confidence}
        self.metadata = metadata


def _patch(monkeypatch, candidates):
    class _FakeResponse:
        top_k_results = candidates

    class _FakeProcessor:
        def __init__(self, engine):
            pass

        def process(self, question, query_id, k):
            return _FakeResponse()

    class _FakeEngine:
        def __init__(self, tsu_dataset_path):
            self.tsus = []

    import scripts.run_evidence_quality_benchmark as mod
    monkeypatch.setattr(mod, "RetrievalEngine", _FakeEngine)
    monkeypatch.setattr(mod, "QueryProcessor", _FakeProcessor)
    return mod


class TestRunBenchmarkBasics:
    def test_missing_gold_file_returns_error_dict(self):
        result = run_benchmark(gold_path="/nonexistent/path.json")
        assert "error" in result

    def test_empty_queries_returns_error_dict(self, tmp_path):
        gold_file = tmp_path / "empty_gold.json"
        gold_file.write_text(json.dumps({"metadata": {}, "queries": []}), encoding="utf-8")
        result = run_benchmark(gold_path=str(gold_file))
        assert "error" in result

    def test_no_hit_miss_judgment_present(self, tmp_path, monkeypatch):
        """Core SPRINT19-D architectural decision: this runner never
        performs expected_book_id/expected_chapter hit/miss judgment —
        that's the Retrieval Benchmark's job, kept fully separate."""
        gold_file = _gold_file(tmp_path, ["test question"])
        mod = _patch(monkeypatch, [_FakeCandidate(book_id="JHN", chapter=3, confidence=0.9)])
        result = mod.run_benchmark(gold_path=str(gold_file))
        for forbidden_key in ("precision_at_1", "mrr", "hit_at_1", "failed_queries", "book_only_hits"):
            assert forbidden_key not in result
            assert forbidden_key not in result.get("evidence_metrics", {})


class TestConfidencePresentCandidate:
    def test_confidence_counted_in_reliability_average(self, tmp_path, monkeypatch):
        gold_file = _gold_file(tmp_path, ["q1"])
        mod = _patch(monkeypatch, [_FakeCandidate(book_id="JHN", chapter=3, confidence=0.8)])
        result = mod.run_benchmark(gold_path=str(gold_file))
        assert result["evidence_metrics"]["citation_reliability"]["at_1"] == 0.8
        assert result["diagnostics"]["present_confidence_count"] == 1
        assert result["diagnostics"]["missing_confidence_count"] == 0


class TestConfidenceMissingCandidate:
    def test_missing_confidence_excluded_from_average_not_zeroed(self, tmp_path, monkeypatch):
        """A candidate with no provenance must not drag the average down
        to 0 — it's excluded entirely and counted separately (HQ
        requirement: "confidence 없는 candidate: 0으로 처리하지 말 것")."""
        gold_file = _gold_file(tmp_path, ["q1"])
        mod = _patch(monkeypatch, [
            _FakeCandidate(book_id="JHN", chapter=3, confidence=0.8),
            _FakeCandidate(book_id="JHN", chapter=None, confidence=None),
        ])
        result = mod.run_benchmark(gold_path=str(gold_file))
        # Average over present-only: 0.8, not (0.8+0)/2 = 0.4
        assert result["evidence_metrics"]["citation_reliability"]["at_10"] == 0.8
        assert result["diagnostics"]["missing_confidence_count"] == 1
        assert result["diagnostics"]["present_confidence_count"] == 1


class TestChapterMissingCandidate:
    def test_chapter_missing_candidate_excluded_from_coverage_hit(self, tmp_path, monkeypatch):
        gold_file = _gold_file(tmp_path, ["q1"])
        mod = _patch(monkeypatch, [
            _FakeCandidate(book_id="JHN", chapter=3),
            _FakeCandidate(book_id="JHN", chapter=None),
        ])
        result = mod.run_benchmark(gold_path=str(gold_file))
        # 1 of 2 candidates has chapter -> coverage_at_10 = 0.5
        assert result["evidence_metrics"]["coverage"]["at_10"] == 0.5


class TestTopKAverageCalculation:
    def test_coverage_and_reliability_bucketed_by_k(self, tmp_path, monkeypatch):
        """5 candidates: only the first has chapter+confidence. at_1
        should reflect only that candidate; at_5/at_10 should dilute."""
        candidates = [_FakeCandidate(book_id="JHN", chapter=3, confidence=1.0)]
        candidates += [_FakeCandidate(book_id="JHN") for _ in range(4)]
        gold_file = _gold_file(tmp_path, ["q1"])
        mod = _patch(monkeypatch, candidates)
        result = mod.run_benchmark(gold_path=str(gold_file))
        cov = result["evidence_metrics"]["coverage"]
        assert cov["at_1"] == 1.0
        assert cov["at_5"] == 0.2
        assert cov["at_10"] == 0.2
        rel = result["evidence_metrics"]["citation_reliability"]
        assert rel["at_1"] == 1.0
        assert rel["at_5"] == 1.0  # only 1 candidate has confidence, average over present-only


class TestMetadataCoverageCalculation:
    def test_metadata_completeness_breakdown(self, tmp_path, monkeypatch):
        gold_file = _gold_file(tmp_path, ["q1"])
        mod = _patch(monkeypatch, [
            _FakeCandidate(book_id="JHN", chapter=3, verse_start=16, confidence=0.9),
            _FakeCandidate(book_id="JHN", chapter=None),
        ])
        result = mod.run_benchmark(gold_path=str(gold_file))
        mc = result["evidence_metrics"]["metadata_completeness"]
        assert mc["book_id"] == 1.0     # both candidates have book_id
        assert mc["chapter"] == 0.5     # only 1 of 2
        assert mc["verse_start"] == 0.5
        assert mc["provenance"] == 0.5

    def test_metadata_completeness_is_diagnostic_only_no_combined_score(self, tmp_path, monkeypatch):
        """No single combined "Evidence Trust Score" key anywhere in the
        output — HQ explicitly prohibited metric combination."""
        gold_file = _gold_file(tmp_path, ["q1"])
        mod = _patch(monkeypatch, [_FakeCandidate(book_id="JHN", chapter=3, confidence=0.9)])
        result = mod.run_benchmark(gold_path=str(gold_file))
        forbidden_terms = ("trust_score", "evidence_trust", "combined_score", "overall_score")
        result_str = json.dumps(result).lower()
        for term in forbidden_terms:
            assert term not in result_str


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
