# NAE TSU Pipeline Resume Readiness Review 001

**Project:** NAE-TSU-PIPELINE-RESUME-READINESS-001
**작성일:** 2026-08-05
**성격:** 재개 조건 검증 — TSU 생성/Embedding/Chunking/Vector Index/
Qdrant·Chroma 변경/RAW 접근/Registry Migration/Manifest 변경/
RetrievalEngine 변경/ADR 변경 전부 미수행(읽기 전용 검증).
**Git Commit/Push:** 미수행 — 사용자 승인 대기.

---

## Executive Summary

**Migration Workstream(Engine/Adapter/Pilot Migration/Validator) 자체는
전부 PASS 상태로 완료됐다.** 그러나 이번 검증(Check 5)에서 **실제 NAE
TSU Pipeline 진입점(`NAE/pipeline/tsu/`)이 Manifest Layer/Authority
Registry/Migration Engine 어느 것과도 연결되어 있지 않다**는 것을
코드 실측으로 확인했다 — TSU Pipeline은 `NAE/corpus/canonical/`과
`NAE/corpus/raw/archive_org/`를 identifier 기준으로 직접 읽을 뿐,
`canonical_id`/`legacy_id`/`TSU_ELIGIBLE`/Manifest lifecycle 필드를
전혀 참조하지 않는다. 즉 지금 TSU Pipeline을 실행하면 Migration
Workstream이 검증해 온 Manifest Gate(TSU_ELIGIBLE)를 완전히 우회하게
된다.

**판정: READY WITH CONDITIONS.**

---

## 1. Check 1 — Git Integrity

```
$ git log -1 --oneline
d2d4e37 feat: add Metadata Migration Engine, Adapters, and Pilot tooling
```

- 마지막 commit: **`d2d4e37`** — 일치 확인.
- Migration Workstream commit 포함 여부: **포함 확인**(`scripts/migration_*.py`,
  `scripts/adapters/*`, `scripts/migrate_pilot.py`, 설계/구현/리뷰
  문서 다수 — 이전 커밋 `c442481`의 Pilot Execute 결과도 히스토리에
  포함).
- 미승인 변경 없음: `git status`에는 이번 세션이 만들지 않은 다른
  세션의 untracked 문서(`docs/NAE_C1_*`, `docs/NAE_MANIFEST_*` 등)와
  기존 `test_seal_3dx3ac_8/` 삭제 표시가 있으나, 이는 이번 작업이나
  Migration Workstream이 발생시킨 변경이 아니다(Migration Workstream
  관련 파일은 전부 이미 커밋됨) — Migration Workstream 관점에서
  **미승인 변경 없음.**

**판정: PASS**

---

## 2. Check 2 — Migration Artifact Verification

| 문서 | 존재 여부 |
|---|---|
| `docs/NAE_METADATA_MIGRATION_ENGINE_DESIGN_001.md` | **FOUND** |
| `docs/NAE_METADATA_MIGRATION_IMPLEMENTATION_REPORT_001.md` | **FOUND** |
| `docs/NAE_METADATA_MIGRATION_PILOT_IMPLEMENTATION_REPORT_001.md` | **FOUND** |
| `docs/NAE_METADATA_MIGRATION_EXECUTE_REVIEW_001.md` | **FOUND**(C1 작성, Pilot Execute Report에 대한 독립 검토) |

**판정: PASS**

---

## 3. Check 3 — Validator Baseline Lock

```
source_validator.py --root resources/theological_sources        : PASS=89  WARNING=0  FAIL=0
manifest_validator.py(Pilot, corpus-manifest-root 지정)           : PASS=138 WARNING=0  FAIL=0
authority_validator.py(Production)                                : PASS=128 WARNING=26 FAIL=0
```

명령서 기준값과 완전히 일치.

**판정: DRIFT = 0**

---

## 4. Check 4 — Architecture Boundary Verification

### Retrieval

```
$ git log -1 --oneline -- core/retrieval.py
e542b86 fix: cap theological/passage scoring pool on BM25-miss fallback (SEARCH-INFRA-001 Phase0/1)
$ git status --short core/retrieval.py
(출력 없음)
```

`core/retrieval.py`의 마지막 변경 커밋은 Migration Workstream과 무관한
이전 작업(`e542b86`, SEARCH-INFRA-001)이며, 이번 워크스트림 전체
기간 동안 **무변경** 확인.

