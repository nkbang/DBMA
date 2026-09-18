# C1 Review 결과 — Authority Tier(T1-T4) M2 Tagging: 구현 코드 검토 (B3)

- 요청서: `docs/NAE_AUTHORITY_TIER_M2_TAGGING_C1_REVIEW_REQUEST_003.md` (§4-B B3)
- 검토자: NAE Forensic Auditor (C1, `qwen3.6:35b-DBMAcode`)
- 일자: 2026-09-17
- 유형: **구현 코드 사후검증** — Amendment D 설계 검토(_RESULT_002) GREEN 이후의 구현 단계
- 게이트: B3 (C1 구현 코드 검토) → GREEN 시 B4 (HQ 최종 승인) 요청

## Git 상태 (본 세션)

```
$ git rev-parse HEAD
2f38c81936201decaa0bd7c8b98176c84c9084b7

$ git rev-parse --show-toplevel
/Users/David/DBMA/.claude/worktrees/c1-review-findings-9b8af7

$ git diff --stat origin/dev/dbma-engine HEAD
 NAE/pipeline/registration/pipeline.py              |  13 ++
 ...E_AUTHORITY_TIER_M2_TAGGING_BUILD_REPORT_001.md | 132 ++++++++++++++++++++
 ...E_AUTHORITY_TIER_M2_TAGGING_C1_REVIEW_REQUEST_003.md | 136 +++++++++++++++++++++
 ...NT-D-Authority-Tier-Doctrinal-Orthodoxy-Axis.md |  21 ++--
 scripts/m2_source_registry_validator.py            |  88 ++++++++++++-
 tests/test_m2_source_registry_governance.py        |  78 ++++++++++++
 6 files changed, 454 insertions(+), 14 deletions(-)
```

---

## 1. `pipeline.py` — RegistrationRequest / manifest_entry 변경

**판정: PASS**

### 근거

`git diff`로 실제 코드를 확인한 결과:

- `RegistrationRequest` dataclass에 3개 optional 필드 추가:
  ```python
  authority_tier: str | None = None
  tradition_relation: str | None = None
  counter_refs: list[str] | None = None
  ```
- manifest_entry 조립 블록에 동일한 패턴 적용:
  ```python
  if request.authority_tier is not None:
      manifest_entry["authority_tier"] = request.authority_tier
  if request.tradition_relation is not None:
      manifest_entry["tradition_relation"] = request.tradition_relation
  if request.counter_refs is not None:
      manifest_entry["counter_refs"] = request.counter_refs
  ```

**Amendment B 필드(4개: authority_class, content_genre, theological_category, tradition)와 완전히 동일한 코드 패턴** — 구조적 동일성 확인. optional 필드의 기본값이 `None`이므로 필드를 지정하지 않으면 기존과 byte-identical 출력을 보장한다. 기존 pipeline 동작에 영향 없음.

---

## 2. `m2_source_registry_validator.py` — V9-V12 신규 검사

**판정: PASS**

### 근거

`check_authority_tier_fields()` 함수 본문을 직접 정독하고 요청서의 4가지 핵심 질문에 각각 답변:

| 질문 | 구현 확인 | 결과 |
|------|----------|------|
| T3가 아닌데 counter_refs 있으면 V12 FAIL? | `if tier in ("T1", "T2", "T4") and counter_refs:` | YES |
| counter_refs 대상이 M2에 없으면(orphan) V11 FAIL? | `if target is None:` | YES |
| counter_refs 대상의 authority_tier ∉ {T1,T2}면 V11 FAIL? | `elif target.get("authority_tier") not in ("T1", "T2"):` | YES |
| T3→T2, T2는 counter_refs 없음 → PASS? | test_pos_09에서 검증 (실제 실행 결과: 33 passed) | YES |

**설계 검토(_RESULT_002)에서 GREEN 판정한 "V11(b)+V12 조합이 counter_ref 순환 참조를 구조적으로 차단한다"는 논증이 실제 코드에서도 정확히 성립함을 확인:**

- T1/T2/T4 → counter_refs 금지 (V12)
- T3만 counter_refs 가능, 하지만 대상은 T1/T2만 가능 (V11b)
- T1/T2는 counter_refs 자체를 가질 수 없으므로 그래프를 되짚어 올 간선 없음
- 결과: 순환 참조가 구조적으로 불가능

---

## 3. `test_m2_source_registry_governance.py` — 신규 테스트 6종

**판정: CONCERN** (사소한 테스트 누락)

### 근거

실제 pytest 실행 결과: **33 passed, 2 skipped** (모든 신규 테스트 통과).

6개 테스트가 V9-V12를 커버하는 범위:

