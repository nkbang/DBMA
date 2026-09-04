# NAE C1 Independent Review — ID Governance Resolution Plan

**Project:** NAE-ID-GOVERNANCE-REVIEW-002  
**Task Order:** C1-TASK-ORDER-038  
**Date:** 2026-08-03  
**Reviewer:** C1 (Independent Architecture Review)  
**Nature:** Read-Only Policy Validation  
**Git Commit/Push:** 미수행 — 사용자 승인 대기  

---

## 1. Executive Summary

C1은 NAE-CUE가 작성한 `NAE_ID_GOVERNANCE_RESOLUTION_PLAN_001.md`의 정책 타당성을 ADR-017, `NAE_ID_GOVERNANCE_v1.md`, Production Registry와 대조하여 독립적으로 검증했다.

**판정: APPROVED WITH CONDITIONS**

---

## 2. Review Targets

| # | 대상 | 상태 | 설명 |
|---|---|---|---|
| 1 | `docs/NAE_ID_GOVERNANCE_RESOLUTION_PLAN_001.md` | ✅ 작성 완료 | 정책 설계 문서 |
| 2 | `docs/NAE_ID_GOVERNANCE_v1.md` | ✅ 정본 | ID Governance v1 (333라인) |
| 3 | `ADR-017-NAE-ID-Governance-Standard.md` | ✅ Proposed | ID Governance Standard (120라인) |
| 4 | `resources/theological_sources/authority/` | ✅ Production | Registry 5 YAML 파일 |
| 5 | `resources/theological_sources/manifest/` | ✅ Pilot | Manifest Layer 3 YAML 파일 |

---

## 3. Migration Strategy 검증 (Option B)

### 3.1 Option B: Canonical + Legacy Alias

| 평가 항목 | 검증 결과 | 설명 |
|---|---|---|
| 참조 안정성 | ✅ 안전 | 기존 FK 문자열 변경 안 함 → 하위 호환 유지 |
| Audit 추적성 | ✅ 안전 | `legacy_id` 필드로 구 ID 역참조 가능 |
| 향후 Migration 가능성 | ✅ 안전 | `canonical_id` 필드 추가 후 점진적 전환 가능 |

### 3.2 Option A (즉시 Rename) 기각 근거 검증

Resolution Plan §3에서 Option A를 기각한 이유:
> "18개 파일(3개 계층)의 FK를 한 트랜잭션으로 동시에 바꿔야 함 — 하나라도 누락되면 authority_validator.py/manifest_validator.py가 즉시 Broken Reference로 잡아내지만, 그 사이 순간에도 데이터 일관성이 깨진 상태가 존재"

**검증: PASS** — 18개 파일 중 하나라도 누락되면 FAIL가 발생하므로, Option B가 현저히 안전함.

### 3.3 Option B 단점 평가

Resolution Plan §3에서 명시한 단점:
> "과도기 동안 두 ID 체계가 공존 — Validator가 legacy_id/canonical_id 양쪽을 다 알아야 함"

**검증: INFO (관리 가능)** — §6 실행 순서에서 3개 Validator 확장 계획이 이미 설계됨.

---

## 4. Blast Radius 검증

### 4.1 26개 ID 참조 위치 실측

Resolution Plan §2.1에서 주장한 "3개 계층·18개 파일"을 검증:

| 계층 | Directory | 파일 수 | 상태 |
|---|---|---|---|
| Production Registry | `authority/*.yaml` | 5 파일 | ✅ 확인 |
| Pilot Registry | `authority/pilot/*`, `authority/fuller/*` | 10 파일 | ✅ 확인 |
| Manifest Layer | `manifest/pilot/*/manifest.yaml` | 3 파일 | ✅ 확인 |
| **합계** | | **18 파일** | ✅ 일치 |

**판정: PASS** — 18개 파일 주장 정확함.

### 4.2 26개 ID 목록 실측 대조

| Entity 타입 | Resolution Plan 주장 | Production 실측 | 일치 |
|---|---|---|---|
| Author | 1건 (`FULLER-ANDREW-001`) | 1건 | ✅ |
| Work | 3건 | 3건 | ✅ |
| Edition | 4건 | 4건 | ✅ |
| Volume | 8건 | 8건 | ✅ |
| Source | 10건 | 10건 | ✅ |
| **합계** | **26건** | **26건** | ✅ |

**판정: PASS** — 26건 목록 정확함. `authority_validator.py` 실행 결과(74 PASS/26 WARNING/0 FAIL)와 정확히 일치.

