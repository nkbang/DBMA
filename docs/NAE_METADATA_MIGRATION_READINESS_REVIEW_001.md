# NAE Metadata Migration Readiness Review 001

**Project:** CUE-TASK-ORDER-040 / NAE-METADATA-MIGRATION-READINESS-REVIEW-001
**작성일:** 2026-08-03
**성격:** **Review Only** — Registry/Manifest/Corpus Manifest/RAW 수정,
TSU 생성, Embedding 생성, Migration 실행, Git Commit/Push 전부 수행하지
않음(읽기 + Validator 실행 + 문서 작성만).

---

## Phase 1 — Architecture Readiness

### 확인 대상 및 실측 결과

| ADR | 문서상 `Status` 필드 | 비고 |
|---|---|---|
| ADR-014 | **Proposed** | `docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md:18` |
| ADR-015 | **Proposed** | `docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md:20` |
| ADR-016 | **Proposed** | `docs/architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md:19` |
| ADR-017 | **Proposed** | `docs/architecture/ADR-017-NAE-ID-Governance-Standard.md:17` |
| ADR-018 | **Proposed** | `docs/architecture/ADR-018-NAE-Periodical-Authority-Extension.md:19` |
| ADR-019 | **Proposed** | `docs/architecture/ADR-019-NAE-Corpus-Manifest-Layer.md:18` |

`docs/NAE_C1_ARCHITECTURE_DESIGN_REVIEW_FINAL_001.md:33`는 "최종 판정:
**APPROVED WITH CONDITIONS**"라고 기록하고 있으나, 이것은 **C1의 리뷰
보고서**이지 ADR 본문 `Status` 필드 자체를 Approved로 갱신한 것이
아니다. 즉 6개 ADR **문서 자체는 지금도 전부 "Proposed" 상태**다.

이는 방금 CLAUDE.md에 명문화한 **Evidence Before Promotion Rule**(구현
완료 + 회귀 통과 + C1 리뷰 + 사용자 승인 4조건 충족 시에만 Approved로
승격)의 관점에서 볼 때, 4조건 중 상당수가 실질적으로 충족됐음에도
**문서 상태 필드 자체를 Approved로 승격하는 명시적 절차가 아직 한
번도 수행되지 않았다**는 뜻이다.

### 질문: 충돌 존재? **NO**

6개 ADR 상호 간, 그리고 C1 Design Review Final-001이 지적한 조건들
(디렉토리 rename 별도 승인, Manifest 스키마 파일 작성 별도 승인 등)
사이에 실질적 내용 충돌은 발견되지 않았다 — 전부 "아직 실행하지
않았다"는 실행 순서상의 대기 상태이지, 규칙끼리 모순되는 것은 아니다.

**단, ADR 문서 status 필드 미승격 자체는 Phase 5의 BLOCKER로 별도
집계한다** — Architecture 내용의 충돌이 아니라 거버넌스 절차의 공백이기
때문에 Q1(충돌 존재?)과는 분리해서 다룬다.

---

## Phase 2 — Registry Readiness

| Entity | 개수 | canonical_id | legacy_id |
|---|---|---|---|
| Author | 3 | 3/3 | 1/3(FULLER-ANDREW-001만) |
| Work | 3 | 3/3 | 3/3 |
| Edition | 4 | 4/4 | 4/4 |
| Volume | 8 | 8/8 | 8/8 |
| Source | 10 | 10/10 | 10/10 |
| **합계** | **28** | **28/28** | **26/28**(NAE-ID-GOVERNANCE-IMPLEMENTATION-001, 커밋 `1042b1f`, C1 Review `378a216` APPROVED) |

`authority_validator.py` 실행(재확인): `PASS=128 WARNING=26 FAIL=0` —
이전 보고(C1 Review-001)와 **동일**, drift 없음.

### 질문: Migration 가능한가?

**부분적으로 가능(스키마 레벨) / 실행 엔진 레벨은 NO.** Registry
스키마(canonical_id/legacy_id) 자체는 완비되어 목표 상태(target
schema)로 사용할 준비가 됐다. 그러나 실제 ID rename이나 corpus-wide
데이터 이관을 수행할 **Migration Engine 코드는 저장소에 아직 존재하지
않음**을 확인했다(`find . -iname "*migration*engine*"` 등 결과 없음)
— 이는 이번 리뷰가 선행되어야 하는 이유와 정확히 일치하는 정상적인
상태(아직 구현 전 단계).

---

## Phase 3 — Manifest Readiness

| 항목 | 확인 결과 |
|---|---|
| Manifest Pilot | 3개 author 디렉토리(dagg/fuller/hiscox), 10개 source manifest entry |
| Manifest Schema | v2.2.x, `docs/NAE_MANIFEST_SCHEMA_V2_2_DESIGN_001.md` 정본 |
| Manifest Validator | `manifest_validator.py --registry-path resources/theological_sources/authority --root resources/theological_sources/manifest/pilot --corpus-manifest-root resources/theological_sources` 재실행 |
| TSU_ELIGIBLE | **10/10 READY** |

