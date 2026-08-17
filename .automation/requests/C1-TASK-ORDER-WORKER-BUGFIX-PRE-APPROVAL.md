# C1 Task Order — ADR-025 승격 전 버그 2건 수정

| | |
|---|---|
| Issued by | CUE, on Rev. Bang's directive (2026-08-17) |
| 전제 | CUE Gate 4개 전부 닫힘(Correction Order 009 완료). 이 2건 수정 후
  ADR-025를 Approved로 승격한다. |
| 범위 | 아래 2개 버그만. 다른 리팩터링·재설계 금지. |

---

## 버그 1 — `set_state()`가 `from_state` 생략 시 검증 없이 항상 성공 반환

`NAE/pipeline/tsu/worker/state.py::set_state()`:

```python
if from_state is not None:
    valid, reason = validate_transition(from_state, new_state)
    if not valid:
        return False, reason
```

`from_state`를 안 넘기면 이 블록 자체가 스킵되어 어떤 전이든 무조건
성공 처리된다.

### 요구 조치

`from_state`가 `None`이면 **현재 실제 저장된 state를 조회해서 그걸
기준으로 검증**해라:

```python
if from_state is None:
    current = self.get_state(candidate_id)
    if current is not None:
        valid, reason = validate_transition(current, new_state)
        if not valid:
            return False, reason
    # current가 None(신규 candidate 최초 생성)이면 검증 스킵 — 정상
else:
    valid, reason = validate_transition(from_state, new_state)
    if not valid:
        return False, reason
```

**주의**: 신규 candidate 최초 생성(`self._data`에 아직 없는 경우)은
검증 대상이 아니다 — 비교할 이전 state가 없다. 이 경우는 계속 허용해라.
기존 호출부(`loader.py`의 최초 READY 설정 등)가 깨지지 않는지 확인해라.

## 버그 2 — 재시도/재처리 후 이전 실패의 `error_type`/`error_message`가 metadata에 잔류

Correction Order 009 Gate 4 종결 evidence(`correction-009/gate4-closure/
target-candidate-final-state.json`)에서 실제로 확인됨: 최종 state가
`CONFIDENCE_CLASSIFIED`(성공)인데도 이전 시뮬레이션 실패의
`error_type`/`error_message`가 metadata에 그대로 남아있다.

### 요구 조치

candidate가 **새로 PROCESSING에 진입할 때**(즉 새로운 시도가 시작될
때), 이전 시도의 `error_type`/`error_message` 필드를 명시적으로
지워라. `worker.py::process_candidate()`에서 PROCESSING으로 전이시키는
지점에 다음과 같은 정리를 추가해라(정확한 위치는 코드를 보고 판단):

```python
# 새 시도 시작 — 이전 시도의 error 필드는 이번 결과와 무관하므로 제거
state_store.clear_metadata_fields(candidate_id, ["error_type", "error_message"])
```

`state.py`에 `clear_metadata_fields(candidate_id, keys)` 헬퍼를 추가해라
(지정된 key만 제거, 나머지 metadata는 그대로 — 전체 metadata를
덮어쓰지 마라).

**주의**: `FAILED` 상태로 끝난 candidate의 `error_type`/`error_message`는
당연히 유지되어야 한다(그게 실패 사유 기록이다) — **이번 시도가 새로
시작될 때만** 이전 필드를 지운다. `retry_failed()`가 `READY`로 되돌리는
시점, 또는 `process_candidate()`가 `PROCESSING`으로 들어가는 시점 중
어디서 지우는 게 맞는지는 코드 흐름 보고 판단해서 정해라 — 단, 두
군데서 중복으로 하지 말고 한 곳에서만 해라.

## 재검증 (버그 수정 후)

1. `test_worker.py`에 각 버그에 대한 신규 assert 추가:
   - 버그 1: `from_state` 생략하고 잘못된 전이(예: `CONFIDENCE_CLASSIFIED`
     상태에서 `set_state(READY)`)를 시도하면 이제 `False`가 반환되는지
   - 버그 2: FAILED→retry→재처리 성공 후 최종 metadata에 `error_type`/
     `error_message`가 **없는지**
2. `pytest NAE/pipeline/tsu/worker/test_worker.py`를 실제 실행해서 전부
   PASS하는지 raw output으로 evidence에 남겨라.
3. Correction Order 009의 Gate 4 재현 절차(FAILED 시뮬레이션 →
   `--retry-failed` → `--worker-mode` 실제 LLM)를 **한 번만** 소규모로
   다시 돌려서, 이번엔 최종 metadata에 stale error 필드가 없는지
   확인해라.

## Evidence

`.automation/evidence/night-shift/corpus-factory-transition/phase3-completion/pre-approval-bugfix/`
에 pytest 결과, git diff, 재검증 실행 로그를 남겨라.

## 완료 후

ADR-025 §4 체크리스트를 최종 갱신하고 CUE에게 최종 재감사를 요청해라.
승격 여부는 CUE/Rev. Bang이 결정한다.
