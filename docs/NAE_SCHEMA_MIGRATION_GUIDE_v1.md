# NAE Schema Migration Guide v1

작성일: 2026-08-02
상태: Infrastructure 구축 완료 후 산출물 — **이 가이드 자체는 Migration을
실행하지 않는다**. 실제 Corpus-wide Metadata Migration은 별도 승인 후
착수한다(로드맵 "Corpus-wide Metadata Migration ⏳").
근거: [ADR-016](architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md),
[`NAE_METADATA_GOVERNANCE_v1.md`](NAE_METADATA_GOVERNANCE_v1.md) §7(Migration Policy),
[`NAE_METADATA_AUTHORITY_IMPLEMENTATION_PLAN_001.md`](NAE_METADATA_AUTHORITY_IMPLEMENTATION_PLAN_001.md) §5

---

## 0. 전제

이 가이드는 800여 권 규모의 자료를 **반복 가능한 절차**로 등록하기 위한
실행 순서다. Schema/Registry/Validator는 이번 작업(NAE-SCHEMA-MIGRATION-001)
에서 Infrastructure로만 준비되었고, 아래 순서는 그 Infrastructure를
**사용**하는 절차를 기술한다 — 이번 가이드 발행 자체가 Migration 착수를
승인하지 않는다.

---

## Migration 순서

```
1. Manifest
   ↓
2. Authority
   ↓
3. Validator
   ↓
4. Pilot
   ↓
5. Corpus
```

### Step 1. Manifest

**목표**: 각 카테고리 디렉토리에 `source_manifest.yaml`을 v2.1.0 스키마로
생성/보강한다.

- 대상: `resources/theological_sources/modern/{category}/source_manifest.yaml`
  (신규 등록) + `resources/theological_sources/baptist/source_manifest.yaml`
  (기존 v1.2, `copyright_status` 등 파생 필드만 추가 — 재작성 아님)
- 사용 스키마: `resources/theological_sources/modern/source_manifest.schema.yaml`
  (Phase 1 산출물)
- **전제조건**: 없음 — 즉시 시작 가능(GOVERNANCE §7.2 Step 1과 동일 원칙)
- **산출물**: 카테고리별 manifest entry(아직 Authority 연결 전 — `author_id`/
  `work_id`/`edition_id`는 이 Step에서는 "잠정 배정"만, 최종 확정은 Step 2)

### Step 2. Authority

**목표**: `authority/{authors,works,editions,volumes,sources}.yaml`에 실제
데이터를 채운다.

- 사용 템플릿: 이번 작업(Phase 2)에서 생성한 빈 템플릿 5개
- 절차: `NAE_METADATA_AUTHORITY_IMPLEMENTATION_PLAN_001.md` §4 "Existing
  Corpus Mapping 방법"의 7단계 파이프라인(Collection→Normalization→
  **Human Verification**→Work Grouping→**Human Verification**→Edition/
  Volume Separation→Validation) 그대로 적용
- **전제조건**: Step 1에서 대상 manifest entry가 존재해야 함(참조 대상이
  있어야 Authority가 의미 있음)
