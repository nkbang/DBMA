"""Tests for NAE/pipeline/tsu/worker (Phase 3).

Tests state machine transitions, exception queue, and worker logic.
Does NOT call LLM — uses mock data for state/queue validation.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

# Ensure NAE is on path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".."))

from NAE.pipeline.tsu.worker.state import (
    TSUExtractionState,
    TSUExtractionStateStore,
    VALID_TRANSITIONS,
    validate_transition,
)
from NAE.pipeline.tsu.worker.queue import TSUExtractionExceptionQueue
from NAE.pipeline.tsu.worker.worker import (
    WorkerResult,
    BatchResult,
    process_candidate,
    process_batch,
    retry_failed,
    get_queue_depth,
    _classify_confidence,
)


# --- State Machine Tests ---

class TestTSUExtractionStateStore:
    def test_create_empty(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = TSUExtractionStateStore(path)
            assert store.get_state("cand-1") is None

    def test_set_and_get_state(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = TSUExtractionStateStore(path)
            store.set_state("cand-1", TSUExtractionState.READY)
            assert store.get_state("cand-1") == TSUExtractionState.READY

    def test_transition_ready_to_processing(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = TSUExtractionStateStore(path)
            store.set_state("cand-1", TSUExtractionState.READY)
            ok, msg = store.set_state(
                "cand-1", TSUExtractionState.PROCESSING,
                from_state=TSUExtractionState.READY,
            )
            assert ok
            assert store.get_state("cand-1") == TSUExtractionState.PROCESSING

    def test_transition_processing_to_extracted(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = TSUExtractionStateStore(path)
            store.set_state("cand-1", TSUExtractionState.PROCESSING)
            ok, msg = store.set_state(
                "cand-1", TSUExtractionState.EXTRACTED,
                from_state=TSUExtractionState.PROCESSING,
            )
            assert ok

    def test_transition_processing_to_failed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = TSUExtractionStateStore(path)
            store.set_state("cand-1", TSUExtractionState.PROCESSING)
            ok, msg = store.set_state(
                "cand-1", TSUExtractionState.FAILED,
                from_state=TSUExtractionState.PROCESSING,
            )
            assert ok

    def test_transition_extracted_to_confidence_classified(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = TSUExtractionStateStore(path)
            store.set_state("cand-1", TSUExtractionState.EXTRACTED)
            ok, msg = store.set_state(
                "cand-1", TSUExtractionState.CONFIDENCE_CLASSIFIED,
                from_state=TSUExtractionState.EXTRACTED,
            )
            assert ok

    def test_terminal_no_further_transitions(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = TSUExtractionStateStore(path)
            store.set_state("cand-1", TSUExtractionState.CONFIDENCE_CLASSIFIED)
            ok, msg = store.set_state(
                "cand-1", TSUExtractionState.PROCESSING,
                from_state=TSUExtractionState.CONFIDENCE_CLASSIFIED,
            )
            assert not ok

    def test_failed_to_ready_manual_retry(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = TSUExtractionStateStore(path)
            store.set_state("cand-1", TSUExtractionState.FAILED)
            ok, msg = store.reset_failed_to_ready("cand-1")
            assert ok
            assert store.get_state("cand-1") == TSUExtractionState.READY

    def test_reset_non_failed_fails(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = TSUExtractionStateStore(path)
            store.set_state("cand-1", TSUExtractionState.READY)
            ok, msg = store.reset_failed_to_ready("cand-1")
            assert not ok

    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store1 = TSUExtractionStateStore(path)
            store1.set_state("cand-1", TSUExtractionState.READY)
            store1.set_state("cand-2", TSUExtractionState.FAILED)
            store1.save()

            store2 = TSUExtractionStateStore(path)
            assert store2.get_state("cand-1") == TSUExtractionState.READY
            assert store2.get_state("cand-2") == TSUExtractionState.FAILED

    def test_summary(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = TSUExtractionStateStore(path)
            store.set_state("cand-1", TSUExtractionState.READY)
            store.set_state("cand-2", TSUExtractionState.FAILED)
            store.set_state("cand-3", TSUExtractionState.READY)
            summary = store.summary()
            assert summary.get(TSUExtractionState.READY.value, 0) == 2
            assert summary.get(TSUExtractionState.FAILED.value, 0) == 1

    def test_entries_by_state(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = TSUExtractionStateStore(path)
            store.set_state("cand-1", TSUExtractionState.READY)
            store.set_state("cand-2", TSUExtractionState.FAILED)
            ready = store.entries_by_state(TSUExtractionState.READY)
            assert "cand-1" in ready
            assert "cand-2" not in ready

    def test_idempotent_transition(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = TSUExtractionStateStore(path)
            store.set_state("cand-1", TSUExtractionState.READY)
            ok, msg = store.set_state(
                "cand-1", TSUExtractionState.READY,
                from_state=TSUExtractionState.READY,
            )
            assert ok  # idempotent

    def test_invalid_transition(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = TSUExtractionStateStore(path)
            store.set_state("cand-1", TSUExtractionState.READY)
            ok, msg = store.set_state(
                "cand-1", TSUExtractionState.EXTRACTED,
                from_state=TSUExtractionState.READY,
            )
            assert not ok


# --- Exception Queue Tests ---

class TestTSUExtractionExceptionQueue:
    def test_record_and_entries(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "queue.json"
            q = TSUExtractionExceptionQueue(path)
            q.record("cand-1", "LLM_ERROR", "timeout", "FAILED")
            entries = q.entries()
            assert len(entries) == 1
            assert entries[0]["candidate_id"] == "cand-1"
            assert entries[0]["error_type"] == "LLM_ERROR"

    def test_summary(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "queue.json"
            q = TSUExtractionExceptionQueue(path)
            q.record("cand-1", "LLM_ERROR", "timeout", "FAILED")
            q.record("cand-2", "PARSE_ERROR", "invalid JSON", "FAILED")
            summary = q.summary()
            assert summary.get("LLM_ERROR", 0) == 1
            assert summary.get("PARSE_ERROR", 0) == 1

    def test_clear(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "queue.json"
            q = TSUExtractionExceptionQueue(path)
            q.record("cand-1", "LLM_ERROR", "timeout", "FAILED")
            q.clear()
            assert len(q.entries()) == 0


# --- Confidence Classification Tests ---

class TestClassifyConfidence:
    def test_high_confidence(self):
        record = {"confidence": 0.95}
        score, label = _classify_confidence(record)
        assert label == "HIGH"
        assert score == 0.95

    def test_medium_confidence(self):
        record = {"confidence": 0.85}
        score, label = _classify_confidence(record)
        assert label == "MEDIUM"
        assert score == 0.85

    def test_low_confidence(self):
        record = {"confidence": 0.7}
        score, label = _classify_confidence(record)
        assert label == "LOW"
        assert score == 0.7

    def test_string_confidence(self):
        record = {"confidence": "0.92"}
        score, label = _classify_confidence(record)
        assert label == "HIGH"
        assert score == 0.92

    def test_missing_confidence(self):
        record = {}
        score, label = _classify_confidence(record)
        assert label == "LOW"
        assert score == 0.0


# --- Queue Depth Tests ---

class TestGetQueueDepth:
    def test_empty_queue(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = TSUExtractionStateStore(path)
            depth = get_queue_depth(store)
            assert depth["READY"] == 0
            assert depth["FAILED"] == 0

    def test_non_empty_queue(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = TSUExtractionStateStore(path)
            store.set_state("cand-1", TSUExtractionState.READY)
            store.set_state("cand-2", TSUExtractionState.FAILED)
            depth = get_queue_depth(store)
            assert depth["READY"] == 1
            assert depth["FAILED"] == 1


# --- Worker Logic Tests (without LLM) ---

class TestProcessCandidate:
    def test_non_claim_candidate(self):
        """Test that non-claim candidates are classified as CONFIDENCE_CLASSIFIED
        without calling LLM (mocked via claim.extract_claim)."""
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            queue_path = Path(td) / "queue.json"

            # Mock claim.extract_claim to return is_claim=False
            import unittest.mock as mock
            mock_result = {
                "is_claim": False,
                "reason": "not_a_claim",
                "confidence": 0.0,
            }

            import unittest.mock as mock_module
            from NAE.pipeline.tsu import claim as claim_mod
            with mock_module.patch.object(claim_mod, "extract_claim", return_value=mock_result):
                result = process_candidate(
                    candidate_id="cand-1",
                    candidate_text="This is a test sentence that should not be a claim.",
                    state_store=TSUExtractionStateStore(state_path),
                    exception_queue=TSUExtractionExceptionQueue(queue_path),
                )

            assert result.state == TSUExtractionState.CONFIDENCE_CLASSIFIED
            assert result.tsu_record is None
            assert result.error_type is None


# --- Batch Result Tests ---

class TestBatchResult:
    def test_success_rate(self):
        br = BatchResult(total=10, extracted=8, failed=2)
        assert br.success_rate == 0.8

    def test_empty_batch(self):
        br = BatchResult(total=0, extracted=0, failed=0)
        assert br.success_rate == 0.0
