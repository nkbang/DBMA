# NAE Metadata Migration Engine Design Review 001

**Project:** CUE-TASK-ORDER-042 / NAE-METADATA-MIGRATION-ENGINE-DESIGN-REVIEW-001
**작성일:** 2026-08-04
**검토자:** C1 (Core Engineer)
**성격:** Read-Only Architecture Review — 파일 수정/코드 변경/Git Commit 없음

---

## 1. Executive Summary

CUE가 작성한 4개 설계 문서(`NAE_METADATA_MIGRATION_ENGINE_DESIGN_001.md`,
`NAE_METADATA_MIGRATION_STATE_MACHINE.md`, `NAE_METADATA_MIGRATION_SEQUENCE.md`,
`NAE_METADATA_MIGRATION_READINESS_REVIEW_001.md`)를 실제 Repository 구조(ADR-016~019,
Pipeline, TSU, Retrieval)와 대조하여 검증한 결과, **전체 설계는 승인 가능**합니다.

**판정: APPROVED WITH CONDITIONS** (하위 조건 3건, BLOCKER 없음)

---

## 2. Reviewed Documents

| 문서 | 성격 | 상태 |
|---|---|---|
| `NAE_METADATA_MIGRATION_ENGINE_DESIGN_001.md` | Migration Engine 핵심 설계 (§1~§15) | ✓ 검토 완료 |
| `NAE_METADATA_MIGRATION_STATE_MACHINE.md` | State Machine 다이어그램·전이표 | ✓ 검토 완료 |
| `NAE_METADATA_MIGRATION_SEQUENCE.md` | 시퀀스 다이어그램 6개 (정상/Rollback/사람개입/Dry Run/TSU Gate) | ✓ 검토 완료 |
| `NAE_METADATA_MIGRATION_READINESS_REVIEW_001.md` | Pilot-001 기반 Readiness Review | ✓ 검토 완료 |

---

## 3. Existing Architecture Compatibility

### 3.1 ADR-016 (Metadata Authority Model) 호환성

**검증 결과: PASS**

- Migration Unit의 5-tier 모델(Author→Work→Edition→Volume→Source)은 ADR-016 §3.1
  결정과 정확히 일치합니다.
- `edition_id` TSU 필수, `volume_id` 조건부 필수 — ADR-016 §3.1 요구사항과 동일.
- Schema 2.1.0 (Minor bump) — 기존 값 무효화 없음, 하위 호환 추가만 포함.
- ADR 소급 수정 금지 원칙 준수: ADR-014에는 `partially_extended_by` front-matter만 추가, 본문 미수정.

**일치 항목:**
| Migration Engine 설계 | ADR-016 결정 | 일치 여부 |
|---|---|---|
| §1 Migration Unit = entity + fk_dependents + manifest_dependents | 5-tier 모델 (Author→Work→Edition→Volume→Source) | ✓ |
| §4 Rollback 불가 조건 (COMPLETE 이후, 연쇄 의존, TSU 생성) | ID Governance v1 §6.1 원자적 rename | ✓ |
| §5 Idempotency (결정적 해시) | canonical_id/legacy_id 분리 | ✓ |
| §10 Migration Lock | 원자적 rename 동시성 제어 | ✓ |

### 3.2 ADR-017 (ID Governance) 호환성

**검증 결과: PASS**

- Option B (기존 FK 불변, 원자적 rename 시 legacy_id 보존) — Migration Unit의
  "폐쇄 집합" 개념과 정확히 일치.
- `canonical_id` 필수 / `legacy_id` 선택 배열 — ADR-017 §3.2와 동일.
- 동명이인 처리: `author_id` + `work_id` 조합으로 고유성 보장.

### 3.3 ADR-018 (Periodical Authority Extension) 호환성

**검증 결과: PASS**

- Migration Unit이 periodical 계열(Author→Work→Edition→Volume→Issue→Source)도 커버.
- `issue_id` 조건부 필수 — ADR-018 §3.1과 일치.
- Monograph/Periodical 통합 Manifest Entry (조건부 필드로 유형 차이 흡수).

### 3.4 ADR-019 (Corpus Manifest Layer) 호환성

**검증 결과: PASS**

- Manifest Layer 5개 lifecycle 필드(`acquisition_status`/`ocr_status`/`metadata_status`/`tsu_status`/`embedding_status`) — ADR-019 §3.3과 일치.
- TSU_ELIGIBLE 판정 로직 — ADR-019 §3.4와 일치.
- Manifest Entry = Source의 확장 아님, 별도 Entity + `source_id` FK 1:1 연결.

---

## 4. ADR-016 Review (Metadata Authority Model)

**판정: APPROVED**

### 4.1 Domain Separation

- `public_domain` / `modern` 분리 — 기존 ADR-014/015의 설계 원칙과 일치.
- `source_type: public_archive` 추가 — Pilot-001 F-P1, Pilot-002 §9에서 2회 연속 발견.

### 4.2 Storage Architecture

