# NAE Pilot Migration Validation Report 001

**Project:** NAE-PILOT-MIGRATION-VALIDATION-001
**작성일:** 2026-08-05
**성격:** Validation — Production Migration 아님. 실제 Pilot Manifest
(`resources/theological_sources/manifest/pilot/**`, 10 entries)를
대상으로 Migration Engine을 실행했으나, **발견된 결함으로 인해 실행
결과는 즉시 `git checkout`으로 되돌렸다**(§4). Registry(`authority/**`)/
RAW/TSU/Embedding/Retrieval/Vector/Benchmark는 전혀 건드리지 않음.
**Git Commit/Push:** 미수행.

---

## 0. 결론 먼저

**이번 검증에서 Migration Engine의 State Machine/Checkpoint/Lock/
Audit/Idempotency/Rollback 자체는 전부 설계대로 정확히 동작함을
확인했다.** 그러나 그 과정에서 **Manifest Adapter(`build_touch_unit`)
가 실제 Pilot Manifest 파일의 주석과 YAML 포맷을 통째로 파괴하는
결함을 발견**했다 — 이는 Migration Unit이 "Audit 필드만 갱신한다"고
설계 문서(§Manifest Adapter 역할)에서 명시한 범위를 벗어난 **의도치
않은 부작용**이다. 실제 파일은 `git checkout`으로 즉시 원상 복구했다
(§4). **이 결함이 수정되기 전까지 Manifest Adapter를 실제 Production/
Pilot 데이터에 다시 실행해서는 안 된다.**

---

## 1. 실행 개요

| 항목 | 값 |
|---|---|
| 대상 | `resources/theological_sources/manifest/pilot/{dagg,fuller,hiscox}/manifest.yaml` (3 파일, 10 entries: dagg 1 + fuller 8 + hiscox 1) |
| Registry 조회 | `resources/theological_sources/authority/` — **READ-ONLY**(FK 교차 검증용, MigrationUnit 생성 대상 아님) |
| Migration Version | `pilot-validation-1.0.0` |
| Engine 상태 저장소 | 세션 scratchpad(리포지토리 밖) — `checkpoints/`, `lock.json`, `audit.jsonl` |
| Migration Unit 수 | 3(파일 단위) |
| Execution Time(Phase 2, 실제 쓰기) | 약 0.01초 미만(3개 파일, 로컬 SSD 기준) |

---

## 2. Phase별 결과

### Phase 1 — Dry Run

```
[dagg]   PASS: 변경 예정(old sha256=6ad8a768.. -> new sha256=4ceebfd9..)
[fuller] PASS: 변경 예정(old sha256=07a328a4.. -> new sha256=aea89504..)
[hiscox] PASS: 변경 예정(old sha256=49dc582a.. -> new sha256=c6b241c8..)
```

**실제 쓰기 없음 확인**(Dry Run 전/후 파일 바이트 완전 동일 — 코드
assert로 검증).

### Phase 2 — Execute(10 Pilot entries)

```
[dagg]   PASS=1 FAIL=0 entries=1
[fuller] PASS=1 FAIL=0 entries=8
[hiscox] PASS=1 FAIL=0 entries=1
합계: 10/10 entries 처리(Migration Unit 3개, entry 10개)
FK broken (Registry 대조): 0건
Registry git status(변경 없어야 함): '' (빈 문자열 — 미변경 확인)
```

### Phase 3 — Validator Regression(즉시 재실행)

```
source_validator.py    : PASS=89  WARNING=0  FAIL=0  (기존 기준선과 동일)
manifest_validator.py  : PASS=138 WARNING=0  FAIL=0  (기존 기준선과 동일)
authority_validator.py : PASS=128 WARNING=26 FAIL=0  (기존 기준선과 동일)
Drift: {source_validator: False, manifest_validator: False, authority_validator: False}
```

**Drift = 0 확인.**

### Phase 4 — 재실행(Idempotency)

```
[dagg]   skipped=1 pass=0
[fuller] skipped=1 pass=0
[hiscox] skipped=1 pass=0
```

**10/10 entries가 포함된 3개 Migration Unit 전부 no-op — Idempotency
확인.**

### Phase 5 — 강제 VERIFY 실패 → Rollback 검증

