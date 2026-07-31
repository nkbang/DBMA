#!/usr/bin/env python3
"""CUE 직접 실행 — Meilisearch/Typesense 신뢰성 있는 벤치마크 재실행.

C1이 반복적으로 인덱스 유실/부분 색인 실패를 겪은 뒤 CUE가 직접 인수받아
실행하는 단일 스크립트. 한 프로세스 안에서 delete -> create -> index ->
verify(assert) -> query -> incremental까지 전부 수행해, 여러 CLI 호출
사이에 인덱스가 지워지는 문제를 원천 차단한다.

성능 벤치마크 전용 합성 데이터 — 신학적 정확도/품질 평가에 사용 금지.
"""
from __future__ import annotations

import json
import statistics
import sys
import time

import httpx

MEILI_URL = "http://localhost:7700"
MEILI_KEY = "bench-test-key"
TS_URL = "http://localhost:8108"
TS_KEY = "bench-test-key"
INDEX = "tsu_bench"

QUERIES = [
    ("은혜", "Korean noun"),
    ("하나님의 나라", "Korean phrase"),
    ("atonement", "English noun"),
    ("Romans", "English book name"),
    ("grace", "English noun"),
    ("자비하심에 관하여", "Korean phrase"),
    ("고난 중의 소망에 관한 설교 자료를 찾아줘", "natural language"),
    ("gracee", "typo"),
    ("asdkfjqpwiuxcvz", "no-result"),
    ("the", "very common word"),
    ("a", "single char"),
    ("Romans 5:1-10", "scripture ref"),
]


def load_dataset(path: str) -> list[dict]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def pct(values: list[float], p: float) -> float:
    s = sorted(values)
    idx = min(len(s) - 1, int(len(s) * p))
    return s[idx]


# ---------------------------------------------------------------------------
# Meilisearch
# ---------------------------------------------------------------------------

def meili_reset(client: httpx.Client) -> None:
    r = client.delete(f"{MEILI_URL}/indexes/{INDEX}", headers={"Authorization": f"Bearer {MEILI_KEY}"})
    if r.status_code in (200, 202):
        task_uid = r.json().get("taskUid")
        try:
            meili_wait_task(client, task_uid)
        except RuntimeError:
            pass  # index_not_found on delete is fine — nothing to delete
    r = client.post(
        f"{MEILI_URL}/indexes",
        headers={"Authorization": f"Bearer {MEILI_KEY}"},
        json={"uid": INDEX, "primaryKey": "tsu_id"},
    )
    assert r.status_code in (200, 202), f"create index failed: {r.status_code} {r.text}"
    meili_wait_task(client, r.json()["taskUid"])
    r = client.patch(
        f"{MEILI_URL}/indexes/{INDEX}/settings",
        headers={"Authorization": f"Bearer {MEILI_KEY}"},
        json={"searchableAttributes": ["title", "content", "author"]},
    )
    meili_wait_task(client, r.json()["taskUid"])


def meili_wait_task(client: httpx.Client, task_uid, timeout_s: float = 60.0) -> dict:
    start = time.time()
    while time.time() - start < timeout_s:
        r = client.get(f"{MEILI_URL}/tasks/{task_uid}", headers={"Authorization": f"Bearer {MEILI_KEY}"})
        d = r.json()
        if d.get("status") in ("succeeded", "failed", "canceled"):
            if d.get("status") != "succeeded":
                raise RuntimeError(f"Meilisearch task {task_uid} ended with {d.get('status')}: {d}")
            return d
        time.sleep(0.2)
    raise RuntimeError(f"Meilisearch task {task_uid} timed out")


