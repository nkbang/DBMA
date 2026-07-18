"""Regression test — scripts/sample_chapter_gold.py::stratified_sample()
(SPRINT21-E). Verifies reproducibility (fixed seed) and per-book
stratification (proportional coverage, no systematic-sampling bias).
"""

import sys
import os
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.sample_chapter_gold import stratified_sample


def _make_queries(counts: dict[str, int]) -> list[dict]:
    queries = []
    for book, n in counts.items():
        for i in range(n):
            queries.append({"id": f"{book}-{i:03d}", "expected_book_id": book})
    return queries


class TestStratifiedSample:
    def test_reproducible_with_same_seed(self):
        queries = _make_queries({"2KI": 300, "JHN": 252, "1CO": 84})
        a = stratified_sample(queries, fraction=0.1, seed=42)
        b = stratified_sample(queries, fraction=0.1, seed=42)
        assert [q["id"] for q in a] == [q["id"] for q in b]

    def test_different_seed_can_differ(self):
        queries = _make_queries({"2KI": 300, "JHN": 252})
        a = stratified_sample(queries, fraction=0.1, seed=42)
        b = stratified_sample(queries, fraction=0.1, seed=7)
        assert [q["id"] for q in a] != [q["id"] for q in b]

    def test_book_distribution_proportional(self):
        counts = {"2KI": 300, "2CH": 300, "JHN": 252, "MRK": 192, "ACT": 168, "ROM": 108, "2CO": 96, "1CO": 84}
        queries = _make_queries(counts)
        sample = stratified_sample(queries, fraction=0.1, seed=42)
        sample_counts = Counter(q["expected_book_id"] for q in sample)
        for book, total in counts.items():
            expected = round(total * 0.1)
            assert abs(sample_counts[book] - expected) <= 1, f"{book}: {sample_counts[book]} vs ~{expected}"

    def test_every_book_represented_even_when_small(self):
        queries = _make_queries({"2KI": 300, "OBA": 3})  # tiny group
        sample = stratified_sample(queries, fraction=0.1, seed=42)
        assert "OBA" in {q["expected_book_id"] for q in sample}  # max(1, round(...)) guarantees >=1

    def test_fraction_roughly_matches_total_size(self):
        queries = _make_queries({"2KI": 300, "2CH": 300, "JHN": 252, "MRK": 192})
        sample = stratified_sample(queries, fraction=0.1, seed=42)
        assert 90 <= len(sample) <= 110  # ~10% of 1044, tolerant of per-book rounding


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
