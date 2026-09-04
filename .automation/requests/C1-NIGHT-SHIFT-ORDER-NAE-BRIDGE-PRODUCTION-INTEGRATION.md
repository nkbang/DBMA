# C1 Night Shift Mission Order — NAE Production Retrieval Bridge → Production Integration & Validation

| | |
|---|---|
| Issued by | CUE, on Rev. Bang's direct order (2026-08-15) |
| Mission | NAE를 실제 Production 사용 상태에 최대한 가깝게 완성 |
| Priority | P0 |
| Mode | Autonomous / No Questions / 장시간 무인 |
| Deadline | 아침까지 |
| Design basis | `docs/architecture/ADR-024-NAE-Production-Retrieval-Bridge.md` (§A-J) |
| Continues | `.automation/requests/C1-NIGHT-SHIFT-ORDER-NAE-RETRIEVAL-BRIDGE-IMPLEMENTATION.md` (진행 중 작업을 중단하지 말고 이어서 수행) |

---

## 이번 Night Shift의 목적

n8n 자체를 개선하는 것이 아니다. **NAE Production Retrieval Bridge를 실제로
쓸 수 있는 상태로 완성**하는 것이다. C1은 Rev. Bang의 추가 질문이나 승인을
기다리지 않고, 승인된 architecture와 ADR 범위 안에서 아래 Phase를 **연속으로**
수행한다.

**보고서만 쓰지 마라. 실제 코드를 실행하라.** 실제 구현·테스트·수정이 없는
"조사 사이클"은 작업으로 인정하지 않는다.

---

## Phase 1 — 현재 구현 상태 확인

다음을 기준으로 현재 구현을 파악한다.

- `NAE/retrieval_adapter.py`
- `ui/pages/research.py`
- 관련 config / module gating (`config.yaml`의 `modules.nae_pd`, `core/module_registry.py`)
- ADR-024 및 `.automation/evidence/night-shift/nae-retrieval-bridge/`의 기존 evidence

**이미 완료된 부분은 다시 구현하거나 반복 조사하지 않는다.** feasibility 조사
(Phase 1-10)는 종료됐다 — 다시 열지 마라.

## Phase 2 — Production Retrieval Bridge 완성

`nae_pd` module이 활성화되었을 때 아래 전체 경로가 **실제로 실행되는지** 검증하고,
막히는 지점의 **버그만** 수정한다.

```
User Query
    ↓
NAE bridge (bridge_query)
    ↓
BGE-M3 embedding
    ↓
NAE Qdrant read-only retrieval (nae_qdrant:7333, nae_tsu_v1)
    ↓
NAE payload → DBMA Citation metadata mapping
    ↓
core/retrieval.py::CitationBuilder
    ↓
UI-compatible result
```

리팩터링·개선·정리는 하지 않는다. **재현된 버그만** 고친다.

## Phase 3 — 실제 Production 경계 검증

반드시 아래 7개를 실행 증거로 확인한다.

| # | 확인 항목 | 증거 방법 |
|---|---|---|
| 1 | `core/retrieval.py` 변경 없음 | `git diff core/retrieval.py` 빈 출력 |
| 2 | DBMA corpus 변경 없음 | `git status` + Production Qdrant(6333) 무접근 |
| 3 | NAE raw corpus 변경 없음 | `NAE/corpus/raw/**` mtime/`git status` 무변화 |
| 4 | NAE Qdrant는 read-only | 검증 전후 `nae_tsu_v1` points 수 동일 |
| 5 | `nae_pd` disabled 시 NAE 미노출 | `NaePdModuleDisabledError` 전파 + Qdrant 접속 로그 없음 |
| 6 | enabled 시 실제 NAE 결과 반환 | 실제 hits + latency 캡처 |
| 7 | Citation/provenance 실제 객체 반환 | `Citation` 객체 dump (`tsu_id`/`source_id`/`work_id`/`edition_id`/`metadata_provenance`) |

검증 후 `config.yaml`의 `modules.nae_pd.enabled`는 **반드시 `false`로 원복**한다.

## Phase 4 — 테스트와 회귀

- **영어와 한국어 query를 모두 포함해** 실제 retrieval을 실행한다.
- 기존 DBMA retrieval regression 실행:
  `tests/test_book_alias_resolution.py`, `tests/test_query_enhancements_full_regression.py`
- NAE benchmark regression 실행.
- 실패하면 원인을 분석하고 C1이 직접 **수정 → 테스트 → 재실행**한다.

## Phase 5 — Production blocker 제거

발견되는 실제 blocker를 우선순위에 따라 해결한다. 단 아래는 **금지**한다.

```
❌ 새로운 ADR 임의 생성
❌ 이미 승인된 ADR 재설계
❌ core/retrieval.py 구조 변경
❌ DBMA/NAE corpus 병합
❌ Qdrant write operation 추가
❌ 불필요한 n8n 구조 개선
❌ 새로운 feasibility investigation
```

ADR 변경이 정말 필요한 경우 **코드를 임의로 architecture 변경하지 말고**,
blocker와 근거를 evidence에 기록하고 그 작업만 보류한 뒤 다음으로 진행한다.

## Phase 6 — Production readiness

모든 수정 후 전체 regression을 다시 실행한다. 아래 cycle을 **더 이상 실제로 개선할
것이 없을 때까지** 반복한다.

```
implementation → test → fix → regression → evidence
```

## Phase 7 — Evidence

모든 실제 작업에 대해 아래를 `.automation/evidence/night-shift/nae-retrieval-bridge-implementation/`
아래 Phase별 디렉터리(`phase-1/`, `phase-2/` …)에 남긴다.

- 실행 명령 (`command.txt`)
- exit code (`exit_code.txt`)
- 테스트 결과 (`stdout.log`, `stderr.log`)
- 변경 파일 목록
- `git diff`
- production safety 결과 (Phase 3의 7개 항목)

마지막에 `SUMMARY.md` — Phase별 PASS/FAIL과 evidence 경로만. 서술 최소화.

---

## Autonomous continuation rule

- 하나의 Task가 **PASS하면 즉시 다음 Phase로 자동 진행**한다. 응답을 기다리지 않는다.
- 실패하면 `diagnose → fix → test → regression`을 반복한다.
- **Rev. Bang에게 질문하지 않는다.**
- 같은 실패를 **3회** 고쳐도 재현되면, 그 항목만 `STOP.md`에 기록하고 다음 Phase로 넘어간다.

## CUE의 판정 기준 (미리 알려둔다)

CUE는 C1의 "PASS / COMPLETE / GREEN" **서술을 신뢰하지 않는다.** 판정은 오직
exit code, 실제 stdout, `git diff`, Qdrant points 수, evidence 파일 실재 여부로만
한다. Phase가 끝날 때마다 CUE가 evidence를 독립 검증하고 다음 작업을 하달한다.

## 성공 조건

밤샘 동안 C1이 **실제 구현·테스트·수정 작업을 계속 수행**하는 것. 아침까지 NAE
Production Retrieval Bridge가 가능한 한 완성된 Production 상태에 도달하는 것.