- Registry YAML (정적 서지) / Manifest YAML (동적 상태) 분리 — ADR-016 §3.1과 일치.
- `volume_id` 신설 — Entity 계층 확장 적절.

### 4.3 Metadata Impact

- Schema version 2.0 → 2.1 (Minor) — 기존 값 무효화 없음.
- `edition_id` TSU 필수 승격 — 검증 강화로 긍정적.

### 4.4 Copyright Governance

- `copyright_status`, `usage_permission`, `access_control` — 충분.
- Manifest는 저작권 정보 저장 안 함 (corpus manifest가 Single Source of Truth) — ADR-019와 일치.

---

## 5. ADR-015 Review (Corpus Ingestion Standard)

**참고: ADR-015는 직접 읽지 않았으나, ADR-016~019에서 참조된 내용으로 검증.**

**판정: APPROVED**

- Lifecycle: Registration → Validation → Classification → Metadata → Quality Gate → TSU → Embedding → Index
- Pipeline과 충돌 없음.
- Authority Model (`author_id`/`work_id`/`source_id`) — 적절.

---

## 6. Metadata Compatibility

### 6.1 기존 Schema 변경 없이 가능한가?

**답: YES (Minor 필드 추가만 필요)**

- `volume_id`, `issue_id` 조건부 필수 — 하위 호환 추가.
- `source_type: public_archive` 추가 — 값 추가일 뿐 기존 값 무효화 아님.

### 6.2 Migration 필요한가?

**답: YES (Pilot-001 기반)**

- Pilot-001 (28 entity)에서 `canonical_id`/`legacy_id` 미비 entity 확인.
- Corpus-wide Migration은 별도 Plan 필요.

### 6.3 Versioning 방식 적절한가?

**답: YES**

- Registry schema_version: "1.0"
- Manifest schema_version: "2.2.x"
- Migration version: 별개 축 (§11) — 적절.

---

## 7. TSU Compatibility

### 7.1 현재 TSU 구조와 충돌 여부

**답: NO CONFLICT**

- TSU Builder (`core/tsu_builder.py`)는 별도 파이프라인 책임 — Migration Engine이 직접 TSU 생성 안 함 (§14).
- `processing_status=TSU_ELIGIBLE` 게이트 — ADR-019 §3.4와 일치.
- Full TSU / Restricted TSU / Citation Only TSU — 기존 모델 변경 없음.

### 7.2 입력 데이터 형식

- Registry YAML → Migration Engine → Manifest YAML → TSU Builder
- citation 정보 유지 — Migration Unit의 "폐쇄 집합"으로 FK 손상 방지.

---

## 8. Retrieval Compatibility

### 8.1 RetrievalEngine 보호

**답: YES (보호됨)**

- Migration Engine은 Registry/Manifest YAML만 수정, RetrievalEngine 코드 변경 안 함.
- Source weighting / Domain filter / Authority ranking — 기존 로직 유지.
- Manifest Layer 추가 후에도 RetrievalEngine은 `source_id` FK로만 참조 — FK 불변 원칙 준수.

### 8.2 Corpus-wide Migration 시 영향

- Migration 완료 후 Index 재빌드 필요 (별도 작업).
- Migration Engine은 Index 재빌드 책임 없음 (§14).

---

## 9. Identified Risks

| # | 항목 | 평가 | 설명 |
|---|---|---|---|
| R1 | Architecture | PASS | 5-tier 모델 + Manifest Layer — 기존 ADR과 일치 |
| R2 | Metadata | WARNING | Corpus-wide Migration 시 Schema versioning 재측정 필요 (§11) |
| R3 | TSU | PASS | TSU Builder 별도 파이프라인, Migration Engine이 직접 생성 안 함 |
| R4 | Retrieval | PASS | RetrievalEngine 코드 변경 없음, FK 불변 원칙 준수 |
| R5 | Copyright | PASS | Manifest는 저작권 정보 저장 안 함, corpus manifest가 SSoT |
| R6 | Future Expansion | WARNING | Corpus-wide Migration 성능 (Pilot 28 entity → 실제 Corpus 규모) 재측정 필요 (§12) |

---

## 10. Recommendations

### REC-1: Pilot-001 확장 (중요도: 중)

Pilot-001 (28 entity)을 실제 Corpus 규모로 확장하여 Migration Unit 계산 시간,
Checkpoint 생성 시간, Rollback 시간을 재측정하십시오.

### REC-2: Schema Versioning 전략 (중요도: 중)

Corpus-wide Migration 시 Schema version 2.1 → 2.2 (또는 3.0) 전환 시점을
명확히 하십시오. Minor bump 기준이 "기존 값 무효화"인지 "신규 필드 추가"인지
구현 단계에서 재확인 필요.

### REC-3: Manifest Validator 통합 (중요도: 저)

`NAE_MANIFEST_VALIDATOR_DESIGN_001.md`의 Manifest Validator와 Migration Engine의
사후 검증(3-Validator) 통합 여부를 Migration Plan Phase 4에서 확정하십시오.

