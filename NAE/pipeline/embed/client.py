"""Shared BGE-M3 embedding client with SHA256-hash-keyed disk cache.

Used by both NAE.pipeline.verify.duplicate (Phase 3.5, similarity check) and
NAE.pipeline.index (Phase 4, Qdrant upsert) so an embedding is computed once
per unique (claim, book, page, scriptures) tuple regardless of which stage
needs it, per the Phase 4 gate review's caching requirement.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Sequence

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


# ── Batch Embedding (SPRINT34 High-Throughput) ─────────────────────────────

EMBED_BATCH_THRESHOLD = 64   # flush when uncached texts reach this count
EMBED_BATCH_TIMEOUT = 5.0    # flush after N seconds even if buffer not full


class _EmbedBuffer:
    """Accumulates (text, content_hash) pairs and flushes them via batch API."""

    def __init__(self, threshold: int = EMBED_BATCH_THRESHOLD,
                 timeout: float = EMBED_BATCH_TIMEOUT,
                 model: str = config.DEFAULT_EMBED_MODEL,
                 cache_root: Path = config.EMBEDDING_CACHE_ROOT) -> None:
        self._buffer: list[tuple[str, str]] = []  # (text, content_hash)
        self._threshold = threshold
        self._timeout = timeout
        self._model = model
        self._cache_root = cache_root
        self._last_flush: float = time.monotonic()

    def add(self, text: str, content_hash: str) -> list[float] | None:
        """Add a text/hash pair. Returns cached vector if available, else buffers it."""
        cached = get_cached(content_hash, self._cache_root)
        if cached is not None:
            return cached

        self._buffer.append((text, content_hash))

        # Auto-flush when threshold reached or timeout exceeded
        elapsed = time.monotonic() - self._last_flush
        if len(self._buffer) >= self._threshold or elapsed >= self._timeout:
            return self._flush()

        return None  # still buffering

    def _flush(self) -> list[float] | None:
        """Flush all buffered items via batch API. Returns vector for LAST item only."""
        if not self._buffer:
            self._last_flush = time.monotonic()
            return None

        texts = [t for t, _ in self._buffer]
        hashes = [h for _, h in self._buffer]
        last_hash = hashes[-1] if hashes else None

        try:
            result = ollama.embed(model=self._model, input=texts)
            vectors = result["embeddings"]  # list[list[float]]

            # Save all to cache
            for h, v in zip(hashes, vectors):
                _save_cache(h, v, self._model, self._cache_root)

            # Return vector for the last item (caller's request)
            if last_hash is not None:
                return get_cached(last_hash, self._cache_root)
        except Exception as e:  # noqa: BLE001
            logger.error("[embed_texts_batch] batch 실패 (%d items, model=%s): %s",
                         len(texts), self._model, e)

        self._buffer.clear()
        self._last_flush = time.monotonic()
        return get_cached(last_hash, self._cache_root) if last_hash else None

    def flush_all(self) -> None:
        """Force-flush remaining buffered items (call at end of batch)."""
        self._flush()


# Module-level singleton buffer
_embed_buffer: _EmbedBuffer | None = None


def _get_embed_buffer() -> _EmbedBuffer:
    global _embed_buffer
    if _embed_buffer is None:
        _embed_buffer = _EmbedBuffer()
    return _embed_buffer


def embed_texts_batch(
    texts_hashes: Sequence[tuple[str, str]],  # [(text, content_hash), ...]
    *,
    model: str = config.DEFAULT_EMBED_MODEL,
    cache_root: Path = config.EMBEDDING_CACHE_ROOT,
) -> list[list[float] | None]:
    """Batch-embed multiple texts using Ollama's batch API.

    Skips already-cached items. Buffers uncached items and flushes when
    threshold is reached or timeout expires.

    Args:
        texts_hashes: Sequence of (text, content_hash) tuples.
        model: Ollama embedding model name.
        cache_root: Directory for SHA256-hash-keyed disk cache.

    Returns:
        List of embedding vectors (or None on failure) in same order as input.
    """
    if not texts_hashes:
        return []

    buffer = _EmbedBuffer(
        threshold=EMBED_BATCH_THRESHOLD,
        timeout=EMBED_BATCH_TIMEOUT,
        model=model,
        cache_root=cache_root,
    )

    results: list[list[float] | None] = []
    for text, content_hash in texts_hashes:
        vec = buffer.add(text, content_hash)
        if vec is not None:
            results.append(vec)
        else:
            # Still buffering - placeholder; will be filled after flush
            results.append(None)

    # Flush remaining items
    buffer.flush_all()

    # Fill any None placeholders from partial-buffer items
    for i, (text, content_hash) in enumerate(texts_hashes):
        if results[i] is None:
            results[i] = get_cached(content_hash, cache_root)

    return results


def reset_embed_buffer() -> None:
    """Reset the module-level embed buffer (for testing / fresh runs)."""
    global _embed_buffer
    _embed_buffer = None
