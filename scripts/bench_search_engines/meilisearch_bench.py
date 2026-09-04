#!/usr/bin/env python3
"""
Meilisearch Bench — 역색인 엔진 벤치마크 (Meilisearch 전용)

DBMA C1 Task Order 033: 역색인 엔진 벤치마크 — Tantivy vs Meilisearch vs Typesense
성능 벤치마크 전용 합성 데이터 — 신학적 정확도/품질 평가에 사용 금지

Root cause of previous 62,051 failure:
  Docs 57566-57585 are each ~290KB (identical large corpus docs).
  A batch of 50 including one of these -> ~14.5MB -> HTTP 413.
Fix: synchronous requests with retry + dynamic batch size starting at 100.

Usage:
    python meilisearch_bench.py --dataset-path output/bench/tsu_dataset_100k_synthetic.jsonl
    python meilisearch_bench.py --dataset-path output/bench/tsu_dataset_300k_synthetic.jsonl
"""

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

try:
    from meilisearch.client import Client
except ImportError:
    print("ERROR: meilisearch package not installed. Run: pip install meilisearch", file=sys.stderr)
    sys.exit(1)


MEILISEARCH_URL = "http://localhost:7700"
API_KEY = "bench-test-key"
INDEX_NAME = "tsu_bench"
INITIAL_BATCH_SIZE = 100


QUERIES = [
    ("은혜", "Korean noun"),
    ("하나님의 나라", "Korean phrase in quotes"),
    ("atonement", "English noun"),
    ("Romans", "English book name"),
    ("ACT AND book_id:ACT", "field filter query"),
    ("grace NOT law", "Boolean NOT query"),
    ("자비하심에 관하여", "Korean phrase"),
    ("고난 중의 소망에 관한 설교 자료를 찾아줘", "natural language question"),
    ("gracee", "typo query"),
    ("asdkfjqpwiuxcvz", "no-result query"),
    ("the", "very common word"),
    ("a", "single character"),
]


def load_dataset(dataset_path: str) -> list[dict]:
    records = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    print(f"  Loaded {len(records)} records from {dataset_path}")
    return records


def create_index(client: Client) -> None:
    try:
        existing = client.get_indexes()
        for idx in existing.get("results", []):
            if idx.get("name") == INDEX_NAME:
                task = client.delete_index(INDEX_NAME)
                client.wait_for_task(task.task_uid, timeout_in_ms=30000)
                break
    except Exception:
        pass
    time.sleep(0.5)

    task = client.create_index(INDEX_NAME, {"primaryKey": "tsu_id"})
    client.wait_for_task(task.task_uid, timeout_in_ms=30000)
    print(f"  Index '{INDEX_NAME}' created")

    settings = {
        "searchableAttributes": ["title", "content", "author"],
        "filterableAttributes": [
            "source_file",
            "book_id",
            "language",
        ],
        "rankingRules": [
            "words",
            "typo",
            "proximity",
            "attribute",
            "sort",
            "exactness",
        ],
    }
    task2 = client.get_index(INDEX_NAME).update_settings(settings)
    client.wait_for_task(task2.task_uid, timeout_in_ms=30000)
    print(f"  Index '{INDEX_NAME}' settings updated")

    # pagination.maxTotalHits 기본값(1000) -> 100000으로 변경 (100k/300k 색인용)
    task3 = client.get_index(INDEX_NAME).update_pagination_settings({"maxTotalHits": 100000})
    client.wait_for_task(task3.task_uid, timeout_in_ms=30000)
    print(f"  Index '{INDEX_NAME}' pagination updated (maxTotalHits=100000)")


