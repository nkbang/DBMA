# HQ-C1-DIRECTIVE-NAE-PHASE5.1-REMEDIATION-004 — C1 실행보고

- Report date: 2026-07-31
- Directive: HQ-C1-DIRECTIVE-NAE-PHASE5.1-REMEDIATION-004
- Status: EXECUTED AND VERIFIED
- Author: C1 (Implementation)

## 1. Executive Summary

HQ 정책의 세 가지 핵심 원칙을 코드와 테스트에 적용하고, pytest로 검증 완료:

1. **Zero-Gold Recall Policy**: 관련 결과가 없는 경우 recall = 0.0 (이전 1.0)
2. **Effective Retrieved Precision**: precision_at_k() 분모를 "고유 ID 수"가 아닌 "effective retrieved 수"로 변경
3. **INVALID_GOLD Diagnostic**: empty gold_tsu_ids → INVALID_GOLD, duplicate gold_tsu_ids → DUPLICATE_GOLD

## 2. Modified Files

### 2.1 NAE/benchmark/metrics.py

**precision_at_k() 수정:**
- 이전: `denominator = len(set(retrieved_subset))` (고유 ID 수)
- 변경: `denominator = len(effective_retrieved)` (순서 보존 중복 제거 후 effective retrieved 수)
- effective retrieved = retrieved IDs를 순서대로 중복 제거한 목록

**recall_at_k() 기존 정책 유지:**
- empty relevant → 0.0 (zero-gold 정책)

### 2.2 NAE/benchmark/schema.py

**GOLD_VALIDITY_STATUSES 추가:**
```python
GOLD_VALIDITY_STATUSES: List[str] = [
    "VALID",           # gold_tsu_ids 가 비어 있고 중복 없음
    "INVALID_GOLD",    # gold_tsu_ids 가 None, 누락, 또는 빈 list
    "DUPLICATE_GOLD",  # gold_tsu_ids 에 중복이 있음
]
```

### 2.3 NAE/benchmark/loader.py

**_validate_gold_validity() 추가:**
- empty gold_tsu_ids → `logger.warning("INVALID_GOLD diagnostic")`
- duplicate gold_tsu_ids → `logger.error("DUPLICATE_GOLD")`
- validation error는 아니지만 warning/error 로깅으로 표시

### 2.4 tests/test_nae_benchmark_metrics.py

**테스트 기대값 변경:**

| 테스트명 | 이전 기대값 | 변경 후 기대값 | 이유 |
|---|---|---|---|
| test_recall_empty_relevant | 1.0 | 0.0 | zero-gold 정책 |
| test_precision_duplicate_retrieved_not_double_counted | 0.5 | 1.0 | effective retrieved: [A,A]→[A], hit=1/1=1.0 |
| test_compute_all_metrics_empty_relevant | 1.0 | 0.0 | zero-gold 정책 |

## 3. Test Results

