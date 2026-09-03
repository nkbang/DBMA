"""NAE Benchmark Template Generator — 빈 placeholder 100개 생성.

TASK 3 (C1-TASK-ORDER-037):
- 실제 신학 문항 내용을 생성하지 않음
- 모든 필드 값은 빈 문자열/빈 리스트 등 placeholder
- CLI: python -m NAE.benchmark.template --count 100 --dataset-version v1 --output <path>
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List


def generate_placeholder_item(index: int, dataset_version: str) -> dict:
    """빈 placeholder BenchmarkItem 생성.

    모든 실제 값(text, gold_tsu_ids, expected_scriptures 등)은 빈 상태.
    """
    return {
        "benchmark_id": f"B{index:04d}",
        "question": {
            "text": "",
            "language": "ko",
            "question_type": "other",
            "theology_area": "",
        },
        "expected": {
            "gold_tsu_ids": [],
            "required_concepts": [],
            "expected_scriptures": [],
            "expected_doctrine": "",
        },
        "retrieval": {
            "top_k": 5,
        },
        "evaluation": {
            "status": "pending",
            "scores": {},
            "notes": "",
        },
        "metadata": {
            "created_version": dataset_version,
            "source": "template",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tsu_schema_version": "",
            "collector_version": "",
            "canonical_version": "",
        },
        "gold_tsu_ids": [],
        "difficulty": "beginner",
        "review_status": "draft",
    }


def generate_template(count: int, dataset_version: str) -> List[dict]:
    """placeholder 레코드 목록 생성."""
    return [generate_placeholder_item(i + 1, dataset_version) for i in range(count)]


def write_jsonl(records: List[dict], output_path: str) -> None:
    """JSONL 파일로 출력."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_parser() -> argparse.ArgumentParser:
    """CLI 파서 생성."""
    parser = argparse.ArgumentParser(
        prog="nae-benchmark-template",
        description="NAE Benchmark — 빈 placeholder 템플릿 생성 (실제 신학 내용 없음)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="생성할 placeholder 개수 (기본값: 100)",
    )
    parser.add_argument(
        "--dataset-version",
        type=str,
        default="v1",
        help="dataset_version 메타데이터 (기본값: v1)",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="출력 JSONL 경로",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    """CLI 메인 함수."""
    parser = build_parser()
    args = parser.parse_args(argv)

    records = generate_template(args.count, args.dataset_version)
    write_jsonl(records, args.output)

    print(f"Generated {len(records)} placeholder records -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