**판정: NO CHANGE**

### TSU ↔ Migration Engine 독립성

```
$ grep -rn "tsu_builder\|core/tsu\|TSU_ELIGIBLE" scripts/migration_*.py scripts/migrate_pilot.py scripts/adapters/*.py
(결과 없음)

$ grep -n "migration_engine\|migrate_pilot\|adapters" core/tsu_builder.py
(결과 없음)
```

Migration Engine/Adapter 어디에도 TSU 관련 코드가 없고, 역방향으로
`core/tsu_builder.py`도 Migration Engine을 참조하지 않는다 — **양방향
결합 없음** 확인.

**판정: 경계 유지 확인(PASS)** — 단, §5에서 "경계가 유지되어 있다"는
것과 "경로가 실제로 연결되어 있다"는 것은 별개임을 발견했다(아래 참고).

---

## 5. Check 5 — TSU Input Contract Review

### 실측 대상 재확인

`core/tsu_builder.py`(DBMA-Index-Authority-Design-v1 기반, 548줄)는
**NAE 전용이 아니다** — docstring 확인 결과 "TSU v1 builder (Index
Authority, library layer)"로, 설교/일반 문서 코퍼스를 위한 별도
라이브러리다. 실제 **NAE 전용 TSU Pipeline 진입점은
`NAE/pipeline/tsu/`**(runner.py/builder.py/parser.py/citation.py/
claim.py/doctrine.py/scripture.py/config.py, 총 547줄)이다 — 명령서의
"TSU Pipeline Entry Point"는 이쪽을 가리키는 것으로 판단해 이 경로를
검토했다.

```python
# NAE/pipeline/tsu/config.py
CANONICAL_ROOT = CORPUS_ROOT / "canonical"
RAW_ROOT = CORPUS_ROOT / "raw" / "archive_org"
TSU_ROOT = CORPUS_ROOT / "tsu"
TSU_SCHEMA_VERSION = "1"
```

```
$ grep -n "canonical_id|legacy_id|TSU_ELIGIBLE|processing_status|schema_version|manifest" NAE/pipeline/tsu/*.py
NAE/pipeline/tsu/builder.py:75:            "tsu_schema_version": config.TSU_SCHEMA_VERSION,
```

(`schema_version` 매칭은 TSU 자체 스키마 버전 필드 정의일 뿐, Registry/
Manifest schema_version과의 교차 참조가 아니다 — 그 외 매칭 없음.)

### 질문별 답변

**1. canonical_id 사용 가능 여부?**
→ **미사용/미참조.** TSU Pipeline은 `--identifier`(예: archive.org
item id)로 `NAE/corpus/canonical/{identifier}/`를 직접 읽는다 — Author/
Work/Edition/Source 등 Registry entity나 그 `canonical_id`를 전혀
조회하지 않는다. "사용 가능한가"라는 질문 자체가 성립하지 않을 만큼
현재는 아예 연결되어 있지 않다.

**2. legacy_id 영향 여부?**
→ **영향 없음(참조하지 않으므로).** canonical_id와 동일한 이유.

