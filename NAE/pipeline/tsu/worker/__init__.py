"""NAE/pipeline/tsu/worker — TSU Extraction Queue Worker (Phase 3).

Separates the monolithic builder.build_tsu_for_identifier() into an
independent queue-based worker with explicit state transitions:

    TSU_EXTRACTION_QUEUE: READY -> PROCESSING -> EXTRACTED -> CONFIDENCE_CLASSIFIED
    실패: PROCESSING -> FAILED -> ERROR/REVIEW QUEUE

Retry policy follows ADR-022 section 8 — no auto-retry/auto-promotion.
"""
from .state import (
    TSUExtractionState,
    TSUExtractionStateStore,
    VALID_TRANSITIONS,
)
from .queue import TSUExtractionExceptionQueue
from .worker import (
    WorkerResult,
    BatchResult,
    process_candidate,
    process_batch,
    retry_failed,
    get_queue_depth,
)

__all__ = [
    "TSUExtractionState",
    "TSUExtractionStateStore",
    "VALID_TRANSITIONS",
    "TSUExtractionExceptionQueue",
    "WorkerResult",
    "BatchResult",
    "process_candidate",
    "process_batch",
    "retry_failed",
    "get_queue_depth",
]
