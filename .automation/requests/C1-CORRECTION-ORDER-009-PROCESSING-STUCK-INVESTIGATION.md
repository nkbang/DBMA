# C1 Correction Order 009 — PROCESSING Terminal-State Failure: 재현 → 원인 확정 → 최소 수정

| | |
|---|---|
| Issued by | CUE, on Rev. Bang's directive (2026-08-16) |
| Continues | Correction Order 008 (경로 버그·placeholder 버그는 수정 확인됨 — 재작업 금지) |
| 판정 대상 | ADR-025는 아래 4개 항목이 evidence로 닫히기 전까지 **Approved 승격하지 않는다** |
| 모드 | **재현 → 원인 확정 → 최소 수정 → 재검증. 수정부터 하지 말 것.** |

---

## 발견된 사실 (확정된 것과 가설을 구분한다)

**확정된 사실(observed)**: CUE가 실제(non-mocked) LLM으로 `--worker-mode`를
실행한 결과, candidate 1건이 `PROCESSING`에 남고 `EXTRACTED`도 `FAILED`도
되지 않았다. `elapsed_seconds: 4.493`(정상 LLM 호출 대비 비정상적으로
짧음), `worker_exception_queue.json`은 빈 배열 — 실패 원인이 기록되지
않았다.

**아직 가설인 것(hypothesis, 확정 아님)**: `state.py`의 `set_state()`가
metadata를 overwrite가 아니라 merge하는 방식이라서, 이전 mock 테스트의
잔여 필드(`error_type: "TEST_FAILURE"` 등)와 이번 실행 결과가 뒤섞였을
가능성. **이게 원인이라고 단정하지 마라 — 확인 대상이다.**

**동시성 문제**: CUE와 C1이 같은 `worker_state.json`을 거의 동시에
건드렸다. 이번 조사부터는 **single-writer 원칙**을 지킨다 — 아래 §0 참고.

## §0 — Single-Writer 원칙 (이번 Correction 전체에 적용)

- 이 Correction 작업 동안 **CUE는 `NAE/corpus/tsu/worker_state.json`과
  `worker_exception_queue.json`을 건드리지 않는다**(읽기만 함, 이미
  아래 evidence로 보존 완료).
- C1도 이 작업 동안 **다른 목적으로 이 두 파일을 동시에 여러 프로세스가
  건드리지 않게 한다**(한 번에 하나의 worker 프로세스만 실행).

## 이미 CUE가 보존해둔 증거 (재수집 불필요)

`.automation/evidence/night-shift/corpus-factory-transition/phase3-completion/correction-009-preserved/`:
- `worker_state-BEFORE-investigation.json` — 발견 당시 전체 state store
- `worker_exception_queue-BEFORE-investigation.json` — 빈 배열이었음
- `cue-real-worker-mode-run.stdout.log` — CUE가 실행한 실제 커맨드의 raw output
- `git-diff-at-discovery.txt` — 발견 시점 전체 diff
- `discovery-timestamp.txt`

---

## Phase A — 현 상태 추가 보존 (수정 금지, 관찰만)

1. 문제의 candidate(`cand-eea68df881b336e1`)의 **전체 state transition
   history**를 재구성해라 — evidence jsonl/로그가 있으면 그걸로, 없으면
   지금까지의 evidence 파일들(`integration-test-evidence.json`,
   `phase3-bugfix-evidence.json` 등)을 시간순으로 대조해서 이 candidate가
   READY→PROCESSING→FAILED→(retry)→READY→PROCESSING까지 어떤 순서로
   움직였는지 타임라인을 문서로 만들어라.
2. `worker.py::process_candidate()`의 예외 처리 경로를 읽어라 — LLM 호출이
   실패하거나 타임아웃되면 정확히 어떤 코드 경로를 타는지, 그 경로가
   `exception_queue`에 기록하는지, `state_store`를 FAILED로 갱신하는지
   추적해서 문서로 남겨라. **아직 고치지 마라 — 읽고 기록만.**

## Phase B — 원인 분리 (재현, 새 fixture로)

3. **같은 candidate를 재사용하지 마라.** 완전히 새로운 deterministic
   candidate(예: `--enqueue`로 아직 안 쓴 identifier/구간에서 1~2건만)로
   재현을 시도해라.
