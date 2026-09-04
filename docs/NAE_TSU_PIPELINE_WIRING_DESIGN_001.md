# NAE TSU Pipeline Wiring Design 001

**Project:** NAE-TSU-PIPELINE-WIRING-DESIGN-001
**작성일:** 2026-08-05
**성격:** Architecture Design Only — `runner.py`/`builder.py`/Gate/
Resolver/Storage 코드 무수정, TSU/Crosswalk/Manual Mapping 생성 없음,
Metadata/Manifest/Registry/RAW/canonical/ADR 변경 없음.

---

## Phase 1 — 현재 Pipeline Call Graph(실제 코드 기준)

```
NAE/pipeline/tsu/runner.py :: main(argv)
    │
    ├── --identifier 지정 시
    │       builder.build_tsu_for_identifier(identifier, model, max_candidates,
    │           canonical_root=config.CANONICAL_ROOT, raw_root=config.RAW_ROOT,
    │           tsu_root=config.TSU_ROOT)
    │
    └── --identifier 미지정 시
            builder.build_tsu_for_all(model, max_candidates_per_item,
                canonical_root=config.CANONICAL_ROOT, raw_root=config.RAW_ROOT,
                tsu_root=config.TSU_ROOT)
                │
                ├── if not canonical_root.exists(): return 빈 summary
                │
                ├── identifiers = [d.name for d in canonical_root.iterdir() if d.is_dir()]
                │       ↑ 유일한 identifier 소스 — Gate/Resolver/Storage 미참조
                │
                └── for identifier in identifiers:
                        build_tsu_for_identifier(identifier, ...)
                            │
                            ├── parser.build_candidates(identifier, canonical_root, raw_root)
                            │       ├── parser.load_canonical(identifier, canonical_root)
                            │       │       → canonical_root/identifier/canonical.json 직접 read
                            │       └── parser._find_raw_metadata(identifier, raw_root)
                            │               → raw_root/{category}/identifier/metadata.json 직접 read
                            │
                            ├── for cand in candidates:
                            │       claim.extract_claim(...)  # LLM 기반 claim 추출, TSU 레코드 구성
                            │
                            └── tsu_root/identifier/{tsu.json, tsu_report.json} 파일 쓰기
```

### 확인된 사실(작업 명령서 §현재 상태 4개 항목 재확인)

```
$ grep -rn "gate_orchestrator|CrosswalkResolver|check_tsu_gate|YamlCrosswalkRepository" NAE/pipeline/tsu/*.py
(결과 없음)
```

1. `runner.py`는 Gate를 호출하지 않는다 — **사실**(코드에 해당 import/호출 없음)
2. Resolver를 호출하지 않는다 — **사실**
3. Crosswalk Storage를 조회하지 않는다 — **사실**
4. `NAE/corpus/canonical/`을 직접 순회한다 — **사실**
   (`build_tsu_for_all`의 `canonical_root.iterdir()`, 위 Call Graph 참고)

---

## Phase 2 — Gate Injection Point 분석

`canonical_root.iterdir()` 호출이 유일한 identifier 소스라는 것이
이미 확인됐으므로(§1), 후보는 그 호출을 **감싸는 위치**를 기준으로
나눈다.

| 후보 | 위치 | 변경 규모 | 장점 | 단점 |
|---|---|---|---|---|
| **A. Runner 앞** | `runner.py::main()` 진입 직후, `builder.build_tsu_for_all()` 호출 전 | Runner 함수 시작부에 판정 로직 삽입 | CLI 레벨에서 가장 이른 시점에 차단 가능 | `--identifier` 단건 실행 경로와 `build_tsu_for_all` 경로 **2곳**에 각각 삽입해야 함(중복 로직 위험) |
| **B. Runner 내부(단일 지점)** | `main()` 안에서 두 분기(`--identifier` 유무)가 합류하는 지점을 만들어 그곳에 삽입 | 현재 두 분기 구조를 하나로 재구성해야 함(더 큰 변경) | 중복 없이 1곳에서 처리 | Runner의 기존 분기 구조 자체를 바꿔야 하므로 "최소 변경" 원칙과 충돌 |
| **C. Builder 앞** | `builder.py`에 새 함수(예: `build_tsu_for_eligible()`)를 추가해 `build_tsu_for_all`을 대체 | Builder 모듈에 함수 1개 추가, 기존 2개 함수는 무수정 | `build_tsu_for_identifier`(핵심 로직)는 완전히 그대로 재사용, Runner도 새 함수 하나만 호출하도록 1줄만 바뀜 | Builder 모듈 파일 자체는 수정(단, 기존 함수 무수정 — "수정 없음"의 해석 범위 문제, §Recommended에서 명확화) |
| **D. Builder 내부** | `build_tsu_for_all()` 함수 본문의 `canonical_root.iterdir()` 줄만 교체 | 가장 작은 diff(한 줄) | 변경 규모 최소 | **기존 함수 자체를 수정**하게 되어 "Builder 무수정" 원칙에 정면으로 위배 — `build_tsu_for_identifier`(claim 추출 핵심 로직)까지 같은 파일에 있어 향후 회귀 위험이 그 함수까지 번질 소지 |

