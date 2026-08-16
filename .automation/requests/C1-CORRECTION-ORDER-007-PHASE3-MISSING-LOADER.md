# C1 Correction Order 007 — Phase 3: READY 큐를 채우는 경로 누락

| | |
|---|---|
| Issued by | CUE 독립 검증 (2026-08-16 15:xx CDT) |
| Continues | `C1-TASK-ORDER-PHASE3-COMPLETION.md` |
| 판정 | Work 1(PASS, 31/31 테스트 재실행 확인) / Work 2(부분 PASS — 구조는 맞으나 빈틈 있음) / Work 3(불가능한 상태였음 — 근본 원인 발견) |

---

## 확인된 사실

`--worker-mode`를 CUE가 직접 실행:
```
$ python3 -m NAE.pipeline.tsu.runner --worker-mode
{"worker_mode": true, "ready_candidates": 0, "processed": 0, "message": "No READY candidates in queue."}
```

`NAE/pipeline/tsu/worker/worker.py` 전체를 grep해도 실제 NAE candidate를
`READY` 상태로 state store에 써 넣는 함수가 없다. `--worker-mode`는
소비(consume) 쪽만 연결됐고, 생산(populate) 쪽이 없다 — 그래서 Work 3
(실제 실행 검증)의 evidence가 없었던 것으로 보인다(추정 — C1이 직접
확인해서 맞는지 답하라).

## 요구 조치

### 1. Loader 함수 추가

`worker.py` 또는 신규 파일(`worker/loader.py`)에 다음을 추가:

```python
def enqueue_from_canonical(identifier: str, state_store: TSUExtractionStateStore,
                            max_candidates: int | None = None) -> int:
    """parser.build_candidates()로 실제 candidate를 뽑아 READY 상태로 큐에 넣는다.
    이미 READY/PROCESSING/... 상태인 candidate_id는 건드리지 않는다(멱등).
    반환값: 새로 READY로 추가된 candidate 수.
    """
```

- 기존 `parser.py`의 candidate 추출 로직을 재사용해라(재구현 금지).
- candidate_id는 결정적으로(deterministic) 생성해라(같은 candidate가
  같은 id를 갖도록 — 예: identifier+page+paragraph+sentence 해시).

### 2. `runner.py`에 연동

`--worker-mode`가 큐가 비어있을 때 자동으로 채우지 않게 해라(그건 또
다른 암묵적 자동화다). 대신 별도 옵션을 추가해라:

```
--enqueue <identifier>   : 지정 identifier의 candidate를 READY로 큐에 채운다
```

`--enqueue`와 `--worker-mode`는 별개 호출이어야 한다(한 커맨드에서 자동
연쇄 금지 — 사람이 두 단계를 명시적으로 거치게).

### 3. Work 3 실제 실행 검증 (이번엔 진짜로)

Fuller_Complete_Works_Vol01은 이미 끝났으니 재사용 금지. Vol02-08 중
**아무거나 하나에서 수십 개 candidate만** 골라서:

```bash
python3 -m NAE.pipeline.tsu.runner --enqueue Fuller_Complete_Works_Vol02 --max-candidates 20
python3 -m NAE.pipeline.tsu.runner --worker-mode
```

- 정상 candidate가 CONFIDENCE_CLASSIFIED까지 가는지
- 의도적으로 실패를 유발한 candidate가 FAILED에서 멈추고 자동 재시도
  안 되는지(`--worker-mode`를 다시 돌려도 FAILED 그대로인지 확인)
- `--retry-failed <실제id>`로 명시 재시도했을 때만 READY로 돌아가는지

전부 raw command + output으로 evidence에 남겨라. **20개 정도로 제한해라
— Vol02 전체를 다 돌리지 마라**(그건 대량 처리이고 이번 작업 범위 밖).

## 절대 하지 말 것 (반복)

```
❌ --worker-mode가 큐를 자동으로 채우게 만들기(암묵적 자동화)
❌ FAILED 자동/일괄 재시도
❌ Vol02-08 전체 배치 실행
```

## Evidence

`.automation/evidence/night-shift/corpus-factory-transition/phase3-completion/`
에 `enqueue-execution.log`, `worker-mode-execution.log`,
`retry-failed-execution.log` 각각 추가해라.
