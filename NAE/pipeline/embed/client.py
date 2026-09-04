"""Shared BGE-M3 embedding client with SHA256-hash-keyed disk cache.

Used by both NAE.pipeline.verify.duplicate (Phase 3.5, similarity check) and
NAE.pipeline.index (Phase 4, Qdrant upsert) so an embedding is computed once
per unique (claim, book, page, scriptures) tuple regardless of which stage
needs it, per the Phase 4 gate review's caching requirement.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import ollama

from . import config

logger = logging.getLogger("nae.embed.client")


def _cache_path(content_hash: str, cache_root: Path = config.EMBEDDING_CACHE_ROOT) -> Path:
    return cache_root / f"{content_hash}.json"


def get_cached(content_hash: str, cache_root: Path = config.EMBEDDING_CACHE_ROOT) -> list[float] | None:
    path = _cache_path(content_hash, cache_root)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)["vector"]
    except (json.JSONDecodeError, OSError, KeyError):
        return None


def _save_cache(content_hash: str, vector: list[float], model: str,
                 cache_root: Path = config.EMBEDDING_CACHE_ROOT) -> None:
    cache_root.mkdir(parents=True, exist_ok=True)
    with open(_cache_path(content_hash, cache_root), "w", encoding="utf-8") as fh:
        json.dump({"hash": content_hash, "model": model, "vector": vector}, fh)


def embed_text(text: str, *, content_hash: str, model: str = config.DEFAULT_EMBED_MODEL,
               cache_root: Path = config.EMBEDDING_CACHE_ROOT) -> list[float] | None:
    """Return the embedding vector for `text`, using the on-disk cache keyed by `content_hash`.

    Returns None (rather than raising) on an embedding-service failure, so a
    batch indexing run can skip and continue rather than dying on one item.
    """
    cached = get_cached(content_hash, cache_root)
    if cached is not None:
        return cached

    try:
        result = ollama.embeddings(model=model, prompt=text)
        vector = result["embedding"]
    except Exception as e:  # noqa: BLE001
        logger.error("[embed_text] 실패 (model=%s): %s", model, e)
        return None

    _save_cache(content_hash, vector, model, cache_root)
    return vector