### 비교 결론

**Option D는 명령서의 "Builder 내부는 수정하지 않는 것을 원칙으로
한다"(Phase 3)를 직접 위반**하므로 제외. **Option A/B는 Runner의
기존 분기 로직을 건드리거나 중복시켜야** 해서 "최소 변경"과
어긋난다. **Option C가 가장 균형적** — Builder **모듈에 새 함수를
추가**하되(파일은 열지만 "추가"이지 "기존 함수 수정"이 아님)
`build_tsu_for_identifier`/`build_tsu_for_all` 기존 2개 함수는 문자
그대로 무수정으로 남길 수 있다.

---

## Phase 3 — Recommended Wiring Architecture

```
Runner(runner.py::main())
    │  (1줄 변경: build_tsu_for_all() 호출을
    │   build_tsu_for_eligible_all() 호출로 교체 — 아래 §Q2 참고)
    ▼
Gate Orchestrator(scripts/crosswalk/gate_orchestrator.py, 기존, 무수정)
    │  ManifestEntryInput(source_identifier, tsu_eligible) 단위로 평가
    ▼
Crosswalk Resolver(scripts/crosswalk/resolver.py, 기존, 무수정)
    │  source_identifier -> target_identifier(= corpus/TSU identifier) 조회
    ▼
TSU Gate(scripts/crosswalk/tsu_gate.py, 기존, 무수정)
    │  PASS/BLOCK/ERROR 판정
    ▼
Eligible Identifier Iterator(신규 — Builder 모듈에 함수로 추가, §Phase2 Option C)
    │  PASS로 판정된 target_identifier만 모아 리스트로 변환
    ▼
Builder(build_tsu_for_identifier(), 기존, 무수정)
    │  기존 claim 추출 로직 그대로
    ▼
TSU(tsu_root/identifier/tsu.json)
```

**핵심 설계 결정**: 새로 추가되는 "Eligible Identifier Iterator"는
Manifest 목록(어디서 오는지는 §Q4/미해결 항목 참고)을 순회하며 각
entry에 대해 `GateOrchestrator.evaluate()`를 호출하고, `PASS`인
것만 `target_identifier`를 모아 기존 `build_tsu_for_identifier()`에
넘기는 **얇은 어댑터 함수**다 — Gate/Resolver/Storage/Builder 4개
기존 모듈 중 어느 것도 내부 로직을 바꾸지 않는다.

### 미해결로 남기는 것(Interface Contract에서 별도 명시)

"Manifest 목록을 어디서 가져오는가"(즉 `ManifestEntryInput`을
생성하는 데이터 소스)는 이번 설계에서 확정하지 않는다 — 실제
Manifest 파일(`resources/theological_sources/manifest/`)을 읽는
것은 자연스러운 선택이지만, 그 read 코드가 어느 모듈에 위치할지
(Builder 신규 함수 안? 별도 신규 모듈?)는 Phase C(Gate Wiring
Implementation) 단계의 구현 세부사항으로 이관한다 — 이번 문서는
"Manifest → Gate Orchestrator" 화살표까지만 아키텍처로 확정한다.

---

## Phase 4 — Interface Contract(정의만, 구현 없음)

### Gate Orchestrator

```
입력:  ManifestEntryInput(source_identifier: str, tsu_eligible: bool)  # 기존 dataclass, 무수정
출력:  TsuGateResult(status: TsuGateStatus[PASS|BLOCK|ERROR], reason: str)  # 기존 dataclass, 무수정
```

(이미 구현·테스트 완료 — NAE-TSU-GATE-RELIABILITY-IMPLEMENTATION-001)

### Crosswalk Resolver

```
입력:  source_identifier: str
출력:  target_identifier: str | None (resolve())
       또는 CrosswalkRecord | None (resolve_record(), Gate Orchestrator가 내부적으로 사용)
```

(이미 구현·테스트 완료 — 무수정)

### Eligible Identifier Iterator(신규, 인터페이스만)

```python
def iter_eligible_identifiers(
    manifest_entries: Iterable[ManifestEntryInput],
    orchestrator: GateOrchestrator,
) -> Iterator[str]:
    """PASS 판정된 항목의 target_identifier만 순서대로 산출한다.
    BLOCK/ERROR 항목은 건너뛴다(Phase 5 Failure Flow에서 각각 로그 처리)."""
```

