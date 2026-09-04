"""NAE Benchmark Infrastructure — Phase 5

검색 품질 측정을 위한 벤치마크 인프라 모듈.

구성:
    schema   — Benchmark Question Unit 스키마
    loader   — JSONL 데이터셋 로더
    metrics  — Retrieval 지표 계산
    evaluator — 평가 실행 로직
    runner   — 전체 벤치마크 러너 + CLI
"""

from NAE.benchmark.schema import (
    BenchmarkItem,
    BenchmarkQuestion,
    BenchmarkExpected,
    BenchmarkRetrieval,
    BenchmarkEvaluation,
    BenchmarkMetadata,
    QUESTION_TYPES,
    DIFFICULTY_LEVELS,
    REVIEW_STATUSES,
)
from NAE.benchmark.loader import (
    load_dataset,
    validate_dataset,
    check_duplicate_benchmark_ids,
    check_empty_dataset,
)
from NAE.benchmark.metrics import (
    recall_at_k,
    precision_at_k,
    mean_reciprocal_rank,
)
from NAE.benchmark.evaluator import Evaluator
from NAE.benchmark.runner import run_benchmark, Retriever, ConfigurationError

__all__ = [
    # schema
    "BenchmarkItem",
    "BenchmarkQuestion",
    "BenchmarkExpected",
    "BenchmarkRetrieval",
    "BenchmarkEvaluation",
    "BenchmarkMetadata",
    "QUESTION_TYPES",
    "DIFFICULTY_LEVELS",
    "REVIEW_STATUSES",
    # loader
    "load_dataset",
    "validate_dataset",
    "check_duplicate_benchmark_ids",
    "check_empty_dataset",
    # metrics
    "recall_at_k",
    "precision_at_k",
    "mean_reciprocal_rank",
    # evaluator
    "Evaluator",
    # runner
    "run_benchmark",
    "Retriever",
    "ConfigurationError",
]
