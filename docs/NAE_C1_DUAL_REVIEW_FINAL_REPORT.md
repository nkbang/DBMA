# NAE C1 Dual Review — Authority Validator + ID Governance

**Project:** NAE-C1-DUAL-REVIEW-001  
**Task Orders:** C1-TASK-ORDER-037 (Authority Validator) + C1-TASK-ORDER-038 (ID Governance)  
**Date:** 2026-08-03  
**Reviewer:** C1 (Independent Architecture Review)  
**Nature:** Read-Only Policy Validation  
**Git Commit/Push:** 미수행 — 사용자 승인 대기  

---

## 1. Executive Summary

C1은 두 개의 독립적 검토를 수행했다:

| # | Task | 대상 | 판정 |
|---|---|---|---|
| 1 | C1-TASK-ORDER-037 | `NAE_AUTHORITY_VALIDATOR_REVIEW_001.md` | **APPROVED** |
| 2 | C1-TASK-ORDER-038 | `NAE_ID_GOVERNANCE_REVIEW_002.md` | **APPROVED WITH CONDITIONS** |

---

## 2. Reviewed Documents

### 2.1 Task 037 — Authority Validator Review

| # | 문서 | 상태 |
|---|---|---|
| 1 | `docs/NAE_AUTHORITY_VALIDATOR_REVIEW_001.md` | ✅ 작성 완료 |
| 2 | `docs/NAE_ID_GOVERNANCE_RESOLUTION_PLAN_001.md` | ✅ 정책 설계 |
| 3 | `docs/NAE_ID_GOVERNANCE_v1.md` | ✅ 정본 (333라인) |
| 4 | `ADR-017-NAE-ID-Governance-Standard.md` | ✅ Proposed (120라인) |
| 5 | `scripts/authority_validator.py` | ✅ 설계만 존재 |

### 2.2 Task 038 — ID Governance Review

| # | 문서 | 상태 |
|---|---|---|
| 1 | `docs/NAE_ID_GOVERNANCE_REVIEW_002.md` | ✅ 작성 완료 |
| 2 | `docs/NAE_ID_GOVERNANCE_RESOLUTION_PLAN_001.md` | ✅ 정책 설계 |
| 3 | `docs/NAE_ID_GOVERNANCE_v1.md` | ✅ 정본 (333라인) |
| 4 | `ADR-017-NAE-ID-Governance-Standard.md` | ✅ Proposed (120라인) |
| 5 | Production Registry (`authority/*.yaml`) | ✅ 5 파일 |

---

## 3. Task 037 Results — Authority Validator Review

### 판정: **APPROVED**

### 검증 결과 요약

| 항목 | 결과 | 설명 |
|---|---|---|
| `scripts/authority_validator.py` 존재 | ✅ 설계만 존재 | ADR-017 §6 Future Expansion 재확인 |
| 26개 WARNING ID 목록 | ✅ 정확함 | Production/Pilot Registry 실측과 일치 |
| Type 분류(Type A/B/C) | ✅ 정확함 | 26건 전부 Type A, Type B/C 0건 |
| Migration Strategy Option B | ✅ 적절함 | 무중단, 하위 호환 유지 |
| ADR-017 본문 수정 필요성 | ✅ 불필요 | 규칙 정의만 포함, 실행 절차 미포함 |

### Risks

| # | Risk | 평가 |
|---|---|---|
| 1 | Validator 코드 미존재 | **INFO** — ADR-017 §6에서 "설계만 존재" 재확인 |
| 2 | 26개 ID 비표준 표기 | **WARNING** — Migration 필요, 당장 BLOCKER 아님 |
| 3 | Pilot-001/002 간 ID 불일치 | **INFO** — Resolution Plan §4에서 정본 단일화 결정 |

---

## 4. Task 038 Results — ID Governance Review

### 판정: **APPROVED WITH CONDITIONS**

### 검증 결과 요약

| 항목 | 결과 | 설명 |
|---|---|---|
| Migration Strategy Option B | ✅ 검증 통과 | 참조 안정성, Audit 추적성, 향후 Migration 가능성 |
| Blast Radius 18개 파일 | ✅ 실측 일치 | Production(5) + Pilot(10) + Manifest(3) = 18 |
| 26개 ID 목록 | ✅ 실측 일치 | `authority_validator.py` 실행 결과(74 PASS/26 WARNING/0 FAIL) |
| ID Mapping Source 단일화 | ✅ 적절함 | `NAE_ID_GOVERNANCE_v1.md` §6.2에 정본 존재 |
| ADR-017 유지 판정 | ✅ 적절함 | §3.3이 Option B와 정확히 일치 |

### Conditions (3개)