- 입력: `ManifestEntryInput` 목록 + 이미 구성된 `GateOrchestrator` 인스턴스
- 출력: `target_identifier`(str) 스트림 — **기존 `canonical_root.iterdir()`가
  반환하던 것과 정확히 같은 타입(문자열 identifier)이므로, Builder
  쪽은 자신이 Gate를 거친 값을 받는지 몰라도 동작한다**(치환 가능성,
  Builder 무수정을 가능하게 하는 핵심 설계 근거)

### Builder(기존, 무수정)

```
입력:  identifier: str  (build_tsu_for_identifier)
출력:  {"records": list[dict], "report": dict}
```

변경 없음 — Eligible Identifier Iterator가 산출하는 값이 기존
`canonical_root.iterdir()`가 주던 값과 타입 호환이므로 Builder는
자신이 어떤 소스에서 이 identifier를 받았는지 알 필요가 없다.

---

## Phase 5 — Failure Flow(Runner에서의 처리 정의)

| Gate 상태 | Runner 처리(설계, 구현 아님) |
|---|---|
| `TSU_GATE_PASS` | 해당 identifier를 Builder로 전달, TSU 생성 진행 |
| `TSU_GATE_BLOCK` | TSU 생성 건너뜀. Runner 출력 summary에 `"skipped_block": [...]` 목록으로 집계(사람이 왜 빠졌는지 확인 가능하도록) — **에러 아님**, 정상 종료 |
| `TSU_GATE_ERROR` | TSU 생성 건너뜀 + Runner가 **경고 수준으로 강조 출력**(`"storage_errors": [...]`) — BLOCK과 같은 카운터에 섞지 않는다(Crosswalk Storage 자체가 손상됐을 가능성이 있으므로 사람이 즉시 알아채야 함). Runner의 종료 코드(exit code)를 BLOCK과 다르게 할지는 구현 단계에서 결정(이번 설계는 "구분해서 보고해야 한다"까지만 확정) |

세 상태 모두 **Runner가 TSU 생성 자체를 중단시키지 않는다** —
`ERROR`가 하나 있어도 다른 identifier가 `PASS`면 그 identifier는
정상 처리된다(단일 항목의 저장소 조회 실패가 전체 배치를 막지
않도록, 기존 `build_tsu_for_all`이 항목별로 독립 처리하는 것과
동일한 내결함성 원칙 유지).

---

## Phase 6 — Architecture Boundary Audit

| 원칙 | 확인 |
|---|---|
| Builder 수정 최소화 | **충족** — `build_tsu_for_identifier`/`build_tsu_for_all` 2개 기존 함수 완전 무수정, 신규 함수 1개만 추가(§Phase2 Option C) |
| Resolver 책임 유지 | **충족** — `CrosswalkResolver`는 이번 설계에서 무수정, "identifier translation only" 책임 그대로(`NAE_TSU_GATE_CONNECTION_DESIGN_001.md` §2 재확인) |
| Gate 책임 유지 | **충족** — `check_tsu_gate()`/`TsuGateStatus` 무수정, PASS/BLOCK/ERROR 판정 로직 그대로 |
| Storage 책임 유지 | **충족** — `YamlCrosswalkRepository`/`validate_storage()` 무수정, YAML authoritative 원칙 그대로 |
| Retrieval 무영향 | **충족** — 이번 설계 어디에도 `core/retrieval.py` 참조 없음(git status로 무변경 재확인, §종합) |
| Migration Engine 무영향 | **충족** — `scripts/migration_engine.py`/`scripts/adapters/` 참조 없음(동일 재확인) |

---

## Phase 7 — ADR Impact Analysis

| ADR | 검토 | 결론 |
|---|---|---|
| ADR-001(Retrieval Authority) | Wiring은 TSU Builder 이전 단계에서 끝남, Retrieval 코드 비접촉 | 영향 없음 |
| ADR-014(Modern Corpus Layer) | Pilot corpus(legacy 유입분) 대상 설계 — Modern Corpus 유입 규칙과 무관 | 영향 없음 |
| ADR-015(Corpus Ingestion Standard) | 아직 미구현(Proposed, 승격 보류) — 이번 설계가 그 실행에 의존하지 않음 | 영향 없음 |
| ADR-016(Metadata Authority Model) | Gate Orchestrator는 Registry를 직접 읽지 않고 Crosswalk을 통해서만 간접 참조 | 영향 없음 |
| ADR-017(ID Governance) | canonical_id/legacy_id는 Gate 판정에 쓰이지 않음(`NAE_TSU_GATE_CONNECTION_DESIGN_001.md` §1 재확인) | 영향 없음 |
| ADR-018(Periodical Extension) | Gate Contract가 Monograph/Periodical 구분 없이 동일 적용(기존 설계와 일관) | 영향 없음 |
| ADR-019(Manifest Lifecycle) | "Manifest 목록을 어디서 가져오는가"가 미해결로 남아있음(§Phase3) — 그 read 코드가 Manifest 파일을 직접 여는 것이라면 ADR-019가 정의한 필드를 **읽기만** 하므로 영향 없음(쓰기 없음) | 영향 없음(단, 구현 단계에서 재확인 권고) |

