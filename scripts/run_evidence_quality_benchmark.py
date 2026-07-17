#!/usr/bin/env python3
"""scripts/run_evidence_quality_benchmark.py — Evidence Quality Benchmark Runner.

SPRINT19-D: independent Evidence Layer measurement, deliberately separate
from the Retrieval Layer (run_book_level_benchmark.py /
run_chapter_level_benchmark.py). Those two runners answer "did we find
it?" (exact book_id/chapter match against Gold). This runner answers a
different question — "how good is what we found as research evidence?"
— and never performs hit/miss judgment against expected_book_id/
expected_chapter. Reuses the existing chapter-level Gold Standard only
as a realistic query set (its questions, not its expected_* answers).

Per SPRINT19-D Preflight: Evidence Coverage, Citation Reliability, and
Metadata Completeness are kept as independent metrics, never combined
into a single "Evidence Trust Score" — combining them would blur
Retrieval Accuracy and Evidence Reliability into one number, which is
exactly the failure mode this Sprint's architecture is designed to
avoid.

core/retrieval.py, RetrievalEngine, BookEvaluator, ChapterEvaluator,
run_book_level_benchmark.py, run_chapter_level_benchmark.py, and Gold
Standard files are not modified by this script.

Usage:
    python -m scripts.run_evidence_quality_benchmark --dry-run
    python -m scripts.run_evidence_quality_benchmark
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Optional

from core.retrieval import RetrievalEngine, QueryProcessor, RankedCandidate
from core.config import DEFAULT_BENCH_DIR, DEFAULT_TSU_DATASET_PATH

_K_BUCKETS = (1, 5, 10)


def _chapter_present(candidate: RankedCandidate) -> bool:
    return "chapter" in candidate.metadata.get("verse_mapping", {})


def _confidence_of(candidate: RankedCandidate) -> Optional[float]:
    provenance = candidate.metadata.get("provenance")
    if not provenance or "confidence" not in provenance:
        return None
    return provenance["confidence"]


def _book_id_present(candidate: RankedCandidate) -> bool:
    return bool(candidate.metadata.get("verse_mapping", {}).get("book_id"))


def _verse_start_present(candidate: RankedCandidate) -> bool:
    return "verse_start" in candidate.metadata.get("verse_mapping", {})


def _provenance_present(candidate: RankedCandidate) -> bool:
    return bool(candidate.metadata.get("provenance"))


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

    n_queries = 0
    latencies_ms: list[float] = []

    # Coverage: candidates-with-chapter / total-candidates, per K bucket.
    coverage_hits = {k: 0 for k in _K_BUCKETS}
    coverage_totals = {k: 0 for k in _K_BUCKETS}

    # Citation reliability: average confidence among candidates that HAVE
    # confidence — missing candidates are excluded from the average, not
    # treated as 0 (HQ requirement), and tracked separately per bucket.
    confidence_sum = {k: 0.0 for k in _K_BUCKETS}
    confidence_present_count = {k: 0 for k in _K_BUCKETS}
    confidence_missing_count = {k: 0 for k in _K_BUCKETS}

    # Metadata completeness — diagnostic only, computed over the full
    # (largest, K=10) retrieved candidate pool actually seen.
    completeness_total = 0
    completeness_book_id = 0
    completeness_chapter = 0
    completeness_verse_start = 0
    completeness_provenance = 0

    for query in queries:
        qid = query.get("id", "")
        question = query.get("question", "")
        if not question:
            continue

        t_start = time.perf_counter()
        response = processor.process(question, query_id=qid, k=k_output)
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        latencies_ms.append(elapsed_ms)

        ranked = response.top_k_results
        if not ranked:
            continue

        n_queries += 1

        for k in _K_BUCKETS:
            bucket = ranked[:k]
            coverage_totals[k] += len(bucket)
            for candidate in bucket:
                if _chapter_present(candidate):
                    coverage_hits[k] += 1
                conf = _confidence_of(candidate)
                if conf is None:
                    confidence_missing_count[k] += 1
                else:
                    confidence_present_count[k] += 1
                    confidence_sum[k] += conf

        # Metadata completeness — full K=10 pool for this query.
        for candidate in ranked[:10]:
            completeness_total += 1
            if _book_id_present(candidate):
                completeness_book_id += 1
            if _chapter_present(candidate):
                completeness_chapter += 1
            if _verse_start_present(candidate):
                completeness_verse_start += 1
            if _provenance_present(candidate):
                completeness_provenance += 1

    avg_latency = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0

    def _ratio(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 4) if denominator else 0.0

    coverage = {
        f"at_{k}": _ratio(coverage_hits[k], coverage_totals[k])
        for k in _K_BUCKETS
    }
    citation_reliability = {
        f"at_{k}": _ratio(confidence_sum[k], confidence_present_count[k])
        for k in _K_BUCKETS
    }
    metadata_completeness = {
        "book_id": _ratio(completeness_book_id, completeness_total),
        "chapter": _ratio(completeness_chapter, completeness_total),
        "verse_start": _ratio(completeness_verse_start, completeness_total),
        "provenance": _ratio(completeness_provenance, completeness_total),
    }

    total_missing_confidence = confidence_missing_count[10]
    total_present_confidence = confidence_present_count[10]

    return {
        "id": "DBMA-EVIDENCE-QUALITY-BENCHMARK",
        "version": "1.0.0",
        "mode": "evidence_quality_evaluation",
        "gold_standard_version": gold_data.get("metadata", {}).get("dataset_version", "unknown"),
        "total_gold_queries": len(queries),
        "queries_evaluated": n_queries,
        "avg_latency_ms": round(avg_latency, 2),
        "queries": n_queries,
        "evidence_metrics": {
            "coverage": coverage,
            "citation_reliability": citation_reliability,
            "metadata_completeness": metadata_completeness,
        },
        "diagnostics": {
            "missing_confidence_count": total_missing_confidence,
            "present_confidence_count": total_present_confidence,
            "average_confidence": _ratio(confidence_sum[10], total_present_confidence),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Evidence Quality Benchmark.")
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
