#!/usr/bin/env python3
"""300k 단계 재개 — Meilisearch 색인은 서버에서 계속 진행 중이므로 reset하지 않고
완료를 기다린 뒤 쿼리/증분만 측정. Typesense 300k는 새로 실행."""
from __future__ import annotations

import json
import time

import httpx

import sys
sys.path.insert(0, "scripts/bench_search_engines")
from run_bench_reliable import (
    MEILI_URL, MEILI_KEY, load_dataset, meili_query, meili_incremental,
    meili_doc_count, meili_index_size_mb, ts_reset, ts_index, ts_doc_count,
    ts_query, ts_incremental,
)


def wait_meili_index_complete(client: httpx.Client, expected: int, timeout_s: float = 900.0) -> int:
    start = time.time()
    while time.time() - start < timeout_s:
        r = client.get(f"{MEILI_URL}/indexes/tsu_bench/stats", headers={"Authorization": f"Bearer {MEILI_KEY}"})
        d = r.json()
        if not d.get("isIndexing") and d.get("numberOfDocuments") == expected:
            return d["numberOfDocuments"]
        time.sleep(5)
    raise RuntimeError(f"Meilisearch 300k indexing did not complete in {timeout_s}s")


if __name__ == "__main__":
    records = load_dataset("output/bench/tsu_dataset_300k_synthetic.jsonl")
    n = len(records)
    print(f"Waiting for Meilisearch 300k indexing to finish (target={n})...", flush=True)

    with httpx.Client(timeout=60.0) as client:
        count = wait_meili_index_complete(client, n)
        print(f"Meilisearch 300k indexing complete: {count} docs verified", flush=True)
        size_mb = meili_index_size_mb(client)
        q = meili_query(client)
        incr_ms = meili_incremental(client, records[0])
        meili_result = {
            "doc_count_verified": count,
            "size_mb": round(size_mb, 1),
            "queries": q,
            "incremental_ms": round(incr_ms, 3),
            "note": "index_time_s not measured for this run (resumed after script crash; server-side indexing continued unattended)",
        }
        print("Meilisearch 300k query+incremental done", flush=True)

        print(f"Typesense 300k reset+index ({n} docs)...", flush=True)
        ts_reset(client)
        idx_time = ts_index(client, records)
        ts_count = ts_doc_count(client)
        assert ts_count == n, f"Typesense doc count mismatch: expected {n}, got {ts_count}"
        ts_q = ts_query(client)
        ts_incr = ts_incremental(client, records[0])
        ts_result = {
            "index_time_s": round(idx_time, 2),
            "doc_count_verified": ts_count,
            "queries": ts_q,
            "incremental_ms": round(ts_incr, 3),
        }
        print(f"Typesense 300k done: index={idx_time:.2f}s verified={ts_count}", flush=True)

    with open("/tmp/bench_reliable_results.json", "r", encoding="utf-8") as f:
        all_results = json.load(f)
    all_results.append({"scale": "300k", "n": n, "meilisearch": meili_result, "typesense": ts_result})
    with open("/tmp/bench_reliable_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print("ALL DONE (300k resumed)", flush=True)
