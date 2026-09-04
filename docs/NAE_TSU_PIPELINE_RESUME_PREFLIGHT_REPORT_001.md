# NAE TSU Pipeline Resume Preflight Report 001

**Project:** NAE-TSU-PIPELINE-RESUME-PREFLIGHT-001
**작성일:** 2026-08-05
**성격:** Preflight(사전 점검) — TSU 생성, TSU Builder 실행, Pipeline
Activation, Crosswalk/Manual Mapping 생성, Metadata/Registry/Manifest/
RAW/canonical 변경, ADR 수정 전부 미수행.
**Git Commit/Push:** 미수행.

---

## 0. 결론 먼저

```
ACTIVATION STATUS: BLOCKED
```

Gate Orchestrator/TSU Gate/Crosswalk Resolver는 전부 설계·구현·테스트
완료 상태이고 정확히 동작하지만, **TSU Pipeline 진입점
(`NAE/pipeline/tsu/runner.py`)이 아직 그 Gate를 호출하도록 배선되어
있지 않다** — 그리고 설령 배선되어 있었다 해도, Crosswalk Storage에
실제 매핑이 0건이므로 모든 Manifest entry가 `TSU_GATE_BLOCK`으로
귀결된다(실측, §3). 두 가지 이유 모두 "정상적으로 막혀 있는 상태"다.

---

## 1. Phase 1 — Pipeline Entry Point 확인

### TSU Pipeline 시작점

```
NAE/pipeline/tsu/runner.py::main()
    --identifier 지정 시 → builder.build_tsu_for_identifier()
    미지정 시            → builder.build_tsu_for_all()
```

### Gate/Resolver/Storage/Builder 호출 순서(현재 실측)

```
$ grep -rn "gate_orchestrator|CrosswalkResolver|check_tsu_gate|YamlCrosswalkRepository" NAE/pipeline/tsu/*.py
(결과 없음)
```

**`NAE/pipeline/tsu/` 어디에도 Crosswalk Layer(Gate/Resolver/Storage)
를 참조하는 코드가 없다** — `build_tsu_for_all()`은 여전히
`canonical_root.iterdir()`로 identifier를 직접 열거한다(§1 재확인,
`NAE_TSU_GATE_CONNECTION_DESIGN_001.md` §3에서 이미 예견된 "미구현"
지점 그대로). 즉 **Gate가 존재해도 아직 아무도 호출하지 않는다.**

---

## 2. Phase 2 — Gate Flow 검증

설계된 흐름(`READY → Resolver → TSU Gate → PASS/BLOCK/ERROR`)이 실제
코드에서 정확히 그 순서로 동작하는지, **실제 프로덕션 Crosswalk
저장소**(`NAE/metadata/crosswalk/`, 읽기 전용 접근)를 대상으로
`GateOrchestrator.evaluate()`를 직접 호출해 확인했다(TSU 생성/Builder
호출 없음 — Gate 판정 함수만 호출):

```python
repo = YamlCrosswalkRepository("NAE/metadata/crosswalk/crosswalk.yaml", "NAE/metadata/crosswalk/index.json")
orchestrator = GateOrchestrator(repo)
result = orchestrator.evaluate(ManifestEntryInput(source_identifier="BAP-CHURCH-DAGG-001", tsu_eligible=True))
```

결과: `validate_storage() → (True, None)`(저장소 정상) →
`CrosswalkResolver.resolve_record()` 호출 → 레코드 없음 →
`check_tsu_gate()` → `TSU_GATE_BLOCK`("Crosswalk mapping 없음"). 설계된
순서(Storage Validation → Resolver → Gate) 그대로 실행됨을 확인했다.

이 흐름은 이미 `tests/test_crosswalk_gate_orchestrator.py`(10개 테스트,
PASS/BLOCK/ERROR 3경로 전부)로도 검증되어 있다 — 이번 Preflight는
그 테스트 결과를 실제 프로덕션 데이터로 재확인한 것이다.

---

## 3. Phase 3 — Activation Block 확인

```
$ grep -c "crosswalk_id" NAE/metadata/crosswalk/crosswalk.yaml
0
```

**Crosswalk Records = 0.** 실제 Pilot Manifest의 10개 `source_id`
전부(`BAP-CHURCH-DAGG-001`, `BAP-CHURCH-HISCOX`,
`BAP-MISS-FULLER-VOL01`~`VOL08`)에 대해 `GateOrchestrator.evaluate()`
를 실행한 결과:

