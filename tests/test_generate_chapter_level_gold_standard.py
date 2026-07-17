"""Regression test — Chapter-level Gold Standard v1 generator (SPRINT18-D).

Guards the two filters that stand between SPRINT18-C's raw
verse_mapping.chapter data and a trustworthy Gold query (Phase18-D
Preflight findings):
  1. Canonical chapter range validation (rejects index/appendix-page
     contamination like 2 Kings chapter=748).
  2. Density threshold >= 3 records (rejects single-chunk, possibly
     noisy ground truth).
And the combinatorial generation (book x chapter x intent x language)
that keeps chapter-level Gold from repeating v3's single-theme collapse.
"""

import sys
import os
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.generate_chapter_level_gold_standard import (
    CANONICAL_MAX_CHAPTER,
    MIN_DENSITY,
    select_chapters,
    generate_queries,
    validate,
    build_dataset,
)


class TestSelectChapters:
    def test_out_of_canonical_range_rejected(self):
        density = Counter({("2KI", 748): 5, ("2KI", 1): 10})
        report = select_chapters(density)
        assert ("2KI", 748) not in report["selected_pairs"]
        assert ("2KI", 1) in report["selected_pairs"]
        assert report["canonical_rejected_count"] == 1

    def test_below_density_threshold_rejected(self):
        density = Counter({("JHN", 5): MIN_DENSITY - 1, ("JHN", 6): MIN_DENSITY})
        report = select_chapters(density)
        assert ("JHN", 5) not in report["selected_pairs"]
        assert ("JHN", 6) in report["selected_pairs"]
        assert report["density_rejected_count"] == 1

    def test_book_not_in_corpus_excluded(self):
        density = Counter({("GEN", 1): 10})
        report = select_chapters(density)
        assert report["selected_pairs"] == []

    def test_chapter_zero_or_negative_rejected(self):
        density = Counter({("ROM", 0): 10, ("ROM", -1): 10})
        report = select_chapters(density)
        assert report["selected_pairs"] == []


class TestGenerateQueries:
    def test_deterministic(self):
        pairs = [("JHN", 3), ("ROM", 8)]
        q1 = generate_queries(pairs)
        q2 = generate_queries(pairs)
        assert q1 == q2

    def test_query_count_matches_combinatorics(self):
        pairs = [("JHN", 3)]
        queries = generate_queries(pairs)
        assert len(queries) == 12  # 6 intents x 2 languages

    def test_each_query_has_expected_chapter_field(self):
        queries = generate_queries([("MRK", 4)])
        assert all(q["expected_chapter"] == 4 for q in queries)
        assert all(q["expected_book_id"] == "MRK" for q in queries)


class TestValidate:
    def test_valid_queries_pass(self):
        queries = generate_queries([("JHN", 3)])
        report = validate(queries)
        assert report["passed"] is True
        assert report["issues"] == []

    def test_out_of_range_chapter_flagged(self):
        queries = [{
            "id": "X-001", "question": "test", "expected_book_id": "JHN",
            "expected_chapter": 999, "language": "ko", "intent": "simple_lookup",
        }]
        report = validate(queries)
        assert report["passed"] is False
        assert any("out of canonical range" in issue for issue in report["issues"])

    def test_no_duplicate_questions_across_full_generation(self):
        """Sanity check against the real degenerate pattern found in v3:
        every (book, chapter, intent, language) combination must produce
        a genuinely distinct question string."""
        pairs = [("JHN", 3), ("JHN", 4), ("MRK", 3)]
        queries = generate_queries(pairs)
        questions = [q["question"] for q in queries]
        assert len(questions) == len(set(questions))


class TestBuildDataset:
    def test_metadata_includes_evaluation_policy(self):
        queries = generate_queries([("JHN", 3)])
        selection_report = {
            "candidate_pairs_count": 1, "canonical_valid_count": 1,
            "canonical_rejected_count": 0, "density_valid_count": 1,
            "density_rejected_count": 0,
        }
        dataset = build_dataset(queries, selection_report)
        assert "evaluation_policy" in dataset["metadata"]
        assert "exact" in dataset["metadata"]["evaluation_policy"].lower()

    def test_canonical_max_chapter_recorded(self):
        queries = generate_queries([("JHN", 3)])
        selection_report = {
            "candidate_pairs_count": 1, "canonical_valid_count": 1,
            "canonical_rejected_count": 0, "density_valid_count": 1,
            "density_rejected_count": 0,
        }
        dataset = build_dataset(queries, selection_report)
        assert dataset["metadata"]["canonical_max_chapter"] == CANONICAL_MAX_CHAPTER


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
