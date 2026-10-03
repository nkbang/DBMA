"""tests/test_merge_safety_registry_comparison.py - Registry comparison safety tests.

Tests for NAE-MERGE-PRODUCTION-IDENTITY-P3 (Rev.1 + Rev.2 + Rev.3):
  T1: EXCLUDED_FROM_COMPARISON contains exactly {excluded_at, exclude_reason}
  T2: compute_registry_preimage_hash excludes only the allowlist fields
  T3: compare_registry_entries detects all non-excluded field differences
  T4: pipeline_state and last_processed_at ARE comparison targets
  T5: pipeline_flags sub-fields ARE comparison targets
  T6: corpus_membership is a comparison target
  T7: ingest_status is a comparison target
  T8: chunk_count is a comparison target
  T9: Idempotent merge does not change registry entries
  T10: Missing field in incoming is detected
  T11: Extra field in incoming is detected
  T12: Nested dict comparison (pipeline_flags) works recursively
  T13: List comparison works correctly
  T14: Hash differs when non-excluded field changes
  T15: Hash is identical when only excluded fields change
"""

import json
import hashlib
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.merge_nae_corpus import (
    EXCLUDED_FROM_COMPARISON,
    compute_registry_preimage_hash,
    compare_registry_entries,
)


def _make_entry(**overrides) -> dict:
    base = {
        "document_id": "test_doc",
        "source_file": "test.jsonl",
        "title": "Test Title",
        "author": "Test Author",
        "status": "processed",
        "chunk_count": 42,
        "language": "en",
        "source_type": "nae_canonical",
        "doc_type": "shinhak",
        "ingest_status": "PROCESSED",
        "pipeline_state": "INDEXED",
        "created_at": "2026-10-01T00:00:00",
        "last_processed_at": "2026-10-01T01:00:00",
        "last_content_hash": "abc123",
        "corpus_membership": "default",
        "pipeline_flags": {
            "ingested": True,
            "copied": True,
            "extracted": True,
            "cleaned": True,
            "chunked": True,
            "output_generated": True,
            "verified": True,
        },
        "excluded_at": "2026-10-01T02:00:00",
        "exclude_reason": "test exclusion",
    }
    base.update(overrides)
    return base


def _make_entry_no_excluded(**overrides) -> dict:
    base = {
        "document_id": "test_doc",
        "source_file": "test.jsonl",
        "title": "Test Title",
        "author": "Test Author",
        "status": "processed",
        "chunk_count": 42,
        "language": "en",
        "source_type": "nae_canonical",
        "doc_type": "shinhak",
        "ingest_status": "PROCESSED",
        "pipeline_state": "INDEXED",
        "created_at": "2026-10-01T00:00:00",
        "last_processed_at": "2026-10-01T01:00:00",
        "last_content_hash": "abc123",
        "corpus_membership": "default",
        "pipeline_flags": {
            "ingested": True,
            "copied": True,
            "extracted": True,
            "cleaned": True,
            "chunked": True,
            "output_generated": True,
            "verified": True,
        },
    }
    base.update(overrides)
    return base


class TestT1ExcludedFields:
    def test_exactly_two_fields(self):
        assert len(EXCLUDED_FROM_COMPARISON) == 2

    def test_contains_excluded_at(self):
        assert "excluded_at" in EXCLUDED_FROM_COMPARISON

    def test_contains_exclude_reason(self):
        assert "exclude_reason" in EXCLUDED_FROM_COMPARISON

    def test_no_extra_fields(self):
        expected = frozenset({"excluded_at", "exclude_reason"})
        assert EXCLUDED_FROM_COMPARISON == expected


class TestT2PreimageHashExcludesAllowlist:
    def test_hash_excludes_excluded_at(self):
        e1 = _make_entry()
        e2 = _make_entry(excluded_at="2026-10-02T00:00:00")
        assert compute_registry_preimage_hash(e1) == compute_registry_preimage_hash(e2)

    def test_hash_excludes_exclude_reason(self):
        e1 = _make_entry()
        e2 = _make_entry(exclude_reason="different reason")
        assert compute_registry_preimage_hash(e1) == compute_registry_preimage_hash(e2)

    def test_hash_differs_when_non_excluded_field_changes(self):
        e1 = _make_entry()
        e2 = _make_entry(pipeline_state="QUEUED")
        assert compute_registry_preimage_hash(e1) != compute_registry_preimage_hash(e2)


