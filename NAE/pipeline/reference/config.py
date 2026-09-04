"""Configuration for the reference corpus ingestion pipeline.

Separate from `NAE.pipeline.index.config` (TSU) — different collection,
different schema, different point-ID scheme.
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = PROJECT_ROOT / "NAE" / "corpus"

# Qdrant target — must match the same instance as TSU but a different collection
QDRANT_URL = "http://localhost:7333"

# Collection name (versioned per TSU_SCHEMA_VERSION convention)
REFERENCE_COLLECTION_NAME = "nae_ref_v1"

# Embedding model (must match the one used by NAE.pipeline.embed)
DEFAULT_EMBED_MODEL = "bge-m3:latest"

# Chunking parameters (CLAUDE.md defaults)
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200

# Canonical source root for reference corpora
REFERENCE_CANONICAL_ROOT = CORPUS_ROOT / "canonical"
