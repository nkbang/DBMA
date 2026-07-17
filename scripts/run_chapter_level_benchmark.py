#!/usr/bin/env python3
"""scripts/run_chapter_level_benchmark.py — Chapter-level Retrieval Benchmark Runner.

SPRINT18-E: evaluates RetrievalEngine/QueryProcessor against
output/bench/chapter_level_gold_standard_v1.json (SPRINT18-D), matching by
expected_book_id AND expected_chapter (exact match on both) instead of
book_id alone.

Deliberately independent of run_book_level_benchmark.py / BookEvaluator
(SPRINT18-E Preflight §1, HQ decision 1): BookEvaluator is the Book-level
Benchmark's baseline and is not modified here so the two Benchmarks can
evolve and regress independently. ChapterEvaluator is a new, separate
class that reuses the same metadata access pattern
(candidate.metadata["verse_mapping"]) read-only.

Evaluation policy (from chapter_level_gold_standard_v1.json's metadata,
HQ decision 2): a hit requires book_id EXACT AND chapter EXACT.
RetrievalEngine._metadata_filter()'s +/-2 chapter tolerance is a
retrieval-time recall aid and is never used here as the pass/fail
criterion.

core/retrieval.py, RetrievalEngine, BookEvaluator, and
run_book_level_benchmark.py are not modified by this script.

Usage:
    python -m scripts.run_chapter_level_benchmark --dry-run
    python -m scripts.run_chapter_level_benchmark
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


class ChapterEvaluator:
    """Stateless — reads metadata["verse_mapping"]["book_id"] and
    metadata["verse_mapping"]["chapter"] from a RankedCandidate (same
    access pattern as BookEvaluator, kept separate per HQ decision 1)."""

    @staticmethod
    def book_id_of(candidate: RankedCandidate) -> Optional[str]:
        return candidate.metadata.get("verse_mapping", {}).get("book_id")

    @staticmethod
    def chapter_of(candidate: RankedCandidate) -> Optional[int]:
        return candidate.metadata.get("verse_mapping", {}).get("chapter")

    @staticmethod
    def is_book_hit(candidate: RankedCandidate, expected_book_id: str) -> bool:
        return ChapterEvaluator.book_id_of(candidate) == expected_book_id

    @staticmethod
    def is_hit(candidate: RankedCandidate, expected_book_id: str, expected_chapter: int) -> bool:
        return (
            ChapterEvaluator.is_book_hit(candidate, expected_book_id)
            and ChapterEvaluator.chapter_of(candidate) == expected_chapter
        )


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

    # [SPRINT19-C] Evidence adjustment diagnostic — corpus-wide provenance
    # coverage, independent of any single query. Baseline data for
    # SPRINT19-D's Evidence Benchmark design (HQ SPRINT19-C directive).
    records_with_confidence = 0
    confidence_sum = 0.0
    for tsu in engine.tsus:
        provenance = tsu.get("provenance")
        if provenance and "confidence" in provenance:
            records_with_confidence += 1
            confidence_sum += provenance["confidence"]
    total_tsus = len(engine.tsus)
    evidence_adjustment = {
        "records_with_confidence": records_with_confidence,
        "missing_confidence": total_tsus - records_with_confidence,
        "average_confidence": round(confidence_sum / records_with_confidence, 4) if records_with_confidence else 0.0,
    }

    hit_at_1 = 0
    hit_at_5 = 0
    total_hits_at_10 = 0
    rr_score = 0.0
    ndcg_at_10 = 0.0
    n_queries = 0
    book_only_hits = 0  # book correct, chapter wrong at top1 — chapter metadata quality signal
    latencies_ms: list[float] = []
    per_book: dict[str, dict[str, int]] = {}
    per_chapter: dict[str, dict[str, int]] = {}
    per_language: dict[str, dict[str, int]] = {}
    per_intent: dict[str, dict[str, int]] = {}
    failed_queries: list[dict[str, Any]] = []

    for query in queries:
        qid = query.get("id", "")
        question = query.get("question", "")
        expected_book_id = query.get("expected_book_id", "")
        expected_chapter = query.get("expected_chapter")
        language = query.get("language", "unknown")
        intent = query.get("intent", "unknown")
        if not expected_book_id or expected_chapter is None:
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
        chapter_key = f"{expected_book_id}-{expected_chapter}"
        chapter_stats = per_chapter.setdefault(chapter_key, {"queries": 0, "hit_at_1": 0})
        chapter_stats["queries"] += 1
        lang_stats = per_language.setdefault(language, {"queries": 0, "hit_at_1": 0})
        lang_stats["queries"] += 1
        intent_stats = per_intent.setdefault(intent, {"queries": 0, "hit_at_1": 0})
        intent_stats["queries"] += 1

        top1 = ranked[0]
        top1_hit = ChapterEvaluator.is_hit(top1, expected_book_id, expected_chapter)
        if top1_hit:
            hit_at_1 += 1
            book_stats["hit_at_1"] += 1
            chapter_stats["hit_at_1"] += 1
            lang_stats["hit_at_1"] += 1
            intent_stats["hit_at_1"] += 1
        else:
            actual_book_id = ChapterEvaluator.book_id_of(top1)
            actual_chapter = ChapterEvaluator.chapter_of(top1)
            book_correct = actual_book_id == expected_book_id
            chapter_correct = actual_chapter == expected_chapter
            if book_correct and not chapter_correct:
                book_only_hits += 1
            failed_queries.append({
                "query": question,
                "id": qid,
                "expected_book_id": expected_book_id,
                "expected_chapter": expected_chapter,
                "actual_book_id": actual_book_id,
                "actual_chapter": actual_chapter,
                "book_correct": book_correct,
                "chapter_correct": chapter_correct,
                "language": language,
                "intent": intent,
            })

        for r in ranked[:5]:
            if ChapterEvaluator.is_hit(r, expected_book_id, expected_chapter):
                hit_at_5 += 1

        for r in ranked[:10]:
            if ChapterEvaluator.is_hit(r, expected_book_id, expected_chapter):
                total_hits_at_10 += 1

        for rank_i, r in enumerate(ranked):
            if ChapterEvaluator.is_hit(r, expected_book_id, expected_chapter):
                rr_score += 1.0 / (rank_i + 1)
                break

        # nDCG@10 — relevant class is now the (book_id, chapter) pair.
        actual_dcg = sum(
            1.0 / math.log2(rank_i + 2)
            for rank_i, r in enumerate(ranked[:10])
            if ChapterEvaluator.is_hit(r, expected_book_id, expected_chapter)
        )
        hits_in_top10 = sum(
            1 for r in ranked[:10] if ChapterEvaluator.is_hit(r, expected_book_id, expected_chapter)
        )
        ideal_dcg = sum(1.0 / math.log2(i + 2) for i in range(hits_in_top10))
        if ideal_dcg > 0:
            ndcg_at_10 += actual_dcg / ideal_dcg

    avg_latency = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0
    n_queries_max = max(n_queries, 1)

    return {
        "id": "DBMA-CHAPTER-LEVEL-BENCHMARK",
        "version": "1.0.0",
        "mode": "chapter_level_evaluation",
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
        "book_only_hits": book_only_hits,
        "evidence_adjustment": evidence_adjustment,
        "per_book": {
            book_id: {
                "queries": stats["queries"],
                "precision_at_1": round(stats["hit_at_1"] / stats["queries"], 4) if stats["queries"] else 0.0,
            }
            for book_id, stats in sorted(per_book.items())
        },
        "per_chapter": {
            chapter_key: {
                "queries": stats["queries"],
                "precision_at_1": round(stats["hit_at_1"] / stats["queries"], 4) if stats["queries"] else 0.0,
            }
            for chapter_key, stats in sorted(per_chapter.items())
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
    parser = argparse.ArgumentParser(description="Run the chapter-level retrieval benchmark.")
    parser.add_argument(
        "--gold-path",
        default=str(Path(DEFAULT_BENCH_DIR) / "chapter_level_gold_standard_v1.json"),
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
