# C1 Review 요청 — Authority Tier(T1-T4) M2 Tagging: 구현 코드 검토 (B3)

- 요청자: CUE
- 일자: 2026-09-17
- 유형: **C1 Review (구현 코드 대상, 사후검증형)** — ADR-030 Amendment D §4-B B3.
  `_REQUEST_001`/`_002`는 **설계 문서**(Plan 001, Amendment D 초안)를 대상으로 한 검토였고
  GREEN으로 종결됐다(`_RESULT_002.md`). 이번은 그 설계를 실제로 구현한 **코드**를 대상으로
  하는 별개 검토다 — Amendment B가 거친 것과 동일한 절차(설계 검토 → HQ 설계 승인 → 구현 →
  구현 코드 검토 → HQ 최종 승인).
- 선행 문서:
  - `docs/NAE_AUTHORITY_TIER_M2_TAGGING_IMPLEMENTATION_PLAN_001.md` (설계, §4-§6)
  - `docs/architecture/ADR-030-AMENDMENT-D-Authority-Tier-Doctrinal-Orthodoxy-Axis.md` (A3 HQ
    설계 승인 완료로 갱신됨, 2026-09-17)
  - `docs/NAE_AUTHORITY_TIER_M2_TAGGING_C1_REVIEW_RESULT_002.md` (설계 검토 GREEN, 근거)
  - `docs/NAE_AUTHORITY_TIER_M2_TAGGING_BUILD_REPORT_001.md` (이번 구현의 Build Report — 전체
    내용이 이번 요청의 근거)

## Git 상태 (요청 시점)

```
$ git rev-parse HEAD
e3adb941b566241560cf525e784c3204da00978c

$ git remote -v
nas     http://100.94.139.122:3000/David/DBMA.git (fetch)
nas     http://100.94.139.122:3000/David/DBMA.git (push)
origin  https://github.com/nkbang/DBMA.git (fetch)
origin  https://github.com/nkbang/DBMA.git (push)

$ git rev-parse --show-toplevel
/Users/David/DBMA/.claude/worktrees/c1-review-findings-9b8af7
```

**브랜치**: `claude/authority-tier-m2-implementation` (base: `origin/dev/dbma-engine` @
`50728a4b`, 구현 커밋 `e3adb94` 1개만 추가). A3(HQ 설계 승인)는 이 구현 커밋 이전에 채팅으로
확인됨 — Architecture Freeze Rule 순서 위반 없음.

```
$ git diff --stat origin/dev/dbma-engine HEAD
 NAE/pipeline/registration/pipeline.py                                     |  13 ++
 docs/NAE_AUTHORITY_TIER_M2_TAGGING_BUILD_REPORT_001.md                    | 132 ++++++++
 docs/architecture/ADR-030-AMENDMENT-D-Authority-Tier-Doctrinal-Orthodoxy-Axis.md |  21 +--
 scripts/m2_source_registry_validator.py                                   |  88 +++++-
 tests/test_m2_source_registry_governance.py                               |  78 +++++-
 5 files changed, 318 insertions(+), 14 deletions(-)
```

---

## 확인해야 할 것

### 1. `pipeline.py` — RegistrationRequest / manifest_entry 변경

`RegistrationRequest`에 `authority_tier`/`tradition_relation`/`counter_refs` 3개
optional 필드(기본값 `None`)를 추가하고, manifest_entry 조립 블록에 동일한
`if request.X is not None: manifest_entry["X"] = request.X` 3줄을 추가했다 — 기존
Amendment B 4필드(`content_genre`/`authority_class`/`tradition`/`theological_category`)와
완전히 동일한 코드 패턴.

**질문**: 이 패턴이 실제로 "필드 미지정 시 기존과 byte-identical 출력"을 보장하는가 — 직접
`git diff` 로 `pipeline.py`를 확인하고, Amendment B 필드 처리 블록과 나란히 대조해 구조적으로
동일한지 확인 요망.

### 2. `m2_source_registry_validator.py` — V9-V12 신규 검사

`check_authority_tier_fields()` 단일 함수가 V9(tier/tradition_relation vocab),
V10(T3→counter_refs 필수), V11(a: orphan 금지, b: 대상 tier ∈ {T1,T2}), V12(T1/T2/T4→
counter_refs 금지)를 순차 실행한다. `validate()` 파이프라인에 `("V9-V12",
check_authority_tier_fields)` 1개 항목으로 등록됨. 어떤 M2 레코드도 신규 3필드를 갖지 않으면
전체를 skip(PASS)한다(현재 실제 M2 15개 레코드는 전부 이 경로 — 백필 전).

