# C1 Night Shift Order 002 — NAE Production Ingestion (Registration Scope)

| | |
|---|---|
| Issued by | CUE, on Rev. Bang's approval (2026-08-15) |
| Mission | NAE RAW Corpus → Registration → Full Processing (실제 무인 실행) |
| Priority | P0 |
| Mode | Autonomous / No Questions / 장시간 Night Shift, 스스로 다음 Phase로 이어감 |
| Absorbs | `C1-CORRECTION-ORDER-002-HOST-EXECUTOR-PROCESSING-INPUT.md` (아직 적용 안 됐다면 Phase 1의 0단계로 먼저 처리) |
| Continues | `C1-TASK-ORDER-ADR023-AMENDMENT-A-HOST-EXECUTOR.md` |

NAE Retrieval Bridge 미션은 CUE 독립 재검증까지 완료되어 종료됐다(커밋
`4a3e616`) — **다시 조사하지 마라.** 목표는 이제 **NAE RAW Corpus →
Registration → Full Processing의 실제 무인 실행**이다.

---

## 범위 확정 (중요 — Rev. Bang이 이 세션에서 직접 결정함)

이 미션은 **Registration Full Processing까지만** 다룬다:

```
RAW → register_source() → Identity → Raw Preservation → Extraction
    → Source Validation → Quality Gate → QUALITY_PASSED/FAILED → evidence
```

**TSU 생성, embedding, Qdrant indexing은 이번 미션 범위 밖이다.** 이유:

- ADR-023(Approved) 자체가 "Full Processing = `register_source()`를 끝까지
  수행하는 등록 처리"로 명문화하며, "TSU Builder 핸드오프 이후 downstream
  (embedding/indexing)은 이 ADR 범위 밖 — 별도 ADR 필요"라고 적혀 있다.
- ADR-020(Approved, Incremental Embedding/Indexing)도 **이미 존재하는 TSU
  레코드**에 대해서만 embed/index한다 — 문서 자체가 "신규 원문 등록→최초
  TSU 생성" 앞단은 "아직 코드로 구현되어 있지 않다"고 명시한다.
- 즉 "새로 등록된 원문 → TSU 생성"을 잇는 코드는 **어떤 Approved ADR에도
  존재하지 않는다.** 이걸 오늘 밤 즉석으로 만드는 것은 새 아키텍처 구현
  금지 원칙 위반이다.

**따라서 TSU/embedding/Qdrant write는 이번 Night Shift에서 절대 시도하지
마라.** `register_source()`가 반환하는 `QUALITY_PASSED`까지가 이번 미션의
완료 조건이다. 그 다음 단계(TSU 생성 이하)가 필요하다고 판단되면, 코드를
쓰지 말고 그 사실만 evidence에 기록해라 — 별도 미션이다.

---

## Phase 1 — Host Executor 완성 (진행 중인 작업 이어서)

0. **Correction Order 002가 아직 반영 안 됐으면 먼저 적용한다**: n8n
   `Code — Decide Transition`이 task 파일 재작성 시 `processing_input`을
   지우는 문제를, `host_executor.py`의 `process_task()`에서 원본
   `processing_input`을 재병합하는 방식으로 고친다(n8n 노드는 무변경).
1. 성공 조건: command 실행, exit code 수집, stdout/stderr 수집, timeout,
   실패 감지, evidence 생성, review-queue routing — 전부 이미 구현돼 있다.
   재구현하지 말고, 파일럿 재실행으로 **검증**만 한다.

## Phase 2 — n8n Integration 확인

기존 `Phase E State Machine`(23노드, 라이브)이 `RECEIVED → VALIDATION_PASSED/
FAILED`를 담당하고, Host Executor가 `VALIDATION_PASSED → PROCESSING →
COMPLETED/FAILED`를 담당하는 역할 분리가 실제로 끊김 없이 동작하는지
확인한다. **워크플로우 노드를 새로 만들지 마라** — 이미 다 있다.

## Phase 3 — Single Source E2E (Registration까지만)