class TestT3CompareDetectsAllDifferences:
    def test_identical_entries_are_equal(self):
        entry = _make_entry()
        equal, diffs = compare_registry_entries(entry, entry)
        assert equal is True

    def test_title_difference_detected(self):
        e1 = _make_entry()
        e2 = _make_entry(title="Different Title")
        equal, diffs = compare_registry_entries(e1, e2)
        assert equal is False
        assert any("title:" in d for d in diffs)

    def test_source_type_difference_detected(self):
        e1 = _make_entry()
        e2 = _make_entry(source_type="external")
        equal, diffs = compare_registry_entries(e1, e2)
        assert equal is False
        assert any("source_type:" in d for d in diffs)


class TestT4PipelineFieldsAreComparisonTargets:
    def test_pipeline_state_is_comparison_target(self):
        e1 = _make_entry_no_excluded()
        e2 = _make_entry_no_excluded(pipeline_state="QUEUED")
        equal, diffs = compare_registry_entries(e1, e2)
        assert equal is False
        assert any("pipeline_state:" in d for d in diffs)

    def test_last_processed_at_is_comparison_target(self):
        e1 = _make_entry_no_excluded()
        e2 = _make_entry_no_excluded(last_processed_at="2026-10-02T00:00:00")
        equal, diffs = compare_registry_entries(e1, e2)
        assert equal is False
        assert any("last_processed_at:" in d for d in diffs)

    def test_pipeline_state_hash_differs(self):
        e1 = _make_entry_no_excluded()
        e2 = _make_entry_no_excluded(pipeline_state="QUEUED")
        assert compute_registry_preimage_hash(e1) != compute_registry_preimage_hash(e2)


class TestT5PipelineFlagsAreComparisonTargets:
    def test_pipeline_flags_ingested_change_detected(self):
        e1 = _make_entry_no_excluded()
        new_flags = dict(e1["pipeline_flags"])
        new_flags["ingested"] = False
        e2 = {**e1, "pipeline_flags": new_flags}
        equal, diffs = compare_registry_entries(e1, e2)
        assert equal is False
        assert any("pipeline_flags.ingested:" in d for d in diffs)

    def test_pipeline_flags_hash_differs(self):
        e1 = _make_entry_no_excluded()
        new_flags = dict(e1["pipeline_flags"])
        new_flags["verified"] = False
        e2 = {**e1, "pipeline_flags": new_flags}
        assert compute_registry_preimage_hash(e1) != compute_registry_preimage_hash(e2)


class TestT6CorpusMembershipIsComparisonTarget:
    def test_corpus_membership_change_detected(self):
        e1 = _make_entry_no_excluded()
        e2 = _make_entry_no_excluded(corpus_membership="nae_canonical")
        equal, diffs = compare_registry_entries(e1, e2)
        assert equal is False
        assert any("corpus_membership:" in d for d in diffs)


class TestT7IngestStatusIsComparisonTarget:
    def test_ingest_status_change_detected(self):
        e1 = _make_entry_no_excluded()
        e2 = _make_entry_no_excluded(ingest_status="FAILED")
        equal, diffs = compare_registry_entries(e1, e2)
        assert equal is False
        assert any("ingest_status:" in d for d in diffs)


class TestT8ChunkCountIsComparisonTarget:
    def test_chunk_count_change_detected(self):
        e1 = _make_entry_no_excluded()
        e2 = _make_entry_no_excluded(chunk_count=99)
        equal, diffs = compare_registry_entries(e1, e2)
        assert equal is False
        assert any("chunk_count:" in d for d in diffs)


class TestT9IdempotentMerge:
    def test_identical_entries_pass_comparison(self):
        entry = _make_entry()
        equal, diffs = compare_registry_entries(entry, entry)
        assert equal is True


class TestT10MissingFieldInIncoming:
    def test_missing_title_detected(self):
        e1 = _make_entry_no_excluded()
        e2 = {k: v for k, v in e1.items() if k != "title"}
        equal, diffs = compare_registry_entries(e1, e2)
        assert equal is False
        assert any("missing_in_incoming: title" in d for d in diffs)


class TestT11ExtraFieldInIncoming:
    def test_extra_field_detected(self):
        e1 = _make_entry_no_excluded()
        e2 = {**e1, "extra_custom_field": "some_value"}
        equal, diffs = compare_registry_entries(e1, e2)
        assert equal is False
        assert any("missing_in_existing: extra_custom_field" in d for d in diffs)