4. 다음 두 실행을 **분리해서** 각각 evidence로 남겨라:
   - (B-1) mock LLM으로 정상 경로 재현(이미 여러 번 했지만, 새 candidate로
     한 번 더 — 참고용)
   - (B-2) **실제 LLM**으로 새 candidate 1건을 처리 — 이번엔 다른 프로세스가
     동시에 같은 state 파일을 건드리지 않는 상태에서 단독 실행
5. `set_state()`의 merge 동작이 실제로 원인인지 확인해라: 새 candidate를
   READY로 처음 넣을 때부터 metadata가 어떻게 누적되는지 각 단계마다
   `get_entry()`로 찍어서 로그를 남겨라(가설 검증용 — 코드 수정 아직 하지
   마라).

## Phase C — Invariant 명시적 검증

6. 다음 invariant를 실제 실행으로 증명하거나, 위반을 재현해라:
   ```
   READY → PROCESSING → (EXTRACTED | FAILED+error record)
   ```
   **정상적인 worker invocation이 끝났는데 PROCESSING에 그대로 남는
   상태는 invariant 위반이다.** 이게 재현되면 정확히 어느 코드 라인에서
   상태 갱신이 누락되는지 특정해라(try/except 블록의 어느 지점에서
   예외가 나서 state_store.set_state(FAILED)가 실행 안 됐는지 등).

## Phase D — 최소 수정 (원인이 확정된 후에만)

7. Phase C에서 원인이 확정되면, **그 원인에 대한 최소 수정만** 해라.
   예를 들어 `process_candidate()`의 try/except가 특정 예외 타입을
   놓치고 있었다면 그 예외 타입을 잡도록 고쳐라. **다음은 하지 마라**:
   - ❌ `PROCESSING → READY` 자동 recovery/timeout 추가(ADR-022 §8 위반)
   - ❌ `set_state()`를 성급하게 overwrite로 바꾸기(§6 먼저 판단 필요 — 아래)
   - ❌ stale PROCESSING을 위한 새 상태(`STALE_PROCESSING` 등) 자동 도입
     (필요하다고 판단되면 **설계 제안만** 문서로 남기고 구현하지 마라 —
     이건 CUE/Rev. Bang이 별도로 판단할 architecture 결정이다)

## Phase E — metadata merge semantics 판단 (수정 아님, 판단만)

8. 현재 metadata에 섞여 있는 필드들을 분류해라: **immutable**(candidate
   고유 정보 — source_identifier, page, text 등), **execution**(model,
   confidence_score 등 — 매 시도마다 갱신되어야 하는 것),
   **error**(error_type, error_message — FAILED일 때만 의미 있고, 성공
   시엔 지워져야 하는지 남아야 하는지), **attempt**(시도 횟수 등, 있다면).
   이 분류 결과를 문서로 남기고, merge vs overwrite 중 어느 쪽이 맞는지
   **권고만** 해라 — 이번 Correction에서 직접 바꾸지 마라.

## Phase F — 깨끗한 fixture로 최종 재검증 (mock 금지)

9. 이번 게이트의 최종 증거는 **mock이 아니라 실제 LLM**이어야 한다:
   ```
   clean candidate → --enqueue → READY → --worker-mode → 실제 LLM → EXTRACTED
   ```
   그리고 별도로:
   ```
   READY → PROCESSING → FAILED(의도적) → --retry-failed <exact-id> → READY → (재처리) → terminal state
   ```
   둘 다 raw command + output으로 evidence에 남겨라. **candidate는 몇 건
   (2~5건) 수준으로 제한해라. Vol02 전체는 여전히 금지.**

---

## CUE Gate — 아래 4개가 전부 evidence로 닫혀야 ADR-025 Approved 검토 가능

1. PROCESSING stuck 재현 여부(재현됐는지, 안 됐는지 — 어느 쪽이든 증거로)
2. 실제 원인 증명 여부(가설이 아니라 확정)
3. 실제 LLM에서 candidate가 terminal state(EXTRACTED/FAILED)에 도달하는지
4. 의도적 실패 → `--retry-failed <candidate_id>` 경로가 실제 LLM 기준으로
   정상 작동하는지

## Evidence 저장 위치

`.automation/evidence/night-shift/corpus-factory-transition/phase3-completion/correction-009/`
신규 생성해서 Phase A~F 각각의 산출물을 순서대로 남겨라.
