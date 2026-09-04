"""TSU content-hash for embedding cache keys.

SHA256(tsu_schema_version + claim + book + page + scripture). schema_version
is required (no default) so callers must pass NAE.pipeline.tsu.config.
TSU_SCHEMA_VERSION explicitly - a future TSU record-shape change bumps that
constant, which changes every hash and naturally invalidates old cache
entries instead of silently reusing embeddings computed under a different
record shape.
"""
from __future__ import annotations

import hashlib


def tsu_hash(*, schema_version: str, claim: str, book: str, page: int | str, scriptures: list[str]) -> str:
    payload = "|".join([
        schema_version,
        claim or "",
        book or "",
        str(page),
        ",".join(sorted(scriptures or [])),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