- **자동 병합 금지**: Author/Work 확정은 반드시 사람이 확인
  (`NAE_METADATA_GOVERNANCE_v1.md` §1 Philosophy #3)
- **우선순위**: `NAE_METADATA_AUTHORITY_IMPLEMENTATION_PLAN_001.md` §4.2
  그대로 계승 — church_order류 소규모 우선, 다권본 그 다음,
  early_baptist_collection은 계속 별도 트랙

### Step 3. Validator

**목표**: `scripts/source_validator.py`를
`docs/NAE_SOURCE_VALIDATOR_REQUIREMENTS_v1.md` 요구사항대로 확장한다.

- **이번 가이드가 최초로 코드 수정을 언급하는 지점**이다 — 이 Step 자체가
  "코드 구현"이므로 착수 전 **별도 승인 필수**(이번 NAE-SCHEMA-MIGRATION-001
  범위 밖).
- 회귀 테스트: 기존 v1.2 manifest 검증 결과 불변 확인(Requirements §7)
- **전제조건**: Step 1/2에서 실제 v2.1.0 데이터 샘플이 있어야 확장 로직을
  검증할 수 있음(적어도 파일럿 규모)

### Step 4. Pilot

**목표**: Step 1~3으로 구축한 실제 Infrastructure(스키마/Authority/
Validator)로 Pilot-001(church_order)과 Pilot-002(Fuller) 데이터를
**재검증**한다.

- 대상: `authority/pilot/`, `authority/pilot/fuller/`의 기존 산출물
- 목적: 설계 단계(Pilot-001/002)에서는 임시 검증 스크립트(Python 즉석
  스크립트)로 Reference Integrity를 확인했으나, 이번 Step에서는 **실제
  Validator(Step 3 산출물)**로 동일 검증이 재현되는지 확인 — 도구가
  실제로 프로덕션에서 동작하는지의 최종 확인 게이트
- **전제조건**: Step 3 완료(Validator 실제 확장)
- 실패 시: Step 3으로 되돌아가 Validator 로직 수정(Rollback §2 참고)

### Step 5. Corpus

**목표**: 나머지 약 800여 권(정확한 수치는 재실측 필요,
`NAE_METADATA_AUTHORITY_PLAN_REVIEW_001.md` §5 지적 사항 참고)에 Step 1~4
검증된 절차를 반복 적용.

- **이 Step은 별도 작업 명령서와 승인이 필요하다** — 이 가이드는 절차를
  정의할 뿐 착수를 승인하지 않는다.
- 점진적 적용: 카테고리 단위로 순차 진행, 전체 일괄 변환 금지
  (GOVERNANCE §7.1)

---

## Rollback 절차

원칙: `NAE_METADATA_AUTHORITY_IMPLEMENTATION_PLAN_001.md` §6과 동일 —
신규 산출물이 기존 v1.2 파일과 물리적으로 분리되어 있어 각 Step은 독립적으로
되돌릴 수 있다.

| Step | Rollback 방법 |
|---|---|
| 1. Manifest | 신규 추가한 manifest entry만 제거(v1.2 파생 필드 추가분은 필드만 제거, 원본 `license` 등은 무손상) |
| 2. Authority | `authority/{authors,works,editions,volumes,sources}.yaml`을 이번 작업이 만든 빈 템플릿 상태로 되돌림(git revert) — manifest는 참조당하는 쪽이라 무손상 |
| 3. Validator | 코드 변경분을 git revert — v1.2 검증 로직이 별도 분기로 존재하는 한(§3.1 "필드명이 아닌 값 기반 분기" 요구사항) v1.2 검증 경로는 그대로 유지됨 |
| 4. Pilot | pilot 재검증 실패는 데이터 손상이 아니라 "재검증 실패" 상태 — Step 3으로 돌아가 재작업, 별도 rollback 불필요 |
| 5. Corpus | 카테고리 단위 진행이므로 문제 발생 카테고리만 되돌리고 나머지는 유지 — 전체 rollback 불필요(점진적 적용의 이점) |

**공통 원칙**: 어느 Step도 RAW 원문을 이동/수정하지 않으므로, 최악의 경우
(Step 5에서 심각한 오류 발견)에도 **원본 데이터 손실은 없다** — metadata
계층만 되돌리면 된다.

---

## Migration 착수 전 체크리스트

Step 5(Corpus) 착수 전 반드시 확인:

- [ ] Step 1~4가 최소 1개 카테고리(예: church_order)에서 실제 성공
- [ ] `docs/NAE_METADATA_AUTHORITY_PLAN_REVIEW_001.md` §11 Required Changes
      전부 해결 확인
      (validator 필드명 불일치, 2단계 파일럿, 875개 수치 재확인 등)
- [ ] `scripts/source_validator.py` 확장이 회귀 테스트 통과
- [ ] 사용자 명시적 승인(별도 작업 명령서)

이 체크리스트가 전부 통과하기 전에는 Step 5(Corpus-wide Migration)를
시작하지 않는다.