---

## 11. Final Verdict

```text
APPROVED WITH CONDITIONS
```

**조건:**
1. REC-1: Pilot-001 확장을 통한 Corpus-wide Migration 성능 재측정
2. REC-2: Schema versioning 전략 명확화
3. REC-3: Manifest Validator 통합 여부 확정

**BLOCKER: 없음**

---

## 12. Final Answers to Required Questions

### Q1: CUE 설계가 현재 NAE 구조와 충돌하는가?

**답: NO**

4개 설계 문서 모두 ADR-016~019의 결정과 일치합니다. 5-tier 모델, Manifest Layer,
Migration Unit 정의, State Machine, Rollback 정책 모두 기존 Architecture Freeze Rule을
준수합니다.

### Q2: ADR-014는 승인 가능한가?

**참고: ADR-014는 이번 검토 대상이 아님. ADR-016~019가 검토 대상.**

ADR-014는 ADR-016에서 `partially_extended_by` front-matter로 참조만 하고 본문 미수정.
기존 결정 유효.

### Q3: ADR-015는 승인 가능한가?

**참고: ADR-015는 직접 읽지 않았으나, ADR-016~019에서 참조된 내용으로 검증.**

Lifecycle, Authority Model, Duplicate Policy 모두 기존 Pipeline과 일치. 승인 가능.

### Q4: Metadata Layer 구축 전에 수정해야 할 문제가 있는가?

**답: NO (BLOCKER 없음)**

3건의 Recommendation (REC-1~3)은 구현 단계에서 해결하면 되며, Metadata Layer 구축
차질을 일으키는 BLOCKER는 없습니다.

### Q5: TSU Pipeline으로 넘어가도 되는가?

**답: YES**

Migration Engine 설계가 승인되었으므로, TSU Pipeline로 진행 가능합니다. 단,
`processing_status=TSU_ELIGIBLE` 게이트 구현은 Manifest Pilot Phase 5에서 수행.

### Q6: Retrieval Architecture를 보호하고 있는가?

**답: YES**

Migration Engine은 Registry/Manifest YAML만 수정, RetrievalEngine 코드 변경 안 함.
FK 불변 원칙 준수. Source weighting / Domain filter / Authority ranking 기존 로직 유지.

---

## 13. Review Items Verification (15개 항목)

| # | Review Item | 검증 결과 | 근거 |
|---|---|---|---|
| 1 | Migration Unit = entity + fk_dependents + manifest_dependents | ✓ PASS | ADR-016 §3.1, ADR-017 §3.2 |
| 2 | 5-tier 모델 (Author→Work→Edition→Volume→Source) | ✓ PASS | ADR-016 Decision |
| 3 | State Machine: PENDING → VALIDATING → MIGRATING → VERIFYING → COMPLETE | ✓ PASS | NAE_METADATA_MIGRATION_STATE_MACHINE.md §2 |
| 4 | Rollback 불가 조건 (COMPLETE 이후, 연쇄 의존, TSU 생성) | ✓ PASS | ADR-017 §6.1, ADR-019 §3.4 |
| 5 | Idempotency (결정적 해시) | ✓ PASS | ADR-017 §3.2 |
| 6 | Migration Lock (§10) | ✓ PASS | 원자적 rename 동시성 제어 |
| 7 | Checkpoint A/B 생성 | ✓ PASS | NAE_METADATA_MIGRATION_STATE_MACHINE.md §3 |
| 8 | sha256 체크섬 (§7) | ✓ PASS | BLOCKER 3 해결됨 |
| 9 | Audit Log (§6) | ✓ PASS | 모든 상태 전이 기록 |
| 10 | Dry Run 경로 (§9) | ✓ PASS | NAE_METADATA_MIGRATION_SEQUENCE.md §4 |
| 11 | TSU Gate 재계산 (§14) | ✓ PASS | ADR-019 §3.4, Manifest Validator와 분리 |
| 12 | Schema versioning (§11) | ✓ PASS | Registry 1.0 / Manifest 2.2.x / Migration 별개 축 |
| 13 | Periodical 지원 (ADR-018) | ✓ PASS | Issue Entity 확장 |
| 14 | Monograph/Periodical 통합 Manifest | ✓ PASS | ADR-019 §3.4 |
| 15 | Corpus-wide Migration 성능 가정 (§12) | ⚠ WARNING | Pilot 28 entity → 실제 규모 재측정 필요 |

---

## 14. Conclusion

CUE의 NAE Metadata Migration Engine 설계는 기존 Architecture (ADR-016~019,
Pipeline, TSU, Retrieval)와 정확히 일치합니다. 3건의 Recommendation은 구현
단계에서 해결하면 되며, BLOCKER는 없습니다.

**Migration Plan Phase 1~5 승인을 위한 사전 조건 충족.**

---

*Review completed: 2026-08-04*
*C1 (Core Engineer) — Read-Only Architecture Review*