`NAE-REG-BAP-CHURCH-DAGG-001` 1건으로 전체 경로를 실행한다:

```
RAW → register → identity → raw preservation → extraction
    → validation/quality gate → evidence
```

**TSU/embedding/Qdrant 단계는 없다 — 위 목록이 전부다.** 실패하면 원인을
수정하고 동일 단계부터 재실행한다(Correction Order 002가 다루는 문제라면
그 지시를 따른다).

성공 조건: `NAE/pipeline/registration/state/registration_state.json`에
`BAP-CHURCH-DAGG-001` 항목이 `QUALITY_PASSED`로 실제 기록됨(exit 0).

## Phase 4 — 10 Source Production Batch (Registration까지만)

Single-source E2E가 GREEN이면 `pilot-queue-backup/`의 나머지 9건
(Fuller Vol01-08, Hiscox)을 `queue/`로 되돌려 순차 실행한다.

- `registration_state.json`을 먼저 확인해 이미 처리된 `source_id`는
  건너뛴다(중복 처리 금지 — `register_source()`의 duplicate detection도
  이중 방어선으로 그대로 작동한다).
- 1건씩 순차 처리한다(동시 실행 금지 — idempotency/lock 미검증 상태에서
  병렬 실행은 하지 않는다).
- 어느 한 건이 실패해도 **나머지 건은 계속 진행한다**(파일럿 1건과 달리,
  이번엔 서로 독립된 원문이므로 한 건의 실패가 다른 건을 막을 이유가 없다).
  실패한 건은 review-queue로 라우팅하고 계속한다.

## Phase 5 — Regression

최소한 다음을 실행한다:

- ADR-022 회귀: `.automation/evidence/night-shift/run-all-cycle.sh` 1사이클
- 기존 registration 테스트: `tests/nae/registration/`
- Production mutation 경계 확인(실행이 아니라 **검사**):
  - `git diff core/retrieval.py NAE/pipeline/registration/pipeline.py` — 0줄
  - NAE Qdrant `nae_tsu_v1` points 수 — 실행 전후 동일(embedding/indexing을
    안 건드렸으므로 당연히 동일해야 한다. 다르면 즉시 중단하고 보고 — §6)
  - TSU 코퍼스 디렉터리(`NAE/corpus/tsu/`) — git status 무변화

## Phase 6 — Overnight Continuation

Phase 5가 GREEN이면, 처리 안 된 RAW source가 더 있는지 확인한다. 현재
`NAE/corpus/raw/`에는 이번 10건이 전부다 — **10건이 모두 처리되면 이
미션은 완료다.** 새로운 RAW 원문이 추가로 발견되지 않는 한 억지로 다음
batch를 만들지 마라.

CUE는 C1의 "완료" 보고만으로 다음 단계를 승인하지 않는다. 매번:
`command → exit code → filesystem → state → evidence`를 CUE가 직접
재실행/재확인한 뒤에만 다음 Phase를 진행시킨다.

---

## 긴급 중단 조건 (이 경우에만 멈추고 보고)

- Production corpus corruption 가능성
- **Qdrant mutation 시도 자체** (이번 미션은 Qdrant를 전혀 건드리지 않는다
  — 시도된다면 그 자체가 범위 이탈이다)
- DBMA/NAE isolation violation
- state machine corruption
- irreversible destructive operation
- ADR architecture conflict (예: TSU 생성이 꼭 필요하다고 판단되는 경우)

그 외 일반적인 test failure, dependency 문제, timeout, malformed input은
C1이 스스로 수정하고 계속 진행한다.

## 최종 보고 (Phase 6 완료 시 또는 아침)

- completed phases / pending phases
- 처리된 source 수, registration 성공/실패 수
- failed/review-queue 건수
- git commit
- evidence 위치
- **production mutation = 0 (core/retrieval.py, DBMA corpus, TSU, embedding, Qdrant 전부)**
  여부 — registration_state.json/checksum ledger에 대한 등록 자체는
  ADR-021/023이 승인한 정상 mutation이므로 "0"의 대상이 아니다. 그 외
  전부가 0이어야 한다.
