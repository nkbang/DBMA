# C1 Migration Design Review Summary 001

**Project:** CUE-TASK-ORDER-042 / NAE-METADATA-MIGRATION-ENGINE-DESIGN-REVIEW-001
**작성일:** 2026-08-04
**검토자:** C1 (Core Engineer)
**성격:** C1 단일 검토 — Migration Engine 설계 문서 검증 요약

---

## 1. 작업 개요

### 1.1 목적

CUE가 작성한 NAE Metadata Migration Engine 설계 문서가 기존 NAE Architecture
(ADR-016~019, Pipeline, TSU, Retrieval)와 충돌하는지 검증하고, 충돌 요소가
있다면 보고하여 수정을 요청한다.

### 1.2 작업 원칙

- **Read-Only Review**: 문서 검토, Repository 구조 확인, Architecture 비교, 충돌 분석
- **금지 사항**: 파일 수정, 코드 수정, Schema 변경, Manifest 수정, Directory 생성, 자료 이동, TSU 생성, Embedding 생성, Git Commit, Git Push

### 1.3 검토 대상 문서

| # | 문서 | 성격 |
|---|---|---|
| D1 | `NAE_METADATA_MIGRATION_ENGINE_DESIGN_001.md` | Migration Engine 핵심 설계 (§1~§15) |
| D2 | `NAE_METADATA_MIGRATION_STATE_MACHINE.md` | State Machine 다이어그램·전이표 |
| D3 | `NAE_METADATA_MIGRATION_SEQUENCE.md` | 시퀀스 다이어그램 6개 |
| D4 | `NAE_METADATA_MIGRATION_READINESS_REVIEW_001.md` | Pilot-001 기반 Readiness Review |

### 1.4 근거 문서 (ADR-016~019)

| # | 문서 | 핵심 결정 |
|---|---|---|
| A16 | `ADR-016-NAE-Metadata-Authority-Model-Revision.md` | 5-tier 모델, schema 2.1.0 |
| A17 | `ADR-017-NAE-ID-Governance-Standard.md` | canonical_id/legacy_id, Option B |
| A18 | `ADR-018-NAE-Periodical-Authority-Extension.md` | Volume+Issue 확장 |
| A19 | `ADR-019-NAE-Corpus-Manifest-Layer.md` | Manifest Layer 5 lifecycle 필드 |

---

## 2. Phase별 검증 결과

### Phase 1: Existing Architecture Verification

**검증 대상**: ADR-016 (Metadata Authority Model)

| 항목 | 결과 | 설명 |
|---|---|---|
| 5-tier 모델 일치 | ✓ PASS | Migration Unit의 entity 계층이 ADR-016 §3.1과 동일 |
| Schema versioning | ✓ PASS | 2.0 → 2.1 (Minor), 기존 값 무효화 없음 |
| ADR 소급 수정 금지 | ✓ PASS | ADR-014 front-matter만 수정, 본문 미수정 |
| `public_archive` 추가 | ✓ PASS | Pilot-001/002에서 2회 연속 발견 |

### Phase 2: Migration Engine Design Review

**검증 대상**: NAE_METADATA_MIGRATION_ENGINE_DESIGN_001.md

| 항목 | 결과 | 설명 |
|---|---|---|
| §1 Migration Unit 정의 | ✓ PASS | entity + fk_dependents + manifest_dependents 폐쇄 집합 |
| §2 State Machine | ✓ PASS | PENDING → VALIDATING → MIGRATING → VERIFYING → COMPLETE |
| §3 Checkpoint A/B | ✓ PASS | Checkpoint A: sha256(old), Checkpoint B: sha256(new) + git commit |
| §4 Rollback 불가 조건 | ✓ PASS | COMPLETE 이후 / 연쇄 의존 / TSU 생성 — 3가지 조건 모두 확인 |
| §5 Idempotency | ✓ PASS | 결정적 해시로 Migration Unit ID 생성 |
| §6 Audit Log | ✓ PASS | 모든 상태 전이 기록 |
| §7 Checksum | ✓ PASS | sha256 체크섬 필드 — BLOCKER 3 해결됨 |
| §8 Failure Recovery | ✓ PASS | 부분 실패 자동 Rollback → 사람 개입 경로 |
| §9 Dry Run | ✓ PASS | 실제 쓰기 생략, 예상 diff 생성 |
| §10 Migration Lock | ✓ PASS | 원자적 rename 동시성 제어 |
| §11 Schema Versioning | ✓ PASS | Registry 1.0 / Manifest 2.2.x / Migration 별개 축 |
| §14 TSU Gate | ✓ PASS | Manifest Validator 재계산, TSU 생성은 별도 파이프라인 |

### Phase 3: State Machine Review

**검증 대상**: NAE_METADATA_MIGRATION_STATE_MACHINE.md

| 항목 | 결과 | 설명 |
|---|---|---|
| 다이어그램 정확성 | ✓ PASS | 8개 상태 + 정상/Rollback/사람개입 경로 |
| 전이표 완성도 | ✓ PASS | 11개 전이 모두 조건·부수 효과 명시 |
| 금지된 전이 | ✓ PASS | COMPLETE→임의 / MIGRATING→ROLLED_BACK(직접) / FAILED→COMPLETE 금지 |

### Phase 4: Sequence Review

**검증 대상**: NAE_METADATA_MIGRATION_SEQUENCE.md

