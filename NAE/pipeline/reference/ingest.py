"""Ingestion pipeline for reference corpora.

Loads canonical.json → chunks → embeds → upserts into Qdrant.
Completely separate from TSU pipeline — no shared schemas or identifiers.

Point ID scheme: uuid5(NAMESPACE, f"{identifier}:{chunk_index}")
  → deterministic (re-runnable), collision-free per chunk.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from NAE.pipeline.embed import client as embed_client
from NAE.pipeline.reference import chunker, config

ChunkerFn = Callable[[dict[str, Any], int, int], list[chunker.ReferenceChunk]]

logger = logging.getLogger("nae.reference.ingest")

# Deterministic UUID namespace for reference corpus point IDs
_REF_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


@dataclass
class IngestResult:
    """Result of a reference corpus ingestion run."""
    identifier: str
    chunks_total: int = 0
    chunks_embedded: int = 0
    chunks_skipped: int = 0
    points_upserted: int = 0
    errors: list[str] = field(default_factory=list)


def _make_point_id(identifier: str, chunk_index: int) -> str:
    """Deterministic UUID5 point ID for a reference chunk.

    Includes *identifier* in the UUID seed so that different volumes
    (Vol1, Vol2, …) never collide even when they share chunk_index values.
    """
    return uuid.uuid5(_REF_NAMESPACE, f"{identifier}:{chunk_index}").hex


def _build_payload(
    chunk: chunker.ReferenceChunk,
    identifier: str,
    source_id: str,
    volume: str,
    content_type: str = "reference_dictionary",
) -> dict[str, Any]:
    """Build Qdrant payload for a reference chunk."""
    payload: dict[str, Any] = {
        "chunk_index": chunk.chunk_index,
        "text": chunk.text,
        "identifier": identifier,
        "source_id": source_id,
        "volume": volume,
        "page_start": chunk.page_start,
        "page_end": chunk.page_end,
        "heading_context": chunk.heading_context,
        "content_type": content_type,
    }
    if chunk.scripture_reference:
        payload["scripture_reference"] = chunk.scripture_reference
    return payload


def _build_point(chunk: chunker.ReferenceChunk, vector: list[float],
                 identifier: str, source_id: str, volume: str,
                 content_type: str = "reference_dictionary") -> PointStruct:
    """Build a Qdrant PointStruct for a reference chunk."""
    return PointStruct(
        id=_make_point_id(identifier, chunk.chunk_index),
        vector=vector,
        payload=_build_payload(chunk, identifier, source_id, volume, content_type),
    )


def _ensure_ref_collection(client: QdrantClient, collection_name: str) -> None:
    """Ensure the given reference collection exists (separate from TSU and
    from any other reference collection — ADR-013 isolation)."""
    existing = {c.name for c in client.get_collections().collections}
    if collection_name in existing:
        return
    logger.info("Creating reference collection %s", collection_name)
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=config.DEFAULT_EMBED_MODEL and 1024,  # bge-m3 output size
            distance=Distance.COSINE,
        ),
    )


def ingest(
    canonical_path: Path,
    identifier: str,
    source_id: str,
    volume: str,
    *,
    chunk_size: int = config.CHUNK_SIZE,
    chunk_overlap: int = config.CHUNK_OVERLAP,
    apply: bool = False,
    collection_name: str = config.REFERENCE_COLLECTION_NAME,
    chunker_fn: ChunkerFn = chunker.chunk_canonical,
    content_type: str = "reference_dictionary",
) -> IngestResult:
    """Ingest a single reference corpus volume.

    Args:
        canonical_path: Path to the canonical.json file.
        identifier: Human-readable identifier (e.g. Smith_Bible_Dictionary_HackettAbbot_Vol1).
        source_id: Source identifier (e.g. BAP-REF-SMITH-VOL01).
        volume: Volume label (e.g. "vol_1_a_g").
        chunk_size: Maximum chunk size in characters.
        chunk_overlap: Overlap between chunks in characters.
        apply: If False, return dry-run stats without embedding/upserting.
        collection_name: Target Qdrant collection. Defaults to the Smith
            dictionary collection (`nae_ref_v1`) — pass
            `config.COMMENTARY_COLLECTION_NAME` for verse-anchored commentary
            corpora, per ADR-013 collection isolation.
        chunker_fn: Chunking strategy. Defaults to the heading+prose
            dictionary chunker (`chunker.chunk_canonical`) — pass
            `chunker.chunk_canonical_verse_anchored` for commentary corpora.
        content_type: Payload `content_type` tag for downstream retrieval
            filtering (e.g. "reference_commentary").

    Returns:
        IngestResult with counts and any errors.
    """
    result = IngestResult(identifier=identifier)

    # 1. Load canonical
    logger.info("Loading canonical: %s", canonical_path)
    canonical = chunker.load_canonical(canonical_path)
    paragraphs = canonical.get("paragraphs", [])
    logger.info("Canonical has %d paragraphs", len(paragraphs))

    # 2. Chunk
    chunks = chunker_fn(canonical, chunk_size, chunk_overlap)
    result.chunks_total = len(chunks)
    logger.info("Generated %d chunks", len(chunks))

    if not apply:
        # Dry-run: show first 3 chunk samples
        for i, chunk in enumerate(chunks[:3]):
            logger.info(
                "Chunk %d [pages %s-%s] heading=%s ref=%s text[:120]=%s",
                chunk.chunk_index, chunk.page_start, chunk.page_end,
                chunk.heading_context[:40] if chunk.heading_context else "(none)",
                chunk.scripture_reference or "(none)",
                chunk.text[:120],
            )
        return result

    # 3. Embed + upsert
    client = QdrantClient(url=config.QDRANT_URL)
    _ensure_ref_collection(client, collection_name)

    for chunk in chunks:
        content_hash = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
        vector = embed_client.embed_text(
            chunk.text, content_hash=content_hash, model=config.DEFAULT_EMBED_MODEL
        )
        if vector is None:
            result.chunks_skipped += 1
            result.errors.append(f"Chunk {chunk.chunk_index}: embedding failed")
            logger.warning("Embedding failed for chunk %d", chunk.chunk_index)
            continue

        point = _build_point(chunk, vector, identifier, source_id, volume, content_type)
        client.upsert(
            collection_name=collection_name,
            points=[point],
        )
        result.chunks_embedded += 1
        result.points_upserted += 1

    logger.info(
        "Ingest complete: %d chunks, %d embedded, %d skipped",
        result.chunks_total, result.chunks_embedded, result.chunks_skipped,
    )
    return result


def dry_run(
    canonical_path: Path,
    identifier: str,
) -> IngestResult:
    """Run ingestion without embedding or upserting."""
    return ingest(
        canonical_path=canonical_path,
        identifier=identifier,
        source_id="",
        volume="",
        apply=False,
    )
