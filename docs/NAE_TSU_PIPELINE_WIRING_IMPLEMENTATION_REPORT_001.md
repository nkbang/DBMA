# NAE TSU Pipeline Wiring Implementation Report 001

**Project:** NAE-TSU-PIPELINE-WIRING-IMPLEMENTATION-001
**작성일:** 2026-08-05
**성격:** C1 `NAE-TSU-PIPELINE-WIRING-REVIEW-001` 승인 설계의 실제
구현 — TSU 생성/Activation, Manual Mapping/Crosswalk Record 생성,
Metadata/Registry/Manifest/RAW/canonical/ADR 변경 전부 미수행.
**Git Commit/Push:** 미수행.

---

## 1. Summary

TSU Pipeline 진입점(`NAE/pipeline/tsu/runner.py`)의 기본 실행 경로를
Crosswalk Gate와 실제로 연결했다. 기존 `build_tsu_for_identifier`/
`build_tsu_for_all`(`builder.py`)는 **한 글자도 수정하지 않았다**
(`git diff` 0줄, §7) — 신규 파일 `NAE/pipeline/tsu/gate_adapter.py`가
Manifest → Resolver → Gate 판정을 전담하고, `runner.py`는 기본 경로가
호출하는 함수 하나만 바뀌었다.

실제 Production 데이터(Crosswalk Records 0건)로 Runner를 직접
실행해 **PASS=0 / BLOCK=10 / ERROR=0 / TSU 생성=0**을 확인했다(§4) —
설계 문서(`NAE_TSU_PIPELINE_RESUME_PREFLIGHT_REPORT_001.md`)가 예측한
결과와 정확히 일치한다.

---

## 2. Files

### 생성

```
NAE/pipeline/tsu/gate_adapter.py
tests/test_tsu_pipeline_wiring.py
docs/NAE_TSU_PIPELINE_WIRING_IMPLEMENTATION_REPORT_001.md
```

### 변경

```
NAE/pipeline/tsu/runner.py  (아래 §Q1 diff 참고 — builder.py는 무변경)
```

---

## 3. Q1. Builder는 수정되었는가?

**NO.**

```
$ git diff NAE/pipeline/tsu/builder.py | wc -l
0
```

`build_tsu_for_identifier()`/`build_tsu_for_all()` 둘 다 함수 시그니처,
본문 전부 원본 그대로다. `build_tsu_for_all()`은 `--legacy-scan` CLI
플래그로 여전히 호출 가능하게 남겨뒀다(죽은 코드로 만들지 않음).

### 변경된 것은 `runner.py`뿐(diff 요약)

```diff
+ from . import builder, config, gate_adapter   # gate_adapter 추가
+ parser.add_argument("--legacy-scan", ...)      # 구 동작 폴백 플래그 추가

+ def _run_gate_wired(model, max_candidates) -> dict:
+     manifest_entries = gate_adapter.load_manifest_entries()
+     orchestrator = gate_adapter.build_default_orchestrator()
+     gate_summary = gate_adapter.iter_eligible_identifiers(manifest_entries, orchestrator)
+     for target_identifier in gate_summary.pass_identifiers:
+         builder.build_tsu_for_identifier(target_identifier, ...)   # 기존 함수, 무수정 호출
+     return {...}

  def main(argv):
      if args.identifier:
          ...(기존 그대로, override 경로 — Gate 우회는 의도된 동작)
+     elif args.legacy_scan:
+         summary = builder.build_tsu_for_all(...)   # 구 동작 폴백
      else:
-         summary = builder.build_tsu_for_all(...)
+         summary = _run_gate_wired(args.model, args.max_candidates)   # 기본 경로 교체
```

`--identifier` 단건 지정 경로는 이번 Wiring 대상에서 **의도적으로
제외**했다 — 사용자가 특정 identifier를 명시하는 것은 "Gate를 거쳐
자동으로 고른다"는 전제 자체와 다른 명시적 override 요청이므로,
그 경로는 원래도 `canonical_root.iterdir()`를 쓰지 않아 배선 대상이
아니었다(`NAE_TSU_PIPELINE_RESUME_PREFLIGHT_REPORT_001.md` §1 Call
Graph 재확인).

---

