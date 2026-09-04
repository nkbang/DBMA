# NAE TSU Pipeline Preflight Report 001

**Project:** NAE-TSU-PIPELINE-PREFLIGHT-001
**작성일:** 2026-08-05
**성격:** Preflight 분석 및 설계(Design Only) — 실제 Corpus TSU 생성,
`core/*`, Migration Engine, ADR 전부 무수정.
**Git Commit/Push:** 미수행 — C1 Review 승인 전까지 대기.

---

## Phase 1 — TSU Pipeline Architecture Audit

### 1. Input Source 확인

```
CURRENT INPUT:
  NAE/corpus/canonical/{identifier}/canonical.json
  NAE/corpus/raw/archive_org/{category}/{identifier}/metadata.json (보조)

EXPECTED INPUT:
  Manifest Layer controlled source(TSU_ELIGIBLE=READY 판정 통과분만)
```

식별자 목록 자체를 `canonical_root.iterdir()`로 그냥 나열해서 얻는다
(`NAE/pipeline/tsu/builder.py::build_tsu_for_all`) — Manifest/Registry
조회 없음.

### 2. Gate Bypass 확인

```
$ grep -R "TSU_ELIGIBLE" NAE/pipeline
(결과 없음)

$ grep -R "canonical_id" NAE/pipeline
(결과 없음)

$ grep -Ri "manifest" NAE/pipeline --include="*.py"
(결과 없음)

$ grep -R "schema_version|authority_id|legacy_id|manifest_id" NAE/pipeline --include="*.py"
NAE/pipeline/embed/hashing.py, NAE/pipeline/verify/duplicate.py,
NAE/pipeline/index/*.py, NAE/pipeline/tsu/builder.py
→ 전부 `tsu_schema_version`(TSU 레코드 자체 shape 버전) 매칭뿐 —
  Registry/Manifest의 schema_version/authority_id/legacy_id/manifest_id
  와는 무관.
```

**추가 발견(Phase 1 확장)**: `NAE/corpus/canonical/`의 실제 identifier
(`PBC1742`, `PBC1765`, `SLBC1689`)가 Registry/Manifest의 실제 source_id
(`BAP-CHURCH-DAGG-001` 등)와 **하나도 겹치지 않는다**(`grep` 결과
0건) — Gate가 "우회"되는 게 아니라 애초에 두 시스템이 다른 데이터
집합을 가리키고 있다. 상세: `docs/NAE_TSU_PIPELINE_CONTRACT_DESIGN_001.md`
§1.

---

## Phase 2 — TSU Contract Design

`docs/NAE_TSU_PIPELINE_CONTRACT_DESIGN_001.md` 작성 완료. 요약:

- Contract 필드: `manifest_id`/`source_id`/`authority_id`/`canonical_id`/
  `schema_version`/`processing_status`, Gate는
  `processing_status == TSU_ELIGIBLE(READY)`만 허용.
- Flow 변경 목표: RAW → Manifest Layer → Validator → TSU_ELIGIBLE →
  TSU Builder(기존 claim 추출 로직 재사용) → TSU.
- **미해결로 명시한 항목**: Manifest `source_id` ↔ TSU Pipeline
  `identifier` 사이의 crosswalk 규칙이 아직 없다 — 이것이 Phase 4
  판단의 핵심 근거.

---

## Phase 3 — Adapter Boundary 확인

TSU Builder(`NAE/pipeline/tsu/parser.py`)가 `canonical_root`/`raw_root`
파라미터로 **RAW/canonical 파일을 직접 읽는다**(`load_canonical()`,
`_find_raw_metadata()`) — Registry나 Manifest를 거치지 않는다.

```
### FAIL
Direct corpus access exists
```

**판정: FAIL** — "TSU Builder receives validated manifest input only"
조건을 충족하지 못한다. 다만 이 FAIL은 코드 결함이 아니라 §Phase1에서
확인한 대로 "애초에 그렇게 설계된 적이 없다"는 사실의 재확인이다.

---

## Phase 4 — Implementation Scope 판단

**선택: Option A**

```
DESIGN ONLY
ADR REQUIRED
```

### 근거

1. **TSU Pipeline 수정 규모가 크다** — 단순히 `build_tsu_for_all`의
   identifier 열거 방식만 바꾸는 것으로는 부족하다. Manifest
   `source_id`와 TSU `identifier`가 전혀 다른 값 체계를 쓰고 있어서
   (§Phase1 발견), 필터를 추가하기 전에 **두 값 체계를 잇는 crosswalk
   규칙 자체를 먼저 정의**해야 한다 — 이는 코드 변경이 아니라
   아키텍처 결정이다.
2. **ADR 필요** — 이 crosswalk을 어디에 저장할지(Manifest에 필드
   추가? Registry `sources.yaml`의 `file_path`를 파싱해서 역산?
   완전히 새로운 매핑 테이블?) 자체가 ADR-019(Manifest Layer) 범위를
   벗어날 가능성이 있다 — Manifest Layer가 "Source 1:1"로 설계됐다는
   기존 결정(ADR-019 §1)과, TSU Pipeline이 요구하는 identifier 단위가
   실제로 일치하는지부터 검증이 필요하다(현재 Pilot 3개 source 중
   Fuller는 8개 volume이 전부 같은 물리 identifier 하나를 공유할
   가능성이 있음 — Editions.yaml의 1:N 구조, ADR-016 §3.1 참고 — 이
   경우 Manifest:TSU identifier가 1:1이 아니라 N:1일 수 있다).

