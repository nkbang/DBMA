# Phase 5.1 Contract Evidence Package

## Overview

This evidence package documents the Phase 5.1 migration implementation:
- `gold_tsu_ids` canonical field (top-level only)
- `expected.gold_tsu_ids` deprecation
- Loader migration matrix
- Evaluator gold_tsu_ids-only contract
- Runner Retriever Protocol + ConfigurationError

## Files

| File | Description |
|------|-------------|
| `manifest.json` | Package manifest with gate status |
| `git.txt` | Full git diff HEAD output |
| `changed-files.txt` | git diff --name-only output |
| `diff-stat.txt` | git diff --stat output |
| `pytest-collect.txt` | pytest --collect-only output |
| `pytest.txt` | Full pytest -v output (10 tests) |
| `contract-tests.txt` | Contract/Protocol/BackwardCompat tests (7 tests) |
| `migration-tests.txt` | Migration tests (3 tests) |

## Test Results

```
10 passed in 0.04s
```

### Contract Tests (7)
- `test_loader_rejects_missing_benchmark_id` — construction error on missing ID
- `test_loader_rejects_invalid_question_type` — construction error on invalid type
- `test_evaluator_accepts_gold_tsu_ids_only` — gold_tsu_ids accepted
- `test_evaluator_rejects_removed_fields` — deprecated fields not tracked
- `test_runner_rejects_none_retrieval` — ConfigurationError on None
- `test_schema_backward_compatible` — from_dict accepts deprecated fields
- `test_schema_expected_dataclass_preserves_deprecated` — deprecation marker exists

### Migration Tests (3)
- `test_migration_gold_tsu_ids_top_level` — top-level gold_tsu_ids preserved
- `test_migration_gold_tsu_ids_in_expected` — nested → top-level migration
- `test_migration_gold_tsu_ids_both_levels_conflict` — conflict raises error

## Migration Matrix (loader.py)

| top-level | nested | Action |
|-----------|--------|--------|
| exists | missing | use top-level |
| missing | exists | copy to top-level, warn |
| both exist, equal | | use top-level, warn |
| both exist, different | | `GoldTsusIdsConflictError` |
| neither exists | | empty list allowed |

## Baseline / Task Diff Separation

```text
This package contains a full working-tree diff for preservation only.
Task-specific changes are identified in changed-files.txt.
Pre-existing uncommitted changes are separately listed and excluded from
the Phase 5.1 implementation claim.
```

**Pre-existing uncommitted (baseline):**
- `NAE/benchmark/datasets/benchmark_v1.jsonl`
- `scripts/build_tsu_dataset.py`

**Phase 5.1 task changes:**
- `NAE/benchmark/__init__.py` — Retriever Protocol export
- `NAE/benchmark/schema.py` — deprecated gold_tsu_ids metadata
- `NAE/benchmark/loader.py` — migration matrix
- `NAE/benchmark/evaluator.py` — gold_tsu_ids-only contract
- `NAE/benchmark/runner.py` — ConfigurationError + Retriever required
- `tests/test_nae_benchmark_contract.py` — 10 contract/migration tests

## Gate Status

```
Phase 5.1 Contract:
IMPLEMENTED — 10/10 tests pass

gold_tsu_ids canonical:
ACTIVE — top-level only

expected.gold_tsu_ids:
DEPRECATED — migration warning on load

Evaluator contract:
GOLD_ONLY — required_concepts scoring removed

Runner protocol:
STRICT — retrieval_fn required (no silent default)