# ADR-025: NAE TSU Extraction Queue Worker (Phase 3)

| | |
|---|---|
| Status | **Approved** (2026-08-17, Rev. Bang 최종 승인. 승격 조건 4개 전부 충족 — 구현 완료, 회귀 테스트 통과(41/41), CUE 독립 검증 완료(Correction Order 007/008/009 + 최종 버그 2건 3중 검증), 사용자 승인. 근거: `.automation/audit/NAE-TSU-PROCESSING-CONNECTION-CUE-WATCH-LOG.md` 2026-08-16~17 기록 전체) |
| Date | 2026-08-16 (초안), 2026-08-17 (승인) |
| Deciders | C1 (초안), CUE (review), Rev. Bang (승인) |
| Supersedes | — |
| Does NOT supersede | ADR-021 (Registration State Machine), ADR-022 (Automation Task State Machine) |

---

## 1. Context

현재 `builder.build_tsu_for_identifier()`는 모든 단계를 단일 함수에서 처리:

```
canonical.json -> parser.build_candidates() -> LLM claim extraction -> TSU records -> output
```

이 monolithic 구조는 다음 문제를 야기:

1. **중단 복구 불가**: 프로세스가 중단되면从头 다시 시작 (checkpointing은 있지만 queue 기반 아님)
2. **실패 격리 없음**: 한 candidate 실패가 전체 batch 차단
3. **상태 추적 불가**: candidate별 상태 전이가 명시적이지 않음
4. **재처리 불가**: 실패한 candidate를 수동으로 재처리하는 경로 없음

Phase 1 병목 분석과 Phase 2 Candidate Filtering 설계로 명확해진 요구사항:

- LLM 호출 전 deterministic filtering (Phase 2)
- 각 source가 파이프라인의 서로 다른 단계에서 동시 전진 (Corpus Factory 전환)
- 실패 격리 (한 권의 실패가 전체 corpus processing 중단하지 않음)

---

## 2. Decision

### 2.1 TSU Extraction Queue Worker 분리

`NAE/pipeline/tsu/worker/` 신규 모듈로 독립 Queue Worker 구현:

```
TSU_EXTRACTION_QUEUE: READY -> PROCESSING -> EXTRACTED -> CONFIDENCE_CLASSIFIED
실패: PROCESSING -> FAILED -> ERROR/REVIEW QUEUE
```

### 2.2 State Machine

```python
class TSUExtractionState(str, Enum):
    READY = "READY"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    CONFIDENCE_CLASSIFIED = "CONFIDENCE_CLASSIFIED"
    FAILED = "FAILED"
```

**전이 규칙**:

| From | To | 조건 |
|------|-----|------|
| READY | PROCESSING | worker 시작 |
| PROCESSING | EXTRACTED | LLM 성공 |
| PROCESSING | FAILED | LLM 실패 |
| EXTRACTED | CONFIDENCE_CLASSIFIED | 자동 confidence classification |
| FAILED | READY | **수동 재시도만** (ADR-022 section 8 준수) |

**terminal state**: CONFIDENCE_CLASSIFIED (더 이상 전이 불가)

### 2.3 Exception Queue

실패한 candidate를 human review를 위해 별도 queue에 기록:

```python
class TSUExtractionExceptionQueue:
    - candidate_id, error_type, error_message, state_at_failure
    - Never writes to NAE/review/human/exception_queue.json
```

### 2.4 Retry Policy (ADR-022 section 8 준수)

- **자동 재시도 금지**: FAILED -> READY는 명시적 human trigger만 허용
- **자동 승격 금지**: EXTRACTED -> CONFIDENCE_CLASSIFIED는 자동 (confidence classification은 deterministic, review gate 아님)
- **멱등성**: 같은 state -> 같은 state는 no-op

### 2.5 파일 구조

```
NAE/pipeline/tsu/worker/
├── __init__.py          # exports
├── config.py            # worker configuration
├── state.py             # TSUExtractionState, TSUExtractionStateStore
├── queue.py             # TSUExtractionExceptionQueue
└── worker.py            # process_candidate, process_batch, retry_failed
```

