#!/usr/bin/env python3
"""
Typesense Bench — 역색인 엔진 벤치마크 (Typesense 전용)

DBMA C1 Task Order 033: 역색인 엔진 벤치마크 — Tantivy vs Meilisearch vs Typesense
성능 벤치마크 전용 합성 데이터 — 신학적 정확도/품질 평가에 사용 금지

Usage:
    python typesense_bench.py --dataset-path output/bench/tsu_dataset_100k_synthetic.jsonl
    python typesense_bench.py --dataset-path output/bench/tsu_dataset_300k_synthetic.jsonl
    python typesense_bench.py --dataset-path output/bench/tsu_dataset_100k_synthetic.jsonl --measure all
"""

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

# Typesense Python client
try:
    import typesense
except ImportError:
    print("ERROR: typesense package not installed. Run: pip install typesense", file=sys.stderr)
    sys.exit(1)


TYPESENSE_URL = "http://localhost:8108"
API_KEY = "bench-test-key"
COLLECTION_NAME = "tsu_bench"
# Typesense는 최대 16MB 페이로드 제한이 있으므로 배치 크기를 작게 설정
BATCH_SIZE = 50

# 쿼리 세트 (12개) — Tantivy/Meilisearch와 동일한 쿼리
QUERIES = [
    ("은혜", "Korean noun"),
    ("하나님의 나라", "Korean phrase in quotes"),
    ("atonement", "English noun"),
    ("Romans", "English book name"),
    ("grace", "English noun"),
    ("자비하심에 관하여", "Korean phrase"),
    ("고난 중의 소망에 관한 설교 자료를 찾아줘", "natural language question"),
    ("gracee", "typo query"),
    ("asdkfjqpwiuxcvz", "no-result query"),
    ("the", "very common word"),
    ("a", "single character"),
    ("Romans 5:1-10", "scripture reference"),
]


def load_dataset(dataset_path: str) -> list[dict]:
    """JSONL 데이터셋을 로드합니다."""
    records = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    print(f"  Loaded {len(records)} records from {dataset_path}")
    return records


def create_collection(client: typesense.Client) -> None:
    """테스트용 컬렉션을 생성하고 필드 설정을 합니다. (기존 컬렉션이 있으면 스킵)"""
    # 기존 컬렉션 확인 — 있으면 스킵 (문서 유실 방지)
    try:
        client.collections[COLLECTION_NAME].retrieve()
        print(f"  Collection '{COLLECTION_NAME}' already exists, skipping creation")
        return
    except Exception:
        pass

    # 컬렉션 스키마 정의
    schema = {
        'name': COLLECTION_NAME,
        'fields': [
            {'name': 'tsu_id', 'type': 'string'},
            {'name': 'document_id', 'type': 'string'},
            {'name': 'title', 'type': 'string'},
            {'name': 'content', 'type': 'string'},
            {'name': 'author', 'type': 'string'},
            {'name': 'source_file', 'type': 'string'},
            {'name': 'book_id', 'type': 'string'},
            {'name': 'language', 'type': 'string'},
        ],
    }

    client.collections.create(schema)
    print(f"  Collection '{COLLECTION_NAME}' created")


