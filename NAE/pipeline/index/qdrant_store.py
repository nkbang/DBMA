"""Qdrant collection management and upsert for the NAE TSU vector store (Phase 4)."""
from __future__ import annotations

import logging
import re

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from . import config

logger = logging.getLogger("nae.index.qdrant_store")

_TSU_ID_RE = re.compile(r"^TSU-(\d+)$")


def get_client(url: str = config.QDRANT_URL) -> QdrantClient:
    return QdrantClient(url=url)


def ensure_collection(client: QdrantClient, *, collection_name: str = config.COLLECTION_NAME,
                       vector_size: int = config.VECTOR_SIZE) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if collection_name in existing:
        return
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )


def tsu_id_to_point_id(tsu_id: str) -> int:
    """Qdrant requires an unsigned int or UUID point ID; TSU IDs are 'TSU-0000123'."""
    match = _TSU_ID_RE.match(tsu_id)
    if not match:
        raise ValueError(f"Unrecognized TSU id format: {tsu_id!r}")
    return int(match.group(1))


def build_point(record: dict, vector: list[float]) -> PointStruct:
    payload = {
        "tsu_id": record["id"],
        "book": record.get("book"),
        "author": record.get("author"),
        "identifier": record.get("identifier"),
        "source_identifier": record.get("source_identifier", record.get("identifier")),
        "doctrine": record.get("doctrine"),
        "page": record.get("page"),
        "paragraph": record.get("paragraph"),
        "sentence": record.get("sentence"),
        "claim": record.get("claim"),
        "source_text": record.get("source_text"),
        "scriptures": record.get("scriptures", []),
        "citations": record.get("citations", []),
        "review_status": record.get("review_status", "unverified"),
        "llm_score": record.get("llm_score", record.get("confidence")),
        "parser_score": record.get("parser_score"),
        "evidence_score": record.get("evidence_score"),
        "citation_score": record.get("citation_score"),
        "overall_score": record.get("overall_score"),
        "duplicate_of": record.get("duplicate_of"),
        # Reproducibility - which pipeline version produced each upstream artifact
        # this point was derived from (Phase 3.5 gate review, item 6).
        "tsu_schema_version": record.get("tsu_schema_version"),
        "collector_version": record.get("collector_version"),
        "canonical_version": record.get("canonical_version"),
    }
    return PointStruct(id=tsu_id_to_point_id(record["id"]), vector=vector, payload=payload)


def upsert_points(client: QdrantClient, points: list[PointStruct], *,
                   collection_name: str = config.COLLECTION_NAME) -> None:
    if not points:
        return
    client.upsert(collection_name=collection_name, points=points)
