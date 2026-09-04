#!/usr/bin/env python
"""
Tantivy 역색인 엔진 벤치마크 스크립트

TSU JSONL 데이터셋을 Tantivy 인덱스에 색인하고, 쿼리 지연/증분 색인 시간을 측정한다.
성능 벤치마크 전용 — 신학적 정확도/품질 평가에 사용 금지.
"""

import argparse
import json
import os
import sys
import time
import pathlib

import tantivy
from tantivy import SchemaBuilder, Document


# ============================================================
# 스키마 정의 (TSU 매핑)
# ============================================================
def build_schema():
    """Tantivy 스키마 빌더 반환.
    - title, content: text 필드 (색인 대상)
    - tsu_id, source_file, book_id, language: facet 필드 (저장만, 색인 안 함)
    - page: integer 필드
    """
    schema_builder = SchemaBuilder()
    # text 필드 (색인됨 + 저장됨)
    schema_builder.add_text_field("title", stored=True)
    schema_builder.add_text_field("content", stored=True)
    # keyword 필드 (저장만, 색인 안 함 — 필터용)
    # tantivy Python 바인딩에는 add_str_field가 없음. text 필드로 저장하고 검색에서 제외
    schema_builder.add_text_field("tsu_id", stored=True)
    schema_builder.add_text_field("source_file", stored=True)
    schema_builder.add_text_field("book_id", stored=True)
    schema_builder.add_text_field("language", stored=True)
    # integer 필드
    schema_builder.add_integer_field("page", stored=True)
    return schema_builder.build()


def create_index(index_path: str, schema):
    """인덱스 디렉터리 생성 및 Index 객체 반환."""
    pathlib.Path(index_path).mkdir(parents=True, exist_ok=True)
    # tantivy.Index(schema, path_string)으로 새로 생성
    return tantivy.Index(schema, str(index_path))


# ============================================================
# 색인 생성
# ============================================================
def index_dataset(index_path: str, jsonl_path: str) -> float:
    """전체 데이터셋을 색인하고 소요 시간(초) 반환."""
    schema = build_schema()
    idx = create_index(index_path, schema)
    writer = idx.writer()

    start = time.time()
    count = 0
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)

            # verse_mapping에서 book_id 추출
            vm = record.get("verse_mapping")
            book_id = ""
            if isinstance(vm, dict):
                book_id = vm.get("book_id", "")
            elif isinstance(vm, str):
                book_id = vm

            doc = Document()
            title_val = record.get("title")
            doc.add_text("title", title_val if title_val is not None else "")
            content_val = record.get("content")
            doc.add_text("content", content_val if content_val is not None else "")
            tsu_id_val = record.get("tsu_id")
            doc.add_text("tsu_id", tsu_id_val if tsu_id_val is not None else "")
            sf_val = record.get("source_file")
            doc.add_text("source_file", sf_val if sf_val is not None else "")
            doc.add_text("book_id", book_id if book_id else "")
            lang_val = record.get("language")
            doc.add_text("language", lang_val if lang_val is not None else "")
            page_val = record.get("page")
            doc.add_integer("page", page_val if page_val is not None else 0)
            writer.add_document(doc)
            count += 1

    writer.commit()
    idx.reload()
    elapsed = time.time() - start
    print(f"  [Tantivy] indexed {count} records in {elapsed:.2f}s")
    return elapsed


def get_index_size_mb(index_path: str) -> float:
    """인덱스 디렉터리 총 용량 (MB)."""
    total = 0
    for root, dirs, files in os.walk(index_path):
        for f in files:
            total += os.path.getsize(os.path.join(root, f))
    return total / (1024 * 1024)


# ============================================================
# 쿼리 벤치마크
# ============================================================
def run_query(idx, query_text: str, top_k: int = 20):
    """단일 쿼리 실행하고 지연 시간(초) 반환. 검색 결과는 사용하지 않음."""
    # Tantivy Index.parse_query(query, default_field_names=...) 시그니처
    query = idx.parse_query(query_text, default_field_names=["title", "content"])

    start = time.time()
    searcher = idx.searcher()
    results = searcher.search(query, top_k)
    elapsed = time.time() - start
    return elapsed


def bench_queries(index_path: str, queries: list, iterations: int) -> dict:
    """여러 쿼리를 여러 번 반복 실행하고 p50/p95/p99 반환."""
    idx = tantivy.Index.open(str(index_path))

    results_map = {}  # query_text -> [latencies]

    for q in queries:
        latencies = []
        for _ in range(iterations):
            t = run_query(idx, q)
            latencies.append(t * 1000)  # ms
        results_map[q] = latencies

    # percentiles 계산
    summary = {}
    for q, lats in results_map.items():
        lats_sorted = sorted(lats)
        n = len(lats_sorted)
        p50 = lats_sorted[int(n * 0.50)]
        p95 = lats_sorted[int(n * 0.95)]
        p99 = lats_sorted[min(int(n * 0.99), n - 1)]
        avg = sum(lats) / n
        summary[q] = {
            "p50_ms": round(p50, 3),
            "p95_ms": round(p95, 3),
            "p99_ms": round(p99, 3),
            "avg_ms": round(avg, 3),
        }
    return summary