class TestT12NestedDictComparison:
    def test_nested_flag_change_detected(self):
        e1 = _make_entry_no_excluded()
        new_flags = dict(e1["pipeline_flags"])
        new_flags["verified"] = False
        e2 = {**e1, "pipeline_flags": new_flags}
        equal, diffs = compare_registry_entries(e1, e2)
        assert equal is False
        assert any("pipeline_flags.verified:" in d for d in diffs)

    def test_nested_flag_addition_detected(self):
        e1 = _make_entry_no_excluded()
        new_flags = dict(e1["pipeline_flags"])
        new_flags["new_flag"] = True
        e2 = {**e1, "pipeline_flags": new_flags}
        equal, diffs = compare_registry_entries(e1, e2)
        assert equal is False
        assert any("pipeline_flags.missing_in_existing: new_flag" in d for d in diffs)


class TestT13ListComparison:
    def test_list_difference_detected(self):
        e1 = _make_entry_no_excluded(doctrine_category=["christology", "soteriology"])
        e2 = _make_entry_no_excluded(doctrine_category=["christology"])
        equal, diffs = compare_registry_entries(e1, e2)
        assert equal is False
        assert any("doctrine_category:" in d for d in diffs)

    def test_identical_lists_pass(self):
        e1 = _make_entry_no_excluded(doctrine_category=["christology", "soteriology"])
        e2 = _make_entry_no_excluded(doctrine_category=["christology", "soteriology"])
        equal, diffs = compare_registry_entries(e1, e2)
        assert equal is True


class TestT14HashDiffersOnNonExcludedChange:
    def test_title_change_changes_hash(self):
        e1 = _make_entry_no_excluded()
        e2 = _make_entry_no_excluded(title="Different Title")
        assert compute_registry_preimage_hash(e1) != compute_registry_preimage_hash(e2)

    def test_ingest_status_change_changes_hash(self):
        e1 = _make_entry_no_excluded()
        e2 = _make_entry_no_excluded(ingest_status="FAILED")
        assert compute_registry_preimage_hash(e1) != compute_registry_preimage_hash(e2)

    def test_chunk_count_change_changes_hash(self):
        e1 = _make_entry_no_excluded()
        e2 = _make_entry_no_excluded(chunk_count=99)
        assert compute_registry_preimage_hash(e1) != compute_registry_preimage_hash(e2)


class TestT15HashIdenticalOnExcludedChange:
    def test_excluded_at_change_does_not_change_hash(self):
        e1 = _make_entry()
        e2 = _make_entry(excluded_at="2026-10-02T00:00:00")
        assert compute_registry_preimage_hash(e1) == compute_registry_preimage_hash(e2)

    def test_exclude_reason_change_does_not_change_hash(self):
        e1 = _make_entry()
        e2 = _make_entry(exclude_reason="different reason")
        assert compute_registry_preimage_hash(e1) == compute_registry_preimage_hash(e2)

    def test_both_excluded_fields_change_does_not_change_hash(self):
        e1 = _make_entry()
        e2 = _make_entry(excluded_at="2026-10-02T00:00:00", exclude_reason="different reason")
        assert compute_registry_preimage_hash(e1) == compute_registry_preimage_hash(e2)


class TestHashStability:
    def test_same_input_produces_same_hash(self):
        entry = _make_entry_no_excluded()
        h1 = compute_registry_preimage_hash(entry)
        h2 = compute_registry_preimage_hash(entry)
        assert h1 == h2

    def test_hash_is_hex_string(self):
        entry = _make_entry_no_excluded()
        h = compute_registry_preimage_hash(entry)
        assert isinstance(h, str)
        assert len(h) == 64
        int(h, 16)


class TestCompareEdgeCases:
    def test_empty_dicts_are_equal(self):
        equal, diffs = compare_registry_entries({}, {})
        assert equal is True
        assert diffs == []

    def test_one_empty_dict_is_not_equal(self):
        e1 = {"document_id": "test"}
        equal, diffs = compare_registry_entries(e1, {})
        assert equal is False
        assert any("missing_in_incoming" in d for d in diffs)

    def test_excluded_fields_ignored_even_when_missing(self):
        e1 = {"document_id": "test_doc"}
        e2 = {"document_id": "test_doc"}
        equal, diffs = compare_registry_entries(e1, e2)
        assert equal is True

    def test_excluded_fields_ignored_even_when_different(self):
        e1 = {"document_id": "test_doc", "excluded_at": "2026-10-01"}
        e2 = {"document_id": "test_doc", "excluded_at": "2026-10-02"}
        equal, diffs = compare_registry_entries(e1, e2)
        assert equal is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
