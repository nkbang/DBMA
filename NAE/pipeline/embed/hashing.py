"""TSU content-hash for embedding cache keys.

Per Phase 4 gate review: SHA256(claim + book + page + scripture), so a TSU
record whose text/location/citations are unchanged is never re-embedded.
"""
from __future__ import annotations

import hashlib


def tsu_hash(*, claim: str, book: str, page: int | str, scriptures: list[str]) -> str:
    payload = "|".join([
        claim or "",
        book or "",
        str(page),
        ",".join(sorted(scriptures or [])),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
