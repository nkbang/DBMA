# CUE 제출 요청 — Phase 5.1 Contract Migration

**작성일:** 2026-07-31
**작업:** C1-DIRECTIVE-047 (HQ-C1-DIRECTIVE-047)
**상태:** CUE 제출 대기 중 (Exception B 승인 필요)

## 요약

Phase 5.1 contract migration이 로컬에서 구현되었습니다. 16개 contract/migration 테스트가 모두 통과했습니다.

## Exception B: metrics.py 변경 필요

metrics.py는 Phase 5.1 허용 source 목록에 포함되지 않았습니다. 그러나 다음 세 결함은 contract correctness에 필수입니다:

1. **precision_at_k denominator dedup:** `len(retrieved_subset)` → `len(unique_retrieved)`
2. **recall_at_k zero-gold=0.0:** `return 1.0` → `return 0.0`
3. **empty retrieval key naming:** `effective_k=0` → `top_k` 고정

## 변경 파일 목록 (10 modified + 1 new)

### Modified (10개)
- `NAE/benchmark/__init__.py` — Retriever Protocol export
- `NAE/benchmark/schema.py` — deprecated gold_tsu_ids metadata
- `NAE/benchmark/loader.py` — migration matrix
- `NAE/benchmark/evaluator.py` — gold_tsu_ids-only contract
- `NAE/benchmark/metrics.py` — precision dedup + recall zero-gold (Exception B)
- `NAE/benchmark/runner.py` — ConfigurationError + Retriever required
- `NAE/benchmark/datasets/benchmark_v1.jsonl` — pre-existing uncommitted
- `scripts/build_tsu_dataset.py` — pre-existing uncommitted
- `tests/test_nae_benchmark_loader.py` — migration tests
- `tests/test_nae_benchmark_schema.py` — schema contract tests

### New (1개)
- `tests/test_nae_benchmark_contract.py` — 16 contract/migration tests

## Test 결과

```
16 passed in 0.04s
```

| 분류 | 수 |
|------|-----|
| Loader validation | 2 |
| Loader migration | 3 |
| Evaluator contract | 2 |
| Runner protocol | 1 |
| Schema backward compat | 2 |
| Required contract assertions | 6 |
| **합계** | **16** |

## Gate Status

```
Phase 5.1 Contract:    IMPLEMENTED — 16/16 tests pass
gold_tsu_ids canonical: ACTIVE — top-level only
expected_gold_tsu_ids: DEPRECATED — migration warning on load
Evaluator contract:    GOLD_ONLY — required_concepts scoring removed
Runner protocol:       STRICT — retrieval_fn required (no silent default)
Metrics:               PRECISION_DEDUP + RECALL_ZERO_GOLD + EMPTY_RETRIEVAL

CUE Contract Review:   NOT YET AUTHORIZED
Commit/Push:           BLOCKED
Gold Authoring P5.2:   BLOCKED
```

## Evidence Package

```
evidence/phase5_1_contract/
  manifest.json          ✅
  README.md              ✅
  self-check-050.md      ✅
  git.txt                ✅
  changed-files.txt      ✅
  diff-stat.txt          ✅
  pytest-collect.txt     ✅
  pytest.txt             ✅
  contract-tests.txt     ✅
  migration-tests.txt    ✅
  diff.txt               ✅ (1622 lines)
```

## 승인 요청 사항

1. **metrics.py Exception B 승인:** precision dedup + recall zero-gold 변경 허용
2. **CUE Contract Review:** 전체 migration 검토
3. **Commit/Push 승인:** evidence-only commit
4. **Gold Authoring Phase 5.2:** 다음 단계 진행 허가