원본 파일 3개를 사전에 캡처해둔 **진짜 원본 바이트**로 별도 스크래치
사본을 만들고, 그 사본에 대해 `verify_hooks`로 강제 실패를 주입해
COMPLETE 이전(MIGRATING→VERIFYING 단계) Rollback이 실제로 원본을
복원하는지 확인했다(§3 "왜 사본을 썼는가" 참고):

```
[dagg]   fail=1 warn=1 restored_matches_original=True
[fuller] fail=1 warn=1 restored_matches_original=True
[hiscox] fail=1 warn=1 restored_matches_original=True
```

**3/3 Rollback PASS — 복원된 내용이 원본과 바이트 단위로 완전 일치.**

---

## 3. 왜 Phase 5는 사본(scratch copy)에서 실행했는가

Phase 2/4에서 이미 실제 3개 파일에 대해 `updated_at` touch Migration
Unit이 COMPLETE 상태에 도달했다. 설계 문서(State Machine 역행 규칙,
`NAE_METADATA_MIGRATION_STATE_MACHINE.md` §3)에 따르면 **COMPLETE
이후에는 같은 Migration Unit을 자동 Rollback 대상으로 삼지 않는다** —
그 상태에서 실제 파일에 새로운 실패를 강제로 유도하면 "COMPLETE된
파일을 다시 흔드는" 것이 되어 검증 목적(Rollback이 원본을 정확히
복원하는가)과 부합하지 않는다. 따라서 Phase 2 이전에 캡처해 둔 **진짜
원본 바이트**를 별도 사본에 심어, 그 사본에서 새 Migration Unit(다른
migration_version)을 강제 실패시켜 Rollback 메커니즘 자체(체크섬 대조 +
파일 복원)를 검증했다 — 이는 Rollback 로직 자체는 실제 파일 여부와
무관하게 동일하게 동작하므로(Engine이 파일 경로만 다룰 뿐 "이게 진짜
Pilot 파일인지"는 모름), 검증의 엄밀성을 해치지 않으면서 실제 데이터의
추가 변경을 피하는 더 안전한 방법이다.

---

## 4. 발견된 결함(Critical) — 실제 파일 즉시 원상 복구

Phase 2 실행 직후 `git diff`로 실제 변경 내용을 확인한 결과, 다음과
같은 **의도하지 않은 대규모 부작용**을 발견했다:

```diff
- # NAE Manifest Pilot — Dagg (monograph) — NAE-MANIFEST-PILOT-IMPLEMENTATION-001
- #
- # Pilot namespace(...) — 실제 운영 Manifest 위치가 아니다...
- schema_version: "1.0.0"
+ schema_version: 1.0.0
  manifests:
- - manifest_id: BAP-CHURCH-DAGG-001
+ - manifest_id: BAP-CHURCH-DAGG-001
    ...
-   updated_at: "2026-08-03T00:00:00Z"
+   updated_at: '2026-08-05T00:00:00+09:00'
```

**원인**: `scripts/adapters/manifest_adapter.py`의 `build_touch_unit`
내부 `transform`이 `yaml.safe_dump()`로 파일 전체를 재직렬화한다 —
`updated_at` 필드 하나만 바꾸려는 의도였지만, 실제로는:

1. 파일 상단의 모든 주석(`#`로 시작하는 설명, ADR 근거 링크 등)이
   전부 삭제됨
2. `schema_version: "1.0.0"`(따옴표로 감싼 문자열)이
   `schema_version: 1.0.0`(따옴표 없는 형태)로 재작성됨(우연히 잘못된
   float 파싱을 유발하지는 않았으나, 형식이 변경되는 것 자체가 문제)
3. 리스트 들여쓰기 스타일이 전체적으로 바뀜(`- key:` 두 칸 들여쓰기 →
   `- key:` 들여쓰기 없음)

이는 이 Adapter를 설계한 원칙("FK 필드는 절대 건드리지 않는다", 즉
"오직 지정된 필드만 바꾼다"는 의도)의 **문서화되지 않은 이면**을
드러낸다 — FK는 안 바뀌었지만, 그 파일에 있던 사람이 쓴 주석과 서식은
전부 사라졌다. Registry Adapter(`build_canonical_id_backfill_unit`)도
동일한 `_serialize()` 방식을 쓰므로 **같은 결함을 잠재적으로 갖고
있다**(단, 이번 검증에서는 Registry에 실제로 실행하지 않았으므로 실증
피해는 없음 — §Strictly Forbidden 준수).

### 조치

```bash
$ git checkout -- resources/theological_sources/manifest/pilot/
$ git status --short resources/theological_sources/manifest/pilot
(출력 없음 — 원상 복구 확인)
```

**3개 실제 Pilot Manifest 파일 전부 Migration 실행 이전 상태로 완전
복구했다.** 최종 `git status`/`git diff --stat` 둘 다 빈 결과 확인.

---

## 5. Success Criteria 대조

| 기준 | 결과 |
|---|---|
| 10/10 migrated | **PASS**(데이터 관점 — FK/필드 값은 정확히 반영됨) — 단 §4의 서식 부작용 동반, 실제 파일은 복구됨 |
| 10/10 verified | **PASS**(manifest_validator PASS=138/0/0, 기존과 동일) |
| 10/10 idempotent | **PASS**(Phase 4, 3개 Unit 전부 skipped) |
| Rollback PASS | **PASS**(3/3, 사본 기준 바이트 단위 완전 복원) |
| Validator Drift = 0 | **PASS**(3개 Validator 전부 기존 기준선과 동일) |
| No Registry modification | **PASS**(`git status` 빈 결과로 확인) |
| No RAW modification | **PASS**(스크립트가 RAW 경로를 아예 참조하지 않음) |
| No TSU generation | **PASS**(TSU 관련 코드 호출 없음) |

**체크리스트 8개 항목은 전부 PASS이지만, 체크리스트에 없는 항목(주석/
서식 보존)에서 Critical 결함을 발견**했다 — 이 발견이 이번 검증의
핵심 산출물이다("Validation 목적이 정확히 이런 문제를 실행 전에
잡아내는 것"이라는 작업 취지에 부합).

---

## 6. 권고

1. **Manifest Adapter/Registry Adapter의 `_serialize`/`transform`을
   comment-preserving 방식으로 재작성하기 전까지, 두 Adapter를 실제
   Production/Pilot 데이터에 재실행하지 않는다.** 후보: `ruamel.yaml`
   (라운드트립 주석 보존) 도입, 또는 대상 필드만 정규식/라인 단위로
   패치하는 텍스트 레벨 transform으로 전환.
2. 수정 후 이번과 동일한 5-Phase 절차로 **재검증**을 반드시 수행한다
   (특히 Phase 2 직후 `git diff`로 "의도한 필드만 바뀌었는지" 사람이
   확인하는 단계를 절차에 명시적으로 추가 권고).
3. Registry Adapter의 canonical_id backfill은 아직 한 번도 실 데이터에
   실행되지 않았으므로(§Strictly Forbidden 준수, 이번엔 read-only만),
   서식 보존 수정이 완료된 뒤 별도 검증이 필요하다 — 이번 보고서가
   그 필요성의 근거다.

---

## 완료 보고

```
STATUS: COMPLETE (validation performed, critical defect found and reverted)

FILES CREATED:
docs/NAE_PILOT_MIGRATION_VALIDATION_REPORT_001.md

FILES MODIFIED (real data, reverted before end of task):
resources/theological_sources/manifest/pilot/dagg/manifest.yaml    (touched then git checkout 복구)
resources/theological_sources/manifest/pilot/fuller/manifest.yaml  (touched then git checkout 복구)
resources/theological_sources/manifest/pilot/hiscox/manifest.yaml  (touched then git checkout 복구)
최종 상태: git status --short resources/theological_sources/manifest/pilot → (빈 결과, 완전 복구)

MIGRATION UNITS: 3 (파일 단위, 10 entries 포함)

EXECUTION TIME: Phase 2 약 0.01초 미만(3 파일)

10/10 MIGRATED: YES(데이터 값 기준)
10/10 VERIFIED: YES
10/10 IDEMPOTENT: YES
ROLLBACK: PASS(3/3, 원본과 바이트 단위 일치)
VALIDATOR DRIFT: 0

CRITICAL FINDING:
Manifest Adapter의 yaml.safe_dump 재직렬화가 주석/서식을 통째로
파괴함(FK/데이터 값 자체는 정확) — 실제 파일은 git checkout으로
즉시 복구, Adapter 수정 전 재실행 금지 권고

NO REGISTRY MODIFICATION: CONFIRMED(git status 빈 결과)
NO RAW MODIFICATION: CONFIRMED
NO TSU GENERATION: CONFIRMED

GIT: NOT COMMITTED, NOT PUSHED(지시대로 대기)
```
