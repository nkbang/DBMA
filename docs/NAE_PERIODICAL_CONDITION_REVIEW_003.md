# NAE Periodical Condition Review 003

**Project:** NAE-PERIODICAL-CONDITION-REVIEW-003
**Date:** 2026-08-02
**Nature:** CUE NAE-PERIODICAL-CONDITION-RESOLUTION-001 결과 독립 검증
**Scope:** Read-Only Architecture Review — 수정/생성 금지

---

## 1. Executive Summary

C1의 `NAE-PERIODICAL-CONDITION-RESOLUTION-001`(조건 4건 해소 시도) 결과를
독립적으로 검증했다. 핵심 발견: **C1이 TSU Field Readiness 조사 과정에서
발견한 "Production Corpus Manifest Layer 부재" 문제는 C1 본인이 예상한
("필드가 자료에 존재하는가") 것보다 더 근본적인 Architecture Gap이다** —
TSU가 읽을 manifest 계층 자체가 Monograph/Periodical 모두 Production 레벨에
전무하며, Periodical은 Pilot 레벨에서도 manifest를 만든 적이 없다.

이 보고서는 C1의 분석을 재확인하고, 각 조건/위험 항목을 독립적으로 평가한
결과를 제시한다.

---

## 2. Reviewed Documents

| # | 문서 | 성격 |
|---|---|---|
| 1 | `docs/NAE_PERIODICAL_CONDITION_RESOLUTION_REPORT_001.md` | C1 조건 해소 시도 결과 (Review-002 조건 4건) |
| 2 | `docs/NAE_PERIODICAL_TSU_FIELD_READINESS_REPORT_001.md` | TSU Field Readiness 실측 조사 |
| 3 | `docs/NAE_PERIODICAL_TITLE_HISTORY_VALIDATION_001.md` | Title History RAW 1차 사료 검증 |
| 4 | `docs/NAE_PERIODICAL_ISSUE_MODEL_TEST_001.md` | Issue Model 가상 ID 시뮬레이션 |
| 5 | `docs/NAE_PERIODICAL_ARCHITECTURE_REVISION_001.md` | Periodical Architecture Revision |
| 6 | `docs/NAE_METADATA_GOVERNANCE_v1.md` | Metadata Governance 정본 |
| 7 | `docs/architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md` | Metadata Authority Model Revision (Design) |
| 8 | `docs/architecture/ADR-017-NAE-ID-Governance-Standard.md` | ID Governance Standard (Design) |
| 9 | `docs/architecture/ADR-018-NAE-Periodical-Authority-Extension.md` | Periodical Authority Extension (Design) |

---

## 3. Existing Architecture Compatibility

### 3.1 ADR-016 ~ ADR-018 설계 문서군 평가

**ADR-016 (Metadata Authority Model Revision):**
- Status: Proposed (사용자 승인 대기)
- Schema Version: 2.0.0 → 2.1.0 (Minor)
- Pilot-001/002 실증 결과를 반영하여 `source_type`에 `public_archive` 추가,
  Work:Edition=1:N 관계 명문화, Volume Entity 신설 등 8개 개선 사항 결정
- **검증 결과:** 설계 문서로서 일관성 있음. 기존 ADR 소급 수정 금지 원칙
  준수. Pilot 데이터 기반 결정 근거 충분.

**ADR-017 (ID Governance Standard):**
- Status: Proposed (사용자 승인 대기)
- Canonical ID Rule: lowercase snake_case, deterministic
- 동명이인 처리: 출생연도 1차 구분자
- 기존 Pilot ID 처리: `dagg_john_l`/`hiscox_edward_t`는 canonical 일치 → 유지
- **검증 결과:** ID 규칙이 monograph/periodical 모두에 적용 가능한 일반적
  규칙임. Periodical 전용 확장(`_i{NN}`)은 ADR-018에서 처리하므로 분리
  설계 적절.

**ADR-018 (Periodical Authority Extension):**
- Status: Proposed (사용자 승인 대기)
- Entity Model: Option A 채택 (Author/Organization → Work → Volume → Issue → Source)
- Edition 생략: 정기간행물에서 Volume이 Edition 역할 대체
- Organization Authority: `author_type` 필드로 기존 Author entity 확장
- Title History: `title_history[]` + 경량 계승 관계 (`continues_work_id`)
- TSU 필수 필드 예외: `edition_id` 면제, `volume_id`+`issue_id` 필수 대체
- Schema Version: 2.1.0 → 2.2.0 (Minor)
- **검증 결과:** Periodical 고유 문제(조직 발행, 제호 변경, volume 리셋)를
  정확히 포착. Edition 생략 결정 적절(정기간행물에 Edition 개념 부합).