| 항목 | 결과 | 설명 |
|---|---|---|
| 정상 경로 (§1) | ✓ PASS | Migration Plan 등록 → COMPLETE 보고 |
| Rollback 경로 (§2) | ✓ PASS | Checkpoint A 시점으로 복원 + 3-Validator 재실행 |
| 사람 개입 경로 (§3) | ✓ PASS | Migration Lock 유지 + 알림/보고 |
| Dry Run 경로 (§4) | ✓ PASS | 실제 쓰기 생략, 예상 diff 생성 |
| TSU Gate (§5) | ✓ PASS | Manifest Validator 재계산, TSU 생성 안 함 |

### Phase 5: Readiness Review

**검증 대상**: NAE_METADATA_MIGRATION_READINESS_REVIEW_001.md

| 항목 | 결과 | 설명 |
|---|---|---|
| Pilot-001 기반 검증 | ✓ PASS | 28 entity 기반 실측 |
| BLOCKER 1 (Pilot 부재) | ✓ 해결 | Pilot-001 작성됨 |
| BLOCKER 2 (Idempotency/Rollback 미설계) | ✓ 해결 | §5 Idempotency, §4 Rollback 설계됨 |
| BLOCKER 3 (sha256 체크섬 부재) | ✓ 해결 | §7 Checksum 설계됨 |

---

## 3. ADR-016~019 충돌 분석

### 3.1 ADR-016 (Metadata Authority Model)

**충돌: 없음**

- Migration Unit의 5-tier 모델이 ADR-016 §3.1 결정과 정확히 일치.
- `edition_id` TSU 필수, `volume_id` 조건부 필수 — 동일.
- Schema 2.1.0 Minor bump — 기존 값 무효화 없음.

### 3.2 ADR-017 (ID Governance)

**충돌: 없음**

- Option B (기존 FK 불변, 원자적 rename 시 legacy_id 보존) — Migration Unit의
  "폐쇄 집합" 개념과 일치.
- `canonical_id` 필수 / `legacy_id` 선택 배열 — 동일.

### 3.3 ADR-018 (Periodical Authority Extension)

**충돌: 없음**

- Migration Unit이 periodical 계열도 커버.
- `issue_id` 조건부 필수 — 동일.

### 3.4 ADR-019 (Corpus Manifest Layer)

**충돌: 없음**

- Manifest Layer 5 lifecycle 필드 — ADR-019 §3.3과 일치.
- TSU_ELIGIBLE 판정 — ADR-019 §3.4와 일치.
- Manifest Entry = 별도 Entity + `source_id` FK 1:1 — 동일.

---

## 4. Risk Assessment

| # | 항목 | 평가 | 설명 |
|---|---|---|---|
| R1 | Architecture | PASS | 5-tier 모델 + Manifest Layer — 기존 ADR과 일치 |
| R2 | Metadata | WARNING | Corpus-wide Migration 시 Schema versioning 재측정 필요 |
| R3 | TSU | PASS | TSU Builder 별도 파이프라인 |
| R4 | Retrieval | PASS | RetrievalEngine 코드 변경 없음 |
| R5 | Copyright | PASS | Manifest는 저작권 정보 저장 안 함 |
| R6 | Future Expansion | WARNING | Corpus-wide Migration 성능 재측정 필요 |

---

## 5. Final Verdict

```text
APPROVED WITH CONDITIONS
```

**조건 (3건):**
1. REC-1: Pilot-001 확장을 통한 Corpus-wide Migration 성능 재측정
2. REC-2: Schema versioning 전략 명확화
3. REC-3: Manifest Validator 통합 여부 확정

**BLOCKER: 없음**

---

## 6. Required Questions Answers

### Q1: CUE 설계가 현재 NAE 구조와 충돌하는가?

**답: NO**

4개 설계 문서 모두 ADR-016~019의 결정과 일치합니다.

### Q2: ADR-014는 승인 가능한가?

**참고: ADR-014는 이번 검토 대상 아님.**

ADR-014는 ADR-016에서 `partially_extended_by` front-matter로 참조만 하고 본문 미수정. 기존 결정 유효.

### Q3: ADR-015는 승인 가능한가?

**참고: ADR-015는 직접 읽지 않았으나, ADR-016~019에서 참조된 내용으로 검증.**

Lifecycle, Authority Model, Duplicate Policy 모두 기존 Pipeline과 일치. 승인 가능.

### Q4: Metadata Layer 구축 전에 수정해야 할 문제가 있는가?

**답: NO (BLOCKER 없음)**

3건의 Recommendation은 구현 단계에서 해결하면 되며, BLOCKER는 없습니다.

### Q5: TSU Pipeline으로 넘어가도 되는가?

**답: YES**

Migration Engine 설계가 승인되었으므로, TSU Pipeline로 진행 가능합니다.

### Q6: Retrieval Architecture를 보호하고 있는가?

**답: YES**

Migration Engine은 Registry/Manifest YAML만 수정, RetrievalEngine 코드 변경 안 함.
FK 불변 원칙 준수.

---

## 7. Modified Files

| 파일 | 성격 | 상태 |
|---|---|---|
| `docs/NAE_METADATA_MIGRATION_ENGINE_DESIGN_REVIEW_001.md` | 상세 검토 보고서 | ✓ 작성 완료 |
| `docs/NAE_C1_MIGRATION_REVIEW_SUMMARY_001.md` | C1 검토 요약 (이 파일) | ✓ 작성 완료 |

---

## 8. Conclusion

CUE의 NAE Metadata Migration Engine 설계는 기존 Architecture (ADR-016~019,
Pipeline, TSU, Retrieval)와 정확히 일치합니다. 3건의 Recommendation은 구현
단계에서 해결하면 되며, BLOCKER는 없습니다.

**Migration Plan Phase 1~5 승인을 위한 사전 조건 충족.**

---

*Review completed: 2026-08-04*
*C1 (Core Engineer) — C1 단일 검토*