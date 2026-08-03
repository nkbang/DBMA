# NAE Manifest Schema Design Report 001

**Project:** NAE-MANIFEST-SCHEMA-DESIGN-001
**Date:** 2026-08-02
**Nature:** Manifest Schema v1.0 설계 완료 — 실제 파일/데이터 생성 없음
**Git Commit:** 미수행 — 사용자 승인 대기

---

## 1. Executive Summary

ADR-019가 승인한 Corpus Manifest Layer를 실제 Schema 수준(Identity/
Authority Reference/Processing Lifecycle/Quality Gate/Audit 5개
범주, 총 17개 필드)으로 구체화했다. 기존 단일 `processing_status`
enum 설계(NAE-SCHEMA-V2.2-IMPLEMENTATION-DESIGN-001)를 **5개
세분화된 단계별 상태 필드로 정밀화**하고, 요약 `processing_status`는
그 파생값으로 재배치했다. C1 WARNING(Lifecycle 관계 미정리)은 이전
작업에서 이미 해소된 B안(별개 층위+대응표)을 유지하며 세분화된 필드에
맞춰 대응표만 갱신했다.

---

## 2. Manifest Entity Model

```
Authority Registry
        │
Source Manifest (이번 설계 대상)
        │
   ┌────┼────┬─────────┐
  RAW   OCR  TSU   Embedding
```

Registry=정적 서지 정체성, Manifest=RAW→OCR→TSU→Embedding 4단계
진행 상태 추적. Index Update(Retrieval 반영)는 Manifest 범위 밖
(ADR-001 소관, ADR-019 Consequences와 일관).

---

## 3. Required Field Table

| 범주 | 필드 | 타입/값 |
|---|---|---|
| Identity | `manifest_id` | string(=source_id) |
| | `source_id` | string(Registry FK) |
| | `schema_version` | string("1.0.0") |
| Authority Reference | `author_id`/`work_id` | string |
| | `edition_id`/`volume_id`/`issue_id` | string\|null(조건부, §Phase2 근거) |
| Processing Lifecycle | `acquisition_status` | pending\|acquired\|failed |
| | `ocr_status` | not_started\|in_progress\|complete\|failed |
| | `metadata_status` | not_started\|in_progress\|verified\|failed |
| | `tsu_status` | not_ready\|ready\|complete\|failed |
| | `embedding_status` | not_started\|in_progress\|complete\|failed |
| Quality Gate | `ocr_quality` | PASS\|WARNING\|FAIL\|null |
| | `metadata_verified` | boolean |
| | `authority_verified` | boolean |
| | `tsu_eligible` | boolean(파생) |
| Audit | `created_at`/`updated_at` | datetime |
| | `verified_by` | string\|null |

전체 17개 필드(파생 요약 `processing_status` 포함 시 18개, §Phase6).

---

## 4. Lifecycle Relationship

**B안 유지**(별개 층위, ADR-015=절차/Manifest=상태) — 대응표는
`NAE_CORPUS_MANIFEST_SCHEMA_DESIGN_v1.md` §Phase3. 이전 설계
(v2.2 Design-001)의 단일 상태 대응표를 5개 세분화 필드 기준으로
갱신한 것 외에 결정 자체의 변경은 없다.

---

## 5. Validator Boundary

**Option A 채택**(계층별 3개 도구: `source_validator.py` →
`authority_validator.py` → `manifest_validator.py`) — 이전 결정
유지, 번복 없음. `manifest_validator.py`의 책임에 `tsu_eligible`
재계산 검증과 5개 상태 필드의 forward-only 규칙 검사를 명시적으로
추가했다(§Phase5, 상세는 Design v1 §Phase5).

**Option B(통합 Validator) 기각**: 계층별 갱신 빈도·책임이 달라
통합 시 회귀 테스트 범위가 불필요하게 커짐(기존 근거 재확인).

---

## 6. schema_version 결정

**필드명: `schema_version`**(접두어 없음), **값: `"1.0.0"`**.
근거: Manifest Entry 문맥 안에서 자기 자신의 스키마를 가리키는 것이
자명하므로 `manifest_` 접두어가 중복 정보(§Phase4 상세).

---

## 7. ADR 영향 분석

**ADR-019 개정 불필요.** 이번 설계는 ADR-019가 정의한 원칙(별도
Entity, Source와 1:1, `manifest_id=source_id`)의 범위 안에서 필드를
구체화했을 뿐이다. 5개 세분화 상태 필드도 ADR-019의 "processing_status
로 진행 추적"이라는 결정을 위반하지 않는다 — 요약 `processing_status`
파생 필드로 여전히 그 개념을 유지하기 때문이다. 다른 ADR(001/014~018)
에도 영향 없음(이전 Review-001의 표 판정 유지).

---

## 8. Migration 준비 여부

**NOT READY.** 이번 작업은 Manifest Schema **설계**를 완료했을 뿐,
실제 스키마 파일도, Manifest 데이터도, Schema v2.2.0 적용도 아직
이뤄지지 않았다.

---

## 완료 조건 답변

1. **Manifest Schema 설계 완료 여부** — **완료**(17개 필드, 5범주).
2. **필수 필드 목록 확정 여부** — **확정**(§3 표).
3. **ADR-015 Lifecycle과 ADR-019 관계 해결 여부** — **해결**(B안 유지, 대응표 갱신, §4).
4. **Manifest Validator 분리 여부** — **분리**(Option A, 3계층 도구 체제, §5).
5. **schema_version 결정** — `schema_version: "1.0.0"`, 필드명 접두어 없음(§6).
6. **Schema v2.2.0 적용 가능 여부** — **아니오** — 이번 설계는 Manifest Schema(별도 v1.0.0 트랙)이며, corpus manifest v2.2.0 적용은 별도 승인 대상(NAE-SCHEMA-V2.2-IMPLEMENTATION-DESIGN-001 산출물이 이미 설계 완료, 적용만 남음).
7. **Metadata Migration 가능 여부** — **아니오, NOT READY**(§8).
8. **TSU Pipeline 진입 가능 여부** — **아니오** — `tsu_eligible` 계산 메커니즘이 여전히 설계 단계이며 `manifest_validator.py` 코드가 없어 실제 판정 수단이 없다.

---

## 로드맵 갱신

```
RAW Acquisition                  ✅
Architecture Design              ✅
Governance                       ✅
Authority Model                  ✅
ID Governance (ADR-017)          ✅
Periodical Extension (ADR-018)   ✅
Manifest Architecture (ADR-019)  ✅
C1 Final Review                  ✅ 조건부 승인
Manifest Schema Design            ✅ (이번 작업)

C1 Manifest Review                  NEXT
Schema v2.2.0 적용 승인               AFTER REVIEW
Manifest Pilot 생성                    FUTURE
TSU Eligibility 검증                    FUTURE
Metadata Migration                      FUTURE
TSU Pipeline                              FUTURE
```

---

*schema yaml 생성, manifest 파일 생성, Registry/Pilot 수정, RAW 접근,
`source_validator.py` 수정, TSU/Embedding 생성, Git Commit — 전부
수행하지 않음.*
