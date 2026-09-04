"""core/search_cache.py — Tiered Search Result Cache (DBMA-SEARCH-INFRA-001 HQ 제안 ⑥).

HQ: "현재는 Cache가 하나이다. 권장: L1 Memory → L2 SQLite → L3 Disk. 검색
결과와 질의 임베딩은 별도 캐시로 관리한다."

Scope: this module caches SEARCH RESULTS for `HybridQueryProcessor.process()`
— the "질의 임베딩(Query Embedding)" cache half of HQ ⑥ does not apply here
because `HybridRetriever` has no embedding/vector search stage at all (Stage
2 is BM25 + theological + passage only, per the Phase 2 plan's Stage split);
`core.retrieval.EmbeddingCache` already exists as its own single-tier cache
for the legacy RetrievalEngine path and is untouched. Building a second,
unused embedding cache here would just be dead code.

L1/L2 only, not L1/L2/L3: L2 (SQLite) is already disk-backed, so a separate
"L3 Disk" tier would be the same storage medium as L2 with no benefit — HQ's
three-tier list makes sense when L2 is a fast key-value service (e.g. Redis)
and L3 is cold storage; here L2 already IS the disk tier. Documented instead
of built as a hollow third layer.

Cache key includes the current TSU dataset's manifest fingerprint (same
`dataset_sha256` `ui/state/query_processor.py` already reads for staleness
detection) — this is the "컬렉션 색인 버전이 바뀌면 캐시 키에 버전 반영"
invalidation HQ asks for: a reindex changes the fingerprint, so old cache
rows become unreachable by construction, with no separate invalidation call
site needed in core/index_orchestrator.py.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
import unicodedata
from pathlib import Path
from typing import Any, Optional


def normalize_query(query: str) -> str:
    """Normalize a query string for cache-key purposes: Unicode NFKC, collapse
    whitespace, lowercase. Not a semantic normalizer — "은혜" vs "은혜 " vs
    "  은혜" should hit the same cache entry; "은혜" vs "Grace" should not
    (that would require translation, which this does not attempt)."""
    text = unicodedata.normalize("NFKC", query)
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def make_cache_key(
    query: str,
    k: int,
    file_scope: Optional[list[str]],
    dataset_fingerprint: Optional[str],
) -> str:
    """(정규화 검색어 + 필터 + 페이지) per HQ's 검색 결과 캐시 key spec, plus
    the dataset fingerprint for index-version invalidation."""
    normalized = normalize_query(query)
    scope_part = ",".join(sorted(file_scope)) if file_scope else ""
    raw = f"{normalized}|k={k}|scope={scope_part}|ds={dataset_fingerprint or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class _L1MemoryCache:
    """In-process dict cache with TTL — fastest tier, lost on restart."""

    def __init__(self, max_entries: int = 512) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._max_entries = max_entries

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        if len(self._store) >= self._max_entries and key not in self._store:
            # Evict the entry with the soonest expiry — simple, no LRU
            # bookkeeping needed for a cache this size.
            oldest_key = min(self._store, key=lambda k: self._store[k][0])
            del self._store[oldest_key]
        self._store[key] = (time.time() + ttl_seconds, value)

    def clear(self) -> None:
        self._store.clear()


class _L2SqliteCache:
    """SQLite-backed cache with TTL — survives process restarts, shared
    across all sessions in the app (same architecture as core/bible_index.py
    and core/search_telemetry.py)."""

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS cache_entry (
        key TEXT PRIMARY KEY,
        value_json TEXT NOT NULL,
        expires_at REAL NOT NULL
    );
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(self._SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def get(self, key: str) -> Optional[Any]:
        row = self._conn.execute(
            "SELECT value_json, expires_at FROM cache_entry WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        value_json, expires_at = row
        if time.time() > expires_at:
            self._conn.execute("DELETE FROM cache_entry WHERE key = ?", (key,))
            self._conn.commit()
            return None
        return json.loads(value_json)

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO cache_entry (key, value_json, expires_at) VALUES (?, ?, ?)",
            (key, json.dumps(value, ensure_ascii=False), time.time() + ttl_seconds),
        )
        self._conn.commit()

    def clear(self) -> None:
        self._conn.execute("DELETE FROM cache_entry")
        self._conn.commit()

    def purge_expired(self) -> int:
        cur = self._conn.execute("DELETE FROM cache_entry WHERE expires_at < ?", (time.time(),))
        self._conn.commit()
        return cur.rowcount


class SearchResultCache:
    """L1 (memory) → L2 (SQLite) tiered cache. `get()` checks L1 first, then
    L2 (and backfills L1 on an L2 hit so the next lookup is fast). `set()`
    writes both tiers."""

    def __init__(self, db_path: str | Path, l1_max_entries: int = 512) -> None:
        self.l1 = _L1MemoryCache(max_entries=l1_max_entries)
        self.l2 = _L2SqliteCache(db_path)

    def close(self) -> None:
        self.l2.close()

    def get(self, key: str) -> Optional[Any]:
        value = self.l1.get(key)
        if value is not None:
            return value
        value = self.l2.get(key)
        if value is not None:
            # L2 entries don't carry their remaining TTL back into L1 here —
            # a short fixed L1 backfill TTL is fine since L2 remains the
            # source of truth for the real expiry.
            self.l1.set(key, value, ttl_seconds=60.0)
        return value

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        self.l1.set(key, value, ttl_seconds)
        self.l2.set(key, value, ttl_seconds)

    def clear(self) -> None:
        self.l1.clear()
        self.l2.clear()
