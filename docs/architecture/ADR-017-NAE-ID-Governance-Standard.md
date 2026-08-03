---
title: "ADR-017: NAE ID Governance Standard (Design Only)"
category: architecture
based_on:
  - docs/NAE_ID_GOVERNANCE_v1.md
  - docs/NAE_AUTHORITY_REGISTRY_DESIGN_v1.md
  - docs/NAE_AUTHORITY_REGISTRY_BUILD_REPORT_001.md
  - docs/architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md
created: 2026-08-02
scope_modified: docs/ only — Registry/RAW/코드 변경 없음, 실제 ID rename 없음
---

# ADR-017: NAE ID Governance Standard (Design Only)

| | |
|---|---|
| Status | Proposed |
| Date | 2026-08-02 |
| Deciders | 사용자 승인 대기 (설계 문서 단계) |
| Supersedes | — |
| Superseded by | — |

---

## 1. Context

Authority Registry Build-001 완료 후, 실제 Registry(`authority/*.yaml`)를
감사한 결과 Author/Work/Edition/Volume/Source ID가 Pilot-001(church_order,
`dagg_john_l` 등 소문자 snake_case)과 Pilot-002(Fuller,
`FULLER-ANDREW-001` 등 대문자-하이픈)에서 서로 다른 표기 관례를 따르고
있음이 확인됐다(Build Report §Phase4 Remaining Risk #1). 800개 이상
규모로 확대하기 전에 이 불일치를 정책 수준에서 해소해야 한다.

## 2. Problem

Author/Work/Edition/Volume/Source 5개 Entity의 ID를 어떤 규칙으로
생성하고, 이름 충돌은 어떻게 처리하며, 기존 두 Pilot의 ID는 어떻게
다뤄야 하는가?

## 3. Decision

### 3.1 Canonical ID Rule

```
author_id  = "{surname}_{given_name}[_{middle_initial}]"
work_id    = "{author_id}_{title_slug}"
edition_id = "{work_id}_{publication_year}[_{place_slug}]"
volume_id  = "{edition_id}_v{NN}"
source_id  = "{volume_id 또는 edition_id}_{scan_suffix}"
```

전부 lowercase, snake_case, ASCII, deterministic. 상세 규칙과 근거는
`NAE_ID_GOVERNANCE_v1.md` §2.

**Author ID 표기 순서**: surname 우선(given-name 우선 아님) — 기존
실 데이터 3건 중 2건이 이미 이 순서를 따르고 있고,
`NAE_CORPUS_INGESTION_STANDARD_v1.md`의 기존 문서화된 규칙과도 일치해
마이그레이션 대상을 최소화한다(상세 근거: GOVERNANCE 문서 §2.1).

### 3.2 Collision Policy

- 동명이인 Author: 출생연도를 1차 구분자로, 그래도 겹치면 숫자 suffix.
- 동일 제목 Work: 사람이 먼저 진짜 다른 저작인지 확인 후, RAW 근거
  기반 구분자(연도/부제 등) 사용 — 임의 순번 지양.
- 동일 Edition(같은 publisher+year+title): 기본은 Duplicate(Source
  scan_suffix만 증가), 실물 대조로 인쇄판 차이가 확인될 때만 신규
  Edition. 모든 판단은 사람이 최종 확인(자동 병합 금지 원칙 재확인).

### 3.3 기존 Pilot ID 처리

`dagg_john_l`/`hiscox_edward_t`는 이미 canonical과 일치해 **유지**.
나머지(Work/Edition/Volume/Source 전체, Fuller의 author_id 포함)는
**변경 필요**로 판정하되, 이번 작업에서 실제로 변경하지 않는다 — 변환
매핑표만 작성(`NAE_ID_GOVERNANCE_v1.md` §6.2). 실제 rename 시
`legacy_id` 필드로 구 ID를 보존한다.

### 3.4 신규 ADR 채택 (ADR-016 개정 아님)

ADR-016은 Entity 모델(계층 구조) 결정이고 이번은 ID 표기 규칙(문자열
포맷) 결정으로 층위가 다르며, "ADR은 소급 수정하지 않는다"는 기존
관례(GOVERNANCE §7.5)를 일관되게 적용하기 위해 신규 ADR로 남긴다.

## 4. Alternatives

| 대안 | 기각 사유 |
|---|---|
| Given-name 우선 author_id(이번 명령서 예시와 동일) | 기존 실 데이터 3건 중 2건과 문서화된 규칙 모두 surname 우선 — given-name 우선을 택하면 오히려 마이그레이션 대상이 늘어남 |
| 즉시 전체 Registry rename | 명령서 금지 사항(전체 Registry 변경 금지) 위반, 참조 무결성 검증 없이 일괄 변경 시 FK 깨짐 위험 |
| ADR-016 개정 | Entity 모델과 ID 표기 규칙은 별개 결정 층위 — 기존 "ADR 소급 수정 금지" 관례와 불일치 |
| 동명이인 처리에 등록 순번(숫자) 사용 | Deterministic하지 않음(등록 순서에 의존) — 새 동명이인이 중간에 추가되면 기존 번호 체계가 흔들릴 수 있음 |

## 5. Consequences

- Registry(`authority/*.yaml`)는 이 ADR로 변경되지 않는다 — 정책만 확정.
- 다음 Pilot(Baptist Missionary Magazine 등)부터는 처음부터 이 규칙으로
  ID를 생성해야 한다.
- 실제 rename(Migration)은 별도 승인 작업이며, 그 작업은 `legacy_id`
  보존 + 원자적 FK 갱신 + Reference Integrity 재검증을 필수 절차로
  요구한다(`NAE_ID_GOVERNANCE_v1.md` §6.1).
- 정기간행물(volume+issue)의 ID 확장 규칙은 이번 ADR 범위 밖 —
  Baptist Missionary Magazine Pilot에서 확정 필요.
- ADR 번호 충돌 확인: 작성 시점 기준 001–016 존재, 017은 미사용 번호로
  충돌 없음.

## 6. Future Expansion

- 정기간행물 ID 확장 규칙(`_i{NN}` issue 접미 등) — 3차 Pilot에서 결정
- 실제 ID Migration 실행(legacy_id 필드 추가 + 원자적 rename) — 별도 승인
- `scripts/authority_validator.py`(설계만 존재, Registry Design v1 §Phase5)에
  이번 ID 규칙 검증 항목(포맷 정규식 검사 등) 추가 검토
- Author 통합(Fuller의 `FULLER-ANDREW-001`과 기존 `AF1815` entry) —
  ID rename과 별개로 별도 결정 필요(Build Report Remaining Risk #3 재확인)

## Validation

설계 문서이므로 코드/데이터 검증 대상 없음. 문서 정합성만 확인:

```
grep -r "ADR-017" docs/
```
