"""NAE Benchmark Evaluator — 검색 결과 평가 로직.

RetrievalEngine를 직접 호출하지 않음.
caller가 retrieved_ids + relevant_ids를 전달하면 지표 계산 + 상태 업데이트만 수행.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from NAE.benchmark.metrics import compute_all_metrics
from NAE.benchmark.schema import BenchmarkItem

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Result Data Class
# ------------------------------------------------------------------

@dataclass
class EvaluationResult:
    """단일 질문에 대한 평가 결과."""

    benchmark_id: str = ""
    question_text: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)
    status: str = "pending"
    notes: str = ""


# ------------------------------------------------------------------
# Evaluator Class
# ------------------------------------------------------------------

class Evaluator:
    """벤치마크 평가기.

    사용법:
        evaluator = Evaluator(top_k=5)
        result = evaluator.evaluate(item)
        report = evaluator.report()
    """

    def __init__(
        self,
        top_k: int = 5,
        verbose: bool = False,
    ) -> None:
        self.top_k: int = top_k
        self.verbose: bool = verbose
        self.results: List[EvaluationResult] = []
        self._pending_count: int = 0
        self._passed_count: int = 0
        self._failed_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        item: BenchmarkItem,
        retrieved_ids: List[str],
        relevant_ids: List[str] | None = None,
    ) -> EvaluationResult:
        """단일 항목을 평가하고 결과를 반환.

        Args:
            item: BenchmarkItem (question + expected 포함).
            retrieved_ids: 검색 결과 TSU ID 목록 (순서 중요).
            relevant_ids: gold standard 관련 ID. None이면 item.expected 에서 추출.

        Returns:
            EvaluationResult
        """
        if relevant_ids is None:
            relevant_ids = item.expected.expected_scriptures or item.expected.required_concepts

        # 관련 결과가 완전히 비어있으면 special case
        if not relevant_ids:
            logger.warning(
                "benchmark_id=%s: relevant_ids가 비어있음 — 평가 스킵",
                item.benchmark_id,
            )
            result = EvaluationResult(
                benchmark_id=item.benchmark_id,
                question_text=item.question.text,
                metrics={},
                status="skipped",
                notes="relevant_ids empty",
            )
            self.results.append(result)
            self._pending_count += 1
            return result

        # 지표 계산
        effective_k = min(self.top_k, len(retrieved_ids))
        metrics = compute_all_metrics(retrieved_ids, relevant_ids, effective_k)

        # 상태 판정 (Recall@K >= 0.5 면 passed)
        recall_key = f"recall@{effective_k}"
        recall_value = metrics.get(recall_key, 0.0)
        status = "passed" if recall_value >= 0.5 else "failed"

        if status == "passed":
            self._passed_count += 1
        else:
            self._failed_count += 1

        result = EvaluationResult(
            benchmark_id=item.benchmark_id,
            question_text=item.question.text,
            metrics=metrics,
            status=status,
        )

        self.results.append(result)

        if self.verbose:
            logger.info(
                "benchmark_id=%s | recall@%d=%.3f | mrr=%.3f | status=%s",
                item.benchmark_id,
                effective_k,
                metrics.get(f"recall@{effective_k}", 0.0),
                metrics.get("mrr", 0.0),
                status,
            )

        return result

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def report(self) -> Dict:
        """전체 평가 리포트 생성."""
        total = len(self.results)
        if total == 0:
            return {
                "total_questions": 0,
                "metrics": {},
                "status_distribution": {"passed": 0, "failed": 0, "skipped": 0},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # 지표 평균 계산
        # 모든 결과의 metric key 합집합을 사용한다 — 첫 번째 결과가 skipped
        # (metrics={})인 경우 이후 결과의 실제 지표가 통째로 누락되는 것을 방지.
        avg_metrics: Dict[str, float] = {}
        metric_keys: List[str] = []
        seen_keys = set()
        for r in self.results:
            for key in r.metrics.keys():
                if key not in seen_keys:
                    seen_keys.add(key)
                    metric_keys.append(key)

        for key in metric_keys:
            values = [r.metrics[key] for r in self.results if key in r.metrics]
            if values:
                avg_metrics[key] = sum(values) / len(values)

        status_dist = {"passed": 0, "failed": 0, "skipped": 0}
        for r in self.results:
            if r.status in status_dist:
                status_dist[r.status] += 1

        return {
            "total_questions": total,
            "passed": self._passed_count,
            "failed": self._failed_count,
            "skipped": self._pending_count,
            "metrics": avg_metrics,
            "status_distribution": status_dist,
            "per_question": [
                {
                    "benchmark_id": r.benchmark_id,
                    "question": r.question_text,
                    "metrics": r.metrics,
                    "status": r.status,
                }
                for r in self.results
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def reset(self) -> None:
        """평가 상태 초기화."""
        self.results.clear()
        self._pending_count = 0
        self._passed_count = 0
        self._failed_count = 0