"""Tests for worker/loader.py — enqueue_from_canonical."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from NAE.pipeline.tsu.worker.loader import enqueue_from_canonical, _make_candidate_id
from NAE.pipeline.tsu.worker.state import TSUExtractionStateStore, TSUExtractionState


class TestMakeCandidateId:
    def test_deterministic(self):
        """Same inputs always produce the same candidate_id."""
        cid1 = _make_candidate_id("test_id", 1, 0, 0)
        cid2 = _make_candidate_id("test_id", 1, 0, 0)
        assert cid1 == cid2

    def test_different_inputs_produce_different_ids(self):
        """Different inputs produce different candidate_ids."""
        cids = set()
        for page in range(5):
            for para in range(3):
                for sent in range(2):
                    cids.add(_make_candidate_id("test", page, para, sent))
        assert len(cids) == 30

    def test_format(self):
        """candidate_id starts with 'cand-' and has 16 hex chars."""
        cid = _make_candidate_id("test", 1, 0, 0)
        assert cid.startswith("cand-")
        assert len(cid) == 21  # "cand-" (5) + 16 hex


class TestEnqueueFromCanonical:
    def test_enqueues_new_candidates(self):
        """New candidates are added as READY."""
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            store = TSUExtractionStateStore(state_path)

            count = enqueue_from_canonical(
                "Fuller_Complete_Works_Vol02", store, max_candidates=3
            )
            assert count == 3
            assert store.summary()["READY"] == 3

    def test_idempotent_skips_existing(self):
        """Already-present candidate_ids are skipped."""
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            store = TSUExtractionStateStore(state_path)

            # First enqueue
            count1 = enqueue_from_canonical(
                "Fuller_Complete_Works_Vol02", store, max_candidates=3
            )
            assert count1 == 3

            # Second enqueue (same identifier) — should be idempotent
            count2 = enqueue_from_canonical(
                "Fuller_Complete_Works_Vol02", store, max_candidates=3
            )
            assert count2 == 0  # No new candidates added

    def test_max_candidates_limits(self):
        """max_candidates limits the number of enqueued candidates."""
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            store = TSUExtractionStateStore(state_path)

            count = enqueue_from_canonical(
                "Fuller_Complete_Works_Vol02", store, max_candidates=1
            )
            assert count == 1
            assert store.summary()["READY"] == 1

    def test_no_candidates_returns_zero(self):
        """Non-existent identifier returns 0."""
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            store = TSUExtractionStateStore(state_path)

            count = enqueue_from_canonical(
                "NonExistentIdentifier", store, max_candidates=10
            )
            assert count == 0

    def test_metadata_contains_source_info(self):
        """Enqueued candidates have source metadata."""
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            store = TSUExtractionStateStore(state_path)

            enqueue_from_canonical(
                "Fuller_Complete_Works_Vol02", store, max_candidates=1
            )
            first_cid = list(store._data.keys())[0]
            meta = store._data[first_cid]["metadata"]
            assert meta["source_identifier"] == "Fuller_Complete_Works_Vol02"
            assert "page" in meta
            assert "paragraph_index" in meta
            assert "sentence_index" in meta
            assert "text" in meta

    def test_already_confidence_classified_not_touched(self):
        """Already CONFIDENCE_CLASSIFIED candidates are not re-enqueued."""
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            store = TSUExtractionStateStore(state_path)

            # First enqueue
            count1 = enqueue_from_canonical(
                "Fuller_Complete_Works_Vol02", store, max_candidates=3
            )
            assert count1 == 3

            # Manually change one to CONFIDENCE_CLASSIFIED
            first_cid = list(store._data.keys())[0]
            store.set_state(first_cid, TSUExtractionState.CONFIDENCE_CLASSIFIED)

            # Second enqueue — should skip the CONFIDENCE_CLASSIFIED one
            count2 = enqueue_from_canonical(
                "Fuller_Complete_Works_Vol02", store, max_candidates=3
            )
            assert count2 == 0  # All 3 already exist
