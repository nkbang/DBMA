"""Regression test — Book-level Gold Standard v1 generator (SPRINT17-Phase6B-1).

Guards the properties the design explicitly required:
  - expected_book_id only, expected_tsu_ids fully removed (fixes v3's
    tsu_id-rebuild fragility).
  - Only the 8 book_ids actually present in the current corpus.
  - No duplicate questions (fixes v3's single-theme degenerate pattern —
    diversity must be real, not templated-but-identical).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.generate_book_level_gold_standard import (
    generate_queries,
    validate,
    build_dataset,
    CORPUS_BOOKS,
)


class TestGenerateBookLevelGoldStandard:
    def test_no_expected_tsu_ids_field(self):
        queries = generate_queries()
        assert all("expected_tsu_ids" not in q for q in queries)

    def test_all_queries_have_expected_book_id(self):
        queries = generate_queries()
        assert all(q.get("expected_book_id") in CORPUS_BOOKS for q in queries)

    def test_no_duplicate_questions(self):
        queries = generate_queries()
        questions = [q["question"] for q in queries]
        assert len(questions) == len(set(questions))

    def test_every_corpus_book_covered(self):
        queries = generate_queries()
        covered = {q["expected_book_id"] for q in queries}
        assert covered == set(CORPUS_BOOKS.keys())

    def test_validate_passes_on_generated_queries(self):
        report = validate(generate_queries())
        assert report["passed"] is True
        assert report["issues"] == []

    def test_validate_flags_invalid_book_id(self):
        queries = [{"id": "X-001", "question": "test", "expected_book_id": "XYZ"}]
        report = validate(queries)
        assert report["passed"] is False
        assert any("invalid expected_book_id" in issue for issue in report["issues"])

    def test_validate_flags_duplicate_question(self):
        queries = [
            {"id": "A-001", "question": "same question", "expected_book_id": "MRK"},
            {"id": "A-002", "question": "same question", "expected_book_id": "JHN"},
        ]
        report = validate(queries)
        assert any("duplicate question" in issue for issue in report["issues"])

    def test_build_dataset_metadata_fields(self):
        queries = generate_queries()
        dataset = build_dataset(queries)
        required_metadata_fields = {
            "dataset_version", "generated_at", "source_dataset",
            "documents_covered", "books_covered", "query_count",
            "generation_policy",
        }
        assert required_metadata_fields.issubset(dataset["metadata"].keys())
        assert dataset["metadata"]["query_count"] == len(queries)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