## 4. Q2~Q4. Gate 호출/BLOCK·ERROR 분리/TSU 생성 여부(실측)

실제 Production 데이터로 Runner를 직접 실행(`python3 -m
NAE.pipeline.tsu.runner`, 인자 없음 = 기본 경로):

```json
{
  "gate_pass": 0,
  "gate_block": 10,
  "gate_error": 0,
  "gate_block_details": [
    ["BAP-CHURCH-DAGG-001", "Crosswalk mapping 없음"],
    ["BAP-MISS-FULLER-VOL01", "Crosswalk mapping 없음"],
    ... (총 10건)
  ],
  "gate_error_details": [],
  "tsu_generated": 0,
  "reports": []
}
```

- **Q2. Runner는 Gate를 실제 호출하는가?** — **예.** 위 출력이 그
  증거다 — `gate_pass`/`gate_block`/`gate_error` 필드는 Gate 판정
  결과 없이는 나올 수 없다.
- **Q3. BLOCK과 ERROR가 실제로 분리되는가?** — **예.** `gate_block`/
  `gate_error`가 별도 카운터·별도 상세 리스트(`gate_block_details`/
  `gate_error_details`)로 완전히 분리되어 있다. 저장소 손상을
  인위적으로 유도한 테스트(`tests/test_tsu_pipeline_wiring.py::
  TestIterEligibleIdentifiers::test_storage_error_outranks_block_for_
  every_entry`)로 ERROR가 BLOCK보다 우선 판정됨도 확인했다.
- **Q4. TSU 생성이 발생하지 않았는가?** — **예, 0건.** `tsu_generated:
  0`, `reports: []`. 실행 전/후 `NAE/corpus/tsu/` 디렉토리 비교 결과
  파일 변화 없음(`.gitkeep`만 존재, §7).

---

## 5. Phase 4/5 — Failure Flow / Summary Report 설계 반영 확인

| Gate 상태 | Runner 처리(실제 구현) |
|---|---|
| `TSU_GATE_PASS` | `gate_summary.pass_identifiers`에 포함 → `builder.build_tsu_for_identifier()` 호출 → `reports`에 결과 추가 |
| `TSU_GATE_BLOCK` | `gate_block_details`에 `(source_identifier, reason)` 기록, Builder 미호출 |
| `TSU_GATE_ERROR` | `gate_error_details`에 별도 기록(BLOCK과 다른 리스트), Builder 미호출, storage_error가 다른 모든 조건보다 우선 판정 |

세 상태 모두 서로 다른 identifier의 처리를 막지 않는다(설계 문서
§Phase5 내결함성 원칙 그대로 구현 — `gate_adapter.
iter_eligible_identifiers`가 entry별로 독립적으로 판정).

---

## 6. Tests

`tests/test_tsu_pipeline_wiring.py`(신규, 16개):

| 클래스 | 테스트 수 | 대상 |
|---|---|---|
| `TestIterEligibleIdentifiers` | 5 | PASS/BLOCK/ERROR 분리, ERROR 우선순위, 혼합 케이스 |
| `TestLoadManifestEntriesRealData` | 3 | 실제 Pilot Manifest 10건 로드, TSU_ELIGIBLE 상태, 실제 Storage 대상 10/10 BLOCK 재확인 |
| `TestBuilderNeverCalledForBlockedOrErrored` | 2 | Builder가 PASS identifier에만 호출됨(monkeypatch로 직접 증명), PASS 0건이면 Builder 호출 0회 |
| `TestRunnerCliDefaultsToGateWiring` | 3 | 기본 경로가 Gate-wired 함수 사용, `--legacy-scan`/`--identifier`가 각각 올바르게 Gate 우회 |
| `TestBuilderUntouched` | 2 | `build_tsu_for_identifier` 시그니처 무변경, `build_tsu_for_all` 여전히 존재·호출 가능 |
| `TestNoTsuFilesWritten` | 1 | 실제 Production 데이터 기준 실행 후 `NAE/corpus/tsu/` 파일 변화 없음 |

```
$ pytest tests/test_tsu_pipeline_wiring.py -q
16 passed in 0.21s
```

---

## 7. Regression