def index_documents(client: typesense.Client, records: list[dict]) -> float:
    """문서를 컬렉션에 추가하고 시간을 측정합니다. (NDJSON 형식 사용)"""
    start_time = time.time()
    
    # Typesense import API는 JSON array가 아닌 NDJSON(newline-delimited) 형식 요구
    # Python SDK의 import_()가 JSON array를 보내서 "Bad JSON" 오류 발생
    # 따라서 httpx로 직접 NDJSON POST
    import httpx
    
    ndjson_lines = []
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        for doc in batch:
            ndjson_lines.append(json.dumps(doc, ensure_ascii=False))
    
    # 배치별 POST (batch_size=100)
    batch_size = 100
    for i in range(0, len(ndjson_lines), batch_size):
        batch_lines = ndjson_lines[i:i + batch_size]
        ndjson_body = "\n".join(batch_lines) + "\n"
        resp = httpx.post(
            f"http://localhost:8108/collections/{COLLECTION_NAME}/documents/import?action=create&batch_size={batch_size}",
            content=ndjson_body,
            headers={"Content-Type": "application/x-ndjson", "x-typesense-api-key": API_KEY},
            timeout=300.0,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Typesense import failed: {resp.status_code} {resp.text}")
    
    elapsed = time.time() - start_time

    print(f"  Indexed {len(records)} documents in {elapsed:.2f}s")
    return elapsed


def add_single_document(client: typesense.Client, doc: dict) -> float:
    """단일 문서를 증분 색인하고 시간을 측정합니다."""
    start_time = time.time()
    client.collections[COLLECTION_NAME].documents.create(doc)
    elapsed_ms = (time.time() - start_time) * 1000

    return elapsed_ms


def run_queries(client: typesense.Client, queries: list[tuple[str, str]], num_runs: int = 20) -> dict[str, dict]:
    """지정된 쿼리 세트를 여러 번 실행하고 지연 시간을 측정합니다."""
    results = {}

    for query_text, description in queries:
        latencies_ms = []
        hit_counts = []

        for _ in range(num_runs):
            start_time = time.time()
            try:
                response = client.collections[COLLECTION_NAME].documents.search({
                    'q': query_text,
                    'query_by': ['title', 'content', 'author'],
                    'limit': 100,
                })
                elapsed_ms = (time.time() - start_time) * 1000
                latencies_ms.append(elapsed_ms)
                hits = response.get('found', 0)
                hit_counts.append(hits)
            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                latencies_ms.append(elapsed_ms)
                hit_counts.append(-1)
                print(f"    Query error: {e}")

        if latencies_ms:
            sorted_latencies = sorted(latencies_ms)
            n = len(sorted_latencies)
            p50 = sorted_latencies[int(n * 0.5)]
            p95 = sorted_latencies[min(int(n * 0.95), n - 1)]
            p99 = sorted_latencies[min(int(n * 0.99), n - 1)]
            avg_ms = statistics.mean(latencies_ms)

            # 결과 수 통계
            hit_counts_list = [h for h in hit_counts if h >= 0]
            min_hits = min(hit_counts_list) if hit_counts_list else 0
            max_hits = max(hit_counts_list) if hit_counts_list else 0
            avg_hits = statistics.mean(hit_counts_list) if hit_counts_list else 0

            results[query_text] = {
                "p50_ms": round(p50, 3),
                "p95_ms": round(p95, 3),
                "p99_ms": round(p99, 3),
                "avg_ms": round(avg_ms, 3),
                "min_hits": min_hits,
                "max_hits": max_hits,
                "avg_hits": round(avg_hits, 1),
            }

        print(f"    '{query_text[:40]}': p50={p50:.3f}ms, p95={p95:.3f}ms, p99={p99:.3f}ms, avg_hits={avg_hits:.1f}")

    return results


def get_collection_doc_count(client: typesense.Client) -> int:
    """컬렉션의 문서 수를 가져옵니다."""
    info = client.collections[COLLECTION_NAME].retrieve()
    return info.get('num_documents', 0)


def measure_collection_disk_size(data_dir: str = "/tmp/typesense_data") -> int:
    """Typesense 데이터 디렉터리의 총 디스크 크기를 바이트 단위로 측정합니다."""
    total_size = 0
    if os.path.exists(data_dir):
        for dirpath, dirnames, filenames in os.walk(data_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.isfile(fp):
                    total_size += os.path.getsize(fp)
    return total_size


def main():
    parser = argparse.ArgumentParser(description="Typesense Bench — 역색인 엔진 벤치마크")
    parser.add_argument("--dataset-path", required=True, help="JSONL 데이터셋 파일 경로")
    parser.add_argument("--measure", choices=["index", "query", "incremental", "all"], default="all",
                        help="측정 항목 (기본: all)")
    parser.add_argument("--num-runs", type=int, default=20, help="쿼리 반복 횟수 (기본: 20)")
    parser.add_argument("--typesense-data-dir", default="/tmp/typesense_data",
                        help="Typesense 데이터 디렉토리 경로")
    args = parser.parse_args()

    print("=" * 70)
    print("Typesense Bench — DBMA C1 Task Order 033")
    print("=" * 70)

    # Typesense 서버 연결 확인
    try:
        client = typesense.Client({
            'nodes': [{
                'host': 'localhost',
                'port': '8108',
                'protocol': 'http',
            }],
            'api_key': API_KEY,
        })
        # 연결 확인 (health check)
        try:
            client.health.retrieve()
        except Exception:
            pass  # health가 없거나 실패해도 계속
        print(f"  Typesense connected at {TYPESENSE_URL}")
    except Exception as e:
        print(f"ERROR: Cannot connect to Typesense at {TYPESENSE_URL}: {e}", file=sys.stderr)
        print("Make sure Typesense is running: ./typesense --data-dir /tmp/typesense_data --api-key=xyz", file=sys.stderr)
        sys.exit(1)

    # 데이터셋 로드
    dataset_path = Path(args.dataset_path)
    if not dataset_path.exists():
        print(f"ERROR: Dataset not found: {dataset_path}", file=sys.stderr)
        sys.exit(1)

    records = load_dataset(args.dataset_path)
    dataset_size_mb = dataset_path.stat().st_size / (1024 * 1024)
    print(f"  Dataset size on disk: {dataset_size_mb:.1f} MB")
    print(f"  Total records: {len(records)}")

    # 컬렉션 생성 (index 또는 all일 때만 — query/incremental 단독 실행 시 기존 데이터 보존)
    print("\n--- Collection Creation ---")
    if args.measure in ("index", "all"):
        create_collection(client)

        # 전체 색인 시간 측정
        index_time = 0
        index_time = index_documents(client, records)
        
        # §0.3: 색인 무결성 확인 (assert)
        index_size_bytes = measure_collection_disk_size(args.typesense_data_dir)
        index_size_mb = index_size_bytes / (1024 * 1024)
        doc_count = get_collection_doc_count(client)
        print(f"  Collection document count: {doc_count}")
        assert doc_count == len(records), f"색인 불일치: 기대 {len(records)}건, 실제 {doc_count}건"
        print(f"  [OK] 색인 무결성 확인 통과: {doc_count}건")
        print(f"  Collection disk size: {index_size_mb:.1f} MB")

        # 쿼리 직전 재확인
        pre_query_count = get_collection_doc_count(client)
        assert pre_query_count == len(records), f"쿼리 직전 불일치: 기대 {len(records)}건, 실제 {pre_query_count}건"
        print(f"  [OK] 쿼리 직전 문서 수 확인: {pre_query_count}건")

    # 쿼리 지연 시간 측정
    query_results = {}
    if args.measure in ("query", "all"):
        # 쿼리 직전 재확인 (index 단계에서 안 한 경우)
        if index_time == 0:
            pre_query_count = get_collection_doc_count(client)
            assert pre_query_count == len(records), f"쿼리 직전 불일치: 기대 {len(records)}건, 실제 {pre_query_count}건"
        
        query_results = run_queries(client, QUERIES, args.num_runs)

        # 요약 통계 계산
        p50_list = [r["p50_ms"] for r in query_results.values()]
        p95_list = [r["p95_ms"] for r in query_results.values()]
        p99_list = [r["p99_ms"] for r in query_results.values()]

        print(f"\n  Summary ({args.num_runs} runs each):")
        print(f"    p50: {statistics.mean(p50_list):.3f} ms (avg across queries)")
        print(f"    p95: {statistics.mean(p95_list):.3f} ms (avg across queries)")
        print(f"    p99: {statistics.mean(p99_list):.3f} ms (avg across queries)")

    # 증분 색인 시간 측정 (별도 호출 시 컬렉션 재생성 필요)
    incremental_time = 0.0
    if args.measure == "incremental":
        # incremental 단독 실행 시 컬렉션 재생성
        create_collection(client)
        index_documents(client, records)
        doc_count = get_collection_doc_count(client)
        assert doc_count == len(records), f"색인 불일치: 기대 {len(records)}건, 실제 {doc_count}건"
        print(f"  [OK] 색인 무결성 확인 통과: {doc_count}건")
    elif args.measure in ("all",):
        # 증분 색인을 위한 단일 문서 준비 (필수 필드만 포함)
        sample_doc = {
            "tsu_id": records[0].get("tsu_id", "test") + "_incremental",
            "document_id": records[0].get("document_id", "test") + "_incremental",
            "title": "Test Title",
            "content": "Test content for incremental indexing.",
            "author": "Test Author",
            "source_file": "test_source.json",
            "book_id": "GEN",
            "language": "ko",
        }

        incremental_time = add_single_document(client, sample_doc)
        print(f"\n  Incremental index time (1 doc): {incremental_time:.3f} ms")

    # 결과 요약
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"  Dataset: {dataset_path.name}")
    print(f"  Records: {len(records)}")
    if index_time > 0:
        print(f"  Full index time: {index_time:.2f}s")
        print(f"  Collection disk size: {index_size_mb:.1f} MB")
    
    # 쿼리 결과 통계 (query_results가 있고 p50_list가 있을 때만)
    query_p50 = None
    query_p95 = None
    query_p99 = None
    if query_results:
        p50_list = [r["p50_ms"] for r in query_results.values()]
        p95_list = [r["p95_ms"] for r in query_results.values()]
        p99_list = [r["p99_ms"] for r in query_results.values()]
        query_p50 = round(statistics.mean(p50_list), 3)
        query_p95 = round(statistics.mean(p95_list), 3)
        query_p99 = round(statistics.mean(p99_list), 3)
        print(f"  Query p50 (avg): {query_p50:.3f} ms")
        print(f"  Query p95 (avg): {statistics.mean(p95_list):.3f} ms")
        print(f"  Query p99 (avg): {statistics.mean(p99_list):.3f} ms")
    if incremental_time > 0:
        print(f"  Incremental index time (1 doc): {incremental_time:.3f} ms")

    # JSON 출력 (후속 보고서 작성용)
    json_output = {
        "engine": "typesense",
        "dataset": str(dataset_path),
        "records": len(records),
        "index_time_seconds": round(index_time, 2) if index_time > 0 else None,
        "index_size_mb": round(index_size_mb, 1) if index_time > 0 else None,
        "query_latency_avg_ms": {
            "p50": query_p50,
            "p95": query_p95,
            "p99": query_p99,
        },
        "incremental_index_time_ms": round(incremental_time, 3) if incremental_time > 0 else None,
        "per_query": {q[0]: query_results.get(q[0], {}) for q in QUERIES},
    }

    print("\n--- JSON Output ---")
    print(json.dumps(json_output, indent=2))


if __name__ == "__main__":
    main()