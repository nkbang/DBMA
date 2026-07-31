"""Duplicate/near-duplicate claim detection.

Two TSU records that make the same claim - possibly worded differently by
different authors (e.g. Gill vs Spurgeon both asserting the same point about
faith) - are flagged so downstream consumers can merge or de-duplicate rather
than double-count them in retrieval or scoring.

Uses the shared BGE-M3 embedding client (NAE.pipeline.embed), so this
similarity check reuses exactly the vectors Phase 4 will index - no separate
embedding call is wasted.
"""
from __future__ import annotations

from NAE.pipeline.embed import client as embed_client
from NAE.pipeline.embed import hashing
from NAE.pipeline.embed.similarity import cosine_similarity

from . import config


def find_duplicates(records: list[dict], *, threshold: float = config.DUPLICATE_SIMILARITY_THRESHOLD) -> dict[str, str]:
    """Return {tsu_id: duplicate_of_tsu_id} for records whose claim is a near-duplicate
    of an earlier record with the same doctrine. The earlier (lower-index) record
    in `records` is treated as canonical; later ones point to it.
    """
    duplicates: dict[str, str] = {}
    vectors: dict[str, list[float]] = {}

    for record in records:
        claim_text = record.get("claim")
        if not claim_text:
            continue
        content_hash = hashing.tsu_hash(
            claim=claim_text, book=record.get("book", ""),
            page=record.get("page", ""), scriptures=record.get("scriptures", []),
        )
        vector = embed_client.embed_text(claim_text, content_hash=content_hash)
        if vector is None:
            continue
        vectors[record["id"]] = vector

    seen: list[tuple[str, str | None, list[float]]] = []  # (id, doctrine, vector)
    for record in records:
        rid = record["id"]
        if rid not in vectors:
            continue
        doctrine = record.get("doctrine")
        vector = vectors[rid]

        match: str | None = None
        for other_id, other_doctrine, other_vector in seen:
            if doctrine != other_doctrine:
                continue
            if cosine_similarity(vector, other_vector) >= threshold:
                match = other_id
                break

        if match is not None:
            duplicates[rid] = match
        else:
            seen.append((rid, doctrine, vector))

    return duplicates
