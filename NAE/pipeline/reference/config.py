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

# Second reference collection — Baptist commentary corpus (verse-anchored,
# e.g. Spurgeon's Treasury of David). Kept isolated from REFERENCE_COLLECTION_NAME
# per ADR-013 collection-isolation principle: different source, different
# chunking rule (verse-anchored vs. heading+prose dictionary entries).
COMMENTARY_COLLECTION_NAME = "nae_ref_commentary_v1"

# All collections search_reference() may query. Order does not affect
# ranking (results are merged and re-sorted by score) but does affect
# which collections exist to be searched at all — a name absent here is
# never queried regardless of caller args.
KNOWN_REFERENCE_COLLECTIONS = (REFERENCE_COLLECTION_NAME, COMMENTARY_COLLECTION_NAME)

# Embedding model (must match the one used by NAE.pipeline.embed)
DEFAULT_EMBED_MODEL = "bge-m3:latest"

# Chunking parameters (CLAUDE.md defaults)
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200

# Canonical source root for reference corpora
REFERENCE_CANONICAL_ROOT = CORPUS_ROOT / "canonical"
