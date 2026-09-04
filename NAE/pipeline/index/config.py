"""Configuration for Phase 4 - BGE-M3 Vector Indexing.

Per ADR-013 (docs/architecture/ADR-013-NAE-Vector-Store.md): this is a
dedicated Qdrant instance, fully separate from the legacy dbma_qdrant/
dbma_sermon collection ADR-003 preserves, and is never wired into
core/retrieval.py::RetrievalEngine's production query path.
"""
from __future__ import annotations

from pathlib import Path

from NAE.pipeline.tsu.config import TSU_SCHEMA_VERSION

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = PROJECT_ROOT / "NAE" / "corpus"

QDRANT_URL = "http://localhost:7333"

# Collection migration policy (Phase 3.5 gate review, item C): the collection
# name is derived from the TSU schema version, so a future record-shape
# change (TSU_SCHEMA_VERSION bump) lands in a new collection (nae_tsu_v2, ...)
# instead of mixing incompatible payload shapes into nae_tsu_v1. Old
# collections are left in place for audit/rollback rather than deleted.
COLLECTION_NAME = f"nae_tsu_v{TSU_SCHEMA_VERSION}"
VECTOR_SIZE = 1024  # bge-m3:latest
