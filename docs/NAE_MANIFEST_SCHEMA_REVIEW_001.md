# NAE Manifest Schema Review 001 — C1 Independent Verification

**Project:** NAE-MANIFEST-SCHEMA-REVIEW-001  
**Date:** 2026-08-02  
**Reviewer:** C1 (Independent Architecture Review)  
**Nature:** Read-Only Review — 수정/생성/삭제 없음  

---

## Executive Summary

Manifest Schema Design(NAE_CORPUS_MANIFEST_SCHEMA_DESIGN_v1.md, NAE_MANIFEST_SCHEMA_DESIGN_REPORT_001.md)과 ADR-019를 독립 검증한 결과, **기존 Architecture와 충돌하지 않으며 설계가 적절함**.

**판정: APPROVED WITH CONDITIONS**

---

## 1. Architecture Compatibility

### 검증 대상

| ADR | 검증 항목 | 판정 |
|---|---|---|
| ADR-001 (Retrieval Authority) | RetrievalEngine 보호 | **PASS** |
| ADR-014 (Domain Separation) | NAE-PD/NAE-MODERN/DBMA 분리 | **PASS** |
| ADR-015 (Lifecycle) | Ingestion Process vs Manifest State | **PASS** |
| ADR-016 (Authority Model) | Entity 모델(정적) vs Manifest(동적) | **PASS** |
| ADR-017 (ID Governance) | manifest_id = source_id 재사용 | **PASS** |
| ADR-018 (Periodical Extension) | work_type 조건부 필드 규칙 | **PASS** |
| ADR-019 (Manifest Layer) | 자체 설계 정합성 | **PASS** |

### 상세 분석

**ADR-001 (Retrieval Authority):**  
Manifest Schema는 TSU 이전 단계의 상태 추적만 담당. RetrievalEngine(코어 파이프라인)과 무관. **영향 없음.**

**ADR-014 (Domain Separation):**  
NAE-PD/NAE-MODERN/DBMA 3영역 분리 원칙 변경 없음. Manifest Schema는 도메인 구분과 무관한 상태 추적 계층. **영향 없음.**

**ADR-015 (Lifecycle):**  
Ingestion Process(운영 절차)와 Manifest State(상태 기록)는 별개 층위. 대응표가 Design v1 §Phase3에 명확히 정의됨. **호환.**

**ADR-016 (Authority Model):**  
Entity 모델(Author→Work→Edition→Volume→Issue→Source, 정적 구조)과 Manifest(동적 상태)는 층위가 다름. FK 연결만 하며 필드 직접 수정 없음. **영향 없음.**

**ADR-017 (ID Governance):**  
`manifest_id = source_id` 재사용 — 별도 ID 체계 신설 안 함. ID 정책 변경 없음. **호환.**

**ADR-018 (Periodical Extension):**  
`issue_id`를 optional로 표기 — monograph에서 forbidden은 Validator 책임으로 이전. 스키마 자체는 유연하게 개방. **적절.**

**ADR-019 (Manifest Layer):**  
자신 자신에 대한 설계 정합성 — 5개 세분화 상태 필드가 "processing_status 로 진행 추적"이라는 결정을 위반하지 않음(요약 processing_status 파생 필드로 유지). **정합.**

---

## 2. Schema Review

### 2.1 필드 누락 검증

**17개 필수 필드 (5개 범주):**

| 범주 | 필드 | 타입 | 누락 여부 |
|---|---|---|---|
| Identity | `manifest_id` | string(=source_id) | ✅ |
| Identity | `source_id` | string(Registry FK) | ✅ |
| Identity | `schema_version` | string("1.0.0") | ✅ |
| Authority Reference | `author_id` | string | ✅ |
| Authority Reference | `work_id` | string | ✅ |
| Authority Reference | `edition_id` | string\|null | ✅ |
| Authority Reference | `volume_id` | string\|null | ✅ |
| Authority Reference | `issue_id` | string\|null | ✅ |
| Processing Lifecycle | `acquisition_status` | pending\|acquired\|failed | ✅ |
| Processing Lifecycle | `ocr_status` | not_started\|in_progress\|complete\|failed | ✅ |
| Processing Lifecycle | `metadata_status` | not_started\|in_progress\|verified\|failed | ✅ |
| Processing Lifecycle | `tsu_status` | not_ready\|ready\|complete\|failed | ✅ |
| Processing Lifecycle | `embedding_status` | not_started\|in_progress\|complete\|failed | ✅ |
| Quality Gate | `ocr_quality` | PASS\|WARNING\|FAIL\|null | ✅ |
| Quality Gate | `metadata_verified` | boolean | ✅ |
| Quality Gate | `authority_verified` | boolean | ✅ |
| Quality Gate | `tsu_eligible` | boolean(파생) | ✅ |
| Audit | `created_at` | datetime | ✅ |
| Audit | `updated_at` | datetime | ✅ |
| Audit | `verified_by` | string\|null | ✅ |

**판정: 필드 누락 없음.**

