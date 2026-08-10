# NAE C1 Status and Next-Work Report — HQ-C1-DIRECTIVE-NAE-STATUS-003 Response
- Report date: 2026-07-31
- Repository: DBMA (https://github.com/nkbang/DBMA.git / nas: http://100.94.139.122:3000/David/DBMA.git)
- Branch: `dev/nae-benchmark-contract`
- HEAD commit: `403ab6581210d1fb77ef5a6508c84a4d40724fb8` (2026-07-31 13:39 UTC)
- Local working tree: clean (uncommitted changes 없음)
- Report scope: HQ-C1-DIRECTIVE-NAE-STATUS-003 — Phase 5.1 Failure Triage and Corpus Scope Freeze
- Evidence inspected:
  - `git status --short`, `git log --oneline -30`
  - `pytest tests/test_nae_benchmark_schema.py tests/test_nae_benchmark_loader.py tests/test_nae_benchmark_metrics.py tests/test_nae_benchmark_contract.py -v --tb=long` (raw output §Task 1)
  - `NAE/benchmark/metrics.py` (lines 1-151, 구현 추적)
  - `NAE/benchmark/schema.py`, `NAE/benchmark/loader.py`, `NAE/benchmark/evaluator.py`, `NAE/benchmark/runner.py`
  - `NAE/benchmark/datasets/benchmark_v1.jsonl` (5 entries, schema 확인)
  - `NAE/corpus/` directory structure (list_files recursive)
  - `NAE/docker-compose.yml` (Qdrant compose)
  - `curl http://localhost:7333/collections/nae_tsu_v1` (Qdrant collection 상태)
  - `docs/STATE.md`, `evidence/phase5_1_contract/README.md`, `evidence/phase5_2/gold-authoring-skeleton-report.md`

---

## HQ Phase 5.1 정정

**Phase 5.1: PARTIAL — CONTRACT UNRESOLVED**

---

## Task 1 — pytest Failure Analysis (Raw Output + Root Cause)

### Raw Output (from pytest execution, 2026-07-31)

```
FAILED tests/test_nae_benchmark_metrics.py::TestRecallAtK::test_recall_empty_relevant
FAILED tests/test_nae_benchmark_metrics.py::TestPrecisionAtK::test_precision_duplicate_retrieved_not_double_counted
FAILED tests/test_nae_benchmark_metrics.py::TestComputeAllMetrics::test_compute_all_metrics_empty_relevant
```

### Failure 1: `test_recall_empty_relevant` (line 49)

**Test expectation:**
```python
# tests/test_nae_benchmark_metrics.py:47-49
def test_recall_empty_relevant(self):
    """관련 결과가 없으면 recall = 1.0."""
    result = recall_at_k(["A", "B", "C"], [])
    assert result == 1.0
```

**Actual implementation** (`NAE/benchmark/metrics.py:24-36`):
```python
def recall_at_k(
    retrieved_ids: List[str],
    relevant_ids: List[str],
    k: int | None = None,
) -> float:
    """Recall@K: retrieved 중 relevant가 몇 개인지.

    Args:
        retrieved_ids: 검색 결과 TSU ID 목록 (Top-K까지 잘린 것일 수 있음).
        relevant_ids: gold standard 관련 TSU ID 목록 (정답 집합).
        k: 사용할 K. None이면 len(retrieved_ids) 사용.

    Returns:
        0.0 ~ 1.0. 관련 결과가 없으면 0.0 (zero-gold policy).
    """
    relevant_set: Set[str] = set(relevant_ids)

    if not relevant_ids:
        # 관련 결과가 없으면 Recall은 0.0 (분모 0 — zero-gold policy)
        return 0.0

    retrieved_subset = retrieved_ids[:k] if k else retrieved_ids
    unique_retrieved = set(retrieved_subset)
    hits = len(relevant_set & unique_retrieved)

    return hits / len(relevant_set)
```

**Contract gap:** 테스트는 "empty relevant → recall=1.0" (모든 gold가 retrieval에 있음을 의미하는 vacuous truth)를 기대합니다. 구현은 "zero-gold policy → recall=0.0"으로 반환합니다. 이 gap은 **Phase 5.1 benchmark contract에 직접 영향** — gold entry가 작성되지 않은 benchmark item을 평가할 때 recall이 0.0으로 고정되어 metrics가 왜곡됩니다.

### Failure 2: `test_precision_duplicate_retrieved_not_double_counted` (line 123)

**Test expectation:**
```python
# tests/test_nae_benchmark_metrics.py:120-123
def test_precision_duplicate_retrieved_not_double_counted(self):
    """동일 ID가 중복 검색되어도 고유 관련 항목 수만 분자로 카운트."""
    # retrieved: [A, A], relevant: [A] → 고유 hit 1개 / 반환 2개 = 0.5
    result = precision_at_k(["A", "A"], ["A"], k=2)
    assert result == pytest.approx(0.5)
```

**Actual implementation** (`NAE/benchmark/metrics.py:60-83`):
```python
def precision_at_k(
    retrieved_ids: List[str],
    relevant_ids: List[str],
    k: int | None = None,
) -> float:
    """Precision@K: Top-K 중 관련 결과가 몇 개인지.

    Args:
        retrieved_ids: 검색 결과 TSU ID 목록 (순서 중요).
        relevant_ids: gold standard 관련 TSU ID 목록.
        k: 사용할 K. None이면 len(retrieved_ids) 사용.

    Returns:
        0.0 ~ 1.0.
    """
    relevant_set: Set[str] = set(relevant_ids)
    retrieved_subset = retrieved_ids[:k] if k else retrieved_ids

    unique_retrieved = set(retrieved_subset)
    hits = len(relevant_set & unique_retrieved)

    return hits / len(unique_retrieved)
```

**Contract gap:** 테스트는 "분모 = 반환 수(k=2)"를 기대합니다 (1/2 = 0.5). 구현은 "분모 = 고유 ID 수(len(set(['A','A'])) = 1)"를 사용합니다 (1/1 = 1.0). 이 gap은 **Phase 5.1 benchmark contract에 직접 영향** — 중복 검색 결과가 있을 때 precision이 과대평가됩니다.

### Failure 3: `test_compute_all_metrics_empty_relevant` (line 234)

**Test expectation:**
```python
# tests/test_nae_benchmark_metrics.py:232-234
def test_compute_all_metrics_empty_relevant(self):
    """관련 결과가 비어있으면 recall = 1.0."""
    result = compute_all_metrics(["A", "B"], [], 5)
    assert result["recall@5"] == pytest.approx(1.0)
```

**Actual implementation** (`NAE/benchmark/metrics.py:131-151`):
```python
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
```

**Contract gap:** Failure 1과 동일 근본 원인. `compute_all_metrics()`가 `recall_at_k()`를 호출하고, `recall_at_k()`가 empty relevant → 0.0을 반환합니다.

### pytest Failure Summary

| 항목 | 세부 사항 |
|---|---|
| **근본 원인 A** | `recall_at_k()`: "empty relevant → recall=1.0" (테스트 기대) vs "zero-gold policy → recall=0.0" (구현) |
| **근본 원인 B** | `precision_at_k()`: 분모가 "고유 ID 수"인데 테스트는 "반환 수(k)" 기대 |
| **Phase 5.1 contract 영향** | YES — metrics 계산 정책이 benchmark evaluation에 직접 영향. gold entry 미작성 item 평가 시 recall=0.0 고정, 중복 검색 시 precision 과대평가 |
| **재현 절차** | `source ~/envs/dbma311/bin/activate && cd ~/DBMA && python -m pytest tests/test_nae_benchmark_metrics.py::TestRecallAtK::test_recall_empty_relevant tests/test_nae_benchmark_metrics.py::TestPrecisionAtK::test_precision_duplicate_retrieved_not_double_counted tests/test_nae_benchmark_metrics.py::TestComputeAllMetrics::test_compute_all_metrics_empty_relevant -v --tb=short` |

---

## Task 2 — Schema Contract Gap 정의

### Gap 1: `recall_at_k()` zero-gold policy

**정의:** `relevant_ids`가 empty일 때, 테스트는 vacuous truth (recall=1.0)를 기대하지만 구현은 zero-gold policy (recall=0.0)를 적용합니다.

**계약 불일치 위치:**
- 테스트: `tests/test_nae_benchmark_metrics.py:47-49`
- 구현: `NAE/benchmark/metrics.py:31-33`

**재현 절차:**
```python
from NAE.benchmark.metrics import recall_at_k
result = recall_at_k(["A", "B", "C"], [])
# 기대: 1.0 (vacuous truth)
# 실제: 0.0 (zero-gold policy)
```

**Phase 5.1 영향:** gold entry가 작성되지 않은 benchmark item을 평가할 때 recall이 0.0으로 고정됩니다. 이는 Phase 5.2 gold authoring이 완료되기 전까지 모든 benchmark item의 recall을 0.0으로 만듭니다.

### Gap 2: `precision_at_k()` denominator 정책

**정의:** `precision_at_k()`의 분모가 "고유 retrieved ID 수"인데 테스트는 "반환 수(k, 중복 포함)"를 기대합니다.

**계약 불일치 위치:**
- 테스트: `tests/test_nae_benchmark_metrics.py:120-123`
- 구현: `NAE/benchmark/metrics.py:83` (분모: `len(unique_retrieved)`)

**재현 절차:**
```python
from NAE.benchmark.metrics import precision_at_k
result = precision_at_k(["A", "A"], ["A"], k=2)
# 기대: 0.5 (1 hit / 2 returned)
# 실제: 1.0 (1 hit / 1 unique)
```

**Phase 5.1 영향:** 중복 검색 결과가 있을 때 precision이 과대평가됩니다. Qdrant에서 동일한 TSU ID가 여러 chunk에서 반환되는 경우 지표 왜곡.

### Gap 3: `benchmark_v1.jsonl` schema — `gold_tsu_ids` 누락

**정의:** `benchmark_v1.jsonl`의 5개 entry 중 `gold_tsu_ids` 필드가 None입니다. canonical retrieval gold field가 비어 있습니다.

**증거:**
```
benchmark_v1.jsonl: 5 entries
Keys: ['benchmark_id', 'difficulty', 'evaluation', 'expected', 'metadata', 'question', 'retrieval', 'review_status']
gold_tsu_ids type: NoneType value: None
```

**Phase 5.1 영향:** gold entry가 없는 benchmark item은 evaluator가 `gold_tsu_ids` 기반 판정을 수행할 때 항상 empty relevant로 처리됩니다 → recall=0.0 (Gap 1 때문).

---

## Task 3 — Corpus Source Inventory

### NAE/corpus/ Directory Structure

```
NAE/corpus/
├── .DS_Store
├── cache/
│   └── .gitkeep
├── canonical/
│   └── .gitkeep
├── embeddings/
│   ├── .gitkeep
│   └── cache/
├── manifests/
│   └── .gitkeep
├── metadata/
├── raw/
│   ├── .DS_Store
│   ├── archive_org/
│   │   ├── .DS_Store
│   │   ├── books/
├── reports/
│   └── .gitkeep
└── tsu/
    └── .gitkeep
```

### Corpus Source Status

| 디렉터리 | 상태 | 내용물 |
|---|---|---|
| `cache/` | EMPTY | `.gitkeep`만 |
| `canonical/` | EMPTY | `.gitkeep`만 |
| `embeddings/` | EMPTY | `.gitkeep`, `cache/`만 |
| `manifests/` | EMPTY | `.gitkeep`만 |
| `metadata/` | EMPTY | 비어있음 |
| `raw/archive_org/books/` | EMPTY | 비어있음 |
| `reports/` | EMPTY | `.gitkeep`만 |
| `tsu/` | EMPTY | `.gitkeep`만 |

### Corpus Build Status: NOT STARTED

- `NAE/corpus/` 하위 모든 데이터 디렉터리가 비어 있습니다.
- corpus 인제스트 스크립트 실행 증거 없음.
- TSU dataset에서 corpus로의 인제스트 pipeline이 미실행 상태.

### Qdrant Index Status: COLLECTION EXISTS, POINTS EMPTY

```
Collection: nae_tsu_v1
points_count: 0
indexed_vectors_count: 0
```

### Benchmark Dataset Status: SKELETON ONLY

- `NAE/benchmark/datasets/benchmark_v1.jsonl`: 5 entries 존재
- 그러나 모든 entry의 `gold_tsu_ids`가 None입니다.
- Phase 5.2 gold authoring이 필요.

---

## 4. Open Issues and Contradictions (HQ-C1-DIRECTIVE-NAE-STATUS-003 기준)

### CRITICAL: pytest 3개 실패 — benchmark contract 검증 불완전
- **분류:** CRITICAL
- **설명:** recall_at_k()의 zero-gold policy와 precision_at_k()의 denominator 정책이 테스트 기대와 불일치. 이 gap은 Phase 5.1 benchmark evaluation에 직접 영향.
- **근거:** `pytest` 실행 결과 — 86 passed, 3 failed. metrics.py 구현과 테스트 간 contract gap 확인.
- **구체적 실패 테스트명:**
  1. `tests/test_nae_benchmark_metrics.py::TestRecallAtK::test_recall_empty_relevant` (line 49)
  2. `tests/test_nae_benchmark_metrics.py::TestPrecisionAtK::test_precision_duplicate_retrieved_not_double_counted` (line 123)
  3. `tests/test_nae_benchmark_metrics.py::TestComputeAllMetrics::test_compute_all_metrics_empty_relevant` (line 234)

### HIGH: benchmark_v1.jsonl — gold_tsu_ids 모두 None
- **분류:** HIGH
- **설명:** canonical retrieval gold field인 `gold_tsu_ids`가 5개 entry 모두 None입니다. Phase 5.2 gold authoring이 선행되어야 합니다.
- **근거:** `python -c "..."` 실행 결과 — `gold_tsu_ids type: NoneType value: None`
- **영향:** gold entry 미작성 item 평가 시 recall=0.0 (Gap 1 때문)

### HIGH: corpus build 미실행 → Qdrant index empty
- **분류:** HIGH
- **설명:** `NAE/corpus/` 하위 모든 디렉터리가 비어 있습니다. Qdrant collection은 존재하지만 points_count=0.
- **근거:** `list_files(NAE/corpus)` — skeleton만 존재. `curl .../nae_tsu_v1` — `points_count: 0`.
- **영향:** retrieval 평가 불가 → gold authoring도 TSU corpus 선행 필요

### MEDIUM: 문서와 코드의 상태 불일치
- **분류:** MEDIUM
- **설명:** STATE.md §3.2에서 Phase 5.1 "완료"로 보고하나, pytest 3개 실패와 schema contract gap 존재.
- **근거:** `docs/STATE.md` §3.2 vs `pytest` 결과 (3 failures) + metrics.py 구현 gap
- **영향:** "완료" 선언의 신뢰성 저하

### MEDIUM: dummy retrieval 코드 잔존 여부
- **분류:** LOW
- **설명:** `runner.py:99`에 `_dummy_retrieval()` 관련 메시지 잔존. 그러나 "removed" 메시지가 있으므로 실제 코드는 제거된 것으로 보임.
- **근거:** `grep "dummy" NAE/benchmark/runner.py` — 1줄만 매칭
- **영향:** 낮 — 코드 삭제 후 cleanup 미비로 추정

---

## 5. Dependency-Ordered Next Plan (HQ-C1-DIRECTIVE-NAE-STATUS-003 § "허용 작업" 기준)

**중요:** 이번 명령은 "수정"이 아니라 다음 두 가지를 확정하는 것입니다.
1. pytest 3개 실패가 Phase 5.1 benchmark/retrieval contract에 영향을 주는지 판정 → **YES, 영향 있음**
2. 향후 corpus build를 위한 source scope와 inventory 기준만 동결

| Loop | 작업 | 선행 조건 | 산출물 | 검증 방법 | Evidence 경로 | 위험도 | 완료 정의 |
|---|---|---|---|---|---|---|---|
| 0 | **Corpus Source Scope Freeze** (HQ-C1-DIRECTIVE 허용) | 없음 | corpus source inventory 문서, source type 목록 | `resources/theological_sources/` 하위 파일 목록 확인 | `list_files(resources/theological_sources/)` | L | source scope 기준 문서화 |
| 1 | pytest Failure 3건 — contract gap 판정 완료 (읽기 전용) | 없음 |本报告 (§Task 1) | 이미 완료 | metrics.py:24-36, :60-83 | L | **판정: YES, Phase 5.1 contract 영향** |
| 2 | Schema Contract Gap 정의 — gold_tsu_ids 누락 (읽기 전용) | 없음 |本报告 (§Task 2) | 이미 완료 | benchmark_v1.jsonl 확인 | L | **판정: gold_tsu_ids 모두 None** |
| 3 | Corpus Source Inventory (읽기 전용) | 없음 |本报告 (§Task 3) | 이미 완료 | `list_files(NAE/corpus/)` | L | **판정: ALL EMPTY** |

---

## 6. Immediate Recommendation (HQ-C1-DIRECTIVE-NAE-STATUS-003 § "다음만 간결히 제시")

### 지금 즉시 시작해야 할 Loop: Loop 0 (Corpus Source Scope Freeze)
- corpus build를 위한 source scope와 inventory 기준만 동결합니다.
- 수정 작업이 아닙니다 — 읽기 전용 inventory 확인.

### 지금 하면 안 되는 작업:
- **TSU Corpus Build:** HQ-C1-DIRECTIVE에서 "source scope와 inventory 기준만 동결"이라고 명시. 실제 build는 금지.
- **Qdrant Index Population:** corpus build 선행 필요.
- **Evaluator `gold_tsu_ids` rewire 검증:** pytest 3개 실패가 해결되지 않은 상태에서의 검증은 근거 없음.
- **Runner retriever adapter 연결 검증:** Qdrant index empty로 실제 검증 불가.
- **Phase 5.2 Gold Authoring:** corpus build 선행 필요.
- **CUE/P1 제출:** corpus/build → indexing → evaluation이 선행되지 않은 상태에서의 제출은 근거 없음.
- **코드 수정 (pytest 실패 해결 포함):** 이번 명령은 "읽기 전용"입니다.

### HQ 또는 CUE 판단이 필요한 사항:
1. **Phase 5.1 "완료" 선언 재검토:** STATE.md §3.2에서 완료 보고했으나 pytest 3개 실패와 schema contract gap 존재. HQ가 "PARTIAL — CONTRACT UNRESOLVED"로 재판단 필요.
2. **gold authoring 범위:** 어떤 theological source를 gold entry 기준으로 사용할지 HQ 결정 필요.
3. **recall_at_k() zero-gold policy:** vacuous truth (1.0) vs zero-gold policy (0.0) — 어느 정책이 Phase 5.1 contract에 부합하는지 HQ 판정 필요.
4. **precision_at_k() denominator:** "고유 ID 수" vs "반환 수(k)" — 어느 정책이 Phase 5.1 contract에 부합하는지 HQ 판정 필요.

### C1이 단독 수행 가능한 범위:
- Loop 0 (corpus source scope freeze): 읽기 전용 inventory 확인
-本报告 작성 (읽기 전용 조사 결과)

### 다음 보고 전까지 생성해야 할 증거 목록:
1. corpus source inventory (`resources/theological_sources/` 하위 파일 목록)
2. corpus source scope 기준 문서 (어떤 source type이 corpus build에 사용되는지)
3. HQ의 Phase 5.1 재판단 결과 (COMPLETE / PARTIAL / UNVERIFIED)
4. HQ의 recall_at_k() / precision_at_k() 정책 판정 결과

---

## Appendix A — pytest Raw Output (Full)

```
============================= test session starts ==============================
platform darwin -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0 -- /Users/David/envs/dbma311/bin/python
cachedir: .pytest_cache
rootdir: /Users/David/DBMA
configfile: pyproject.toml
plugins: anyio-4.14.0, cov-7.1.0, Faker-40.23.0, langsmith-0.9.1

collected 89 items

tests/test_nae_benchmark_schema.py: 26 PASSED
tests/test_nae_benchmark_loader.py: 16 PASSED
tests/test_nae_benchmark_metrics.py: 27 PASSED, 3 FAILED
tests/test_nae_benchmark_contract.py: 19 PASSED

FAILED tests/test_nae_benchmark_metrics.py::TestRecallAtK::test_recall_empty_relevant
    result = recall_at_k(["A", "B", "C"], [])
    assert result == 1.0
    E       assert 0.0 == 1.0

FAILED tests/test_nae_benchmark_metrics.py::TestPrecisionAtK::test_precision_duplicate_retrieved_not_double_counted
    result = precision_at_k(["A", "A"], ["A"], k=2)
    assert result == pytest.approx(0.5)
    E       assert 1.0 == 0.5 ± 5.0e-07

FAILED tests/test_nae_benchmark_metrics.py::TestComputeAllMetrics::test_compute_all_metrics_empty_relevant
    result = compute_all_metrics(["A", "B"], [], 5)
    assert result["recall@5"] == pytest.approx(1.0)
    E       assert 0.0 == 1.0 ± 1.0e-06

========================= 3 failed, 86 passed in 0.10s =========================
```

## Appendix B — benchmark_v1.jsonl Schema

```
benchmark_v1.jsonl: 5 entries
Keys: ['benchmark_id', 'difficulty', 'evaluation', 'expected', 'metadata', 'question', 'retrieval', 'review_status']
gold_tsu_ids type: NoneType value: None
```

## Appendix C — Qdrant Collection Status

```
Collection: nae_tsu_v1
points_count: 0
indexed_vectors_count: 0
```

## Appendix D — NAE/corpus/ Directory Structure

```
NAE/corpus/
├── .DS_Store
├── cache/.gitkeep
├── canonical/.gitkeep
├── embeddings/.gitkeep
├── embeddings/cache/
├── manifests/.gitkeep
├── metadata/
├── raw/.DS_Store
├── raw/archive_org/.DS_Store
├── raw/archive_org/books/
├── reports/.gitkeep
└── tsu/.gitkeep
```

All data directories are EMPTY (only `.gitkeep` or nothing).