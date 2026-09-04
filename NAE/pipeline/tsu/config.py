"""Configuration for the TSU (Theological Semantic Unit) Builder (Phase 3)."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = PROJECT_ROOT / "NAE" / "corpus"

CANONICAL_ROOT = CORPUS_ROOT / "canonical"
RAW_ROOT = CORPUS_ROOT / "raw" / "archive_org"
TSU_ROOT = CORPUS_ROOT / "tsu"

BUILDER_VERSION = "3.0.0"

# Bumped whenever the TSU record *shape* changes (fields added/removed/renamed).
# Included in the embedding cache hash (NAE.pipeline.embed.hashing) so a schema
# change invalidates old cache entries instead of silently reusing embeddings
# computed under a different record shape.
TSU_SCHEMA_VERSION = "1"

# Ollama-backed claim extraction, following the existing convention in
# core/evaluation/sermon_judge.py (same JSON-schema-prompt + brace-extraction
# parsing, same fail-soft error handling so one bad sentence never kills a batch run).
DEFAULT_CLAIM_MODEL = "my-theology-bot-v2:latest"
CLAIM_TEMPERATURE = 0.0

# Only prose sentences at or above this length are sent to the LLM as claim
# candidates - short fragments ("See also.", "Amen.") are near-certain non-claims
# and are skipped to save calls.
MIN_CLAIM_SENTENCE_CHARS = 25

# Closed vocabulary: the LLM is instructed to choose from this list (or "Other" /
# "None"). A closed set is used instead of free-text classification so
# downstream consumers can trust the doctrine field is one of a known, reviewable
# set of values rather than an LLM-invented label.
DOCTRINE_CATEGORIES = [
    "Baptism",
    "Church Covenant",
    "Church Discipline",
    "Lord's Supper",
    "Confession",
    "Election",
    "Justification",
    "Sanctification",
    "Ecclesiology",
    "Soteriology",
    "Trinity",
    "Scripture / Authority",
    "Providence",
    "Eschatology",
    "Other",
]

# Known Priority-B authors (from the Phase 1 collector's keyword list) used as
# a deterministic, rule-based signal for citation candidates - not LLM-derived.
KNOWN_AUTHORS = [
    "John Smyth", "Thomas Helwys", "Benjamin Keach", "John Gill",
    "Andrew Fuller", "William Carey", "Charles Spurgeon", "B. H. Carroll",
    "J. M. Pendleton", "John Broadus", "A. H. Strong", "E. Y. Mullins",
    "Calvin", "Luther", "Augustine",
]