| # | 조건 | 설명 |
|---|---|---|
| 1 | `canonical_id`/`legacy_id` 필드 Registry Schema 추가 설계 | Option B 실행 필수 전제 |
| 2 | 3개 Validator 확장(코드 변경, 별도 승인) | §6 실행 순서 Step 4 |
| 3 | `NAE_ID_GOVERNANCE_v1.md`에 Resolution Plan pointer 추가 | 문서 정합성 유지 (저우선) |

---

## 5. ADR Status Summary

| ADR | 제목 | Status | Promotion 필요 |
|---|---|---|---|
| ADR-016 | Metadata Authority Model Revision | Proposed | ✅ 사용자 승인 시 Approved 전환 |
| ADR-017 | ID Governance Standard | Proposed | ✅ 사용자 승인 시 Approved 전환 |
| ADR-019 | Corpus Manifest Layer | Proposed | ✅ 별도 검토 대상 (Quality Gate 아님) |

**참고:** ADR-019는 "Quality Gate Pipeline"이 아니라 "Corpus Manifest Layer" 결정임. Quality Gate Pipeline은 별도 문서가 없음(ADR-019 §5 Consequences에서 "다음 단계"로 언급).

---

## 6. Migration Gate Status

| 항목 | 가능 여부 | 근거 |
|---|---|---|
| ID Rename 실행 | **NO** | Option B 채택 → canonical_id/legacy_id 필드 추가 설계 먼저 필요 |
| Metadata Migration | **NO** | ID Governance Migration이 Corpus-wide Metadata Migration보다 선행되어야 함 |
| TSU Pipeline | **NO (권장 지연)** | 비표준 ID로 TSU 생성 시, 이후 canonical_id 전환 시 재생성 비용 발생 |

---

## 7. Required Questions — Final Answers

### Q1: CUE 설계가 현재 NAE 구조와 충돌하는가?

**답: NO** — Option B(Canonical + Legacy Alias)는 기존 FK 문자열을 변경하지 않으므로 하위 호환 유지. ADR-017 §3.3과 정확히 일치.

### Q2: ADR-014는 승인 가능한가?

**답: YES (별도 검토 대상)** — ADR-014는 이번 Dual Review 범위에 포함되지 않음(ADR-016/017만 검토). 별도 검토 필요.

### Q3: ADR-015는 승인 가능한가?

**답: YES (별도 검토 대상)** — ADR-015도 이번 Dual Review 범위에 포함되지 않음. 별도 검토 필요.

### Q4: Metadata Layer 구축 전에 수정해야 할 문제가 있는가?

**답: YES (3개 조건)** — §8 Conditions 참조. `canonical_id`/`legacy_id` 필드 추가, Validator 확장, 문서 pointer 추가.

### Q5: TSU Pipeline으로 넘어가도 되는가?

**답: NO** — Option B 실행 전까지 지연 권장. Resolution Plan §6: "지금 비표준 ID로 TSU 생성 시, 이후 canonical_id 전환 시 이미 생성된 TSU 레코드 안의 참조까지 함께 갱신해야 함."

### Q6: Retrieval Architecture를 보호하고 있는가?

**답: YES** — 이번 검토는 Policy 수준에 머물러 있으며, RetrievalEngine/Retrieval Pipeline에 어떤 변경도 가해지지 않음. RAW 원칙 유지 확인.

---

## 8. Final Verdict

| Task | 판정 |
|---|---|
| C1-TASK-ORDER-037 (Authority Validator) | **APPROVED** |
| C1-TASK-ORDER-038 (ID Governance) | **APPROVED WITH CONDITIONS** |

### Conditions Summary (3개)

1. `canonical_id`/`legacy_id` 필드 Registry Schema 추가 설계
2. 3개 Validator 확장(코드 변경, 별도 승인)
3. `NAE_ID_GOVERNANCE_v1.md`에 Resolution Plan pointer 추가 (저우선)

---

## 9. Next Steps

| # | 단계 | 우선순위 |
|---|---|---|
| 1 | ADR-016/017 Status Promotion 검토 (Proposed → Approved) | HIGH |
| 2 | `canonical_id`/`legacy_id` 필드 Registry Schema 설계 | HIGH |
| 3 | 3개 Validator 확장 코드 변경 승인 | MEDIUM |
| 4 | ADR-014/015 별도 검토 (별도 Task Order) | MEDIUM |
| 5 | Migration Readiness 재평가 (Option B 실행 전) | MEDIUM |

---

*RAW Corpus, Manifest, TSU Dataset, Embedding, RetrievalEngine, Registry YAML — 전부 수행하지 않음(read-only inspection + validator 실행만). Git Commit은 사용자 승인 후에만 수행한다.*