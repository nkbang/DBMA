"""core/search_telemetry.py — Search Telemetry (DBMA-SEARCH-INFRA-001 HQ 제안 ⑨).

HQ: "현재 latency만 측정한다. 추가: 검색 성공률, Zero-hit 비율, Top1/Top5
Click, Average Candidate, Average Merge Time, Cache Hit, Embedding Time,
ANN Time — 이 데이터가 Retrieval 품질을 지속적으로 개선하는 기반이 된다."

SQLite-backed, same architecture as core/bible_index.py (a posting-list
table there, an events table here) — no new dependency.

Scope boundary: wired into `core.hybrid_candidate_pipeline.HybridQueryProcessor`
only, not into `core.retrieval.QueryProcessor` (which stays unmodified per
every prior phase in this project). Some HQ metrics genuinely don't apply to
this pipeline yet and are recorded honestly rather than invented:
  - Cache Hit: always False/0 — HQ 제안 ⑥(L1/L2/L3 캐시 계층)은 아직 미착수.
  - Embedding Time / ANN Time: always 0.0 — HybridRetriever has no vector/
    embedding search step (Stage 2 here is BM25 + theological + passage
    only, per the Phase 2 plan's Stage 1/2 split); these columns exist so
    the schema doesn't need to change again once a vector stage is added.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS search_query (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    query_text TEXT NOT NULL,
    route TEXT NOT NULL,
    result_count INTEGER NOT NULL,
    candidate_count INTEGER NOT NULL,
    latency_ms REAL NOT NULL,
    merge_time_ms REAL NOT NULL,
    embedding_time_ms REAL NOT NULL DEFAULT 0.0,
    ann_time_ms REAL NOT NULL DEFAULT 0.0,
    cache_hit INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS search_click (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_record_id INTEGER NOT NULL,
    tsu_id TEXT NOT NULL,
    rank INTEGER NOT NULL,
    timestamp REAL NOT NULL,
    FOREIGN KEY (query_record_id) REFERENCES search_query(id)
);
CREATE INDEX IF NOT EXISTS idx_search_click_query ON search_click(query_record_id);
"""


class SearchTelemetry:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def record_query(
        self,
        query_text: str,
        route: str,
        result_count: int,
        candidate_count: int,
        latency_ms: float,
        merge_time_ms: float = 0.0,
        embedding_time_ms: float = 0.0,
        ann_time_ms: float = 0.0,
        cache_hit: bool = False,
    ) -> int:
        """Record one query's telemetry. Returns the new row id, used by
        `record_click()` to correlate a later click back to this query."""
        cur = self._conn.execute(
            """INSERT INTO search_query
               (timestamp, query_text, route, result_count, candidate_count,
                latency_ms, merge_time_ms, embedding_time_ms, ann_time_ms, cache_hit)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                time.time(), query_text, route, result_count, candidate_count,
                latency_ms, merge_time_ms, embedding_time_ms, ann_time_ms, int(cache_hit),
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def record_click(self, query_record_id: int, tsu_id: str, rank: int) -> None:
        """`rank` is 1-indexed position in the result list the user clicked."""
        self._conn.execute(
            "INSERT INTO search_click (query_record_id, tsu_id, rank, timestamp) VALUES (?, ?, ?, ?)",
            (query_record_id, tsu_id, rank, time.time()),
        )
        self._conn.commit()

    # --- Aggregates -------------------------------------------------------

    def success_rate(self) -> float:
        """Fraction of recorded queries with result_count > 0."""
        return self._fraction("result_count > 0")

    def zero_hit_rate(self) -> float:
        """Fraction of recorded queries with result_count == 0."""
        return self._fraction("result_count = 0")

    def _fraction(self, where: str) -> float:
        total = self._conn.execute("SELECT COUNT(*) FROM search_query").fetchone()[0]
        if total == 0:
            return 0.0
        matched = self._conn.execute(f"SELECT COUNT(*) FROM search_query WHERE {where}").fetchone()[0]
        return matched / total

    def avg_candidate_count(self) -> float:
        return self._avg("candidate_count")

    def avg_merge_time_ms(self) -> float:
        return self._avg("merge_time_ms")

    def avg_latency_ms(self) -> float:
        return self._avg("latency_ms")

    def avg_embedding_time_ms(self) -> float:
        return self._avg("embedding_time_ms")

    def avg_ann_time_ms(self) -> float:
        return self._avg("ann_time_ms")

    def cache_hit_rate(self) -> float:
        return self._fraction("cache_hit = 1")

    def _avg(self, column: str) -> float:
        row = self._conn.execute(f"SELECT AVG({column}) FROM search_query").fetchone()
        return row[0] if row and row[0] is not None else 0.0

    def click_through_rate(self, top_n: int) -> float:
        """Fraction of queries where the clicked result's rank was <= top_n
        (Top1/Top5 Click from the HQ spec — call with top_n=1 or 5). A query
        with multiple clicks counts once if ANY of its clicks was within
        top_n."""
        total = self._conn.execute("SELECT COUNT(*) FROM search_query").fetchone()[0]
        if total == 0:
            return 0.0
        hit = self._conn.execute(
            "SELECT COUNT(DISTINCT query_record_id) FROM search_click WHERE rank <= ?",
            (top_n,),
        ).fetchone()[0]
        return hit / total

    def summary(self) -> dict[str, float]:
        """All aggregates in one call — what a telemetry dashboard would show."""
        return {
            "success_rate": self.success_rate(),
            "zero_hit_rate": self.zero_hit_rate(),
            "top1_click_rate": self.click_through_rate(1),
            "top5_click_rate": self.click_through_rate(5),
            "avg_candidate_count": self.avg_candidate_count(),
            "avg_merge_time_ms": self.avg_merge_time_ms(),
            "avg_latency_ms": self.avg_latency_ms(),
            "cache_hit_rate": self.cache_hit_rate(),
            "avg_embedding_time_ms": self.avg_embedding_time_ms(),
            "avg_ann_time_ms": self.avg_ann_time_ms(),
        }


def open_telemetry(db_path: Optional[str] = None) -> SearchTelemetry:
    if db_path is None:
        from core.config import DEFAULT_SEARCH_TELEMETRY_PATH

        db_path = DEFAULT_SEARCH_TELEMETRY_PATH
    return SearchTelemetry(db_path)
