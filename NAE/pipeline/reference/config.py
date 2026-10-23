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

# [2026-10-23] 서버 없는 내장(로컬) 저장소 — Docker를 요구하지 않는 사용자용.
# scripts/nae_reference_to_local.py가 위 서버의 참고 컬렉션을 이 폴더로 복사한다.
# 폴더가 있고 완료 표식(READY)이 있으면 search_reference()가 서버 대신 이것을 쓴다.
# NAE_REFERENCE_LOCAL_PATH 환경변수로 위치를 바꿀 수 있다. data/는 git 대상이 아니다.
LOCAL_STORE_PATH = PROJECT_ROOT / "data" / "reference_qdrant"

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
