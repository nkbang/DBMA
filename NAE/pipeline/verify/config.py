"""Configuration for the Knowledge Verification Layer (Phase 3.5)."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = PROJECT_ROOT / "NAE" / "corpus"

TSU_ROOT = CORPUS_ROOT / "tsu"
VERIFY_VERSION = "3.5.0"

# Duplicate detection: two claims within the same doctrine whose embeddings
# exceed this cosine similarity are flagged as near-duplicates.
DUPLICATE_SIMILARITY_THRESHOLD = 0.93

# Citation proximity window (pages) - mirrors NAE.pipeline.tsu.citation's window,
# re-checked here independently against canonical.json rather than trusted from
# the TSU record, to catch drift or bugs between build and verify time.
CITATION_PAGE_WINDOW = 1

# Contradiction detection is LLM-based, pairwise, and therefore expensive and
# imprecise at scale - it is capped and opt-in (see contradiction.py docstring).
CONTRADICTION_MAX_PAIRS_PER_ITEM = 30
CONTRADICTION_MODEL = "my-theology-bot-v2:latest"

# score.py weights - a heuristic weighted combination, not a calibrated
# probability. See score.py docstring for what each component can and cannot
# certify.
SCORE_WEIGHTS = {
    "llm_score": 0.4,
    "parser_score": 0.2,
    "evidence_score": 0.2,
    "citation_score": 0.2,
}
