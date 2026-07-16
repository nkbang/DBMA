#!/usr/bin/env python3
"""scripts/run_book_level_benchmark.py — Book-level Retrieval Benchmark Runner.

SPRINT17-Phase6B-2: evaluates RetrievalEngine/QueryProcessor against
output/bench/book_level_gold_standard_v1.json (Phase6B-1), matching by
expected_book_id instead of expected_tsu_ids — book_id is stable across
TSU rebuilds (Phase6A-1/2, 100% coverage), tsu_id's sequential numbering
is not.

Deliberately independent of core.retrieval.run_benchmark_integration():
that function's Precision@K/MRR/nDCG computation is inlined in a loop
(not factored into reusable helpers) and matches on tsu_id, so this
runner reimplements the same standard IR formulas against a different
match predicate rather than modifying the ADR-001 authoritative file
(Phase6B-2-0 preflight confirmed this is the lowest-risk path).

core/retrieval.py is not modified by this script.

Usage:
    python -m scripts.run_book_level_benchmark --dry-run
    python -m scripts.run_book_level_benchmark
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any, Optional

from core.retrieval import RetrievalEngine, QueryProcessor, RankedCandidate
from core.config import DEFAULT_BENCH_DIR, DEFAULT_TSU_DATASET_PATH


class BookEvaluator:
    """Stateless — the only input it reads from a RankedCandidate is
    metadata["verse_mapping"]["book_id"] (Phase6B-2-0 preflight §2)."""

    @staticmethod
    def book_id_of(candidate: RankedCandidate) -> Optional[str]:
        return candidate.metadata.get("verse_mapping", {}).get("book_id")

    @staticmethod
    def is_hit(candidate: RankedCandidate, expected_book_id: str) -> bool:
        return BookEvaluator.book_id_of(candidate) == expected_book_id


def run_benchmark(
    gold_path: str | Path,
    tsu_path: str | Path = DEFAULT_TSU_DATASET_PATH,
    k_output: int = 10,
) -> dict[str, Any]:
    gold_path = Path(gold_path)
    if not gold_path.exists():
        return {"error": "Gold standard file not found", "gold_path": str(gold_path)}

    with open(gold_path, "r", encoding="utf-8") as f:
        gold_data = json.load(f)

    queries = gold_data.get("queries", [])
    if not queries:
        return {"error": "No queries in gold standard file"}

    engine = RetrievalEngine(tsu_dataset_path=tsu_path)
    processor = QueryProcessor(engine)

    hit_at_1 = 0
    hit_at_5 = 0
    total_hits_at_10 = 0
    rr_score = 0.0
    ndcg_at_10 = 0.0
    n_queries = 0
    latencies_ms: list[float] = []
    per_book: dict[str, dict[str, int]] = {}
    per_language: dict[str, dict[str, int]] = {}
    per_intent: dict[str, dict[str, int]] = {}
    failed_queries: list[dict[str, Any]] = []

    for query in queries:
        qid = query.get("id", "")
        question = query.get("question", "")
        expected_book_id = query.get("expected_book_id", "")
        language = query.get("language", "unknown")
        intent = query.get("intent", "unknown")
        if not expected_book_id:
            continue

        t_start = time.perf_counter()
        response = processor.process(question, query_id=qid, k=k_output)
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        latencies_ms.append(elapsed_ms)

        ranked = response.top_k_results
        if not ranked:
            continue

        n_queries += 1
        book_stats = per_book.setdefault(expected_book_id, {"queries": 0, "hit_at_1": 0})
        book_stats["queries"] += 1
        lang_stats = per_language.setdefault(language, {"queries": 0, "hit_at_1": 0})
        lang_stats["queries"] += 1
        intent_stats = per_intent.setdefault(intent, {"queries": 0, "hit_at_1": 0})
        intent_stats["queries"] += 1

        top1_hit = BookEvaluator.is_hit(ranked[0], expected_book_id)
        if top1_hit:
            hit_at_1 += 1
            book_stats["hit_at_1"] += 1
            lang_stats["hit_at_1"] += 1
            intent_stats["hit_at_1"] += 1
        else:
            failed_queries.append({
                "id": qid,
                "question": question,
                "expected_book_id": expected_book_id,
                "language": language,
                "intent": intent,
                "actual_top1_book_id": BookEvaluator.book_id_of(ranked[0]),
            })

        for r in ranked[:5]:
            if BookEvaluator.is_hit(r, expected_book_id):
                hit_at_5 += 1

        for r in ranked[:10]:
            if BookEvaluator.is_hit(r, expected_book_id):
                total_hits_at_10 += 1

        for rank_i, r in enumerate(ranked):
            if BookEvaluator.is_hit(r, expected_book_id):
                rr_score += 1.0 / (rank_i + 1)
                break

        # nDCG@10 — a query has exactly one "relevant class" (its book_id),
        # so the ideal ranking is all-relevant up to min(10, hits_at_10).
        actual_dcg = sum(
            1.0 / math.log2(rank_i + 2)
            for rank_i, r in enumerate(ranked[:10])
            if BookEvaluator.is_hit(r, expected_book_id)
        )
        hits_in_top10 = sum(1 for r in ranked[:10] if BookEvaluator.is_hit(r, expected_book_id))
        ideal_dcg = sum(1.0 / math.log2(i + 2) for i in range(hits_in_top10))
        if ideal_dcg > 0:
            ndcg_at_10 += actual_dcg / ideal_dcg

    avg_latency = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0
    n_queries_max = max(n_queries, 1)

    return {
        "id": "DBMA-BOOK-LEVEL-BENCHMARK",
        "version": "1.0.0",
        "mode": "book_level_evaluation",
        "gold_standard_version": gold_data.get("metadata", {}).get("dataset_version", "unknown"),
        "total_gold_queries": len(queries),
        "queries_evaluated": n_queries,
        "avg_latency_ms": round(avg_latency, 2),
        "metrics": {
            "precision_at_1": round(hit_at_1 / n_queries_max, 4),
            "precision_at_5": round(hit_at_5 / (n_queries_max * 5), 4),
            "mrr": round(rr_score / n_queries_max, 4),
            "ndcg_at_10": round(ndcg_at_10 / n_queries_max, 4),
            "hit_rate_at_10": round(total_hits_at_10 / (n_queries_max * 10), 4),
        },
        "per_book": {
            book_id: {
                "queries": stats["queries"],
                "precision_at_1": round(stats["hit_at_1"] / stats["queries"], 4) if stats["queries"] else 0.0,
            }
            for book_id, stats in sorted(per_book.items())
        },
        "per_language": {
            lang: {
                "queries": stats["queries"],
                "precision_at_1": round(stats["hit_at_1"] / stats["queries"], 4) if stats["queries"] else 0.0,
            }
            for lang, stats in sorted(per_language.items())
        },
        "per_intent": {
            intent: {
                "queries": stats["queries"],
                "precision_at_1": round(stats["hit_at_1"] / stats["queries"], 4) if stats["queries"] else 0.0,
            }
            for intent, stats in sorted(per_intent.items())
        },
        "failed_queries": failed_queries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the book-level retrieval benchmark.")
    parser.add_argument(
        "--gold-path",
        default=str(Path(DEFAULT_BENCH_DIR) / "book_level_gold_standard_v1.json"),
    )
    parser.add_argument("--tsu-path", default=DEFAULT_TSU_DATASET_PATH)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs only, do not run queries")
    args = parser.parse_args()

    gold_path = Path(args.gold_path)
    if args.dry_run:
        if not gold_path.exists():
            print(f"[DRY-RUN] gold file not found: {gold_path}")
            raise SystemExit(1)
        with open(gold_path, "r", encoding="utf-8") as f:
            gold_data = json.load(f)
        print(f"[DRY-RUN] gold file OK: {len(gold_data.get('queries', []))} queries")
        print(f"[DRY-RUN] tsu path: {args.tsu_path} (exists={Path(args.tsu_path).exists()})")
        return

    result = run_benchmark(gold_path, args.tsu_path, args.k)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
