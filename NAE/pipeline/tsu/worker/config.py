"""Worker configuration for TSU Extraction Queue (Phase 3)."""
from __future__ import annotations

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_TSU_ROOT = _PROJECT_ROOT / "NAE" / "corpus" / "tsu"

DEFAULT_STATE_PATH = _TSU_ROOT / "worker_state.json"
DEFAULT_EXCEPTION_QUEUE_PATH = _TSU_ROOT / "worker_exception_queue.json"

# Batch processing settings
DEFAULT_BATCH_SIZE = 50  # candidates per batch checkpoint
CHECKPOINT_INTERVAL = 100  # save state every N candidates