---

## 3. Consequences

### 3.1 Positive

- **실패 격리**: 한 candidate 실패가 다른 candidate 차단하지 않음
- **상태 추적 가능**: candidate별 상태 전이가 명시적
- **수동 재처리**: FAILED candidate를 human이 명시적으로 재시도
- **Corpus Factory 전환 기반**: 각 source가 파이프라인의 서로 다른 단계에서 동시 전진

### 3.2 Negative

- **추가 모듈**: worker/ 디렉터리 신규 생성 (12개 파일 추가)
- **기존 builder.py 변경 없음**: `builder.build_tsu_for_identifier()`는 그대로 유지 (backward compatibility)
- **runner.py 수정 필요**: worker를 호출하는 경로 추가 (Phase 3 구현 시)

### 3.3 Neutral

- **기존 state machine과 물리 분리**: Registration State, Automation Task State와 독립 namespace
- **confidence classification 자동**: human review는 Phase 4에서 별도 처리

---

## 4. Implementation Plan

### Phase 3.1: Worker Module 구현 (C1)

- [x] `NAE/pipeline/tsu/worker/state.py` — TSUExtractionState, TSUExtractionStateStore
- [x] `NAE/pipeline/tsu/worker/queue.py` — TSUExtractionExceptionQueue
- [x] `NAE/pipeline/tsu/worker/config.py` — worker configuration
- [x] `NAE/pipeline/tsu/worker/worker.py` — process_candidate, process_batch, retry_failed
- [x] `NAE/pipeline/tsu/worker/test_worker.py` — unit tests (41 tests, all passed)

### Phase 3.1.1: Correction Order 009 — Bugfix (CUE → C1 worker)

- [x] Bug 1: `set_state()` from_state 생략 시 검증 스킵 → 현재 state 조회로 복구
- [x] Bug 2: retry 후 stale error_type/error_message 잔류 → clear_metadata_fields() 추가
- [x] 회귀 테스트 9건 추가 (TestBugfix1 ×4, TestBugfix2 ×5)
- [x] pytest 전체 41건 PASS
- [x] Gate 4 재검증: FAILED→retry→reprocess 시 error 필드 소멸 확인

### Phase 3.2: Runner Wiring (C1)

- [x] `runner.py` 수정: worker 호출 경로 추가 (--worker-mode, --retry-failed <id>)
- [x] CLI 옵션: `--worker-mode`, `--retry-failed <id>` (candidate_id 명시적 요구)

### Phase 3.3: CUE Review (CUE)

- [x] Architecture review — state machine·retry policy 코드 직접 검토, ADR-022 §8 준수 확인
- [x] Governance check — production boundary(core/retrieval.py, DBMA corpus) 매 단계 무변경 확인, single-writer 원칙 준수
- [x] Approval gate — CUE Gate 4개 전부 닫힘(Correction Order 009), 버그 2건 3중 검증(코드/테스트/실제 LLM) 완료. Rev. Bang 최종 승인 2026-08-17

---

## 5. Appendix: State Transition Diagram

```
                    +--------+
                    | READY  |
                    +--------+
                         |
                    (worker starts)
                         v
                  +------------+
                  | PROCESSING |
                  +------------+
                     /        \
              success/          \ error
                   /              \
                  v                v
         +----------------+  +-------+
         | EXTRACTED      |  | FAILED|
         +----------------+  +-------+
                |             |
        (auto classify)  (manual retry only)
                |             |
                v             v
    +-------------------+  +------+
    | CONFIDENCE_       |  | READY|
    | CLASSIFIED        |  +------+
    +-------------------+
         (terminal)
```

---

*이 ADR은 TSU Extraction Queue Worker의 state machine, exception queue,
retry policy를 정의한다. 실제 구현은 C1이 수행하고 CUE가 독립 검증한다.*
