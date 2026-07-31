"""NAE Benchmark Runner — 전체 벤치마크 실행 + CLI.

사용법 (CLI):
    python -m NAE.benchmark.runner \
        --dataset benchmark_v1.jsonl \
        --top-k 5 \
        --output report.json \
        --verbose

사용법 (Python API):
    from NAE.benchmark.runner import run_benchmark

    report = run_benchmark(
        dataset_path="benchmark_v1.jsonl",
        retrieval_fn=my_retrieval_function,
        top_k=5,
    )
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

from NAE.benchmark.evaluator import Evaluator, EvaluationResult
from NAE.benchmark.loader import load_dataset
from NAE.benchmark.schema import BenchmarkItem

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Type alias for retrieval function
# ------------------------------------------------------------------

# retrieval_fn: question text -> List[str] (TSU IDs)
RetrievalFn = Callable[[str], List[str]]


# ------------------------------------------------------------------
# Core Runner
# ------------------------------------------------------------------

def run_benchmark(
    dataset_path: str | Path,
    retrieval_fn: RetrievalFn,
    top_k: int = 5,
    output: str | Path | None = None,
    verbose: bool = False,
) -> Dict:
    """전체 벤치마크를 실행하고 리포트를 반환.

    Args:
        dataset_path: JSONL 데이터셋 경로.
        retrieval_fn: question_text -> List[tsu_id] 함수.
                      실제 Qdrant 검색 등을 여기에 연결.
        top_k: 검색 결과 K.
        output: 보고서 출력 경로. None이면 파일에 쓰지 않음.
        verbose: 상세 로그 출력.

    Returns:
        리포트 딕셔너리.
    """
    # 1. 데이터셋 로드
    logger.info("loading dataset: %s", dataset_path)
    items: List[BenchmarkItem] = load_dataset(dataset_path)
    logger.info("loaded %d items", len(items))

    if not items:
        logger.error("dataset is empty — aborting")
        return {"error": "dataset is empty", "timestamp": datetime.now(timezone.utc).isoformat()}

    # 2. 평가기 초기화
    evaluator = Evaluator(top_k=top_k, verbose=verbose)

    # 3. 각 질문별 검색 + 평가
    passed = 0
    failed = 0
    errors = 0

    for i, item in enumerate(items, start=1):
        qid = item.benchmark_id or f"Q{i}"
        qtext = item.question.text

        try:
            retrieved_ids = retrieval_fn(qtext)
        except Exception as exc:
            logger.error("retrieval failed for %s: %s", qid, exc)
            errors += 1
            continue

        relevant_ids = item.expected.expected_scriptures or item.expected.required_concepts
        result = evaluator.evaluate(item, retrieved_ids, relevant_ids)

        if result.status == "passed":
            passed += 1
        elif result.status == "failed":
            failed += 1

    # 4. 리포트 생성
    report = evaluator.report()
    report["dataset_path"] = str(dataset_path)
    report["top_k"] = top_k
    report["retrieval_errors"] = errors

    # 5. 파일 출력
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2, default=str)
        logger.info("report saved to %s", output_path)

    return report


# ------------------------------------------------------------------
# CLI Entry Point
# ------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """CLI 파서 생성."""
    parser = argparse.ArgumentParser(
        prog="nae-benchmark",
        description="NAE Benchmark Infrastructure — 검색 품질 측정",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        help="JSONL 데이터셋 경로 (예: NAE/benchmark/datasets/benchmark_v1.jsonl)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="검색 결과 K (기본값: 5)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="보고서 출력 경로 (기본값: stdout)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="상세 로그 출력",
    )
    parser.add_argument(
        "--retrieval-fn",
        type=str,
        default="dummy",
        help="검색 함수 이름 (기본값: dummy — 실제 연결 전까지 더미 사용)",
    )
    return parser


def _dummy_retrieval(question_text: str) -> List[str]:
    """더미 검색 함수 — 실제 Qdrant 연결 전까지 사용.

    TODO: 실제 Qdrant retrieval_fn으로 교체.
    """
    # 인프라 검증용: 빈 목록 반환 (모든 결과가 fail로 기록됨)
    # 실제 데이터가 필요하면 Phase 5.1에서 생성.
    return []


def main(argv: List[str] | None = None) -> int:
    """CLI 메인 함수.

    Returns:
        종료 코드 (0=성공, 1=실패).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # 로깅 설정
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # 검색 함수 선택
    retrieval_fn = _dummy_retrieval
    if args.retrieval_fn != "dummy":
        logger.warning("custom retrieval_fn은 아직 미구현 — dummy 사용")

    # 실행
    try:
        report = run_benchmark(
            dataset_path=args.dataset,
            retrieval_fn=retrieval_fn,
            top_k=args.top_k,
            output=args.output,
            verbose=args.verbose,
        )
    except Exception as exc:
        logger.error("benchmark failed: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # 결과 출력
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())