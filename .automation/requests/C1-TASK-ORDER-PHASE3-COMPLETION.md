# C1 Task Order — Phase 3 잔여 작업 완료 (runner.py 연동 + unit test)

| | |
|---|---|
| Issued by | CUE, on Rev. Bang's directive (2026-08-16) |
| Mission | ADR-025 Implementation Plan §4의 미완 항목 완료 |
| Continues | `docs/architecture/ADR-025-NAE-TSU-Extraction-Queue-Worker.md`(Proposed) |
| 무관 사안 | `2026-08-16-dbma-core-nae-isolation-violation` incident는 이 작업과
  완전히 독립된 별개 governance track이다 — 다시 언급하거나 섞지 마라 |

---

## 현재 상태 (재확인, 재조사 금지)

ADR-025 §4 체크리스트:

```
[x] state.py — TSUExtractionState, TSUExtractionStateStore
[x] queue.py — TSUExtractionExceptionQueue
[x] config.py — worker configuration
[x] worker.py — process_candidate, process_batch, retry_failed
[ ] test_worker.py — unit tests          <- 이번 작업 대상
[ ] runner.py 수정: worker 호출 경로 추가  <- 이번 작업 대상
[ ] CLI 옵션: --worker-mode, --retry-failed <- 이번 작업 대상
```

CUE가 `worker.py`/`state.py`를 직접 읽어 이미 검증 완료한 것(다시
확인할 필요 없음): `reset_failed_to_ready()`는 `retry_failed()`에서만
호출되고 `process_batch()`의 자동 루프는 FAILED를 기록만 함 — ADR-022 §8
"자동 재시도 금지" 준수가 코드 수준에서 확인됨. **이 부분은 건드리지
마라.**

`NAE/pipeline/tsu/runner.py`는 이미 `--identifier`, `--model`,
`--max-candidates`, `--legacy-scan` 옵션과 `main(argv)` 진입점을 갖고 있다.

---

## 작업 1 — `test_worker.py` 단위 테스트

`NAE/pipeline/tsu/worker/test_worker.py` 신규 작성. 최소한 다음을 실제
assert로 검증(서술 금지, pytest로 실행 가능해야 함):

1. `READY -> PROCESSING -> EXTRACTED -> CONFIDENCE_CLASSIFIED` 정상 경로
2. `READY -> PROCESSING -> FAILED` 경로
3. **`FAILED -> READY`가 `retry_failed()`를 거치지 않고는 절대 일어나지
   않음을 증명하는 테스트** — 이게 가장 중요하다. 예: `process_batch()`를
   FAILED 상태의 candidate로 여러 번 돌려도 상태가 자동으로 READY로
   돌아가지 않는지 확인
4. `validate_transition()`이 허용 안 된 전이(예: `CONFIDENCE_CLASSIFIED
   -> READY`)를 거부하는지
5. 멱등성: 같은 state로 다시 `set_state()` 호출 시 no-op
6. `TSUExtractionExceptionQueue`가 실패 candidate를 기록하는지, 그리고
   `NAE/review/human/exception_queue.json`(Production human-review
   queue)에는 **절대 쓰지 않는지**(state.py 자체 docstring이 명시한
   경계 — 코드로 증명해라)

실행 결과(pytest raw output, pass/fail count)를 evidence로 남겨라.

## 작업 2 — `runner.py` worker 호출 경로 추가

기존 `--identifier`/`--legacy-scan` 경로는 그대로 둔다(하위 호환,
ADR-025 §3.2 "기존 builder.py 변경 없음" 원칙). 추가할 것:

```
--worker-mode       : worker.process_batch()를 통해 처리(신규 경로)
--retry-failed <id>  : worker.retry_failed(candidate_id) 호출(사람의
                        명시적 지시로만 실행되는 CLI 진입점 — 자동화 아님)
```

`--retry-failed`는 **CLI 인자로 candidate_id를 명시적으로 받아야 한다**
— "전체 FAILED를 한 번에 재시도" 같은 일괄 자동 재시도 옵션은 만들지
마라(ADR-022 §8, ADR-025 §2.4 위반).

## 작업 3 — 실제 실행 검증 (Vol.1 production과 무관, 소규모)

`Fuller_Complete_Works_Vol01`은 이미 완료됐으니 재사용하지 마라. 대신
**아직 TSU가 없는 소규모 대상**으로 `--worker-mode`를 실제로 몇 건만
실행해서(수십 candidate 수준, 전체 볼륨 아님) 다음을 evidence로 남겨라:

- 정상 candidate가 `CONFIDENCE_CLASSIFIED`까지 도달하는지
- 의도적으로 실패를 유발한 candidate가 `FAILED`에서 멈추고 자동으로
  재시도되지 않는지(몇 분 뒤 재확인)
- `--retry-failed <id>`로 명시 재시도했을 때만 `READY`로 돌아가는지

**Fuller Vol02-08 전체를 이걸로 돌리지 마라** — 이번 작업은 wiring
검증이 목적이지 대량 처리가 목적이 아니다. Corpus Factory의 실제 대량
처리는 이 작업이 CUE 재감사를 통과한 뒤 별도 지시로 진행한다.

## 절대 하지 말 것

```
❌ core/retrieval.py, data/제련완성본/, core.processing, core.tsu_builder 접근
❌ builder.py, state.py, queue.py의 기존 검증된 로직 재작성
❌ FAILED -> READY 자동/일괄 재시도 옵션
❌ ADR-025를 Approved로 스스로 표시(CUE/Rev. Bang만 승격 가능)
❌ Fuller Vol02-08 전체 배치 실행(이번 작업 범위 아님)
```

## Evidence

`.automation/evidence/night-shift/corpus-factory-transition/phase3-completion/`에
작업 1(pytest 결과), 작업 2(git diff), 작업 3(worker-mode 실행 로그) 각각
남겨라. 완료 후 ADR-025 §4 체크리스트를 전부 `[x]`로 갱신하되 §4.3
"CUE Review"는 체크하지 마라 — 그건 CUE가 한다.