### 2.2 필드 중복 검증

- `manifest_id`와 `source_id`는 서로 다른 역할:
  - `manifest_id`: Manifest Entry의 고유 식별자 (= source_id 값)
  - `source_id`: Registry sources.yaml FK (외부 참조)
  - 값은 동일하지만 역할이 다름 — 중복 아님.

- `schema_version`은 Manifest Entry 내부에서 자기 자신의 스키마를 가리킴 — 접두어 없이 단순 `schema_version` 사용 (Design v1 §Phase4 근거 적절).

**판정: 필드 중복 없음.**

### 2.3 Authority FK 연결 가능성

필요한 FK:
- `author_id` → `authority/authors.yaml`
- `work_id` → `authority/works.yaml`
- `edition_id` → `authority/editions.yaml` (monograph 필수, periodical null)
- `volume_id` → `authority/volumes.yaml` (다권본/periodical 필수, 단권 null)
- `issue_id` → `authority/issues.yaml` (periodical만, optional)

**판정: 모든 FK 연결 가능.** Registry 구조(ADR-016/018)와 정합.

### 2.4 Periodical 대응 가능성

- `work_type=periodical`일 때:
  - `edition_id`: null (Periodical은 Edition 개념 없음)
  - `volume_id`: 필수 (권号 식별)
  - `issue_id`: optional (스키마는 열어둠, Validator가 monograph에서 값 있으면 FAIL로 처리)

**판정: Periodical 대응 적절.** ADR-018과 정합.

---

## 3. Lifecycle Review

### 검증 구조

```
ADR-015 Ingestion Process (운영 절차)
        ↓
Manifest State Tracking (5개 세분화 필드)
        ↓
TSU Pipeline (처리 실행)
```

### 대응표 (Design v1 §Phase3)

| ADR-015 단계 | Manifest 필드 대응 | 판정 |
|---|---|---|
| Registration | `acquisition_status: acquired` | ✅ |
| Validation, Classification | `authority_verified` 계산 | ✅ |
| Metadata Creation | `metadata_status: in_progress → verified` | ✅ |
| Quality Check | `ocr_quality` 판정 결과 기록 | ✅ |
| Clean Processing | `ocr_status: in_progress → complete` | ✅ |
| TSU | `tsu_status: ready → complete` (`tsu_eligible=true`가 전이 조건) | ✅ |
| Embedding | `embedding_status: in_progress → complete` | ✅ |
| Index Update | Manifest 범위 밖 (Retrieval 책임, ADR-001) | ✅ |

**판정: Lifecycle 구조 적절.** ADR-015(절차)와 Manifest(상태)가 별개 층위로서 명확히 구분됨.

---

## 4. Status Model Review

### 5개 독립 상태 모델

```yaml
acquisition_status: pending | acquired | failed
ocr_status: not_started | in_progress | complete | failed
metadata_status: not_started | in_progress | verified | failed
tsu_status: not_ready | ready | complete | failed
embedding_status: not_started | in_progress | complete | failed
```

### 장점

1. **정밀한 진행도 추적**: "OCR은 끝났지만 metadata 검증이 아직 안 된 상태"처럼 동시에 여러 단계가 서로 다른 진행도를 가질 수 있는 실제 상황을 정확히 표현 가능.
2. **부분 실패 격리**: 한 단계에서 실패해도 다른 단계의 완료 기록이 보존됨.
3. **재작업 명확성**: `embedding_status`만 `in_progress`로 재설정 — 다른 4개 필드 완료 기록 그대로 보존.

### 위험 요소

| # | 위험 | 평가 | 완화 방안 |
|---|---|---|---|
| 1 | 상태 관리 복잡도 증가 | WARNING | 요약 `processing_status` 파생 필드로 빠른 필터링 제공 (§Phase6) |
| 2 | 역행 처리 오용 가능성 | WARNING | "요약값 강제 역행 금지" 정책 + audit 로그 필수 기록 (§Phase6) |
| 3 | Validator 구현 부담 | WARNING | `manifest_validator.py`가 forward-only 규칙 검사 (Option A, §Phase5) |

**판정: 장점 > 위험. 설계 적절.**

---

## 5. Validator Boundary Review

### 분리 구조

```
source_validator.py     (기존, corpus manifest)
        ↓
authority_validator.py  (설계만, Registry)
        ↓
manifest_validator.py    (신규 설계, Manifest Entry)
```

### Option A(분리) vs Option B(통합)

**Option A 채택 근거:**
- 세 계층(corpus manifest/Registry/Manifest)은 각각 다른 파일·다른 갱신 빈도·다른 책임
- 통합 시 책임이 섞이고 회귀 테스트 범위가 불필요하게 커짐 (NAE_VALIDATOR_BOUNDARY_DESIGN_001.md §2와 동일 논리)

**`manifest_validator.py` 신규 책임:**
1. `tsu_eligible` 파생값이 계산식과 일치하는지 재계산·대조
2. 5개 상태 필드의 개별 전이 규칙 준수 여부(각 enum 내에서 forward-only)
3. `issue_id`가 monograph에 값 있으면 FAIL (스키마는 optional, Validator가 강제)