### 3.2 기존 Architecture와의 충돌 분석

| 기존 요소 | ADR-016/017/018과 충돌 여부 | 근거 |
|---|---|---|
| ADR-014 (NAE Modern Corpus Layer) | **충돌 없음** | ADR-016 §3.2에서 "기존 ADR 직접 개정 아님" 원칙 준수. Periodical은 `public_archive`로 분류되어 ADR-014의 domain separation과 호환 |
| ADR-015 (NAE Corpus Ingestion Standard) | **충돌 없음** | Ingestion Pipeline에 신규 Entity 추가만 — 기존 monograph ingestion 경로 영향 없음 |
| ADR-001 (Retrieval Engine Authority) | **충돌 없음** | Retrieval Engine은 TSU/Embedding을 소비 — manifest layer 부재는 Retrieval이 아닌 ingestion 전단계 문제 |
| ADR-013 (NAE Vector Store) | **충돌 없음** | Vector Store 스키마는 TSU embedding을 저장 — TSU 생성 전 단계이므로 직접 영향 없음 |
| Authority Registry (`authority/*.yaml`) | **충돌 없음** | Registry는 설계 단계에서 실제 생성/수정하지 않음 (scope_modified: docs/ only) |

---

## 4. ADR-014 Review (NAE Modern Corpus Layer)

### 4.1 Domain Separation 평가

ADR-014가 제안하는 분리:
```
NAE-PD (public_domain)
NAE-MODERN
DBMA
```

**검증:** Periodical 자료(Baptist Missionary Magazine 등)는 `public_archive`
(source_type)로 분류되므로 ADR-014의 domain separation과 충돌하지 않음.
Periodical Pilot은 `resources/theological_sources/authority/pilot_periodical/`에
Registry만 존재 — corpus manifest는 아직 생성되지 않음.

### 4.2 Storage Architecture 평가

제안 구조:
```
NAE/corpus/raw/
  public_domain/
  modern/
```

**실제 Repository 구조와 비교:**
- `NAE/corpus/raw/` 존재 (archive.org 등 RAW 소스 수집 위치)
- `resources/theological_sources/modern/` — 스키마 파일(`source_manifest.schema.yaml`)만 존재, 실제 manifest 없음
- **Gap:** ADR-014의 storage 제안은 적절하나, 실제 manifest 데이터가 Production/Pilot 모두에서 생성되지 않은 상태

**판정: WARNING** — 설계는 적절하나 실행 단계에서 manifest 계층이 누락됨

---

## 5. ADR-015 Review (NAE Corpus Ingestion Standard)

### 5.1 Lifecycle 평가

제안 Pipeline:
```
Registration → Validation → Classification → Metadata → Quality Gate → TSU → Embedding → Index
```

**현재 Pipeline과의 충돌 분석:**
- 기존 TSU Pipeline (`core/tsu_builder.py` 등)은 `source_manifest.yaml`을
  입력으로 가정 — manifest가 없으면 TSU 생성 불가
- ADR-015의 Lifecycle은 논리적으로 타당하나, **입력 데이터(manifest) 부재**로
  실제 실행 불가

**판정: WARNING** — 설계 적절, 그러나 입력 데이터 부재로 실행 불가 상태

### 5.2 Authority Model 평가

제안 구조:
```
author_id → work_id → source_id
```

**적절성:**
- Monograph: `author_id` → `work_id` → `edition_id` → `volume_id` → `source_id` (5단계)
- Periodical: `author_id`(organization 가능) → `work_id` → `volume_id` → `issue_id` → `source_id` (5단계)
- 동일 저자(다수 작품): `work_id`에서 `title_slug`로 분리 → 적절
- 동명이인: ADR-017 §3.2 출생연도 구분 → 적절
- Edition 관리: ADR-016 §3.1 Work:Edition=1:N 명문화 → 적절

**판정: PASS** — Authority Model 구조 적절

### 5.3 Duplicate Policy 평가

"삭제 금지 원칙"이 기존 정책과 일치:
- ADR-017 §3.2: "모든 판단은 사람이 최종 확인(자동 병합 금지 원칙 재확인)"
- DBMA Core Rules: "샘플 데이터 생성 금지"와 동일한 "실제 데이터 존중" 철학

