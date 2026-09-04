"""Configuration for the shared NAE embedding client/cache (used by verify.duplicate and Phase 4 indexing)."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = PROJECT_ROOT / "NAE" / "corpus"

EMBEDDING_CACHE_ROOT = CORPUS_ROOT / "embeddings" / "cache"

DEFAULT_EMBED_MODEL = "bge-m3:latest"
EMBED_DIMENSION = 1024
