# Phase 5.1 Contract Migration — Complete

**Status:** COMPLETE — 16/16 contract/migration tests pass
**Date:** 2026-07-31
**Task:** C1-DIRECTIVE-047 (HQ-C1-DIRECTIVE-047)

## Summary

Phase 5.1 migration implementation complete:

| Component | Change | Test |
|-----------|--------|------|
| `schema.py` | `BenchmarkExpected.gold_tsu_ids` deprecated marker | test_schema_expected_dataclass_preserves_deprecated |
| `loader.py` | `_canonicalize_gold_tsu_ids()` migration matrix | 3 migration tests |
| `evaluator.py` | gold_tsu_ids-only contract + empty retrieval fix | 2 evaluator tests |
| `metrics.py` | precision denominator dedup + recall zero-gold=0 | precision/recall unit tests |
| `runner.py` | `retrieval_fn` required (no silent default) | test_runner_rejects_none_retrieval |
| `__init__.py` | `Retriever` export | import check |
| `test_nae_benchmark_contract.py` | 16 contract/migration tests | **16/16 pass** |

## Migration Matrix (loader.py)

| top-level | nested | Action |
|-----------|--------|--------|
| exists | missing | use top-level |
| missing | exists | copy to top-level, warn |
| both exist, equal | | use top-level, warn |
| both exist, different | | `GoldTsusIdsConflictError` |
| neither exists | | empty list allowed |

## Test Results

```
16 passed in 0.04s
```

### Test List

1. `test_loader_rejects_missing_benchmark_id` — construction error on missing ID
2. `test_loader_rejects_invalid_question_type` — construction error on invalid type
3. `test_migration_gold_tsu_ids_top_level` — top-level gold_tsu_ids preserved
4. `test_migration_gold_tsu_ids_in_expected` — nested → top-level migration
5. `test_migration_gold_tsu_ids_both_levels_conflict` — conflict raises error
6. `test_evaluator_accepts_gold_tsu_ids_only` — gold_tsu_ids accepted
7. `test_evaluator_rejects_removed_fields` — deprecated fields not tracked
8. `test_runner_rejects_none_retrieval` — ConfigurationError on None
9. `test_schema_backward_compatible` — from_dict accepts deprecated fields
10. `test_schema_expected_dataclass_preserves_deprecated` — deprecation marker exists
11. `test_expected_fields_do_not_affect_retrieval_metrics` — expected_* fields don't affect metrics
12. `test_empty_valid_retrieval_returns_zero_metrics` — empty retrieval → all zero
13. `test_zero_gold_item_returns_zero_metrics_and_is_counted` — zero gold → zero metrics + counted
14. `test_duplicate_retrieved_ids_do_not_inflate_metrics` — dedup precision policy
15. `test_runner_passes_retriever_ids_to_evaluator_unchanged` — runner→evaluator API contract
16. `test_no_dummy_retrieval_runtime_path` — ConfigurationError on None (runtime path)

## Defect Remediation (C1-Self-Check-050)

| 결함 | 수정 | 테스트 |
|------|------|--------|
| `precision_at_k` 분모가 중복 ID 포함 | `unique_retrieved` 사용 | test_duplicate_retrieved_ids_do_not_inflate_metrics |
| `recall_at_k` zero-gold=1.0 | recall zero-gold=0.0 | test_zero_gold_item_returns_zero_metrics_and_is_counted |
| `effective_k=0` → "recall@0" 키 | empty retrieval 시 top_k 고정 | test_empty_valid_retrieval_returns_zero_metrics |

## Gate Status

```
Phase 5.1 Contract:
IMPLEMENTED — 16/16 tests pass

gold_tsu_ids canonical:
ACTIVE — top-level only

expected.gold_tsu_ids:
DEPRECATED — migration warning on load

Evaluator contract:
GOLD_ONLY — required_concepts scoring removed

Runner protocol:
STRICT — retrieval_fn required (no silent default)

Metrics:
PRECISION_DEDUP — denominator uses unique IDs
RECALL_ZERO_GOLD — returns 0.0 (not 1.0)
EMPTY_RETRIEVAL — always uses top_k for key naming
```

## Evidence Package

Located at `evidence/phase5_1_contract/README.md`.