```
결론: No amendment required(7개 ADR 전부)
```

---

## Required Questions

| 질문 | 답변 |
|---|---|
| Q1. Pipeline에서 Gate를 삽입할 최적 위치는 어디인가? | **Builder 앞(Option C)** — Builder 모듈에 신규 함수를 추가해 Runner가 그 함수 하나만 호출하도록 1줄 교체. 기존 `build_tsu_for_identifier`/`build_tsu_for_all`은 완전히 무수정(§Phase2 비교표). |
| Q2. Builder를 수정하지 않는 설계가 가능한가? | **예.** Eligible Identifier Iterator가 산출하는 값이 기존 `canonical_root.iterdir()`가 주던 것과 동일한 타입(identifier 문자열)이므로, `build_tsu_for_identifier()`는 자신이 Gate를 거친 identifier를 받는지 전혀 몰라도 그대로 동작한다(§Phase4 Builder Contract — 입출력 시그니처 무변경). |
| Q3. Resolver 책임은 그대로 유지되는가? | **예.** 이번 설계는 Resolver를 호출하는 새 지점(Eligible Identifier Iterator 내부, Gate Orchestrator를 통해 간접 호출)만 추가할 뿐, Resolver 자체의 코드나 책임 범위(identifier translation only)는 전혀 바꾸지 않는다. |
| Q4. Gate Orchestrator는 Runner와 Builder 사이에 위치하는 것이 적절한가? | **예, 정확히는 "Runner와 Builder 사이의 신규 Eligible Identifier Iterator 내부에서" 사용된다.** Runner가 Gate Orchestrator를 직접 호출하는 게 아니라, Runner는 Iterator 함수 하나만 호출하고 그 Iterator가 내부적으로 Gate Orchestrator를 매 항목마다 호출하는 구조(§Phase3) — 이렇게 하면 Runner의 변경 폭도 최소화된다(호출 대상 함수 이름 1개만 바뀜). |
| Q5. ADR 수정이 필요한가? | **불필요.** 7개 ADR 전부 영향 없음(§Phase7). |
| Q6. 이 Wiring 설계는 Retrieval Architecture를 그대로 보호하는가? | **예.** 설계 전체가 TSU Builder 이전 단계에서 끝나며, `core/retrieval.py`를 참조하는 지점이 전혀 없다(§Phase6). |

---

## 종합 — Architecture Boundary / 데이터 변경 최종 확인

```
$ git status --short core/ scripts/adapters/ scripts/migration_engine.py \
    NAE/corpus/raw NAE/corpus/canonical NAE/corpus/tsu \
    resources/theological_sources/ docs/architecture/ NAE/pipeline/tsu \
    scripts/crosswalk/tsu_gate.py scripts/crosswalk/resolver.py \
    scripts/crosswalk/storage/yaml_repository.py
?? scripts/crosswalk/resolver.py
?? scripts/crosswalk/tsu_gate.py

$ grep -c "crosswalk_id" NAE/metadata/crosswalk/crosswalk.yaml
0(데이터 변경 0건)
```

**해석**: 위 `??` 두 줄은 "이번 Task로 새로 생긴 변경"이 아니라, 이전
작업(NAE-CROSSWALK-ADAPTER-IMPLEMENTATION-001 등)에서 만들어진 뒤
아직 한 번도 git commit되지 않은 채로 남아있는 기존 파일이다 — `M`
(modified) 표시가 아니라 `??`(untracked, 내용 자체는 이전 그대로)
이므로 **이번 설계 작업이 그 파일들을 건드리지 않았다는 점은
동일하게 유효**하다. 나머지 forbidden 경로(`core/`, `scripts/
adapters/`, `scripts/migration_engine.py`, `NAE/corpus/{raw,canonical,
tsu}`, `resources/theological_sources/`, `docs/architecture/`,
`NAE/pipeline/tsu`, `scripts/crosswalk/storage/yaml_repository.py`)
는 전부 아무 표시도 없음(무변경 확인).