실행 결과: `PASS=138 WARNING=0 FAIL=0` — 이전 보고(Manifest Pilot
Lifecycle Normalization, 커밋 `a8e4581`)와 **동일**, drift 없음.
(`--corpus-manifest-root` 미지정 시 전원 `TSU_ELIGIBLE=BLOCKED`로 잘못
집계되므로, 정확한 판정을 위해 반드시 지정해야 한다는 점을 재확인.)

### 질문: Migration 가능한가?

**Pilot 규모(3 author/10 source)에서는 YES.** 다만 이 규모는 전체
목표 corpus 대비 매우 작아(Baptist 계열 실측 89건 중 Manifest는 아직
10건만), corpus-wide Migration으로 확장하려면 Manifest 생성 자체를
먼저 대량으로 수행해야 한다 — 이는 Metadata Migration의 선행 조건이지
Migration 자체의 BLOCKER는 아니다.

---

## Phase 4 — Validator Readiness

| Validator | 실행 결과(이번) | 기존 보고 | 차이 |
|---|---|---|---|
| `source_validator.py --root .../baptist` | PASS=21 WARNING=0 FAIL=0 | 21/0/0 | 없음 |
| `source_validator.py --root .`(전체) | PASS=89 WARNING=0 FAIL=0 | 89/0/0 | 없음 |
| `manifest_validator.py`(Pilot, corpus-manifest-root 지정) | PASS=138 WARNING=0 FAIL=0 | 138/0/0 | 없음 |
| `authority_validator.py`(Production) | PASS=128 WARNING=26 FAIL=0 | 128/26/0 | 없음 |

**3개 Validator 전부 기존 결과와 완전히 동일 — drift 없음.**

---

## Phase 5 — Migration Dependency Matrix

| 의존 요소 | 판정 | 근거 |
|---|---|---|
| Registry | **READY** | canonical_id 28/28, legacy_id 26/28, FK FAIL 0건(§Phase2) |
| Manifest | **READY**(Pilot 규모 한정) | TSU_ELIGIBLE 10/10 READY, WARNING/FAIL 0건(§Phase3) — corpus-wide 확장은 별도 과제 |
| Validator | **READY** | 3종 전부 재실행 확인, drift 없음(§Phase4) |
| Schema | **READY** | Registry Schema v1.0(canonical_id/legacy_id 포함), Manifest Schema v2.2.x 안정 |
| ADR | **NOT READY** | 6개 ADR 문서 `Status` 필드가 전부 Proposed(§Phase1) — Evidence Before Promotion Rule 기준 명시적 승격 미실행 |
| TSU | **BLOCKED** | `core/tsu_builder.py`에 `processing_status`/`TSU_ELIGIBLE` 게이트 코드 없음(grep 0건 확인) — ADR-019가 요구하는 Phase 5 구현 미착수 |
| Embedding | **NOT READY**(미착수) | TSU 이후 단계, 이번 Migration과 직접 의존 아님 — 참고용으로만 기록 |

---

## Phase 6 — Migration Risk Review

| 항목 | 평가 |
|---|---|
| Rollback 가능? | **부분적으로 가능** — 모든 변경이 git 커밋 단위로 추적되고(`git revert`/브랜치 백업 `backup/pre-git-cleanup`, 태그 `pre-git-cleanup-20260803` 존재 확인), RAW는 git 밖(`~/NAE_CORPUS_RAW/raw/`)에 별도 보존됨. 그러나 Registry/Manifest 데이터 자체를 위한 전용 스냅샷/버전 태깅 메커니즘은 없음 — git 이력에만 의존. |
| Audit 가능한가? | **부분적으로 가능** — Manifest에 `created_at`/`updated_at`/`verified_by` 필드가 있고 validator가 이를 검사함(PASS 확인). 그러나 `source_manifest.yaml`에 `sha256`/`checksum` 필드가 **없음**(grep 0건 확인) — 파일 변조·손상 탐지 근거가 약함. |
| Idempotent 가능한가? | **미확인** — Migration Engine 코드 자체가 아직 없어(§Phase2) 판단 불가. 구현 시 반드시 설계에 포함해야 할 요구사항으로 기록. |
| FK 손상 가능성? | **낮음** — canonical_id/legacy_id는 기존 FK 필드(`author_id`/`work_id`/`edition_id`/`volume_id`/`source_id`)를 전혀 변경하지 않는 additive 설계(Option B), authority_validator FK Integrity 검사 FAIL 0건. |
| Data Loss 가능성? | **낮음(현재 상태 기준)** — RAW 백업 완료, Registry/Manifest 전부 git 추적 중. 단, 향후 corpus-wide 대량 Migration 시 원자적 실행/부분 실패 처리 전략이 아직 설계되지 않아, 규모가 커지면 위험도 상승 예상. |