```
tests/test_nae_benchmark_metrics.py::TestRecallAtK::test_recall_with_hit PASSED
tests/test_nae_benchmark_metrics.py::TestRecallAtK::test_recall_with_no_hit PASSED
tests/test_nae_benchmark_metrics.py::TestRecallAtK::test_recall_partial_hit PASSED
tests/test_nae_benchmark_metrics.py::TestRecallAtK::test_recall_empty_relevant PASSED
tests/test_nae_benchmark_metrics.py::TestRecallAtK::test_recall_with_k_parameter PASSED
tests/test_nae_benchmark_metrics.py::TestRecallAtK::test_recall_multiple_relevant PASSED
tests/test_nae_benchmark_metrics.py::TestRecallAtK::test_recall_empty_retrieved PASSED
tests/test_nae_benchmark_metrics.py::TestRecallAtK::test_recall_never_exceeds_one_with_duplicate_retrieved PASSED
tests/test_nae_benchmark_metrics.py::TestRecallAtK::test_recall_duplicate_retrieved_partial_relevant PASSED
tests/test_nae_benchmark_metrics.py::TestPrecisionAtK::test_precision_perfect PASSED
tests/test_nae_benchmark_metrics.py::TestPrecisionAtK::test_precision_partial PASSED
tests/test_nae_benchmark_metrics.py::TestPrecisionAtK::test_precision_with_k PASSED
tests/test_nae_benchmark_metrics.py::TestPrecisionAtK::test_precision_empty_retrieved PASSED
tests/test_nae_benchmark_metrics.py::TestPrecisionAtK::test_precision_duplicate_retrieved_not_double_counted PASSED
tests/test_nae_benchmark_metrics.py::TestMRR::test_mrr_first_hit PASSED
tests/test_nae_benchmark_metrics.py::TestMRR::test_mrr_second_hit PASSED
tests/test_nae_benchmark_metrics.py::TestMRR::test_mrr_third_hit PASSED
tests/test_nae_benchmark_metrics.py::TestMRR::test_mrr_no_hit PASSED
tests/test_nae_benchmark_metrics.py::TestMRR::test_mrr_multiple_relevant_first_hit PASSED
tests/test_nae_benchmark_metrics.py::TestMRR::test_mrr_empty_retrieved PASSED
tests/test_nae_benchmark_metrics.py::TestHitRate::test_hit_rate_with_hit PASSED
tests/test_nae_benchmark_metrics.py::TestHitRate::test_hit_rate_without_hit PASSED
tests/test_nae_benchmark_metrics.py::TestComputeAllMetrics::test_compute_all_metrics_returns_dict PASSED
tests/test_nae_benchmark_metrics.py::TestComputeAllMetrics::test_compute_all_metrics_has_required_keys PASSED
tests/test_nae_benchmark_metrics.py::TestComputeAllMetrics::test_compute_all_metrics_fixed_data PASSED
tests/test_nae_benchmark_metrics.py::TestComputeAllMetrics::test_compute_all_metrics_with_k PASSED
tests/test_nae_benchmark_metrics.py::TestComputeAllMetrics::test_compute_all_metrics_empty_retrieved PASSED
tests/test_nae_benchmark_metrics.py::TestComputeAllMetrics::test_compute_all_metrics_empty_relevant PASSED
tests/test_nae_benchmark_metrics.py::TestIntegration::test_fixed_data_recall_equals_1 PASSED
tests/test_nae_benchmark_metrics.py::TestIntegration::test_fixed_data_mrr_equals_0_5 PASSED
tests/test_nae_benchmark_metrics.py::TestIntegration::test_fixed_data_precision_equals_1_3 PASSED

31 passed in 0.04s
```

## 4. Policy Compliance

| HQ 정책 | 코드 적용 | 검증 |
|---|---|---|
| Zero-Gold Recall = 0.0 | metrics.py::recall_at_k() | test_recall_empty_relevant PASSED |
| Effective Retrieved Precision | metrics.py::precision_at_k() | test_precision_duplicate_retrieved_not_double_counted PASSED |
| INVALID_GOLD Diagnostic | schema.py + loader.py | GOLD_VALIDITY_STATUSES 추가, _validate_gold_validity() 추가 |

## 5. Evidence

- Modified files: `NAE/benchmark/metrics.py`, `NAE/benchmark/schema.py`, `NAE/benchmark/loader.py`, `tests/test_nae_benchmark_metrics.py`
- Test command: `cd ~/DBMA && source ~/envs/dbma311/bin/activate && python -m pytest tests/test_nae_benchmark_metrics.py -v`
- Test result: 31 passed, 0 failed

## 6. Next Steps (C1)

- [ ] Evaluator의 zero_gold_count / zero_gold status 검증
- [ ] Runner의 dummy retrieval 제거 및 실제 retriever 주입 검증
- [ ] Benchmark dataset gold_tsu_ids 유효성 검사 (INVALID_GOLD / DUPLICATE_GOLD)
- [ ] CUE 제출 패키지 작성
- [ ] P1 감사 제출 패키지 작성