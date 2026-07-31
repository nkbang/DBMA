"""Configuration for Phase 4 - BGE-M3 Vector Indexing.

Per ADR-013 (docs/architecture/ADR-013-NAE-Vector-Store.md): this is a
dedicated Qdrant instance, fully separate from the legacy dbma_qdrant/
dbma_sermon collection ADR-003 preserves, and is never wired into
core/retrieval.py::RetrievalEngine's production query path.
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = PROJECT_ROOT / "NAE" / "corpus"

QDRANT_URL = "http://localhost:7333"
COLLECTION_NAME = "nae_tsu"
VECTOR_SIZE = 1024  # bge-m3:latest