---

## Phase 7 — 최종 질문

### Q1. Metadata Migration을 시작해도 되는가?

**CONDITIONAL.**

Registry/Manifest/Validator 3개 축은 모두 READY이고 ID Governance
Option B(canonical_id/legacy_id)도 C1 독립 검증까지 완료됐다(커밋
`1042b1f`/`378a216`). 하지만 아래 §Q2의 3개 BLOCKER가 해소되기 전에는
"예"라고 답할 수 없다 — 특히 되돌리기 비용이 큰 작업이라는 이번
작업의 전제(사용자 명시)에 비추어, Idempotency/Rollback 설계 부재와
ADR 문서 상태 공백은 사전에 반드시 메워야 한다.

### Q2. 남아있는 BLOCKER는 무엇인가(우선순위 포함)?

```
[1순위] ADR-014~019 6개 문서 Status 필드가 전부 "Proposed"
        — Evidence Before Promotion Rule의 4조건(구현/회귀/C1/사용자
          승인)이 실질적으로 충족된 항목들도 있으나, 문서 status
          필드를 Approved로 명시 승격하는 절차가 한 번도 수행되지
          않음. Migration Engine이 이 ADR들을 "확정된 근거"로 삼기
          전에 승격 절차(각 ADR별 4조건 재확인 + status 필드 갱신
          커밋)가 필요.

[2순위] Migration Engine의 Idempotency/Rollback 전략 미설계
        — 코드 자체가 없으므로 당연한 상태이나, 설계 문서 단계에서
          반드시 명시해야 함(재실행 시 중복 방지, 실패 시 원상복구
          경로).

[3순위] source_manifest.yaml에 sha256/checksum 필드 없음
        — Migration 전/후 파일 무결성을 대조할 근거가 약함. Audit
          가능성을 높이려면 Migration Engine 설계에 체크섬 검증
          단계를 포함해야 함.
```

### Q3. Migration 전에 반드시 구현해야 하는 기능은?

- Migration Engine의 **Idempotent 실행** 보장(같은 입력 재실행 시
  중복/충돌 없음)
- **Rollback 절차**(체크포인트 커밋/태그 + 복원 스크립트) — 지금은
  git 이력에만 암묵적으로 의존
- 실행 전/후 **Reference Integrity 자동 재검증**(기존 3-Validator를
  Migration Engine 파이프라인에 편입 — 신규 로직 개발이 아니라 기존
  도구 재사용)
- **ADR-014~019 승격 절차**(4조건 재확인 + status 필드 갱신, 별도
  Task Order로 진행 권장 — 이번 Review 범위 밖)

### Q4. Migration 이후 즉시 실행해야 하는 것은?

- `source_validator.py`/`manifest_validator.py`/`authority_validator.py`
  3종 전체 재실행(회귀 확인, 이번 Review의 §Phase4 결과를 기준선으로
  비교)
- (체크섬 필드가 추가된 이후) `source_manifest.yaml` sha256 재대조
- Manifest `processing_status` 진행 상태 갱신 확인(TSU_ELIGIBLE 재계산)

### Q5. TSU Pipeline으로 넘어가기 위한 마지막 조건은?

- `core/tsu_builder.py`에 `processing_status=TSU_ELIGIBLE` 게이트
  구현(현재 코드에 해당 로직 없음 — grep 결과 0건으로 확인, ADR-019
  §Phase5가 요구하는 항목)
- Manifest Pilot 규모(3 author/10 source)를 corpus-wide로 확장 —
  Metadata Migration 완료가 선행 조건

---

## 산출물 요약

```
STATUS: COMPLETE (review only, no data/code changes)

Migration Ready:
CONDITIONAL

BLOCKER:
3
  1. ADR-014~019 status 필드 미승격(Proposed 유지)
  2. Migration Engine Idempotency/Rollback 미설계
  3. source_manifest.yaml sha256/checksum 필드 부재

WARNING:
2
  1. core/tsu_builder.py TSU_ELIGIBLE 게이트 미구현(TSU Pipeline 단계 조건, 이번 Migration 자체의 BLOCKER 아님)
  2. R6(NAE_ID_GOVERNANCE_REVIEW_001 인계) — 향후 modern/copyrighted corpus 추가 시 canonical_id 규칙 적용 여부 ADR-017 §2 재확인 필요

NEXT STEP:
1. ADR-014~019 승격 Task Order(문서 status 필드 갱신, 4조건 재확인) — 우선 처리 권장
2. Migration Engine 설계 문서(Idempotency/Rollback/체크섬 포함) 작성 — 구현 전 C1 선행 검토
3. 위 2개 완료 후 Migration Engine 구현 → Pilot Migration → C1 재검토 → Corpus-wide Migration

Git:
NOT PERFORMED
```