```
BAP-CHURCH-DAGG-001:    TSU_GATE_BLOCK — Crosswalk mapping 없음
BAP-CHURCH-HISCOX:      TSU_GATE_BLOCK — Crosswalk mapping 없음
BAP-MISS-FULLER-VOL01:  TSU_GATE_BLOCK — Crosswalk mapping 없음
BAP-MISS-FULLER-VOL02:  TSU_GATE_BLOCK — Crosswalk mapping 없음
BAP-MISS-FULLER-VOL03:  TSU_GATE_BLOCK — Crosswalk mapping 없음
BAP-MISS-FULLER-VOL04:  TSU_GATE_BLOCK — Crosswalk mapping 없음
BAP-MISS-FULLER-VOL05:  TSU_GATE_BLOCK — Crosswalk mapping 없음
BAP-MISS-FULLER-VOL06:  TSU_GATE_BLOCK — Crosswalk mapping 없음
BAP-MISS-FULLER-VOL07:  TSU_GATE_BLOCK — Crosswalk mapping 없음
BAP-MISS-FULLER-VOL08:  TSU_GATE_BLOCK — Crosswalk mapping 없음

ALL 10 BLOCKED: True
```

**10/10 BLOCK 확인.** `tsu_eligible=True`(READY, 최대한 유리한 조건)
로 넣었는데도 전부 막힌다 — Crosswalk mapping 부재가 유일하고
결정적인 차단 사유임을 실측으로 증명했다. 실행 후 저장소 재확인
결과 파일 무변경(`git status --short NAE/metadata/` — `??`만, 내용
변경 없음, records 여전히 0).

---

## 4. Phase 4 — Manual Mapping Requirement 확인

`scripts/crosswalk/tsu_gate.py` 실측(코드 인용):

```python
if crosswalk_record.mapping_status != MappingStatus.MANUAL_CONFIRMED:
    return TsuGateResult(status=TsuGateStatus.BLOCK, reason=...)
...
if not tsu_eligible:
    return TsuGateResult(status=TsuGateStatus.BLOCK, reason="TSU_ELIGIBLE != READY")
```

**두 조건 다 실제 코드에 존재하며 AND로 결합**되어 있다 — 하나라도
빠지면 `BLOCK`. `mapping_status == "manual-confirmed"`(사람이 최종
확인한 매핑만)와 `TSU_ELIGIBLE == READY`(Manifest 쪽 처리 상태) 둘 다
동시에 만족해야 `PASS` 가능 — 설계 문서(`NAE_TSU_GATE_CONNECTION_
DESIGN_001.md` §1)가 아니라 **실행 가능한 코드**에서 확인했다.

---

## 5. Phase 5 — Validator Regression

```
source_validator.py --root resources/theological_sources        : PASS=89  WARNING=0  FAIL=0  (baseline 일치)
manifest_validator.py(Pilot, corpus-manifest-root 지정)           : PASS=138 WARNING=0  FAIL=0  (baseline 일치)
authority_validator.py(Production)                                : PASS=128 WARNING=26 FAIL=0  (baseline 일치)
```

**DRIFT = 0.**

---

## 6. Phase 6 — Architecture Boundary Audit

```
$ git status --short core/ scripts/adapters/ scripts/migration_engine.py \
    NAE/corpus/raw NAE/corpus/canonical NAE/corpus/tsu \
    resources/theological_sources/ docs/architecture/
(출력 없음)
```

**변경 0건 확인.**

---

## 7. Phase 7 — Pipeline Activation Readiness

```
현재 상태: BLOCKED
```

### 판정 근거

1. **배선 공백**: `NAE/pipeline/tsu/runner.py`(TSU Pipeline 유일한
   진입점)가 Gate/Resolver/Storage 어느 것도 호출하지 않는다(§1) —
   지금 `python -m NAE.pipeline.tsu.runner`를 실행하면 Gate를 완전히
   우회하고 `canonical_root.iterdir()`가 찾는 것(현재
   `PBC1742`/`PBC1765`/`SLBC1689`)을 그대로 처리하려 시도한다. 이
   Preflight는 그 배선을 추가하지 않았다(금지 목록 — TSU Builder/
   Pipeline 수정 금지).
2. **데이터 공백**: 설령 배선이 되어 있었다 해도, Crosswalk Records
   0건이므로 실제 Pilot Manifest 10건 전부가 `TSU_GATE_BLOCK`으로
   귀결됨을 실측으로 증명했다(§3).