### 4.3 "이미 참조 중"이 Type C을 성립시키지 않는 근거 검증

Resolution Plan §2.1에서 주장:
> "이 26건은 내부 데이터 계층끼리만 참조하고 있어 외부 종속성이 없다"

**검증:** Production Registry, Pilot Registry, Manifest Layer 모두 동일 Repository 내 데이터. 외부 시스템(예: archive.org, 외부 API)의 참조 없음.

**판정: PASS** — Type A(Canonical 불일치) 분류 정확함. Type B/Type C 해당 사례 없음.

---

## 5. ID Mapping Source 검증

### 5.1 정본 위치

Resolution Plan §4에서 주장:
> "이미 `NAE_ID_GOVERNANCE_v1.md` §6.2에 26건 전부 존재 — 이번 Resolution Plan은 그 표를 재도출하지 않고 그대로 정본으로 채택"

**검증:** `NAE_ID_GOVERNANCE_v1.md` §6.2(279~318라인)에서 26건 매핑표 확인:
- Author 1건: `FULLER-ANDREW-001 -> fuller_andrew`
- Work 3건: `WORK-DAGG-*`, `WORK-HISCOX-*`, `FULLER-COMPLETE-WORKS-001`
- Edition 4건: `WORK-DAGG-*`, `WORK-HISCOX-*`, `FULLER-COMPLETE-WORKS-*` (2판)
- Volume 8건: `FULLER-COMPLETE-WORKS-VOL01~VOL08`
- Source 10건: `BAP-CHURCH-DAGG-001`, `BAP-CHURCH-HISCOX`, `BAP-MISS-FULLER-VOL01~VOL08`

**판정: PASS** — 26건 매핑표 정확함. 별도 Mapping 문서 생성 불필요한 결정 적절함.

### 5.2 재작성 시 위험 평가

Resolution Plan §4에서 주장:
> "재작성 시 두 문서가 어긋날 위험만 커짐"

**검증:** 실제로 Resolution Plan이 매핑표를 재작성하면 `NAE_ID_GOVERNANCE_v1.md`와 어긋날 가능성 높음(인위적 계산 오류, 오타 등).

**판정: PASS** — 정본 단일화 결정 적절함.

---

## 6. ADR-017 영향 평가

### 6.1 ADR-017 본문 수정 필요성

Resolution Plan §5에서 판정:
> "ADR-017 유지(수정 불필요)"

**검증:** ADR-017 §3.1 Canonical ID Rule이 Resolution Plan의 Option B와 충돌하지 않음:
- ADR-017: "lowercase, snake_case, ASCII only" → Option B의 `canonical_id` 필드 규칙과 일치
- ADR-017 §3.3: "변경 필요 + legacy_id alias 보존" → Option B와 정확히 일치
- ADR-017 본문은 규칙 정의만 포함, 실행 절차는 포함 안 함 → 수정 불필요

**판정: PASS** — ADR-017 유지 판정 정확함.

### 6.2 `NAE_ID_GOVERNANCE_v1.md` 보완 필요성

Resolution Plan §5에서 권고:
> "3계층 18파일 blast radius와 Option B 재확인 근거는 이번 문서에만 있음 — 향후 혼동 방지를 위해 pointer 한 줄만 추가하는 것을 권고"

**검증:** `NAE_ID_GOVERNANCE_v1.md`에 Resolution Plan을 가리키는 reference 없음. 향후 참조 시 blast radius 근거를 찾기 어려움.

**판정: WARNING (저우선)** — pointer 추가 권고. 이번 작업에서는 미실행.

---

## 7. Migration Gate 판단

### 7.1 3개 항목 판단

| 항목 | 가능 여부 | 근거 |
|---|---|---|
| ID Rename 실행 | **NO** | Option B 채택 → canonical_id/legacy_id 필드 추가 설계 먼저 필요 |
| Metadata Migration | **NO** | Resolution Plan §6: "ID Governance Migration이 Corpus-wide Metadata Migration보다 선행" |
| TSU Pipeline | **NO (권장 지연)** | Resolution Plan §6: "지금 비표준 ID로 TSU 생성 시, 이후 canonical_id 전환 시 이미 생성된 TSU 레코드 안의 참조까지 함께 갱신해야 함" |

### 7.2 실행 순서 검증

