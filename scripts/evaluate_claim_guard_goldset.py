#!/usr/bin/env python
"""scripts/evaluate_claim_guard_goldset.py — ClaimGuard 골드셋 평가 스크립트.

목적: goldset의 각 질의를 실제 파이프라인(QueryProcessor.process →
GenerationService.generate, 프로덕션 config의 RetrievalEngine/Ollama 모델
사용)으로 1회씩 실행하고, ClaimGuard 판정 결과를 기록한다.

실행:
    python scripts/evaluate_claim_guard_goldset.py tests/goldsets/claim_guard_goldset_v1.jsonl
    python scripts/evaluate_claim_guard_goldset.py                  # 기본 경로 사용

의존:
    - Ollama 서버가 로컬에서 실행 중이어야 함
    - 프로덕션 TSU 데이터셋(output/bench/tsu_dataset.jsonl)이 존재해야 함
    - 느림: 30개 질의 기준 수 분 소요 (CI/일반 회귀 테스트에 넣지 않음)

실패 처리:
    개별 질의(Ollama 오류 등)가 있어도 스크립트 전체가 죽지 않고
    해당 질의만 오류로 기록 후 계속 진행.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# DBMA 경로 설정
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import DEFAULT_TSU_DATASET_PATH, DEFAULT_GEN_MODEL, DEFAULT_TEMPERATURE
from core.retrieval import QueryProcessor
from core.generation import GenerationService

logger = logging.getLogger(__name__)


# ============================================================
# 데이터 모델
# ============================================================

@dataclass
class GoldsetQuery:
    """goldset의 개별 질의."""
    id: str
    query: str
    expected_risk_terms: list[str]
    category: str  # absolute_first | absolute_only | absolute_universal | neutral


@dataclass
class EvalResult:
    """단일 질의의 평가 결과."""
    id: str
    query: str
    category: str
    expected_risk_terms: list[str]
    actual_risk_level: str = ""
    actual_matched_terms: list[str] = field(default_factory=list)
    is_true_positive: bool = False
    is_false_positive: bool = False
    is_false_negative: bool = False
    absolute_claim_blocked: bool = False
    scope_qualifier_required: bool = False
    competing_candidates_found: bool = False
    suggested_wording: str | None = None
    error: str | None = None
    latency_ms: float = 0.0
    generated_answer: str = ""  # §2.1 계측: LLM이 생성한 실제 답변 전체 텍스트


# ============================================================
# goldset 로드
# ============================================================

def load_goldset(path: Path) -> list[GoldsetQuery]:
    """goldset jsonl 파일을 로드한다."""
    queries: list[GoldsetQuery] = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                queries.append(GoldsetQuery(
                    id=obj["id"],
                    query=obj["query"],
                    expected_risk_terms=obj.get("expected_risk_terms", []),
                    category=obj.get("category", "neutral"),
                ))
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("[goldset 로드 경고] %s 라인 %d: %s — 건너뜀", path, line_num, e)
    return queries


# ============================================================
# 단일 질의 평가
# ============================================================

def evaluate_one(
    q: GoldsetQuery,
    processor: QueryProcessor,
    generator: GenerationService,
) -> EvalResult:
    """단일 질의를 실제 파이프라인으로 실행하고 ClaimGuard 결과를 기록한다."""
    result = EvalResult(
        id=q.id,
        query=q.query,
        category=q.category,
        expected_risk_terms=q.expected_risk_terms,
    )

    t_start = time.perf_counter()
    try:
        # 1. QueryProcessor.process(query) 호출
        response = processor.process(q.query, query_id=q.id)

        # 2. GenerationService.generate(response) 호출
        gen_result = generator.generate(
            response,
            gen_model=DEFAULT_GEN_MODEL,
            temperature=DEFAULT_TEMPERATURE,
        )

        # 3. ClaimGuard 결과 기록
        if gen_result.claim_guard_result is not None:
            result.actual_risk_level = gen_result.claim_guard_result.risk_level.value
            result.actual_matched_terms = gen_result.claim_guard_result.matched_terms
            result.absolute_claim_blocked = gen_result.claim_guard_result.absolute_claim_blocked
            result.scope_qualifier_required = gen_result.claim_guard_result.scope_qualifier_required
            result.competing_candidates_found = gen_result.claim_guard_result.competing_candidates_found
            result.suggested_wording = gen_result.claim_guard_result.suggested_wording

        # 4. §2.1 계측: 실제 생성된 답변 텍스트 저장 (기존 4번 → 5번으로 번호 재조정)
        result.generated_answer = gen_result.answer if gen_result else ""

        # 5. expected_risk_terms와 실제 matched_terms 비교
        if q.category == "neutral":
            # neutral인데 matched_terms가 비어있지 않으면 "예상외 탐지"(false positive)
            if result.actual_matched_terms:
                result.is_false_positive = True
        else:
            # absolute_* 카테고리인데 matched_terms가 비어있으면 "미탐지"(false negative)
            if not result.actual_matched_terms:
                result.is_false_negative = True
            # expected_risk_terms 중 하나가 matched_terms에 있으면 true positive
            for term in q.expected_risk_terms:
                if term in result.actual_matched_terms:
                    result.is_true_positive = True
                    break

        # Ollama 오류 처리
        if gen_result.error:
            result.error = f"생성 오류: {gen_result.error}"
            logger.warning("[evaluate_one] 질의 %s: %s", q.id, result.error)

    except Exception as e:
        result.error = f"실행 오류: {e}"
        logger.error("[evaluate_one] 질의 %s 실행 실패: %s", q.id, e, exc_info=True)
    finally:
        result.latency_ms = (time.perf_counter() - t_start) * 1000

    return result


# ============================================================
# 요약 및 리포트
# ============================================================

def summarize(results: list[EvalResult]) -> dict[str, Any]:
    """전체 평가 결과를 요약한다."""
    total = len(results)
    true_positive = sum(1 for r in results if r.is_true_positive)
    false_positive = sum(1 for r in results if r.is_false_positive)
    false_negative = sum(1 for r in results if r.is_false_negative)
    errors = sum(1 for r in results if r.error is not None)
    successful = total - errors

    # category별 분포
    by_category: dict[str, dict[str, int]] = {}
    for r in results:
        by_category.setdefault(r.category, {"tp": 0, "fp": 0, "fn": 0, "other": 0})
        if r.is_true_positive:
            by_category[r.category]["tp"] += 1
        elif r.is_false_positive:
            by_category[r.category]["fp"] += 1
        elif r.is_false_negative:
            by_category[r.category]["fn"] += 1
        else:
            by_category[r.category]["other"] += 1

    # 평균 지연시간
    successful_results = [r for r in results if r.error is None]
    avg_latency_ms = (
        sum(r.latency_ms for r in successful_results) / len(successful_results)
        if successful_results else 0.0
    )

    return {
        "total": total,
        "successful": successful,
        "errors": errors,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "by_category": by_category,
        "avg_latency_ms": round(avg_latency_ms, 2),
    }


def print_report(results: list[EvalResult], summary: dict[str, Any]) -> None:
    """평가 리포트를 stdout에 출력한다."""
    print("=" * 70)
    print("ClaimGuard 골드셋 평가 결과")
    print("=" * 70)
    print(f"총 질의 수:     {summary['total']}")
    print(f"성공:           {summary['successful']}")
    print(f"오류:           {summary['errors']}")
    print(f"정탐(true pos): {summary['true_positive']}")
    print(f"오탐(false pos):{summary['false_positive']}")
    print(f"미탐(false neg):{summary['false_negative']}")
    print(f"평균 지연시간:   {summary['avg_latency_ms']:.2f} ms")
    print()

    # category별 분포
    print("--- category별 분포 ---")
    for cat, counts in sorted(summary["by_category"].items()):
        print(f"  {cat}: tp={counts['tp']} fp={counts['fp']} fn={counts['fn']} other={counts['other']}")
    print()

    # 미탐지(false negative) 사례
    false_negatives = [r for r in results if r.is_false_negative]
    if false_negatives:
        print("--- 미탐지(false negative) 사례 ---")
        for r in false_negatives:
            print(f"  [{r.id}] query={r.query!r}")
            print(f"    expected: {r.expected_risk_terms}")
            print(f"    actual_matched: {r.actual_matched_terms}")
            print()

    # 오탐(false positive) 사례
    false_positives = [r for r in results if r.is_false_positive]
    if false_positives:
        print("--- 오탐(false positive) 사례 ---")
        for r in false_positives:
            print(f"  [{r.id}] query={r.query!r}")
            print(f"    expected: {r.expected_risk_terms}")
            print(f"    actual_matched: {r.actual_matched_terms}")
            print()

    # 오류 사례
    errors = [r for r in results if r.error is not None]
    if errors:
        print("--- 오류 사례 ---")
        for r in errors:
            print(f"  [{r.id}] query={r.query!r}")
            print(f"    error: {r.error}")
            print()


# ============================================================
# 메인
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="ClaimGuard 골드셋 평가 스크립트"
    )
    parser.add_argument(
        "goldset_path",
        nargs="?",
        default=None,
        help="goldset jsonl 파일 경로 (기본값: tests/goldsets/claim_guard_goldset_v1.jsonl)",
    )
    args = parser.parse_args()

    goldset_path = Path(args.goldset_path) if args.goldset_path else Path(__file__).parent.parent / "tests" / "goldsets" / "claim_guard_goldset_v1.jsonl"

    if not goldset_path.exists():
        logger.error("goldset 파일을 찾을 수 없습니다: %s", goldset_path)
        sys.exit(1)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    # goldset 로드
    queries = load_goldset(goldset_path)
    if not queries:
        logger.error("goldset에 질이가 없습니다.")
        sys.exit(1)
    logger.info("goldset 로드 완료: %d개 질의", len(queries))

    # QueryProcessor + GenerationService 초기화 (프로덕션 설정 그대로)
    logger.info("QueryProcessor 초기화 중...")
    processor = QueryProcessor()
    generator = GenerationService()
    logger.info("초기화 완료")

    # 각 질의 평가
    results: list[EvalResult] = []
    t_total_start = time.perf_counter()

    for i, q in enumerate(queries, 1):
        logger.info("[%d/%d] 질의 평가 중: %s ...", i, len(queries), q.id)
        r = evaluate_one(q, processor, generator)
        results.append(r)
        status = "OK"
        if r.is_true_positive:
            status = "TP"
        elif r.is_false_positive:
            status = "FP"
        elif r.is_false_negative:
            status = "FN"
        elif r.error:
            status = "ERR"
        logger.info("  [%s] latency=%.0fms risk=%s matched=%s",
                     status, r.latency_ms, r.actual_risk_level, r.actual_matched_terms)

    t_total_ms = (time.perf_counter() - t_total_start) * 1000

    # 요약
    summary = summarize(results)
    print_report(results, summary)

    print(f"\n총 소요시간: {t_total_ms / 1000:.1f} 초")
    print()

    # 결과 JSON 저장
    output_dir = Path(__file__).parent.parent / "output" / "claim_guard_eval"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_file = output_dir / f"goldset_v1_result_{timestamp}.json"

    # serializable한 형태로 변환 (§2.1 generated_answer 추가)
    output_data = {
        "evaluated_at": timestamp,
        "goldset_path": str(goldset_path),
        "total": summary["total"],
        "successful": summary["successful"],
        "errors": summary["errors"],
        "true_positive": summary["true_positive"],
        "false_positive": summary["false_positive"],
        "false_negative": summary["false_negative"],
        "by_category": summary["by_category"],
        "avg_latency_ms": summary["avg_latency_ms"],
        "total_latency_ms": round(t_total_ms, 2),
        "results": [
            {
                "id": r.id,
                "query": r.query,
                "category": r.category,
                "expected_risk_terms": r.expected_risk_terms,
                "actual_risk_level": r.actual_risk_level,
                "actual_matched_terms": r.actual_matched_terms,
                "is_true_positive": r.is_true_positive,
                "is_false_positive": r.is_false_positive,
                "is_false_negative": r.is_false_negative,
                "absolute_claim_blocked": r.absolute_claim_blocked,
                "scope_qualifier_required": r.scope_qualifier_required,
                "competing_candidates_found": r.competing_candidates_found,
                "suggested_wording": r.suggested_wording,
                "error": r.error,
                "latency_ms": round(r.latency_ms, 2),
                "generated_answer": r.generated_answer,  # §2.1 계측 필드
            }
            for r in results
        ],
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info("결과 JSON 저장 완료: %s", output_file)


if __name__ == "__main__":
    main()