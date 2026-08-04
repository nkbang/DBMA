---
title: "ADR-019: NAE Corpus Manifest Layer (Design Only)"
category: architecture
based_on:
  - docs/NAE_CORPUS_MANIFEST_ARCHITECTURE_v1.md
  - docs/NAE_CORPUS_MANIFEST_MIGRATION_PLAN_001.md
  - docs/NAE_PERIODICAL_CONDITION_RESOLUTION_REPORT_001.md
  - docs/architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md
  - docs/architecture/ADR-018-NAE-Periodical-Authority-Extension.md
created: 2026-08-02
scope_modified: docs/ only — Manifest 실제 생성, Schema/Validator/Registry 변경 없음
---

# ADR-019: NAE Corpus Manifest Layer (Design Only)

| | |
|---|---|
| Status | Approved |
| Date | 2026-08-02 |
| Approved | 2026-08-03 (NAE-ADR-PROMOTION-001) |
| Deciders | 사용자 승인 완료 (2026-08-03) |
| Supersedes | — |
| Superseded by | — |

---

## 1. Context

Periodical Condition Resolution(NAE-PERIODICAL-CONDITION-RESOLUTION-001)
과정에서 C1의 BLOCKER("TSU 필요 필드 확인")를 조사하다가, 실제로는
"TSU가 읽을 corpus manifest 계층이 Production 레벨에 전혀 없고
Periodical Pilot은 그 계층을 만든 적조차 없다"는 더 근본적인 gap이
드러났다(`NAE_PERIODICAL_CONDITION_RESOLUTION_REPORT_001.md` §4).
지금까지 "corpus manifest"(`source_manifest.yaml`)는 Pilot 산출물로만
비공식적으로 존재했고, Authority Registry와 TSU 사이의 경계 역할을
정식으로 설계한 적이 없었다.

## 2. Problem

Authority Registry(정적 서지 구조)와 TSU(의미 단위 생성) 사이에
"이 자료가 지금 파이프라인의 어느 단계에 있는가"를 추적하는 계층이
필요한가? 필요하다면 어떤 Entity 관계·필드·상태 전이로 설계할 것인가?

## 3. Decision

### 3.1 Manifest Layer 신설

```
Authority Registry (정적 서지 구조: Author→Work→Edition→Volume→Issue→Source)
        │
Manifest Layer (신설 — 동적 처리 상태: Source 1:1, processing_status로 진행 추적)
        │
TSU
```

### 3.2 Entity 관계

- Manifest Entry는 Source의 확장(하위 필드)이 아니라 **별도 Entity**,
  `source_id` FK로 **1:1** 연결한다.
- `manifest_id = source_id`(별도 ID 체계 신설 안 함, ADR-017 미개정).
- Manifest는 OCR/TSU/Embedding별로 나뉘지 않고 **단일 Entry 안에서
  `processing_status`가 전진**하는 선형 모델을 채택한다.

### 3.3 Schema(문서 수준)

필수 필드: `manifest_id`, `source_id`, `work_id`, `edition_id`(조건부),
`volume_id`(조건부), `issue_id`(조건부), `processing_status`,
`tsu_access`, `schema_version`. 조건부 필드 규칙은 ADR-018의
`work_type` 분기(TSU 필수 필드 예외)를 그대로 재사용한다.

Lifecycle: `RAW Acquired → Registered → Manifest Created → Validated
→ TSU Eligible → TSU Generated → Indexed`(단조 진행 원칙).

### 3.4 Monograph/Periodical 통합

**PASS** — 별도 스키마 분기 없이 동일 Manifest Entry 구조를 공유한다
(조건부 필드로 유형 차이 흡수, ADR-018과 동일 패턴).

### 3.5 신규 ADR 채택

기존 ADR-014/015/016/017/018 중 어느 것도 이 결정(Registry-TSU 경계에
새 계층 신설)을 다루지 않는다 — 신규 [ADR-019](.)로 기록하며, 기존
ADR 본문은 수정하지 않는다("ADR 소급 수정 금지" 관례의 네 번째 일관된
적용, ADR-014→016, GOVERNANCE→017, Revision→018에 이어).

## 4. Alternatives

| 대안 | 기각 사유 |
|---|---|
| Manifest 필드를 Registry Source entity에 직접 추가(별도 Entity 신설 안 함) | 갱신 빈도가 다른 값(정적 서지 vs 동적 처리 상태)이 한 엔티티에 섞여 git diff 가독성 저하, Registry Design v1 §2.5 원칙과 불일치 |
| Source당 여러 Manifest(OCR/TSU/Embedding 별도 문서) | Lifecycle이 선형인데 병렬 문서로 나누면 "지금 어느 단계인가"를 여러 문서 대조로만 알 수 있어 목적에 반함 |
| ADR-016 개정(Entity 모델에 Manifest 통합) | Manifest는 Registry Entity 모델과 층위가 다름(정적 구조 vs 동적 상태) — 기존 "소급 수정 금지" 관례 위반 |

## 5. Consequences

- Schema/Registry/Validator/Pilot/RAW는 이 ADR로 변경되지 않는다 —
  정책·설계만 확정.
- 다음 실행 단계(Migration Plan Phase 1~5)는 각각 별도 승인이
  필요하다.
- Monograph Pilot(Phase 2)이 Periodical Pilot(Phase 3)보다 먼저
  진행되어야 한다(낮은 리스크 우선 원칙).
- ADR 번호 충돌 확인: 작성 시점 기준 001–018 존재, 019는 미사용 번호로
  충돌 없음.

## 6. Future Expansion

- Manifest 실제 스키마 파일 작성(Migration Plan Phase 1)
- Registry Validation Tool(설계만 존재)과 Manifest 검증 도구의 관계
  확정 — 통합할지 별도로 둘지(Migration Plan Phase 4)
- TSU 빌더에 `processing_status=TSU_ELIGIBLE` 게이트 구현(Phase 5)

## Validation

설계 문서이므로 코드/데이터 검증 대상 없음. 문서 정합성만 확인:

```
grep -r "ADR-019" docs/
```

## Promotion Evidence (NAE-ADR-PROMOTION-001, 2026-08-03)

Evidence Before Promotion Rule(CLAUDE.md) 4조건 충족 확인:

1. **구현 완료** — `scripts/manifest_validator.py` 구현, Manifest
   Pilot(dagg/hiscox/fuller, 10 source) 실제 구축
2. **회귀 테스트 통과** — `tests/test_manifest_validator.py`, Pilot
   실행 PASS=138 WARNING=0 FAIL=0, TSU_ELIGIBLE=READY 10/10(drift 없음,
   `docs/NAE_METADATA_MIGRATION_READINESS_REVIEW_001.md` §Phase3 재확인)
3. **독립 리뷰(C1) 완료** — `docs/NAE_MANIFEST_VALIDATOR_REVIEW_001.md`,
   `docs/NAE_MANIFEST_PILOT_REVIEW_002.md`
4. **사용자 승인** — 2026-08-03 NAE-ADR-PROMOTION-001

`scope_modified`(frontmatter)는 작성 시점 "Manifest 실제 생성,
Schema/Validator/Registry 변경 없음"이었으나, 이후 Manifest Pilot이
실제 구축·검증됨 — 위 Evidence 문서가 실행 근거. TSU 빌더 게이트
(`core/tsu_builder.py`의 `processing_status=TSU_ELIGIBLE` 연동)는 여전히
미구현 상태(Readiness Review §Phase5 WARNING) — ADR 승격과 별개로
남은 과제.