### 기존 source_validator.py 경계 침범 여부

**판정: 침범 없음.**  
`manifest_validator.py`는 **신규 도구**로, 기존 `source_validator.py`를 수정/확장하지 않음. 둘은 병렬 관계(서로 다른 파일, 다른 책임).

---

## 6. Migration Readiness

### 최종 질문 답변

| # | 질문 | 답변 | 근거 |
|---|---|---|---|
| 1 | Manifest Schema 승인 가능한가? | **예 (APPROVED)** | 17개 필드, 5범주, 누락/중복 없음, FK 연결 가능, Periodical 대응 적절 |
| 2 | 필수 필드 충분한가? | **예** | Identity(3) + Authority Reference(5) + Processing(5) + Quality Gate(4) + Audit(3) = 18개 (요약 processing_status 포함) |
| 3 | ADR-019 승인 가능한가? | **예 (APPROVED)** | 자체 설계 정합성, 기존 ADR(001~018)과 충돌 없음 |
| 4 | Manifest Pilot 생성 준비되었는가? | **아니오 (NOT READY)** | Schema v2.2.0 적용 먼저 필요 (BLOCKER) |
| 5 | Schema v2.2.0 적용 가능한가? | **아니오 (별도 승인 필요)** | NAE-SCHEMA-V2.2-IMPLEMENTATION-DESIGN-001 산출물 이미 설계 완료, 적용만 남음 — 별도 승인 대상 |
| 6 | Metadata Migration 가능한가? | **아니오 (NOT READY)** | Manifest Entry 생성 + Validator 실행 먼저 필요 |
| 7 | TSU Pipeline 진입 가능한가? | **아니오 (NOT READY)** | `tsu_eligible` 계산 메커니즘이 설계 단계, `manifest_validator.py` 코드 없음 |

---

## 7. Risk Register

| # | 리스크 | 평가 | 설명 |
|---|---|---|---|
| 1 | 상태 관리 복잡도 증가 | WARNING | 5개 필드 + 요약값 — 관리 부담 증가하지만 요약값으로 완화 |
| 2 | 역행 처리 오용 가능성 | WARNING | "요약값 강제 역행 금지" 정책으로 완화 |
| 3 | Validator 구현 부담 | WARNING | `manifest_validator.py` 신규 개발 필요 |
| 4 | Schema v2.2.0 적용 전 Manifest Pilot 불가 | **BLOCKER** | `edition_id`/`volume_id`/`issue_id` 참조 대상이 먼저 존재해야 함 |
| 5 | schema_version 체계 혼동 가능성 | WARNING | Manifest: `1.0.0`, Metadata Schema: `2.2.0`, Registry Schema: 별도 — 문서로 명확히 구분 필요 |

---

## 8. Migration Recommendation

### 조건부 승인

**Manifest Schema v1.0: APPROVED WITH CONDITIONS**

조건:
1. Schema v2.2.0 적용 후 Manifest Pilot 생성 (BLOCKER #4 대응)
2. `schema_version` 체계 문서로 명확히 구분 (WARNING #5 대응)
3. `manifest_validator.py` 구현 (WARNING #3 대응)

### 다음 단계 로드맵

```
Manifest Schema Design          ✅ (이번 작업)
C1 Independent Review           ✅ (이번 작업)
Schema v2.2.0 적용 승인         NEXT (별도 승인 필요)
Manifest Pilot 생성              FUTURE (v2.2.0 적용 후)
TSU Eligibility 검증             FUTURE (Validator 구현 후)
Metadata Migration                FUTURE (Pilot 성공 후)
TSU Pipeline                      FUTURE (Migration 성공 후)
```

---

## 9. Final Verdict

### 판정: **APPROVED WITH CONDITIONS**

| 항목 | 판정 |
|---|---|
| Manifest Schema 승인 가능한가? | **예 (APPROVED)** — 17개 필드 적절, 누락/중복 없음 |
| 필수 필드 충분한가? | **예** — Identity/Authority/Processing/Quality/Audit 5범주 완전 |
| ADR-019 승인 가능한가? | **예 (APPROVED)** — 기존 ADR(001~018)과 충돌 없음 |
| Manifest Pilot 생성 준비되었는가? | **아니오** — Schema v2.2.0 적용 먼저 필요 (BLOCKER) |
| Schema v2.2.0 적용 가능한가? | **아니오** — 별도 승인 필요 |
| Metadata Migration 가능한가? | **아니오** — Manifest Entry 생성 + Validator 실행 먼저 필요 |
| TSU Pipeline 진입 가능한가? | **아니오** — `manifest_validator.py` 구현 먼저 필요 |

---

*이 보고서는 Read-Only Review입니다. YAML 생성, Manifest 생성, Registry 변경, Schema 변경, Validator 코드 수정, RAW 접근, Git Commit — 전부 수행하지 않음.*