Resolution Plan §6에서 제시한 순서:
```
1. Resolution Plan(정책) 승인
   ↓
2. C1 ID Governance Review-002(독립 검증) ← 현재 단계
   ↓
3. canonical_id/legacy_id 필드를 Registry Schema에 추가하는 설계
   ↓
4. 3개 Validator 확장(코드 변경, 별도 승인)
   ↓
5. Registry 18개 파일에 실제 canonical_id 필드 추가(RAW/FK 문자열 자체는 변경 안 함)
   ↓
6. 이후에만 Corpus-wide Metadata Migration 재검토
```

**검증:** 순서 논리적임. Option B의 `canonical_id` 필드 추가 없이 Validator 확장 불가 → Validator 확장 없이 Registry 수정 불가.

**판정: PASS** — 실행 순서 적절함.

---

## 8. Policy Validity Assessment

### 8.1 Option B 전략적 타당성

| 항목 | 평가 | 설명 |
|---|---|---|
| 무중단 운영 | ✅ | 기존 FK 문자열 변경 안 함 |
| 점진적 전환 | ✅ | `canonical_id` 필드 추가 후 하위 호환 유지 |
| 검증 용이성 | ✅ | `authority_validator.py`가 `canonical_id`/`legacy_id` 인식하면 자동 검증 가능 |
| 외부 호환성 | ✅ | 기존 참조 시스템(archive.org 등)에 영향 없음 |

### 8.2 Risks

| # | Risk | 평가 | 설명 |
|---|---|---|---|
| 1 | `canonical_id`/`legacy_id` 필드 추가 시 Schema 변경 필요 | **WARNING** | Registry Schema 확장 별도 승인 필요 |
| 2 | 3개 Validator 확장 코드 변경 필요 | **WARNING** | source/manifest/authority Validator 전부 수정 필요 |
| 3 | 과도기 동안 두 ID 체계 공존으로 혼란 가능성 | **INFO** | 문서화·교육으로 관리 가능 |

---

## 9. Final Verdict

### **APPROVED WITH CONDITIONS**

### 조건 (3개)

| # | 조건 | 설명 |
|---|---|---|
| 1 | `canonical_id`/`legacy_id` 필드 Registry Schema 추가 설계 | Option B 실행을 위한 필수 전제 |
| 2 | 3개 Validator 확장(코드 변경, 별도 승인) | §6 실행 순서 Step 4 |
| 3 | `NAE_ID_GOVERNANCE_v1.md`에 Resolution Plan pointer 추가 | 문서 정합성 유지 (저우선) |

---

## 10. Required Questions Answered

### Q1: Migration Strategy Option B는 승인 가능한가?

**답: YES (WITH CONDITIONS)** — 참조 안정성, Audit 추적성, 향후 Migration 가능성 전부 검증 통과. 단, `canonical_id`/`legacy_id` 필드 추가 설계 필요.

### Q2: Blast Radius 18개 파일 분석은 충분한가?

**답: YES** — Production Registry(5), Pilot Registry(10), Manifest Layer(3) 전부 실측 확인. 26개 ID 목록도 `authority_validator.py` 실행 결과와 정확히 일치.

### Q3: ID Mapping Source 단일화 결정은 적절한가?

**답: YES** — `NAE_ID_GOVERNANCE_v1.md` §6.2에 26건 매핑표 존재. 별도 문서 생성 시 어긋날 위험만 커짐.

### Q4: ADR-017 수정이 필요한가?

**답: NO** — ADR-017 §3.3("변경 필요 + legacy_id alias 보존")이 Option B와 정확히 일치. 본문 수정 불필요.

### Q5: Migration Gate는 통과하는가?

**답: NO (3개 항목 전부)** — ID Rename, Metadata Migration, TSU Pipeline 모두 Option B 실행 전까지 지연 권장.

---

## 11. Next Steps (C1 승인 후)

| # | 단계 | 설명 | 우선순위 |
|---|---|---|---|
| 1 | ADR-016/017/019 Status Promotion 검토 | Proposed → Approved 전환 | HIGH |
| 2 | Quality Gate Pipeline 설계 | ADR-019에서 신규 추가 예정 단계 | MEDIUM |
| 3 | Migration Readiness 재평가 | Option B 실행 전 최종 확인 | MEDIUM |

---

*RAW Corpus, Manifest, TSU Dataset, Embedding, RetrievalEngine, Registry YAML — 전부 수행하지 않음(read-only inspection + validator 실행만). Git Commit은 사용자 승인 후에만 수행한다.*