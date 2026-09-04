# NAE Periodical Architecture Review 002 (C1 Final Architecture Review)

**Project:** NAE-PERIODICAL-ARCHITECTURE-REVIEW-002
**Reviewer:** C1 (Independent Verification)
**Date:** 2026-08-02
**Nature:** Final Architecture Review — **실행 아님, 검토만**
**검토 대상 문서:**
- [`NAE_PERIODICAL_ARCHITECTURE_REVISION_001.md`](NAE_PERIODICAL_ARCHITECTURE_REVISION_001.md) (Revision)
- [`ADR-018-NAE-Periodical-Authority-Extension.md`](architecture/ADR-018-NAE-Periodical-Authority-Extension.md) (ADR)
- [`NAE_PERIODICAL_AUTHORITY_REVIEW_001.md`](NAE_PERIODICAL_AUTHORITY_REVIEW_001.md) (Review-001)
- [`NAE_METADATA_GOVERNANCE_v1.md`](NAE_METADATA_GOVERNANCE_v1.md) (Governance)
- [`NAE_ID_GOVERNANCE_v1.md`](NAE_ID_GOVERNANCE_v1.md) (ID Governance)

---

## 1. Executive Summary

CUE가 작성한 Periodical Architecture Revision(안 1 채택, `author_type` 필드 추가, `title_history[]` 구조화, ADR-018 신규 채택)을 독립 검증했다. Review-001(APPROVED WITH CONDITIONS)에서 미해결로 남긴 Organization Authority와 Title History 처리가 Revision에서 구체적으로 해결되었으며, 기존 Architecture와 충돌 없음.

**판정: APPROVED WITH CONDITIONS** (조건부 승인 — Migration 전제조건 충족 시 APPROVED로 격상)

---

## 2. Architecture Compatibility

### 2.1 RAW 원칙 (NAE_DATA_ARCHITECTURE.md)

**검증 결과: 호환**

- Revision §3에서 Edition 계층 생략 결정은 Pilot Design v1 §2 Option A와 동일 — C1이 Review-001 §4.1에서 "적절"로 승인한 모델 재확인.
- RAW 파일 이동/수정 없음 — Revision은 정책 정의만, 실제 데이터 변경 없음.

### 2.2 Retrieval Authority (ADR-001)

**검증 결과: 권한 침해 없음**

- Revision §TSU Metadata 확정에서 `work_type` 기반 필수 필드 예외 규칙은 TSU 생성 시점의 영향일 뿐, Retrieval Engine(`core/retrieval.py`)에 직접 영향을 주지 않음.
- `author_type` 필드 추가도 기존 Source weighting 로직(`source_type`/`copyright_status` 기준)과 충돌 없음.

### 2.3 Metadata Schema 호환성 (schema_version 2.1.0 → 2.2.0)

**검증 결과: Minor 변경 적절**

- Revision §7에서 제안한 신규 필드(`author_type`, `title_history[]`, `continues_work_id`, `continued_by_work_id`, `editor_id`)는 전부 optional 추가.
- 기존 데이터 무효화 없음 — Minor bump(`2.1.0 → 2.2.0`)로 적절.
- Governance §2.2에서 정의한 Semantic Versioning 원칙과 일치.

---

## 3. ADR-018 Review

### 3.1 Entity Model (안 1 채택)

**검토 결과: 적절**

```
Author/Organization(author_type로 구분)
  └── Work(work_type: periodical)
        └── Volume
              └── Issue (신규, periodical 전용 조건부 Entity)
                    └── Source
```

- Edition 계층 생략 — 정기간행물에서 Edition이 의미less(발행 조직이 판본을 구분하지 않음).
- Article Registry Entity 기각 — RAW가 article 단위 파일 제공 안 함.
- C1 Review-001 §4.1에서 "적절"로 승인한 Option A와 동일.

### 3.2 Organization Authority (`author_type` 필드)

**검토 결과: 적절**

- 별도 `CorporateAuthor` Entity 기각 — `author_id` FK 대상이 두 테이블로 갈라지는 문제(중복 인프라) 회피.
- `birth_year`/`death_year`는 organization일 때 항상 `null` — 설립/해산 연도로 재해석하지 않음(`notes` 자유 텍스트).
- Governance §5.1 Author Entity에 `author_type: person | organization` 추가 — 기존 필드 유지, 신규 필드 optional 추가.

### 3.3 Title History (`title_history[]` + 경량 계승 관계)

**검토 결과: 적절**

```yaml
title_history: [{title, start_date, end_date}, ...]
continues_work_id: string|null
continued_by_work_id: string|null
```

