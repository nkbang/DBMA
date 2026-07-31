"""NAE Benchmark Metrics — Retrieval 지표 계산.

평가 대상: answer quality 아님.
검색 품질만 측정 (Recall@K, Precision@K, MRR).
"""

from __future__ import annotations

import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Individual Metrics
# ------------------------------------------------------------------

def recall_at_k(
    retrieved_ids: List[str],
    relevant_ids: List[str],
    k: int | None = None,
) -> float:
    """Top-K 안에 관련 결과가 몇 개 있는지 비율.

    Args:
        retrieved_ids: 검색 결과 TSU ID 목록 (순서 중요 아님).
        relevant_ids: gold standard 관련 TSU ID 목록.
        k: 사용할 K. None이면 len(retrieved_ids) 사용.

    Returns:
        0.0 ~ 1.0 사이의 Recall 값.
    """
    if not relevant_ids:
        # 관련 결과가 없으면 Recall은 1.0 (모두 정확)
        return 1.0

    if k is not None:
        retrieved_subset = retrieved_ids[:k]
    else:
        retrieved_subset = retrieved_ids

    relevant_set: Set[str] = set(relevant_ids)
    # 교집합 크기로 계산 — retrieved_subset에 동일 ID가 중복되어도
    # 한 번만 카운트한다 (중복 시 recall이 1.0을 초과하는 것을 방지).
    hits = len(relevant_set & set(retrieved_subset))

    return hits / len(relevant_ids)


def precision_at_k(
    retrieved_ids: List[str],
    relevant_ids: List[str],
    k: int | None = None,
) -> float:
    """Top-K 중 관련 결과의 비율.

    Args:
        retrieved_ids: 검색 결과 TSU ID 목록.
        relevant_ids: gold standard 관련 TSU ID 목록.
        k: 사용할 K. None이면 len(retrieved_ids) 사용.

    Returns:
        0.0 ~ 1.0 사이의 Precision 값.
    """
    if not retrieved_ids:
        return 0.0

    if k is not None:
        retrieved_subset = retrieved_ids[:k]
    else:
        retrieved_subset = retrieved_ids

    relevant_set: Set[str] = set(relevant_ids)
    # 분자는 고유 관련 항목 수 (동일 ID 중복 검색을 여러 hit으로 세지 않음),
    # 분모는 실제 반환된 결과 개수(중복 포함) — 검색기가 같은 결과를 중복
    # 반환하면 precision이 인위적으로 부풀려지지 않도록 한다.
    hits = len(relevant_set & set(retrieved_subset))

    return hits / len(retrieved_subset)


def mean_reciprocal_rank(
    retrieved_ids: List[str],
    relevant_ids: List[str],
) -> float:
    """첫 번째 관련 결과가 몇 번째인지 역수.

    Args:
        retrieved_ids: 검색 결과 TSU ID 목록 (순서 중요).
        relevant_ids: gold standard 관련 TSU ID 목록.

    Returns:
        1/rank 값. 관련 결과가 없으면 0.0.
    """
    relevant_set: Set[str] = set(relevant_ids)

    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in relevant_set:
            return 1.0 / rank

    return 0.0


# ------------------------------------------------------------------
# Aggregation Helpers
# ------------------------------------------------------------------

def hit_rate(
    retrieved_ids: List[str],
    relevant_ids: List[str],
    k: int | None = None,
) -> float:
    """Top-K 안에 최소 하나의 관련 결과가 있는지 여부.

    Args:
        retrieved_ids: 검색 결과 TSU ID 목록.
        relevant_ids: gold standard 관련 TSU ID 목록.
        k: 사용할 K. None이면 len(retrieved_ids) 사용.

    Returns:
        0.0 또는 1.0.
    """
    recall = recall_at_k(retrieved_ids, relevant_ids, k)
    return 1.0 if recall > 0.0 else 0.0


def compute_all_metrics(
    retrieved_ids: List[str],
    relevant_ids: List[str],
    top_k: int = 5,
) -> Dict[str, float]:
    """모든 지표를 한 번에 계산.

    Args:
        retrieved_ids: 검색 결과 TSU ID 목록.
        relevant_ids: gold standard 관련 TSU ID 목록.
        top_k: 사용할 K 값.

    Returns:
        {"recall@K": ..., "precision@K": ..., "mrr": ..., "hit_rate": ...}
    """
    return {
        f"recall@{top_k}": recall_at_k(retrieved_ids, relevant_ids, top_k),
        f"precision@{top_k}": precision_at_k(retrieved_ids, relevant_ids, top_k),
        "mrr": mean_reciprocal_rank(retrieved_ids, relevant_ids),
        f"hit_rate@{top_k}": hit_rate(retrieved_ids, relevant_ids, top_k),
    }