두 공백은 **서로 다른 후속 작업**을 요구한다 — 배선 공백은 "TSU
Pipeline 진입점 수정"(코드 작업, 별도 Task Order + 이번엔 금지된
영역), 데이터 공백은 "사람이 최소 1건 이상 원문을 대조해 Crosswalk
매핑을 `manual-confirmed`로 확정하는 것"(Mapping Policy Rule 3에
따라 자동화 불가, 사람 검증 필수).

---

## Required Questions

| 질문 | 답변 |
|---|---|
| Q1. 현재 TSU Pipeline은 어디에서 시작되는가? | `NAE/pipeline/tsu/runner.py::main()` — `--identifier` 인자로 단건, 없으면 `build_tsu_for_all()`로 `NAE/corpus/canonical/` 전체 순회(§1). |
| Q2. Gate 호출 순서는 설계와 일치하는가? | **Gate 자체의 내부 흐름은 일치**(Storage Validation → Resolver → Gate, §2에서 실제 프로덕션 데이터로 재확인) — **그러나 TSU Pipeline 진입점이 아직 그 Gate를 호출하지 않는다**(§1, 배선 공백). "Gate가 설계대로 동작하는가"와 "Pipeline이 Gate를 실제로 거치는가"는 별개 질문이며, 전자는 YES, 후자는 NO. |
| Q3. Crosswalk Records가 0건이면 실제 Activation은 BLOCK되는가? | **예, 실측으로 확인.** 실제 Pilot Manifest 10개 source_id 전부, `tsu_eligible=True`(최대한 유리한 조건)로도 10/10 `TSU_GATE_BLOCK`(§3). |
| Q4. Validator Drift는 0인가? | **예.** source 89/0/0, manifest 138/0/0, authority 128/26/0 — 전부 baseline 일치(§5). |
| Q5. Architecture Boundary는 보호되고 있는가? | **예.** `core/`, `scripts/adapters/`, `scripts/migration_engine.py`, `NAE/corpus/{raw,canonical,tsu}`, `resources/theological_sources/`, `docs/architecture/` 전부 git status 빈 결과(§6). |
| Q6. 현재 상태는 READY인가, READY WITH CONDITIONS인가, BLOCKED인가? | **BLOCKED.** §7의 두 가지 독립적 이유(배선 공백 + 데이터 공백) 중 하나만 해소되어도 여전히 다른 하나 때문에 막힌다 — "조건부 준비"가 아니라 "두 가지 별도 선행 작업이 모두 필요한 완전 차단" 상태로 판단한다. |

---

## 완료 보고

```
STATUS: COMPLETE (preflight only — no TSU execution, no activation, no data changes)

FILES CREATED:
docs/NAE_TSU_PIPELINE_RESUME_PREFLIGHT_REPORT_001.md

FILES MODIFIED:
(없음)

PIPELINE ENTRY:
NAE/pipeline/tsu/runner.py::main() — Gate/Resolver/Storage 미배선 확인(grep 0건)

GATE FLOW:
Storage Validation -> Resolver -> Gate 순서 확인(실제 프로덕션 Crosswalk 저장소 대상 실행, TSU 생성 없음)

CROSSWALK RECORDS:
0

ACTIVATION STATUS:
BLOCKED (배선 공백 + 데이터 공백, 독립적인 두 원인)

VALIDATOR:
source_validator PASS=89 WARNING=0 FAIL=0
manifest_validator PASS=138 WARNING=0 FAIL=0
authority_validator PASS=128 WARNING=26 FAIL=0

DRIFT:
0

FORBIDDEN PATH CHECK:
PASS (core/, adapters/, migration_engine.py, NAE/corpus/{raw,canonical,tsu}, resources/theological_sources/, docs/architecture/ 전부 무변경)

BLOCKER:
2
  1. TSU Pipeline 진입점(NAE/pipeline/tsu/runner.py)이 Gate Orchestrator를 호출하지 않음(배선 미구현)
  2. Crosswalk Records 0건 — 사람이 검증한 manual-confirmed 매핑이 하나도 없음

WARNING:
0

NEXT STEP:
1. Crosswalk Record Population(사람이 원문 대조 후 최소 1건 이상 manual-confirmed 매핑 생성 — 별도 승인 작업, 이번 Preflight 범위 밖)
2. TSU Pipeline 진입점에 Gate Orchestrator 배선(별도 CUE 구현 Task, 이번엔 금지 영역)
3. 위 2개 완료 후 C1 TSU Pipeline Activation Review → 실제 Activation

GIT:
NOT PERFORMED
```
