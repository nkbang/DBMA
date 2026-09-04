"""NAE reference corpus retrieval adapter (TSU-separated).

Provides `search_reference()` for querying the reference corpus
(`nae_ref_v1` collection) independently of the TSU pipeline.

Unlike `NAE/retrieval_adapter.py`, this module has NO `module_registry`
gate — it is always enabled because reference content is a "default
background knowledge" source, not an optional module.

Does NOT import `core.retrieval.RetrievalEngine` and is NOT imported by it.

SPRINT34-SMITH-PHASEB: Added timeout enforcement, exception categorization,
and deterministic return schema for fault isolation during Smith Bible
Dictionary integration.
"""
from __future__ import annotations

import logging
import hashlib
import time
from typing import Any

import ollama

from NAE.pipeline.reference import config as ref_config

logger = logging.getLogger("nae.reference.retrieval_adapter")

# ── Timeout thresholds (seconds) ─────────────────────────────────────
_EMBEDDING_TIMEOUT_S = 5.0
_QDRANT_TIMEOUT_S = 5.0


class ReferenceRetrievalError(RuntimeError):
    """Base exception for reference retrieval failures."""
    pass


class EmbeddingTimeoutError(ReferenceRetrievalError):
    """Embedding step exceeded timeout."""
    pass


class QdrantConnectionError(ReferenceRetrievalError):
    """Qdrant connection/search failed."""
    pass


def search_reference(
    query: str,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Search the reference corpus for the given query.

    Embeds `query` with bge-m3 and searches the `nae_ref_v1` Qdrant
    collection.  Returns the top-k most similar chunks.

    Fault isolation guarantees:
        - Embedding timeout → returns [] (never hangs)
        - Qdrant connection failure → returns [] (never raises)
        - Malformed response → returns [] (never crashes)
        - Deterministic return schema: always list[dict] with fixed keys

    Args:
        query: The search query text.
        top_k: Number of results to return (default 3).

    Returns:
        List of dicts with keys: text, source_id, volume, page_start,
        page_end, heading_context, chunk_index, content_type.
        Always returns a list — never raises an exception.
    """
    if not query or not query.strip():
        return []

    # Embed the query with timeout
    content_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
    cached = _get_cached_embedding(content_hash)
    if cached is not None:
        query_vector = cached
    else:
        try:
            t0 = time.monotonic()
            client = ollama.Client(timeout=_EMBEDDING_TIMEOUT_S)
            result = client.embeddings(
                model=ref_config.DEFAULT_EMBED_MODEL,
                prompt=query,
            )
            elapsed_ms = (time.monotonic() - t0) * 1_000
            if elapsed_ms > _EMBEDDING_TIMEOUT_S * 800:
                logger.warning(
                    "[search_reference] embedding slow: %.0fms", elapsed_ms,
                )
            query_vector = result["embedding"]
            _save_cached_embedding(content_hash, query_vector)
        except TimeoutError as e:
            logger.error("[search_reference] embedding timeout (%.1fs): %s", _EMBEDDING_TIMEOUT_S, e)
            return []
        except ollama.ResponseError as e:
            logger.error("[search_reference] embedding API error: %s", e)
            return []
        except Exception as e:  # noqa: BLE001
            logger.error("[search_reference] embedding unexpected error: %s", e)
            return []

    # Search Qdrant with timeout
    from qdrant_client import QdrantClient
    client = QdrantClient(url=ref_config.QDRANT_URL)

    try:
        t0 = time.monotonic()
        results = client.query_points(
            collection_name=ref_config.REFERENCE_COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
            timeout=max(1, int(_QDRANT_TIMEOUT_S)),
        )
        elapsed_ms = (time.monotonic() - t0) * 1_000
        if elapsed_ms > _QDRANT_TIMEOUT_S * 800:
            logger.warning("[search_reference] Qdrant search slow: %.0fms", elapsed_ms)
    except TimeoutError as e:
        logger.error("[search_reference] Qdrant timeout (%.1fs): %s", _QDRANT_TIMEOUT_S, e)
        return []
    except ConnectionError as e:
        logger.error("[search_reference] Qdrant connection failed: %s", e)
        return []
    except Exception as e:  # noqa: BLE001
        logger.error("[search_reference] Qdrant unexpected error: %s", e)
        return []

    # Format results — deterministic schema
    output = []
    for point in results.points:
        payload = point.payload or {}
        output.append({
            "text": payload.get("text", ""),
            "source_id": payload.get("source_id", ""),
            "volume": payload.get("volume", ""),
            "page_start": payload.get("page_start"),
            "page_end": payload.get("page_end"),
            "heading_context": payload.get("heading_context", ""),
            "chunk_index": payload.get("chunk_index"),
            "content_type": payload.get("content_type", "reference_dictionary"),
        })

    logger.info(
        "[search_reference] query=%r top_k=%d → %d results",
        query[:50], top_k, len(output),
    )
    return output


def _get_cached_embedding(content_hash: str) -> list[float] | None:
    """Get a cached embedding from the embed cache."""
    from NAE.pipeline.embed import client as embed_client
    return embed_client.get_cached(content_hash)


def _save_cached_embedding(
    content_hash: str, vector: list[float],
) -> None:
    """Save an embedding to the embed cache."""
    from NAE.pipeline.embed import client as embed_client
    from NAE.pipeline.reference import config as ref_config
    embed_client._save_cache(content_hash, vector, ref_config.DEFAULT_EMBED_MODEL)