**판정: PASS** — 기존 정책과 일치

---

## 6. Metadata Compatibility

### 6.1 Schema v2.2.0 평가

추가 예정 필드:
| 필드 | 유형 | 기존 데이터 영향 | 판정 |
|---|---|---|---|
| `author_type` | enum(person|organization) | optional, 기존 자료는 영향 없음 | PASS |
| `editor_id` | string (Author FK) | optional | PASS |
| `issue_id` | string (periodical 전용) | optional, periodical만 사용 | PASS |
| `title_history[]` | array | optional | PASS |
| `continues_work_id` | string|null | optional | PASS |
| `continued_by_work_id` | string|null | optional | PASS |

**Minor Version (2.1.0 → 2.2.0) 적절성:**
- GOVERNANCE §2.2 Minor 기준: "optional 추가, 기존 데이터 무효화 없음"
- 6개 필드 전부 optional + 기존 값 무효화 없음 → Minor 기준 충족

**판정: PASS** — Schema v2.2.0 적용 적절

### 6.2 Migration 필요성 평가

| 질문 | 답변 | 근거 |
|---|---|---|
| 기존 Schema 변경 없이 가능한가? | **아니오** — v2.2.0 적용 필요 | 신규 필드 추가는 스키마 파일 수정 요구 |
| Migration 필요한가? | **예** — Pilot manifest 생성 + Schema 적용 필요 | Production manifest 전무, Periodical Pilot manifest 누락 |
| Versioning 방식 적절한가? | **예** — Minor (2.1.0 → 2.2.0) | GOVERNANCE §2.2 Minor 기준 충족 |

---

## 7. TSU Compatibility

### 7.1 현재 TSU 구조와의 충돌 분석

**현재 TSU Pipeline 가정:**
- 입력: `source_manifest.yaml` (corpus manifest)
- Monograph 필수 필드: `edition_id`, `source_id`, `work_id`, `author_id`
- Periodical 필수 필드: `work_id`, `volume_id`, `issue_id`, `source_id`

**실제 상태:**
| 계층 | Monograph | Periodical |
|---|---|---|
| Registry 필드 완비 | PASS | WARNING (유도 경로 깊음) |
| Production corpus manifest | **FAIL** | **FAIL** |
| Pilot corpus manifest (TSU 필드 포함) | PASS (10건) | **FAIL (전무)** |

**판정: BLOCKER** — TSU 생성을 위한 manifest 계층이 Periodical에 전무

### 7.2 Periodical Entity Model 최소성 평가

제안 모델:
```
Monograph: Work → Edition → Source
Periodical: Work → Volume → Issue → Source
```

**적절성:**
- Monograph에서 Edition은 동일 작품의 다른 출판본을 구분 — 필수
- Periodical에서 Volume은 호수, Issue는 호 — 정기간행물 고유 구조
- **Edition이 Periodical에 필요한가?** — 아니요. Periodical은 "호수"로
  표현되며 Edition 개념과 매칭되지 않음. ADR-018 §3.1의 Edition 생략 결정
  적절.

**판정: PASS** — 최소 Entity 모델 적절

---

## 8. Retrieval Compatibility

### 8.1 RetrievalEngine과의 호환성 평가

**현재 RetrievalEngine 가정:**
- Source weighting: `source_type` 기반
- Domain filter: `public_domain` / `modern`
- Authority ranking: `author_id` → `work_id` 체인

**ADR-016/017/018과의 충돌:**
- `source_type`에 `public_archive` 추가 — RetrievalEngine이 이 값을
  어떻게 처리하는지 실제 코드 확인 필요 (현재는 설계 단계)
- Periodical의 `author_type: organization` — Retrieval ranking에 영향
  있을 수 있으나, TSU 생성 전 단계이므로 Retrieval 직접 영향 없음
- **핵심:** Retrieval은 TSU/Embedding을 소비 — manifest layer 부재는
  Retrieval이 아닌 ingestion 전단계 문제

**판정: PASS** — Retrieval Architecture 보호됨 (직접 영향 없음)

---

## 9. Identified Risks

