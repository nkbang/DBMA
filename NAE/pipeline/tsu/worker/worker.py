"""TSU Extraction Worker (Phase 3).

Processes candidates through the queue with explicit state transitions:

    READY -> PROCESSING -> EXTRACTED -> CONFIDENCE_CLASSIFIED
    실패: PROCESSING -> FAILED -> ERROR/REVIEW QUEUE

Retry policy follows ADR-022 section 8 — no auto-retry/auto-promotion.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config as worker_config
from .state import (
    TSUExtractionState,
    TSUExtractionStateStore,
)
from .queue import TSUExtractionExceptionQueue

logger = logging.getLogger("nae.tsu.worker")


@dataclass
class WorkerResult:
    """Result of processing a single candidate or batch."""

    candidate_id: str
    state: TSUExtractionState
    tsu_record: dict[str, Any] | None = None
    error_type: str | None = None
    error_message: str | None = None
    confidence: float | None = None
    elapsed_seconds: float = 0.0


@dataclass
class BatchResult:
    """Result of processing a batch of candidates."""

    total: int = 0
    extracted: int = 0
    failed: int = 0
    results: list[WorkerResult] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    @property
    def success_rate(self) -> float:
        return self.extracted / self.total if self.total > 0 else 0.0


def _classify_confidence(
    tsu_record: dict[str, Any],
) -> tuple[float, str]:
    """Classify confidence from TSU record (deterministic).

    Returns (confidence_score, confidence_label).
    Uses the model's self-reported confidence as a starting point.
    This is NOT a theological truthiness assessment — it is purely
    a routing signal for the review gate (Phase 4).
    """
    raw_confidence = tsu_record.get("confidence", 0.0)
    if isinstance(raw_confidence, str):
        try:
            raw_confidence = float(raw_confidence)
        except ValueError:
            raw_confidence = 0.0

    if raw_confidence >= 0.9:
        label = "HIGH"
    elif raw_confidence >= 0.8:
        label = "MEDIUM"
    else:
        label = "LOW"

    return float(raw_confidence), label


def process_candidate(
    candidate_id: str,
    candidate_text: str,
    context_before: str | None = None,
    context_after: str | None = None,
    candidate_scriptures: list[str] | None = None,
    candidate_citations: list[str] | None = None,
    model: str = "my-theology-bot-v2:latest",
    state_store: TSUExtractionStateStore | None = None,
    exception_queue: TSUExtractionExceptionQueue | None = None,
) -> WorkerResult:
    """Process a single candidate through the TSU extraction queue.

    State transitions:
        READY -> PROCESSING (entry)
        PROCESSING -> EXTRACTED (success) or FAILED (error)
        EXTRACTED -> CONFIDENCE_CLASSIFIED (automatic)

    Returns WorkerResult with final state and any TSU record or error.
    """
    start = time.monotonic()

    if state_store is None:
        state_store = TSUExtractionStateStore()
    if exception_queue is None:
        exception_queue = TSUExtractionExceptionQueue()

    # Step 1: Transition to PROCESSING
    current_state = state_store.get_state(candidate_id)
    success, reason = state_store.set_state(
        candidate_id,
        TSUExtractionState.PROCESSING,
        from_state=TSUExtractionState.READY,
        metadata={"model": model, "text_length": len(candidate_text)},
    )
    if not success:
        elapsed = time.monotonic() - start
        return WorkerResult(
            candidate_id=candidate_id,
            state=TSUExtractionState.FAILED,
            error_type="STATE_TRANSITION_ERROR",
            error_message=f"Cannot transition to PROCESSING: {reason}",
            elapsed_seconds=elapsed,
        )

    # Clear stale error fields from any prior attempt — this is a new trial.
    state_store.clear_metadata_fields(candidate_id, ["error_type", "error_message"])

    # Step 2: Extract claim via LLM (reuse existing claim.py)
    from .. import claim as claim_mod

    try:
        result = claim_mod.extract_claim(
            candidate_text,
            context_before=context_before,
            context_after=context_after,
            candidate_scriptures=candidate_scriptures or [],
            candidate_citations=candidate_citations or [],
            model=model,
        )
    except Exception as exc:
        elapsed = time.monotonic() - start
        state_store.set_state(
            candidate_id,
            TSUExtractionState.FAILED,
            from_state=TSUExtractionState.PROCESSING,
            metadata={"error_type": type(exc).__name__, "error_message": str(exc)},
        )
        exception_queue.record(
            candidate_id=candidate_id,
            error_type="LLM_ERROR",
            error_message=str(exc),
            state_at_failure=TSUExtractionState.FAILED.value,
        )
        return WorkerResult(
            candidate_id=candidate_id,
            state=TSUExtractionState.FAILED,
            error_type="LLM_ERROR",
            error_message=str(exc),
            elapsed_seconds=elapsed,
        )

    # Step 2b: Transition to EXTRACTED (LLM call completed)
    success, reason = state_store.set_state(
        candidate_id,
        TSUExtractionState.EXTRACTED,
        from_state=TSUExtractionState.PROCESSING,
    )
    if not success:
        elapsed = time.monotonic() - start
        return WorkerResult(
            candidate_id=candidate_id,
            state=TSUExtractionState.FAILED,
            error_type="STATE_TRANSITION_ERROR",
            error_message=f"Cannot transition to EXTRACTED: {reason}",
            elapsed_seconds=elapsed,
        )

    # Step 3: Check if claim was extracted
    # ClaimResult dataclass -> dict for uniform .get() access
    if hasattr(result, "model_fields"):
        # pydantic model
        result_dict = result.model_dump()
    elif hasattr(result, "__dict__"):
        # dataclass / object
        result_dict = result.__dict__
    else:
        result_dict = result
    is_claim = result_dict.get("is_claim", False)
    if not is_claim:
        # Not a claim — skip (no TSU record generated)
        elapsed = time.monotonic() - start
        state_store.set_state(
            candidate_id,
            TSUExtractionState.CONFIDENCE_CLASSIFIED,
            from_state=TSUExtractionState.EXTRACTED,
            metadata={"is_claim": False, "reason": result_dict.get("reason", "not_a_claim")},
        )
        return WorkerResult(
            candidate_id=candidate_id,
            state=TSUExtractionState.CONFIDENCE_CLASSIFIED,
            tsu_record=None,
            confidence=0.0,
            elapsed_seconds=elapsed,
        )

    # Step 4: Build TSU record
    tsu_record = {
        "id": result_dict.get("id"),
        "claim": result_dict.get("claim", ""),
        "doctrine": result_dict.get("doctrine", "Other"),
        "scriptures": result_dict.get("scriptures", []),
        "citations": result_dict.get("citations", []),
        "confidence": result_dict.get("confidence", 0.0),
        "extraction_method": "llm_claim_extraction",
        "model": model,
        "review_status": "generated",
        "candidate_id": candidate_id,
    }

    # Step 5: Confidence classification (automatic)
    confidence_score, confidence_label = _classify_confidence(tsu_record)
    tsu_record["confidence_label"] = confidence_label

    # Step 6: Final state transition
    state_store.set_state(
        candidate_id,
        TSUExtractionState.CONFIDENCE_CLASSIFIED,
        from_state=TSUExtractionState.EXTRACTED,
        metadata={
            "is_claim": True,
            "confidence_score": confidence_score,
            "confidence_label": confidence_label,
            "doctrine": tsu_record["doctrine"],
        },
    )

    elapsed = time.monotonic() - start
    return WorkerResult(
        candidate_id=candidate_id,
        state=TSUExtractionState.CONFIDENCE_CLASSIFIED,
        tsu_record=tsu_record,
        confidence=confidence_score,
        elapsed_seconds=elapsed,
    )


def process_batch(
    candidates: list[dict[str, Any]],
    *,
    model: str = "my-theology-bot-v2:latest",
    state_store: TSUExtractionStateStore | None = None,
    exception_queue: TSUExtractionExceptionQueue | None = None,
    checkpoint_every: int = worker_config.CHECKPOINT_INTERVAL,
) -> BatchResult:
    """Process a batch of candidates through the TSU extraction queue.

    Each candidate is processed independently — one failure does not
    block others (failure isolation principle).

    Args:
        candidates: List of dicts with keys:
            - candidate_id (str): unique identifier
            - text (str): sentence text
            - context_before (str, optional)
            - context_after (str, optional)
            - candidate_scriptures (list[str], optional)
            - candidate_citations (list[str], optional)
        model: LLM model name
        state_store: State store (creates default if None)
        exception_queue: Exception queue (creates default if None)
        checkpoint_every: Save state every N candidates

    Returns:
        BatchResult with summary statistics and per-candidate results.
    """
    start = time.monotonic()

    if state_store is None:
        state_store = TSUExtractionStateStore()
    if exception_queue is None:
        exception_queue = TSUExtractionExceptionQueue()

    batch_result = BatchResult(total=len(candidates))

    for idx, cand in enumerate(candidates, start=1):
        result = process_candidate(
            candidate_id=cand["candidate_id"],
            candidate_text=cand["text"],
            context_before=cand.get("context_before"),
            context_after=cand.get("context_after"),
            candidate_scriptures=cand.get("candidate_scriptures"),
            candidate_citations=cand.get("candidate_citations"),
            model=model,
            state_store=state_store,
            exception_queue=exception_queue,
        )

        batch_result.results.append(result)
        if result.state == TSUExtractionState.CONFIDENCE_CLASSIFIED and result.tsu_record:
            batch_result.extracted += 1
        elif result.state == TSUExtractionState.FAILED:
            batch_result.failed += 1

        # Checkpoint
        if idx % checkpoint_every == 0:
            state_store.save()
            logger.info(
                "Batch checkpoint: %d/%d processed, %d extracted, %d failed",
                idx, len(candidates), batch_result.extracted, batch_result.failed,
            )

    batch_result.elapsed_seconds = time.monotonic() - start
    state_store.save()  # final save
    exception_queue.save()

    logger.info(
        "Batch complete: %d total, %d extracted, %d failed, %.2fs",
        batch_result.total, batch_result.extracted, batch_result.failed,
        batch_result.elapsed_seconds,
    )

    return batch_result


def retry_failed(
    candidate_id: str,
    state_store: TSUExtractionStateStore | None = None,
    exception_queue: TSUExtractionExceptionQueue | None = None,
) -> tuple[bool, str]:
    """Manually retry a FAILED candidate (requires explicit call).

    Per ADR-022 section 8: no auto-retry. This function must be called
    explicitly by a human operator or an external scheduler.

    Returns (success, reason).
    """
    if state_store is None:
        state_store = TSUExtractionStateStore()

    success, reason = state_store.reset_failed_to_ready(candidate_id)
    if success:
        state_store.save()
        logger.info("Retried candidate %s: FAILED -> READY", candidate_id)
    return success, reason


def get_queue_depth(state_store: TSUExtractionStateStore | None = None) -> dict[str, int]:
    """Get current queue depth by state."""
    if state_store is None:
        state_store = TSUExtractionStateStore()
    summary = state_store.summary()
    return {
        "READY": summary.get(TSUExtractionState.READY.value, 0),
        "PROCESSING": summary.get(TSUExtractionState.PROCESSING.value, 0),
        "EXTRACTED": summary.get(TSUExtractionState.EXTRACTED.value, 0),
        "CONFIDENCE_CLASSIFIED": summary.get(TSUExtractionState.CONFIDENCE_CLASSIFIED.value, 0),
        "FAILED": summary.get(TSUExtractionState.FAILED.value, 0),
    }