- Pilot의 `aliases`(평면 배열) 대비 시간순 정보 보존 — 개선.
- 별도 Series Entity 기각 — 두 Work 사이 단순 관계일 뿐 완전한 Entity로 만들 실익 없음.
- 서지 검증 전까지 `continues_work_id` 비워두기 — 자동 병합 금지 원칙(Governance §1 Philosophy #3)과 일관.

### 3.4 TSU 필수 필드 예외

**검토 결과: 적절**

- `work_type=periodical`: `edition_id` 면제, `volume_id`+`issue_id` 필수 대체.
- Governance §6의 조건부 예외로 문서화 — 기존 TSU 레코드 무효화 없음.

### 3.5 Schema Version (2.1.0 → 2.2.0)

**검토 결과: Minor 변경 적절**

- 전부 optional 필드 추가, 기존 데이터 무효화 없음.
- Governance §2.2 Minor bump 기준(필드 추가)과 일치.

### 3.6 ADR-018 판정: **APPROVED**

---

## 4. Entity Model Review

### Q1. Work subtype 모델 — `work_type: periodical`

**판정: PASS**

- 기존 `work_type` enum(`monograph`, `multi_volume`)에 `periodical` 추가 — Minor 확장.
- 별도 Periodical Entity가 더 필요한가? → **아님**. Revision §3에서 안 2(Periodical 전용 최상위 구조)를 기각한 논리가 적절:
  - Author→Work 인프라 중복 구축 필요 없음.
  - Series 관계는 경량 필드(`continues_work_id`)로 충분히 표현 가능.
  - Pilot Design v1이 이미 "Option B 기각" 근거로 제시한 것과 동일(중복 인프라, CLAUDE.md 과설계 금지 원칙).

### Q2. Organization Authority 모델

**판정: PASS (조건부)**

장점:
- 기존 FK(`author_id`) 유지 — 참조 무결성 단순화.
- `author_type` 필드로 Person/Organization 구분 — 명확.

위험:
- Author 의미 확장 — `birth_year`/`death_year`가 조직에는 무의미.
  - **완화책**: organization일 때 항상 `null` 고정, 설립/해산 연도는 `notes` 자유 텍스트로 기록.
- Person/Organization 혼합 가능성 — 등록 시 사람이 구분.

### Q3. `editor_id` 추가 필요성

**판정: PASS**

- Editor/Translator/Compiler/Publisher 구분 필요 — 정기간행물 특성상 발행 조직(`author_id`)과 편집자(`editor_id`)가 다른 경우가 많음.
- 선택 필드로 추가 — 기존 monograph 데이터 영향 없음.
- `author_type=person`인 Author FK로 연결 — ID 체계 이원화 없음.

### Q4. Title History 모델

**판정: PASS**

- `title_history[]`는 시간순 구조화 — Pilot의 평면 배열(`aliases`) 대비 개선.
- `continues_work_id`/`continued_by_work_id`는 경량 관계 필드 — 완전한 Entity 불필요.
- **장기적 Series Entity 필요성**: 현재는 두 Work 사이 단순 관계로 충분하나, 정기간행물 컬렉션이 확장되면 Series Entity 고려 가능 — 이번 Revision 범위 밖.

### Q5. Issue Entity

**판정: PASS (조건부)**

- Periodical 전용 조건부 Entity — monograph에는 항상 빈 채로 남는 계층이 되지 않음(조건부 적용).
- Volume이 "다권본에서만 사용"인 것と同원칙.
- **Schema v2.2.0 필요성**: `issue_id` 필드 추가 필요 — Minor bump 범위 내.

---

## 5. Schema Impact

### 5.1 기존 Schema 변경 없이 가능한가?

**답: 부분적으로 가능**

| 필드 | 영향 | 판정 |
|---|---|---|
| `author_type` | Author 스키마 optional 추가 | Minor |
| `title_history[]` | Work 스키마 optional 추가 | Minor |
| `continues_work_id`/`continued_by_work_id` | Work 스키마 optional 추가 | Minor |
| `editor_id` | Work 스키마 optional 추가 | Minor |
| `issue_id` | Issue Entity 신규(조건부) | Minor |
| `work_type: periodical` | 기존 enum 확장 | Minor |

### 5.2 Migration 필요한가?

**답: NOT READY (Revision §9 4개 전제조건 미충족)**

1. TSU 필요 필드 모두 갖춘 자료 확인 전까지 TSU 생성 금지.
2. `author_type` 필드가 실제 스키마 파일에 반영되기 전까지 Organization Author 데이터 추가 금지.
3. 제호 계승 관계 서지 검증 — 미완료 상태로는 두 Work를 병합하거나 분리 상태를 최종 확정하지 않음.
4. 동일 volume 내 복수 issue 시나리오 미검증.

### 5.3 Versioning 방식 적절한가?

**답: 적절**

- Semantic Versioning 채택(Governance §2.2).
- 전부 optional 필드 추가 → Minor bump(`2.1.0 → 2.2.0`).
- 기존 데이터 무효화 없음.

---

## 6. Risk Assessment

| # | 리스크 | 평가 | 설명 |
|---|---|---|---|
| 1 | 제호 계승 관계 서지 미검증 | WARNING | `continues_work_id` 필드만 마련, 실제 연결은 보류 — 서지 전문가 확인 필요 |
| 2 | 동일 volume 내 복수 issue 미검증 | WARNING | 3차 Pilot 확대 대상 |
| 3 | `author_type` 필드 미구현(설계만) | WARNING | 실제 스키마 파일/코드 미반영 |
| 4 | `title_history[]`가 기존 Pilot YAML(`aliases`)과 형식 불일치 | LOW | Pilot 데이터를 소급 갱신하지 않기로 결정 — Production 반영 시에만 신규 형식 적용 |
| 5 | TSU 필드 예외 규칙(work_type 분기) 미구현 | WARNING | 정책만, Validator/TSU 빌더 코드 없음 |
| 6 | Editor/Organization 구분(author_id vs editor_id)이 아직 Pilot 데이터에 반영 안 됨 | LOW | Baptist Missionary Magazine Pilot 데이터는 organization만 `author_id`로 기록, editor 미등록 |
| 7 | Migration 준비도 부족 | **BLOCKER** | Revision §9 4개 전제조건 미충족 |

---

## 7. Migration Readiness

**판정: READY WITH CONDITIONS**

### 조건부 승인 조건

| # | 조건 | 우선순위 |
|---|---|---|
| 1 | TSU 필요 필드(periodical: `volume_id`+`issue_id`, monograph: `edition_id`) 모두 갖춘 자료 확인 | BLOCKER |
| 2 | `author_type` 필드가 실제 스키마 파일(`modern/source_manifest.schema.yaml`)에 반영 | 중간 |
| 3 | 제호 계승 관계(1803/1817) 서지 검증 | 중간 |
| 4 | 동일 volume 내 복수 issue 시나리오 검증 | 중간 |

### 조건 충족 시 APPROVED로 격상

- TSU 생성: 해당 자료가 필요 필드를 모두 갖춘 이후에만 허용.
- Schema v2.2.0 실제 적용: 별도 승인 대상.
- Periodical Registry Expansion Pilot: 3차 Pilot 확대 대상.
- 전체 Corpus Metadata Migration: 별도 Pilot과 검증 필요.

---

## 8. Final Recommendation

### ADR-018 판정: **APPROVED**

### 7개 최종 질문 답변

| # | 질문 | 답변 |
|---|---|---|
| 1 | ADR-018 승인 가능한가? | **APPROVED** — Entity Model, Organization Authority, Title History, TSU 예외 규칙 모두 적절 |
| 2 | Work subtype 선택이 적절한가? | **적절** — 별도 Periodical Entity 불필요, 경량 필드로 Series 관계 표현 가능 |
| 3 | Organization Authority 모델이 안전한가? | **안전** — `author_type` 필드로 Person/Organization 구분, FK 이원화 없음 |
| 4 | `editor_id` 추가가 필요한가? | **필요** — 정기간행물 특성상 발행 조직과 편집자 구분 필요 |
| 5 | `title_history` 모델이 충분한가? | **충분** — 시간순 구조화 + 경량 계승 관계로 기존 Pilot 대비 개선 |
| 6 | Schema v2.2.0 승격이 타당한가? | **타당** — 전부 optional 필드 추가, Minor bump 기준 충족 |
| 7 | Migration 착수 가능한가? | **NOT READY** — Revision §9 4개 전제조건 미충족 (BLOCKER) |

---

## 9. 로드맵

```
Architecture Revision          ✅
Schema v2.1.0                  ✅
Validator                      ✅
Authority Registry              ✅
ID Governance ADR-017           ✅
Periodical Pilot                 ✅
C1 Periodical Review             ✅
Periodical Architecture Revision  ✅
C1 Final Architecture Review     ✅ (이번 작업)

Schema v2.2.0 반영(실제 파일)         NEXT (별도 승인)
Periodical Registry Expansion Pilot   FUTURE (조건부)
Corpus Metadata Migration              FUTURE (BLOCKER 해제 후)
```

---

*이 보고서는 설계/Pilot 문서 검토만 수행했으며, 파일 수정, 코드 변경, TSU 생성, Embedding 생성, Git Commit, Git Push — 전부 수행하지 않음.*