```
$ pytest tests/test_crosswalk*.py tests/test_tsu_pipeline_wiring.py -q
155 passed

$ pytest tests/test_source_validator_v2.py ... tests/test_crosswalk_gate_orchestrator.py \
         tests/test_tsu_pipeline_wiring.py -q
304 passed  (직전 288 + 신규 16, 감소 없음)
```

### Validator

```
source_validator.py --root resources/theological_sources        : PASS=89  WARNING=0  FAIL=0  (baseline 일치)
manifest_validator.py(Pilot, corpus-manifest-root 지정)           : PASS=138 WARNING=0  FAIL=0  (baseline 일치)
authority_validator.py(Production)                                : PASS=128 WARNING=26 FAIL=0  (baseline 일치)
```

**DRIFT = 0.**

---

## 8. Architecture Boundary(Q6 포함)

```
$ git status --short core/ scripts/adapters/ scripts/migration_engine.py \
    resources/theological_sources/ NAE/corpus/raw NAE/corpus/canonical \
    NAE/corpus/tsu docs/architecture/
(출력 없음)

$ git diff NAE/pipeline/tsu/builder.py | wc -l
0

$ grep -c "crosswalk_id" NAE/metadata/crosswalk/crosswalk.yaml
0
```

**Q6. Retrieval Architecture 보호 여부** — `core/`(Retrieval 포함) 전체
무변경, `gate_adapter.py`/`runner.py` 어디에도 `core.retrieval` import
없음 — **보호됨.**

---

## 완료 보고

```
STATUS: COMPLETE (Gate wiring implementation only — no TSU generation, no activation)

FILES CREATED:
NAE/pipeline/tsu/gate_adapter.py
tests/test_tsu_pipeline_wiring.py
docs/NAE_TSU_PIPELINE_WIRING_IMPLEMENTATION_REPORT_001.md

FILES MODIFIED:
NAE/pipeline/tsu/runner.py (기본 경로를 Gate-wired 함수로 교체, --legacy-scan 폴백 플래그 추가)

RUNNER WIRING:
기본 경로(--identifier/--legacy-scan 미지정 시) = Manifest -> Resolver -> Gate -> Builder(PASS만) 순서로 실제 연결됨. --identifier(단건 override)는 의도적으로 Gate 우회 유지, --legacy-scan은 구 동작(build_tsu_for_all 직접 호출) 폴백으로 보존.

BUILDER CHANGES:
NO — git diff builder.py = 0줄. build_tsu_for_identifier/build_tsu_for_all 시그니처·본문 전부 무수정.

GATE FLOW:
Storage Validation -> Resolver -> Gate 순서로 실제 프로덕션 데이터 대상 실행 확인(gate_adapter.iter_eligible_identifiers)

PASS: 0
BLOCK: 10
ERROR: 0

TSU GENERATED:
0 (NAE/corpus/tsu/ 파일 변화 없음, .gitkeep만 존재)

REGRESSION:
304 passed(직전 288 + 신규 16, 감소 없음)

VALIDATOR:
source 89/0/0, manifest 138/0/0, authority 128/26/0 — 전부 baseline 일치

DRIFT:
0

FORBIDDEN PATH CHECK:
PASS (core/, scripts/adapters/, scripts/migration_engine.py, resources/theological_sources/, NAE/corpus/{raw,canonical,tsu}, docs/architecture/ 전부 git status 빈 결과; builder.py diff 0줄; Crosswalk records 여전히 0건)

BLOCKER:
0

WARNING:
1 (`iter_eligible_identifiers`가 설계 문서의 `Iterator[str]` 대신 `GateWiringSummary` dataclass를 반환하도록 구체화됨 — Phase 5 Summary Report(PASS/BLOCK/ERROR 건수 + 상세)를 위해 구현 중 필요성이 확인된 인터페이스 확장. PASS identifier 목록은 여전히 포함되어 있어 원래 계약을 대체하지 않고 확장한 것으로 판단 — C1 재확인 권장)

NEXT STEP:
C1 Wiring Implementation Review 요청 → 승인 후 Phase D(Manual Crosswalk Population, 사람이 원문 대조 후 최소 1건 이상 manual-confirmed 매핑 생성) → Phase E(Activation)

GIT:
NOT PERFORMED
```