def meili_index(client: httpx.Client, records: list[dict]) -> float:
    start = time.time()
    batch_size = 1000
    i = 0
    last_task = None
    while i < len(records):
        batch = records[i:i + batch_size]
        r = client.post(
            f"{MEILI_URL}/indexes/{INDEX}/documents",
            headers={"Authorization": f"Bearer {MEILI_KEY}", "Content-Type": "application/json"},
            content=json.dumps(batch, ensure_ascii=False).encode("utf-8"),
        )
        if r.status_code == 413:
            batch_size = max(50, batch_size // 2)
            continue
        assert r.status_code in (200, 202), f"index batch failed: {r.status_code} {r.text[:300]}"
        last_task = r.json()["taskUid"]
        i += len(batch)
    meili_wait_task(client, last_task, timeout_s=120.0)
    return time.time() - start


def meili_doc_count(client: httpx.Client) -> int:
    r = client.get(f"{MEILI_URL}/indexes/{INDEX}/stats", headers={"Authorization": f"Bearer {MEILI_KEY}"})
    return r.json()["numberOfDocuments"]


def meili_index_size_mb(client: httpx.Client) -> float:
    r = client.get(f"{MEILI_URL}/stats", headers={"Authorization": f"Bearer {MEILI_KEY}"})
    d = r.json()
    size = d.get("indexes", {}).get(INDEX, {}).get("rawDocumentDbSize") or d.get("databaseSize", 0)
    return size / (1024 * 1024)


def meili_query(client: httpx.Client) -> dict:
    per_query = {}
    for q, desc in QUERIES:
        lat = []
        hits = None
        for _ in range(20):
            t0 = time.time()
            r = client.post(
                f"{MEILI_URL}/indexes/{INDEX}/search",
                headers={"Authorization": f"Bearer {MEILI_KEY}"},
                json={"q": q, "limit": 20},
            )
            lat.append((time.time() - t0) * 1000)
            hits = r.json().get("estimatedTotalHits")
        per_query[q] = {"desc": desc, "p50": pct(lat, 0.5), "p95": pct(lat, 0.95), "p99": pct(lat, 0.99), "hits": hits}
    return per_query


def meili_incremental(client: httpx.Client, sample: dict) -> float:
    doc = dict(sample)
    doc["tsu_id"] = doc["tsu_id"] + "_incr_test"
    t0 = time.time()
    r = client.post(
        f"{MEILI_URL}/indexes/{INDEX}/documents",
        headers={"Authorization": f"Bearer {MEILI_KEY}"},
        json=[doc],
    )
    meili_wait_task(client, r.json()["taskUid"], timeout_s=30.0)
    return (time.time() - t0) * 1000


# ---------------------------------------------------------------------------
# Typesense
# ---------------------------------------------------------------------------

TS_SCHEMA = {
    "name": INDEX,
    "fields": [
        {"name": "tsu_id", "type": "string"},
        {"name": "document_id", "type": "string"},
        {"name": "title", "type": "string", "optional": True},
        {"name": "content", "type": "string"},
        {"name": "author", "type": "string", "optional": True},
        {"name": "source_file", "type": "string", "optional": True},
        {"name": "book_id", "type": "string", "optional": True},
        {"name": "language", "type": "string", "optional": True},
    ],
}


def ts_reset(client: httpx.Client) -> None:
    client.delete(f"{TS_URL}/collections/{INDEX}", headers={"X-TYPESENSE-API-KEY": TS_KEY})
    r = client.post(f"{TS_URL}/collections", headers={"X-TYPESENSE-API-KEY": TS_KEY}, json=TS_SCHEMA)
    assert r.status_code == 201, f"create collection failed: {r.status_code} {r.text}"


def _flatten_for_ts(rec: dict) -> dict:
    return {
        "tsu_id": rec.get("tsu_id", ""),
        "document_id": rec.get("document_id", ""),
        "title": rec.get("title") or "",
        "content": rec.get("content") or "",
        "author": rec.get("author") or "",
        "source_file": rec.get("source_file") or "",
        "book_id": (rec.get("verse_mapping") or {}).get("book_id") or "",
        "language": rec.get("language") or "",
    }


def ts_index(client: httpx.Client, records: list[dict]) -> float:
    start = time.time()
    batch_size = 200
    i = 0
    while i < len(records):
        batch = records[i:i + batch_size]
        ndjson = "\n".join(json.dumps(_flatten_for_ts(r), ensure_ascii=False) for r in batch) + "\n"
        r = client.post(
            f"{TS_URL}/collections/{INDEX}/documents/import?action=create",
            headers={"X-TYPESENSE-API-KEY": TS_KEY, "Content-Type": "text/plain"},
            content=ndjson.encode("utf-8"),
            timeout=120.0,
        )
        assert r.status_code == 200, f"import failed: {r.status_code} {r.text[:300]}"
        for line in r.text.strip().split("\n"):
            d = json.loads(line)
            if not d.get("success", False):
                raise RuntimeError(f"Typesense import doc failed: {d}")
        i += len(batch)
    return time.time() - start


def ts_doc_count(client: httpx.Client) -> int:
    r = client.get(f"{TS_URL}/collections/{INDEX}", headers={"X-TYPESENSE-API-KEY": TS_KEY})
    return r.json()["num_documents"]


def ts_query(client: httpx.Client) -> dict:
    per_query = {}
    for q, desc in QUERIES:
        lat = []
        hits = None
        for _ in range(20):
            t0 = time.time()
            r = client.get(
                f"{TS_URL}/collections/{INDEX}/documents/search",
                headers={"X-TYPESENSE-API-KEY": TS_KEY},
                params={"q": q, "query_by": "title,content,author", "per_page": 20},
            )
            lat.append((time.time() - t0) * 1000)
            hits = r.json().get("found")
        per_query[q] = {"desc": desc, "p50": pct(lat, 0.5), "p95": pct(lat, 0.95), "p99": pct(lat, 0.99), "hits": hits}
    return per_query


def ts_incremental(client: httpx.Client, sample: dict) -> float:
    doc = _flatten_for_ts(sample)
    doc["tsu_id"] = doc["tsu_id"] + "_incr_test"
    t0 = time.time()
    r = client.post(
        f"{TS_URL}/collections/{INDEX}/documents",
        headers={"X-TYPESENSE-API-KEY": TS_KEY},
        json=doc,
    )
    assert r.status_code == 201, f"incremental insert failed: {r.status_code} {r.text}"
    return (time.time() - t0) * 1000


# ---------------------------------------------------------------------------

def run_for_scale(dataset_path: str, scale_label: str) -> dict:
    records = load_dataset(dataset_path)
    n = len(records)
    result: dict = {"scale": scale_label, "n": n}

    with httpx.Client(timeout=60.0) as client:
        print(f"[{scale_label}] Meilisearch reset+index ({n} docs)...", flush=True)
        meili_reset(client)
        idx_time = meili_index(client, records)
        count = meili_doc_count(client)
        assert count == n, f"Meilisearch doc count mismatch: expected {n}, got {count}"
        size_mb = meili_index_size_mb(client)
        q = meili_query(client)
        incr_ms = meili_incremental(client, records[0])
        result["meilisearch"] = {
            "index_time_s": round(idx_time, 2),
            "doc_count_verified": count,
            "size_mb": round(size_mb, 1),
            "queries": q,
            "incremental_ms": round(incr_ms, 3),
        }
        print(f"[{scale_label}] Meilisearch done: index={idx_time:.2f}s verified={count}", flush=True)

        print(f"[{scale_label}] Typesense reset+index ({n} docs)...", flush=True)
        ts_reset(client)
        idx_time = ts_index(client, records)
        count = ts_doc_count(client)
        assert count == n, f"Typesense doc count mismatch: expected {n}, got {count}"
        q = ts_query(client)
        incr_ms = ts_incremental(client, records[0])
        result["typesense"] = {
            "index_time_s": round(idx_time, 2),
            "doc_count_verified": count,
            "queries": q,
            "incremental_ms": round(incr_ms, 3),
        }
        print(f"[{scale_label}] Typesense done: index={idx_time:.2f}s verified={count}", flush=True)

    return result


if __name__ == "__main__":
    all_results = []
    for path, label in [
        ("output/bench/tsu_dataset_100k_synthetic.jsonl", "100k"),
        ("output/bench/tsu_dataset_300k_synthetic.jsonl", "300k"),
    ]:
        res = run_for_scale(path, label)
        all_results.append(res)
        with open("/tmp/bench_reliable_results.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"=== {label} COMPLETE, saved to /tmp/bench_reliable_results.json ===", flush=True)

    print("ALL DONE")