**3. manifest lifecycle 상태가 TSU Gate와 연결되는지?**
→ **연결되지 않음.** `manifest_validator.py`가 계산하는
`TSU_ELIGIBLE`(READY/BLOCKED)을 `NAE/pipeline/tsu/`의 어떤 모듈도
조회하지 않는다 — `runner.py`/`builder.py`에 Manifest 파일 경로나
`tsu_status`/`metadata_status` 필드를 읽는 코드가 없다. 즉 지금 TSU
Pipeline을 실행하면 **Manifest Gate를 완전히 우회하고 RAW/canonical을
직접 소비**하게 된다 — 이는 `NAE_METADATA_MIGRATION_READINESS_REVIEW_001.md`
§Phase5(WARNING: "TSU 빌더에 processing_status=TSU_ELIGIBLE 게이트
미구현")에서 이미 예고된 상태였고, 이번 검증으로 실제 진입점
(`NAE/pipeline/tsu/`)에서도 동일하게 확인됐다.

**4. schema_version 호환 여부?**
→ **호환성 자체가 정의되어 있지 않음(비교 대상 아님).** TSU Pipeline은
독립된 `TSU_SCHEMA_VERSION = "1"`(builder.py의 TSU 레코드 shape
버전)만 갖고 있고, Registry `schema_version: "1.0"`이나 Manifest
schema v2.2.x와는 아무 관계가 없다 — "호환된다/안 된다"를 판정할
연결점 자체가 없다.

### TSU READY

```
TSU READY: NO
```

**근거**: 위 4개 질문 전부가 "아직 연결되어 있지 않다"로 귀결된다 —
코드에 결함이 있는 것이 아니라(Migration Engine/Adapter/Validator는
전부 정상 동작 확인됨, §1~4), **TSU Pipeline이 애초에 이 Migration
Workstream이 만든 Manifest/Registry 계층을 소비하도록 설계·연결된
적이 없다.** 지금 TSU를 실행하면 기술적으로는 동작하겠지만(RAW/
canonical을 직접 읽으므로), Migration Workstream이 지금까지 검증해 온
"Metadata Migration → Metadata Complete → TSU Eligible" 게이트를 그냥
건너뛰게 된다.

---

## 6. Check 6 — Modern Corpus ADR 상태 확인

```
docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md:      | Status | Proposed(승격 보류, 2026-08-03 NAE-ADR-PROMOTION-001 검토) |
docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md: | Status | Proposed(승격 보류, 2026-08-03 NAE-ADR-PROMOTION-001 검토) |
```

예상대로 **ADR-014/015 둘 다 Proposed** — 변경하지 않았다(보고만).

---

## Validation Matrix

| Item | Result |
|---|---|
| Migration Engine | PASS |
| Adapter | PASS |
| Pilot Migration | PASS |
| Validator Drift | PASS |
| Metadata Schema | PASS |
| TSU Contract | **FAIL**(연결 안 됨 — §5) |

---

## Decision

```
READY WITH CONDITIONS
```

Migration Workstream 자체(Engine/Adapter/Pilot Migration/Validator/
Architecture Boundary)는 전부 PASS다. 그러나 TSU Contract가 FAIL이므로
**TSU Pipeline을 지금 실행하면 이번 워크스트림이 만든 Manifest Gate를
우회하게 된다** — Architecture Freeze Rule에 따라 TSU Pipeline
Preflight 단계에서 아래 조건을 먼저 충족해야 한다:

1. `NAE/pipeline/tsu/`(또는 그 상위 오케스트레이션 레이어)가 처리
   대상 identifier를 결정하기 전에 `manifest_validator.py`의
   `TSU_ELIGIBLE=READY` 판정을 조회하도록 게이트를 추가해야 한다
   (이번 Task는 이 구현을 수행하지 않음 — TSU Pipeline Preflight
   단계의 작업으로 이관).
2. 위 게이트 설계는 새로운 Architecture 결정(Manifest ↔ TSU Pipeline
   결합 지점)이므로, ADR-019(Approved) 범위 안에서 가능한지 먼저
   확인하고, 범위를 벗어나면 ADR Amendment가 필요할 수 있다 — 이 판단
   자체를 TSU Pipeline Preflight의 첫 항목으로 넘긴다.

---

## 완료 보고

```
STATUS: COMPLETE (readiness verification only, no TSU/Embedding/data changes)

FILES CREATED:
docs/NAE_TSU_PIPELINE_RESUME_READINESS_REVIEW_001.md

VALIDATOR:
DRIFT = 0 (source 89/0/0, manifest 138/0/0, authority 128/26/0 — 전부 기준값과 일치)

ARCHITECTURE:
core/retrieval.py NO CHANGE 확인
Migration Engine ↔ TSU 양방향 결합 없음 확인(경계 유지)
ADR-014/015 Proposed 유지 확인(무변경)

TSU READY:
NO (TSU Contract FAIL — NAE/pipeline/tsu/가 Manifest TSU_ELIGIBLE 게이트를 전혀 참조하지 않음, canonical_id/legacy_id/schema_version 어느 것도 연결되어 있지 않음)

BLOCKER:
1 (TSU Pipeline이 Manifest Gate와 연결되지 않음 — TSU Pipeline Preflight 단계에서 게이트 연결 설계·구현 필요, 필요 시 ADR Amendment 검토)

WARNING:
0

GIT:
NOT PERFORMED(사용자 승인 대기)
```