def index_documents(client: Client, records: list[dict]) -> float:
    """Index all records using synchronous requests with dynamic batch size."""
    import httpx

    start_time = time.time()

    total_indexed = 0
    failed = 0
    current_batch_size = INITIAL_BATCH_SIZE

    print(f"  Starting with batch size: {current_batch_size}")

    for i in range(0, len(records), current_batch_size):
        actual_batch_size = min(current_batch_size, len(records) - i)
        batch = records[i:i + actual_batch_size]

        success = False
        while not success:
            try:
                post_http = httpx.Client(timeout=120.0)
                r = post_http.post(
                    f"{MEILISEARCH_URL}/indexes/{INDEX_NAME}/documents?primaryKey=tsu_id",
                    json=batch,
                )

                if r.status_code == 413:
                    if current_batch_size > 1:
                        current_batch_size = max(1, current_batch_size // 2)
                        print(f"    HTTP 413 at docs {i}-{i+len(batch)}: reducing batch to {current_batch_size}")
                        continue
                    else:
                        print(f"    ERROR at docs {i}-{i+len(batch)}: HTTP 413 even with batch=1, skipping", file=sys.stderr)
                        failed += len(batch)
                        success = True
                        continue

                if r.status_code != 202:
                    print(f"    ERROR at docs {i}: status={r.status_code} body={r.text[:200]}", file=sys.stderr)
                    failed += len(batch)
                    success = True
                    continue

                task_uid = r.json().get("taskUid")
                poll_url = f"{MEILISEARCH_URL}/tasks/{task_uid}"

                poll_http = httpx.Client(timeout=30.0)
                for attempt in range(1200):
                    tresp = poll_http.get(poll_url, timeout=30.0)
                    td = tresp.json()
                    status = td.get("status")
                    if status in ("succeeded", "failed", "canceled"):
                        break
                    time.sleep(0.5)
                else:
                    print(f"    WARNING: Task {task_uid} timed out after 120s", file=sys.stderr)
                    failed += len(batch)

                poll_http.close()
                total_indexed += len(batch)
                success = True

            except (httpx.ReadError, httpx.ConnectError, httpx.TimeoutException, ConnectionResetError) as e:
                print(f"    Connection error at docs {i}: {e}, retrying...", file=sys.stderr)
                time.sleep(1)
                continue
            finally:
                post_http.close()

        if i % 5000 == 0 and i > 0:
            print(f"    Progress: {i}/{len(records)} docs indexed, total={total_indexed}, batch={current_batch_size}")

    elapsed = time.time() - start_time
    print(f"  Total: {total_indexed}/{len(records)} indexed in {elapsed:.2f}s (failed={failed})")
    return elapsed


def add_single_document(client: Client, doc: dict) -> float:
    start_time = time.time()
    task = client.get_index(INDEX_NAME).add_documents([doc])
    client.wait_for_task(task.task_uid, timeout_in_ms=30000)
    elapsed_ms = (time.time() - start_time) * 1000
    return elapsed_ms


def run_queries(client: Client, queries: list[tuple], num_runs: int) -> dict:
    results = {}

    for query, desc in queries:
        latencies = []
        for run in range(num_runs):
            start_time = time.time()
            try:
                client.get_index(INDEX_NAME).search(query)
                latency_ms = (time.time() - start_time) * 1000
                latencies.append(latency_ms)
            except Exception as e:
                print(f"  ERROR query '{query}' run {run}: {e}", file=sys.stderr)

        if latencies:
            sorted_lat = sorted(latencies)
            results[(query, desc)] = {
                "p50_ms": round(statistics.median(latencies), 3),
                "p95_ms": round(sorted_lat[int(len(sorted_lat) * 0.95)], 3),
                "p99_ms": round(sorted_lat[int(len(sorted_lat) * 0.99)], 3),
                "avg_ms": round(statistics.mean(latencies), 3),
                "min_ms": round(min(latencies), 3),
                "max_ms": round(max(latencies), 3),
                "runs": len(latencies),
            }
        else:
            results[(query, desc)] = {"p50_ms": None, "p95_ms": None, "p99_ms": None, "runs": 0}

    return results


def measure_index_disk_size(data_dir: str) -> int:
    total = 0
    if os.path.exists(data_dir):
        for dirpath, _, filenames in os.walk(data_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.isfile(fp):
                    total += os.path.getsize(fp)
    return total


def get_index_doc_count(client: Client) -> int:
    try:
        stats = client.get_index(INDEX_NAME).get_stats()
        return stats.get("number_of_documents", 0)
    except Exception:
        import httpx
        with httpx.Client(timeout=30.0) as http:
            r = http.get(f"{MEILISEARCH_URL}/indexes/{INDEX_NAME}/stats")
            if r.status_code == 200:
                return r.json().get("numberOfDocuments", 0)
        return -1


def main():
    parser = argparse.ArgumentParser(description="Meilisearch Bench -- DBMA C1 Task Order 033")
    parser.add_argument("--dataset-path", required=True, help="JSONL dataset path")
    parser.add_argument("--measure", default="all", choices=["index", "query", "incremental", "all"],
                        help="Measurement type (default: all)")
    parser.add_argument("--num-runs", type=int, default=20, help="Query iteration count (default: 20)")
    parser.add_argument("--meilisearch-data-dir", default="/tmp/meilisearch_data",
                        help="Meilisearch data directory path")
    args = parser.parse_args()

    print("=" * 70)
    print("Meilisearch Bench -- DBMA C1 Task Order 033")
    print("=" * 70)

    try:
        client = Client(MEILISEARCH_URL, API_KEY)
        try:
            client.get_health()
        except Exception:
            pass
        print(f"  Meilisearch connected at {MEILISEARCH_URL}")
    except Exception as e:
        print(f"ERROR: Cannot connect to Meilisearch at {MEILISEARCH_URL}: {e}", file=sys.stderr)
        print("Make sure Meilisearch is running: meilisearch --db-path /tmp/meilisearch_data", file=sys.stderr)
        sys.exit(1)

    dataset_path = Path(args.dataset_path)
    if not dataset_path.exists():
        print(f"ERROR: Dataset not found: {dataset_path}", file=sys.stderr)
        sys.exit(1)

    records = load_dataset(args.dataset_path)
    dataset_size_mb = dataset_path.stat().st_size / (1024 * 1024)
    print(f"  Dataset size on disk: {dataset_size_mb:.1f} MB")
    print(f"  Total records: {len(records)}")

    # Index creation
    print("\n--- Index Creation ---")
    create_index(client)

    # Full index time measurement
    index_time = 0
    index_size_mb = 0
    if args.measure in ("index", "all"):
        index_time = index_documents(client, records)

        # Section 0.3: Index integrity check
        index_size_bytes = measure_index_disk_size(args.meilisearch_data_dir)
        index_size_mb = index_size_bytes / (1024 * 1024)
        doc_count = get_index_doc_count(client)
        print(f"  Index document count: {doc_count}")
        assert doc_count == len(records), f"Index mismatch: expected {len(records)}, actual {doc_count}"
        print(f"  [OK] Index integrity check passed: {doc_count} docs")
        print(f"  Index disk size: {index_size_mb:.1f} MB")

        # Pre-query recheck
        pre_query_count = get_index_doc_count(client)
        assert pre_query_count == len(records), f"Pre-query mismatch: expected {len(records)}, actual {pre_query_count}"
        print(f"  [OK] Pre-query doc count confirmed: {pre_query_count} docs")

    # Query latency measurement
    print("\n--- Query Latency ---")
    query_results = {}
    if args.measure in ("query", "all"):
        if index_time == 0:
            pre_query_count = get_index_doc_count(client)
            assert pre_query_count == len(records), f"Pre-query mismatch: expected {len(records)}, actual {pre_query_count}"

        query_results = run_queries(client, QUERIES, args.num_runs)

        p50_list = [r["p50_ms"] for r in query_results.values()]
        p95_list = [r["p95_ms"] for r in query_results.values()]
        p99_list = [r["p99_ms"] for r in query_results.values()]

        print(f"\n  Summary ({args.num_runs} runs each):")
        print(f"    p50: {statistics.mean(p50_list):.3f} ms (avg across queries)")
        print(f"    p95: {statistics.mean(p95_list):.3f} ms (avg across queries)")
        print(f"    p99: {statistics.mean(p99_list):.3f} ms (avg across queries)")

    # Incremental index time measurement
    incremental_time = 0.0
    if args.measure in ("incremental", "all"):
        sample_doc = records[0].copy()
        sample_doc["tsu_id"] = sample_doc.get("tsu_id", "test") + "_incremental"
        sample_doc["document_id"] = sample_doc.get("document_id", "test") + "_incremental"

        incremental_time = add_single_document(client, sample_doc)
        print(f"\n  Incremental index time (1 doc): {incremental_time:.3f} ms")

    # Results summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"  Dataset: {dataset_path.name}")
    print(f"  Records: {len(records)}")
    if index_time > 0:
        print(f"  Full index time: {index_time:.2f}s")
        print(f"  Index disk size: {index_size_mb:.1f} MB")
    if query_results:
        p50_list = [r["p50_ms"] for r in query_results.values()]
        p95_list = [r["p95_ms"] for r in query_results.values()]
        p99_list = [r["p99_ms"] for r in query_results.values()]
        print(f"  Query p50 (avg): {statistics.mean(p50_list):.3f} ms")
        print(f"  Query p95 (avg): {statistics.mean(p95_list):.3f} ms")
        print(f"  Query p99 (avg): {statistics.mean(p99_list):.3f} ms")
    if incremental_time > 0:
        print(f"  Incremental index time (1 doc): {incremental_time:.3f} ms")

    # JSON output
    json_output = {
        "engine": "meilisearch",
        "dataset": str(dataset_path),
        "records": len(records),
        "index_time_seconds": round(index_time, 2) if index_time > 0 else None,
        "index_size_mb": round(index_size_mb, 1) if index_time > 0 else None,
        "query_latency_avg_ms": {
            "p50": round(statistics.mean(p50_list), 3) if p50_list else None,
            "p95": round(statistics.mean(p95_list), 3) if p95_list else None,
            "p99": round(statistics.mean(p99_list), 3) if p99_list else None,
        },
        "incremental_index_time_ms": round(incremental_time, 3) if incremental_time > 0 else None,
        "per_query": {q[0]: r for q, r in zip(QUERIES, [query_results.get(q[0], {}) for q in QUERIES])},
    }

    print("\n--- JSON Output ---")
    print(json.dumps(json_output, indent=2))


if __name__ == "__main__":
    main()