| 검증 | 테스트 | 상태 |
|------|--------|------|
| V9 (authority_tier enum) | test_pos_08 (실제 M2 대상, 공허 통과) | OK |
| V9 (tradition_relation enum) | test_neg_12에서 tradition_relation="own" 사용 (값은 유효) | PARTIAL |
| V10 (T3 → counter_refs 필수) | test_neg_09 | OK |
| V11(a) (orphan 참조) | test_neg_10 | OK |
| V11(b) (대상 ∉ {T1,T2}) | test_neg_11 | OK |
| V12 (T1/T2/T4 → counter_refs 금지) | test_neg_12 (3-tier 파라미터화) | OK |
| 정상 케이스 (T3→T2) | test_pos_09 | OK |

### CONCERN 상세: V9 두 번째 조건 negative 테스트 누락

코드상 다음 분기가 존재하지만 이를 검증하는 negative 테스트가 없다:

```python
if tier is not None and rel is None:
    result.add("FAIL", f"V9: M2 record {sid} has authority_tier but no tradition_relation")
```

즉, **`authority_tier`는 있는데 `tradition_relation`이 없는 경우**에 대한 negative 테스트가 누락됐다. 현재 구현에서는 이 분기가 실제 M2 레코드에서触发될 수 없다(백필 전이므로) — 하지만 테스트 커버리지 관점에서 V9의 두 가지 실패 조건 중 하나를 검증하는 테스트가 없다.

**영향도**: 사소함. 백필 전이므로 실제 런타임에서 이 경로가触发될 가능성 없음. 테스트상으로도 `authority_tier`만 설정하고 `tradition_relation`을 생략한 synthetic 레코드로 추가 negative 테스트 1건이면 충분.

---

## 4. Freeze 준수 확인

**판정: PASS**

### 근거

| 항목 | git diff 결과 | 판정 |
|------|--------------|------|
| M2 YAML (`source_manifest.yaml`) | empty (무변경) | OK |
| `core/retrieval.py` | empty (무변경) | OK |
| Retrieval Engine 비접촉 게이트 | diff에 포함되지 않음 | OK |

Amendment D §3의 "Retrieval Engine 비접촉 게이트"를 이번 구현이 위반하지 않음을 확인.

---

## 5. Build Report의 회귀 주장 검증

**판정: PASS**

### 근거

Build Report가 보고한 실패 2건을 직접 재현하고 분석:

```
FAILED tests/test_indexer_review_gate_wiring.py::...test_real_production_dry_run_excludes_non_verified
    assert 8936 == 3319  ← TSU 인덱스 baseline 하드코딩(3319) vs 실제 디스크(8936)

FAILED tests/test_nae_pilot_human_review_intake.py::...test_real_production_review_gate_state_unchanged
    assert 8936 == 3319  ← 동일 원인
```

**무관성 확인:**

- `grep`으로 두 테스트 파일에서 `m2_source_registry_validator`, `pipeline.py`(registration), `check_authority_tier`에 대한 import를 검색 → **NO_IMPORTS_FOUND**
- `test_indexer_review_gate_wiring.py`는 `NAE.pipeline.index.indexer`만 import (인덱서 관련)
- `test_nae_pilot_human_review_intake.py`는 `NAE.review.human` 모듈만 import (리뷰 관련)
- 두 테스트 모두 이번 구현(diff 5개 파일)과 **import/의존 관계가 전혀 없음**

Build Report의 "본 구현과 무관" 주장에 **동의**. 실패 원인은 TSU 데이터 증가로 인한 baseline 하드코딩 값(3319)의 stale화 — 별도 이슈로 분리 필요.

---

## 종합 판정

### GREEN

| 항목 | 판정 |
|------|------|
| 1. pipeline.py 변경 | PASS |
| 2. V9-V12 신규 검사 | PASS |
| 3. 신규 테스트 6종 | CONCERN (사소) |
| 4. Freeze 준수 | PASS |
| 5. 회귀 주장 검증 | PASS |

**B3 충족.** CONCERN(§3)은 사소한 테스트 누락으로 실제 기능에 영향 없음. B4 (HQ 최종 승인) 요청 단계로 진행 가능.

### CONCERN 상세 (CUE 반영 권장)

`tests/test_m2_source_registry_governance.py::TestAuthorityTierGovernance`에 다음 테스트 추가 권장:

```python
def test_neg_09b_tier_without_tradition_relation_fails(self):
    """authority_tier는 있는데 tradition_relation 없으면 → V9 FAIL."""
    import scripts.m2_source_registry_validator as v
    synthetic = [{**{k: "x" for k in M2_BASE_KEYS}, "source_id": "SYN-T3-NOREL",
                  "authority_tier": "T3"}]  # tradition_relation 생략
    fails = v.check_authority_tier_fields(synthetic).failed
    assert any("V9" in f and "tradition_relation" in f for f in fails), \
        f"T3 without tradition_relation should FAIL V9: {fails}"
```

---

## 게이트

- **B3 (C1 구현 코드 검토): GREEN**
- 다음 단계: B4 (HQ 최종 승인) → Amendment D APPROVED 승격
- 승인 이후 Plan 001 §6-§8(실제 M2 backfill, `corpus_admissions.jsonl` 태깅)은 별도 HQ 결정·별도 작업

---

**End of C1 Review Result 003.**