**질문 (핵심)**: 설계 검토(`_RESULT_002.md`)에서 GREEN 판정한 "V11(b)+V12 조합이 counter_ref
순환 참조를 구조적으로 차단한다"는 논증이, **실제 코드 로직에서도** 정확히 성립하는가?
구체적으로 `scripts/m2_source_registry_validator.py`의 `check_authority_tier_fields()` 함수
본문을 직접 읽고:
  - T3가 아닌데 counter_refs가 있으면 V12로 FAIL하는가 (T1/T2/T4 3개 tier 모두)?
  - counter_refs 대상이 M2에 없으면(orphan) V11로 FAIL하는가?
  - counter_refs 대상이 M2에는 있지만 authority_tier가 T1/T2가 아니면(T3, T4, 또는 없음) V11로
    FAIL하는가?
  - 이 3개 검사를 모두 통과하는 최소 예(T3 → T2, T2 자신은 counter_refs 없음)가 실제로 FAIL 0
    으로 PASS하는가?

이 4가지를 코드를 직접 실행하거나 정독하여 확인하고, 설계 검토 시점의 논증과 실제 구현이
일치하는지 판정해달라.

### 3. `test_m2_source_registry_governance.py` — 신규 테스트 6종

`TestAuthorityTierGovernance` 클래스에 `test_pos_08`(실제 M2 대상, 백필 전 공허 통과),
`test_neg_09`(V10), `test_neg_10`(V11a), `test_neg_11`(V11b), `test_neg_12`(V12, 3-tier
파라미터화), `test_pos_09`(정상 케이스 PASS 확인) 6종을 추가했다. `test_pos_07`과 동일하게
synthetic in-memory 레코드로 validator 함수를 직접 호출하는 패턴을 사용한다.

**질문**: 이 6종이 §2의 4가지 핵심 분기(V9-V12)를 실제로 각각 최소 1건씩 양성/음성 모두
커버하는가, 아니면 빠진 케이스가 있는가? 예를 들어 `authority_tier`가 있는데
`tradition_relation`이 없는 경우(V9의 두 번째 조건)에 대한 negative 테스트가 없는데, 이것이
누락으로 볼 사안인지 판단 요망.

### 4. Freeze 준수 확인

- M2 실제 YAML(`NAE/pipeline/registration/state/source_manifest.yaml`) 파일 자체가 이번
  커밋에서 전혀 수정되지 않았는지 `git diff --stat`로 재확인.
- `core/retrieval.py` 및 그 어떤 검색 경로 파일도 diff에 포함되지 않았는지 확인.
- Amendment D §3의 "Retrieval Engine 비접촉 게이트"를 이번 구현이 위반하지 않는지 (구현은
  M2 스키마/validator/pipeline 등록 경로에만 한정됨).

### 5. Build Report의 회귀 주장 검증

Build Report(`_BUILD_REPORT_001.md` §4)는 전체 스위트 3076 passed / 17 skipped / 2 failed를
보고하며, 실패 2건(`test_indexer_review_gate_wiring.py`,
`test_nae_pilot_human_review_intake.py`)을 "TSU 인덱스 baseline 하드코딩(3319) vs 실제 디스크
상태(8936) 불일치, 본 구현과 무관"으로 분류했다.

**질문**: 이 2건이 실제로 이번 구현(3개 코드 파일 diff)과 무관한지 — 해당 실패 테스트 파일이
diff에 포함된 5개 파일과 import/의존 관계가 있는지 확인하고, 무관하다면 그 판단에 동의하는지,
그렇지 않다면 어떤 연결고리를 놓쳤는지 지적해달라.

---

## 요청 형식

- 판정: 각 항목(1-5)에 대해 **PASS / CONCERN / FAIL** 중 하나, 근거 포함
- 전부 PASS(또는 CONCERN이 사소하여 즉시 반영 가능)면 **종합 판정 GREEN** — B3 충족, B4(HQ
  최종 승인) 요청 단계로 진행
- 하나라도 FAIL이면 구체적으로 무엇을 고쳐야 하는지 명시 — 재구현 후 다시 요청
- 산출물: `docs/NAE_AUTHORITY_TIER_M2_TAGGING_C1_REVIEW_RESULT_003.md`
- PLAN MODE only — 코드/문서 직접 수정 금지, 반영은 CUE가 한다
- 결과 문서 상단에 `git rev-parse HEAD` 등 본인 세션의 실제 git 상태를 그대로 남길 것 (과거
  `_RESULT_002.md`에서 stale HEAD 보고가 있었던 사례 — CUE가 사후 검증으로 발견·기록함 —
  재발하지 않도록 주의)

## 게이트

- 종합 GREEN + HQ 최종 승인(B4) → Amendment D가 **APPROVED**로 승격 (4조건: 구현 완료·회귀
  통과·C1 리뷰·HQ 승인 전부 충족).
- 승격 이후에도 Plan 001 §6-§8(실제 M2 backfill, `corpus_admissions.jsonl` 태깅)은 이번
  구현 범위 밖 — 별도 HQ 결정·별도 작업으로 진행.
