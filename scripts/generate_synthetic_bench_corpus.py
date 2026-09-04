#!/usr/bin/env python
"""
성능 벤치마크 전용 합성 데이터 — 신학적 정확도/품질 평가에 사용 금지

기존 TSU 데이터셋을 순환 반복하여 복제하고, tsu_id와 document_id에 _dupN 접미사를 붙여
유일성을 보장한다. content 등 나머지 필드는 원본 그대로 유지 (실제 텍스트 분포 유지).
"""

import argparse
import json
import os
import sys
import time


def generate_synthetic_corpus(
    source_path: str,
    output_path: str,
    target_size: int,
) -> None:
    """원본 JSONL을 순환 반복하여 target_size 크기까지 합성 데이터셋 생성."""
    if not os.path.isfile(source_path):
        print(f"[ERROR] source file not found: {source_path}", file=sys.stderr)
        sys.exit(1)

    # 원본 읽기
    with open(source_path, "r", encoding="utf-8") as f:
        original_records = [json.loads(line) for line in f if line.strip()]

    n_orig = len(original_records)
    if n_orig == 0:
        print("[ERROR] source file is empty", file=sys.stderr)
        sys.exit(1)

    full_cycles = target_size // n_orig
    remainder = target_size % n_orig

    total_written = 0
    start_time = time.time()

    with open(output_path, "w", encoding="utf-8") as out:
        # 완전 반복 사이클
        for cycle in range(full_cycles):
            for i, record in enumerate(original_records):
                dup_index = cycle * n_orig + i
                new_record = _make_dup_record(record, dup_index)
                out.write(json.dumps(new_record, ensure_ascii=False) + "\n")
                total_written += 1

        # 나머지 부분
        for i in range(remainder):
            dup_index = full_cycles * n_orig + i
            new_record = _make_dup_record(original_records[i], dup_index)
            out.write(json.dumps(new_record, ensure_ascii=False) + "\n")
            total_written += 1

    elapsed = time.time() - start_time
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[DONE] generated {total_written} records -> {output_path}")
    print(f"  elapsed: {elapsed:.2f}s")
    print(f"  file size: {file_size_mb:.2f} MB")


def _make_dup_record(record: dict, dup_index: int) -> dict:
    """record의 tsu_id와 document_id에 _dupN 접미사를 붙인 사본 반환."""
    new_record = dict(record)  # shallow copy of top-level keys

    # tsu_id에 _dupN 추가
    original_tsu_id = record.get("tsu_id", "")
    new_record["tsu_id"] = f"{original_tsu_id}_dup{dup_index}"

    # document_id에 _dupN 추가
    original_doc_id = record.get("document_id", "")
    new_record["document_id"] = f"{original_doc_id}_dup{dup_index}"

    return new_record


def main():
    parser = argparse.ArgumentParser(
        description="성능 벤치마크 전용 합성 데이터셋 생성 (원본 JSONL 순환 반복)"
    )
    parser.add_argument(
        "--target-size",
        type=int,
        required=True,
        help="생성할 목표 레코드 수 (예: 100000, 300000)",
    )
    parser.add_argument(
        "--source-path",
        type=str,
        default="output/bench/tsu_dataset.jsonl",
        help="원본 JSONL 파일 경로",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        required=True,
        help="출력 JSONL 파일 경로",
    )
    args = parser.parse_args()

    generate_synthetic_corpus(
        source_path=args.source_path,
        output_path=args.output_path,
        target_size=args.target_size,
    )


if __name__ == "__main__":
    main()