Option B(작은 Adapter만 추가)를 선택하지 않은 이유: "기존 TSU Builder
유지 + Input Adapter만 추가"라는 조건 자체는 기술적으로는 맞을 수
있으나(§2 Flow 변경 목표에서도 이미 그렇게 설계함), **그 Adapter가
의존할 identifier crosswalk 규칙이 없는 상태에서 Adapter부터 만들면
잘못된 매핑을 코드에 고정시킬 위험**이 크다 — 규칙을 먼저 확정하는
것이 우선이다.

---

## Phase 5 — Required Questions

| 질문 | 답 |
|---|---|
| Q1. TSU Pipeline이 Manifest Gate를 우회하는가? | **우회가 아니라 애초에 연결된 적이 없음**(grep 0건 — TSU_ELIGIBLE/canonical_id/manifest 참조 전무). 결과적으로는 우회와 동일한 효과("Gate를 안 거치고 실행됨"). |
| Q2. canonical_id 연결이 필요한가? | **예, 필요 — 단 이번 단계에서 실행하지 않음.** Contract 설계(§Phase2)에 canonical_id를 필수 필드로 포함시켰으나, 실제 연결(코드 구현)은 identifier crosswalk이 먼저 확정된 뒤 별도 작업. |
| Q3. ADR-014/015 수정 필요 여부 | **불필요.** ADR-014/015는 Modern Corpus Layer/Ingestion Standard(신규 corpus 유입 규칙)를 다루며, 이번 발견(기존 Pilot corpus의 TSU 연결 문제)과 직접 관련 없음 — 무변경 유지, 이번 Task에서도 손대지 않음(§금지 4 준수). |
| Q4. Migration Architecture 충돌 여부 | **없음.** Migration Engine/Adapter는 Registry/Manifest만 다루고 TSU를 전혀 참조하지 않는다(Readiness Review Check 4 재확인, 이번 Task에서도 grep으로 재검증). 이번 발견은 "충돌"이 아니라 "아직 연결되지 않은 별개 시스템"이라는 사실의 확인이다. |
| Q5. Retrieval Architecture 보호 여부 | **보호됨.** `core/retrieval.py` git 이력 무변경 확인(§Regression 이전 Readiness Review와 동일 결과), 이번 Task에서도 `core/*` 전혀 접근하지 않음. 단, `NAE/pipeline/index/`(Qdrant 연동)가 이미 존재함을 이번 감사에서 확인했다 — 이는 `core/retrieval.py`와 별개 코드지만, 향후 TSU→Retrieval 연결 설계 시 참고 필요(이번 Task 범위 밖, 기록만). |
| Q6. TSU Pipeline 재개 가능 여부 | **NO.** Contract(§Phase2)와 Gate 요구사항은 정의됐으나, identifier crosswalk 미확정으로 실제 연결 구현이 아직 불가능하다. |

---

## Regression

```
source_validator.py --root resources/theological_sources        : PASS=89  WARNING=0  FAIL=0  (baseline 일치)
manifest_validator.py(Pilot, corpus-manifest-root 지정)           : PASS=138 WARNING=0  FAIL=0  (baseline 일치)
authority_validator.py(Production)                                : PASS=128 WARNING=26 FAIL=0  (baseline 일치)
```

**Drift = 0.**

### 금지 목록 준수 확인

```
$ git status --short core/ scripts/migration_engine.py scripts/adapters/ scripts/migrate_pilot.py docs/architecture/ NAE/corpus/
(출력 없음 — 전부 무변경)
```

---

## 완료 보고

```
STATUS: COMPLETE (design only, no TSU generation, no core/Engine/ADR changes)

FILES CREATED:
docs/NAE_TSU_PIPELINE_CONTRACT_DESIGN_001.md
docs/NAE_TSU_PIPELINE_PREFLIGHT_REPORT_001.md

FILES MODIFIED:
(없음)

TSU GATE STATUS:
NOT CONNECTED — Contract 정의 완료(§Phase2), 실제 연결은 identifier crosswalk 확정 후 별도 작업 필요(Q2/Q6)

ADR IMPACT:
ADR-001/014/015/016/017/018/019 전부 무변경. 단 향후 identifier crosswalk을 어디에 정의할지는 ADR-019 범위 확장 또는 신규 ADR 필요 가능성 있음(§Phase4, 이번 Task는 결정하지 않고 다음 단계로 이관)

VALIDATOR DRIFT:
0 (89/0/0, 138/0/0, 128/26/0 전부 baseline과 일치)

BLOCKER:
1 (identifier crosswalk 미정의 — Manifest source_id ↔ TSU Pipeline identifier 대응 규칙 없음, §Phase2/Phase4)

WARNING:
1 (`NAE/pipeline/index/`에 Qdrant 연동 코드가 이미 존재 — core/retrieval.py와 별개이나 향후 TSU→Retrieval 연결 설계 시 검토 필요, 이번 범위 밖으로 기록만)

NEXT STEP:
1. Identifier Crosswalk 설계 Task(ADR Amendment 필요 여부 포함) — 이번 발견의 직접 후속
2. 위 완료 후 Manifest 기반 identifier 필터 Adapter 구현(Option B 수준의 작은 변경, crosswalk 확정 후에는 가능)
3. C1에 NAE-TSU-PIPELINE-PREFLIGHT-REVIEW-001 전달 — Contract Design/Boundary 판정/Phase4 Option A 선택 근거 검증 요청

GIT:
NOT PERFORMED
```