| # | 항목 | 평가 | 근거 |
|---|---|---|---|
| R1 | Architecture: Manifest Layer 부재 | **BLOCKER** | Production/Pilot 모두 manifest 전무, TSU 생성 불가 |
| R2 | Metadata: Schema v2.2.0 적용 | **WARNING** | 설계 적절하나 실제 적용(파일 수정) 별도 승인 필요 |
| R3 | TSU: Periodical Pilot manifest 누락 | **BLOCKER** | Pilot-001/002 대비 진행도 한 단계 낮음 |
| R4 | Retrieval: 직접 영향 없음 | **PASS** | TSU 생성 전 단계 문제 |
| R5 | Copyright: `source_type` 처리 | **WARNING** | `public_archive` 값의 RetrievalEngine 처리 미확인 |
| R6 | Future Expansion: 3차 Pilot 필요 | **WARNING** | 동일 volume 복수 issue 실자료 검증 아직 없음 |

---

## 10. Recommendations

### 10.1 우선순위 기반 권고

| 우선순위 | 조치 | 책임 |
|---|---|---|
| P0 (BLOCKER) | Periodical Pilot에 corpus manifest 계층(`source_manifest.yaml` 동등물) 신규 작성 | CUE |
| P0 (BLOCKER) | Monograph Production manifest 승격 (Pilot → Production) | CUE |
| P1 (WARNING) | Schema v2.2.0을 `modern/source_manifest.schema.yaml`에 적용 | CUE (별도 승인) |
| P1 (WARNING) | `public_archive` 값의 RetrievalEngine 처리 확인 | CUE |
| P2 (FUTURE) | 3차 Pilot: 동일 volume 복수 issue 실자료 확보 | CUE |
| P2 (FUTURE) | 1803~1817 공백기 자료 추가 확보 또는 "미확인"으로 종결 | CUE |

### 10.2 승인 조건

ADR-016/017/018 승인을 위한 조건:
1. Periodical Pilot manifest 생성 계획 명시
2. Schema v2.2.0 적용 일정 명시
3. Monograph Production manifest 승격 기준 명시

---

## 11. Final Verdict

### 11.1 판정 결과

```
ADR-016 (Metadata Authority Model Revision):
  Status: APPROVED WITH CONDITIONS
  Conditions:
    - Periodical Pilot manifest 생성 계획 필요
    - Schema v2.2.0 적용 일정 필요

ADR-017 (ID Governance Standard):
  Status: APPROVED
  Reason: ID 규칙 적절, 기존 데이터와 호환, 마이그레이션 계획 포함

ADR-018 (Periodical Authority Extension):
  Status: APPROVED WITH CONDITIONS
  Conditions:
    - Periodical Pilot manifest 생성 전까지 실행 불가
    - TSU 필수 필드 예외 로직 구현 필요
```

### 11.2 최종 질문 답변

| 질문 | 답변 | 근거 |
|---|---|---|
| 1. CUE 설계가 현재 NAE 구조와 충돌하는가? | **아니오** (WARNING: manifest layer 부재) | ADR-016/017/018 설계는 기존 Architecture와 충돌하지 않으나, 실행을 위한 manifest 데이터가 없음 |
| 2. ADR-014는 승인 가능한가? | **APPROVED WITH CONDITIONS** | Domain separation 적절, 그러나 manifest 계층 부재로 실행 불가 |
| 3. ADR-015는 승인 가능한가? | **APPROVED WITH CONDITIONS** | Ingestion Lifecycle 적절, 그러나 입력(manifest) 부재 |
| 4. Metadata Layer 구축 전에 수정해야 할 문제가 있는가? | **예 — Periodical Pilot manifest 생성 필요** | TSU 생성을 위한 직접 입력이 전무 |
| 5. TSU Pipeline으로 넘어가도 되는가? | **아니오 (BLOCKER)** | Periodical Pilot manifest 전무 → TSU 생성 불가 |
| 6. Retrieval Architecture를 보호하고 있는가? | **예** | Retrieval은 TSU/Embedding 소비 — manifest layer 부재는 ingestion 전단계 문제 |

---

## 12. Final Status Summary

```
Architecture:     PASS WITH CONDITIONS (manifest layer 부재 WARNING)
Metadata Migration: NOT READY (Pilot manifest 생성 필요)
Next Recommended Action:
  1. Periodical Pilot에 corpus manifest 계층 신규 작성 (BLOCKER 해소)
  2. Schema v2.2.0 적용 (별도 승인)
  3. Monograph Production manifest 승격 기준 확정
  4. TSU Pipeline 재평가 (manifest 생성 후)
```

---

*본 보고서는 읽기 전용 검증 결과입니다. 파일 수정, 데이터 생성, Git Commit 등
모든 쓰기 작업은 수행하지 않았습니다.*