# ============================================================
# 증분 색인
# ============================================================
def benchmark_incremental(index_path: str, single_record: dict) -> float:
    """이미 구축된 인덱스에 문서 1건 추가하고 소요 시간(ms) 반환."""
    idx = tantivy.Index.open(str(index_path))
    writer = idx.writer()

    vm = single_record.get("verse_mapping")
    book_id = ""
    if isinstance(vm, dict):
        book_id = vm.get("book_id", "")
    elif isinstance(vm, str):
        book_id = vm

    doc = Document()
    doc.add_text("title", single_record.get("title", "") if single_record.get("title") is not None else "")
    doc.add_text("content", single_record.get("content", "") if single_record.get("content") is not None else "")
    doc.add_text("tsu_id", single_record.get("tsu_id", "") if single_record.get("tsu_id") is not None else "")
    doc.add_text("source_file", single_record.get("source_file", "") if single_record.get("source_file") is not None else "")
    doc.add_text("book_id", book_id if book_id else "")
    doc.add_text("language", single_record.get("language", "") if single_record.get("language") is not None else "")
    doc.add_integer("page", single_record.get("page") if single_record.get("page") is not None else 0)

    start = time.time()
    writer.add_document(doc)
    writer.commit()
    idx.reload()
    elapsed_ms = (time.time() - start) * 1000
    return elapsed_ms


# ============================================================
# 메인
# ============================================================
QUERIES_12 = [
    "은혜",
    '"하나님의 나라"',
    "atonement",
    "Romans",
    "ACT",  # book_id 필터는 Tantivy facet 쿼리로 구현 필요 (이벤트 벤치마크에서는 기본 텍스트 검색만)
    "grace",
    "자비하심에 관하여",
    "고난 중의 소망에 관한 설교 자료를 찾아줘",
    "gracee",
    "asdkfjqpwoeiuxcvz",
    "the",
    "a",
]


def main():
    parser = argparse.ArgumentParser(description="Tantivy 역색인 벤치마크")
    parser.add_argument("--index-dir", required=True, help="인덱스 저장 디렉터리")
    parser.add_argument("--data-path", help="TSU JSONL 데이터셋 경로 (index 모드 필수)")
    parser.add_argument("--mode", choices=["index", "query", "incremental"], default="index",
                        help="실행 모드: index(색인생성), query(쿼리벤치), incremental(증분색인)")
    parser.add_argument("--queries-path", help="쿼리 목록 JSON 파일 (기본값: 내장 12개)")
    parser.add_argument("--iterations", type=int, default=20, help="쿼리 반복 횟수")
    parser.add_argument("--single-record-path", help="증분 색인용 단일 레코드 JSONL 경로")
    args = parser.parse_args()

    if args.mode == "index":
        print(f"[Tantivy Bench] Indexing {args.data_path} -> {args.index_dir}")
        elapsed = index_dataset(args.index_dir, args.data_path)
        size_mb = get_index_size_mb(args.index_dir)
        print(f"  [Result] index_time: {elapsed:.2f}s")
        print(f"  [Result] index_size_mb: {size_mb:.2f}")

    elif args.mode == "query":
        queries = QUERIES_12
        if args.queries_path and os.path.isfile(args.queries_path):
            with open(args.queries_path, "r") as f:
                queries = [json.loads(line)["q"] for line in f if line.strip()]
        print(f"[Tantivy Bench] Query benchmark: {args.index_dir} ({len(queries)} queries x {args.iterations} iters)")
        summary = bench_queries(args.index_dir, queries, args.iterations)
        # 평균 p50/p95/p99 출력
        avg_p50 = sum(v["p50_ms"] for v in summary.values()) / len(summary)
        avg_p95 = sum(v["p95_ms"] for v in summary.values()) / len(summary)
        avg_p99 = sum(v["p99_ms"] for v in summary.values()) / len(summary)
        print(f"  [Result] avg_p50_ms: {avg_p50:.3f}")
        print(f"  [Result] avg_p95_ms: {avg_p95:.3f}")
        print(f"  [Result] avg_p99_ms: {avg_p99:.3f}")
        # 쿼리별 출력
        for q, s in summary.items():
            print(f"  [{q}] p50={s['p50_ms']:.3f} p95={s['p95_ms']:.3f} p99={s['p99_ms']:.3f}")

    elif args.mode == "incremental":
        if not args.single_record_path:
            print("[ERROR] --single-record-path required for incremental mode", file=sys.stderr)
            sys.exit(1)
        with open(args.single_record_path, "r") as f:
            record = json.loads(f.readline())
        elapsed_ms = benchmark_incremental(args.index_dir, record)
        print(f"  [Result] incremental_add_1_doc_ms: {elapsed_ms:.3f}")


if __name__ == "__main__":
    main()