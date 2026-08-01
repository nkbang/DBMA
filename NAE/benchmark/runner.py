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

from typing import Protocol

from NAE.benchmark.evaluator import Evaluator, EvaluationResult
from NAE.benchmark.loader import load_dataset
from NAE.benchmark.schema import BenchmarkItem

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Retriever Protocol (contract boundary)
# ------------------------------------------------------------------

class Retriever(Protocol):
    """Retrieval contract.

    retrieved_tsu_ids: list[str]
    → BenchmarkItem.gold_tsu_ids: list[str]
    → Evaluator → Recall@K / Precision@K / MRR / Hit Rate
    """

    def retrieve(self, query: str, k: int) -> List[str]:
        ...


# Type alias for backward compat (deprecated)
RetrievalFn = Callable[[str], List[str]]


class ConfigurationError(ValueError):
    """retriever 미주입 등 구성 오류."""

    pass


# ------------------------------------------------------------------
# Core Runner
# ------------------------------------------------------------------

def run_benchmark(
    dataset_path: str | Path,
    retrieval_fn: Optional[Retriever] = None,
    top_k: int = 5,
    output: str | Path | None = None,
    verbose: bool = False,
) -> Dict:
    """전체 벤치마크를 실행하고 리포트를 반환.

    canonical ground truth: BenchmarkItem.gold_tsu_ids (top-level only).

    Args:
        dataset_path: JSONL 데이터셋 경로.
        retrieval_fn: Retriever (injectable) 또는 None.
                      None 이면 명시적 ConfigurationError.
        top_k: 검색 결과 K.
        output: 보고서 출력 경로. None이면 파일에 쓰지 않음.
        verbose: 상세 로그 출력.

    Returns:
        리포트 딕셔너리.

    Raises:
        ConfigurationError: retrieval_fn 이 None 인 경우.
    """
    # retriever 필수화 — silent default 제거
    if retrieval_fn is None:
        raise ConfigurationError(
            "retrieval_fn is required. "
            "Provide a Retriever (injectable) or test-only FakeRetriever. "
            "Silent _dummy_retrieval() default path has been removed."
        )
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
            # Retriever Protocol: retrieve(query, k) -> List[str]
            if hasattr(retrieval_fn, "retrieve"):
                retrieved_ids = retrieval_fn.retrieve(qtext, top_k)
            else:
                # Deprecated: Callable[[str], List[str]]
                retrieved_ids = retrieval_fn(qtext)  # type: ignore[misc]
        except Exception as exc:
            logger.error("retrieval failed for %s: %s", qid, exc)
            errors += 1
            continue

        result = evaluator.evaluate(item, retrieved_ids)

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
    return parser


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

    # CLI 에서 retrieval_fn 은 직접 제공해야 함 (Phase 5.2 에서 구현)
    # 현재는 test-only 로만 사용 가능.
    logger.error(
        "CLI requires a retrieval_fn argument. "
        "Provide via Python API or implement --retrieval-fn module:func."
    )
    print(
        "ERROR: CLI requires retrieval_fn to be provided via Python API.",
        file=sys.stderr,
    )
    return 1

    # TODO: Phase 5.2 에서 실제 Qdrant client 연결 시 이 부분을 업데이트.


if __name__ == "__main__":
    sys.exit(main())