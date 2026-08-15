# CUE Watch Log — ADR-023 Amendment A Host Executor Implementation

CUE는 C1(Cline)을 프로그래밍적으로 트리거하거나 상태를 실시간으로 읽을 수 없다.
이 로그는 CUE가 주기적으로 스스로 깨어나 filesystem(evidence/requests/git)을
점검한 기록이다. 완료 보고는 항상 evidence 파일과 git 상태로 직접 재검증하며,
C1의 서술만으로 PASS를 인정하지 않음 (NAE Retrieval Bridge 미션에서 이미 2회
거짓/오보고 적발 — Correction Order 001 참고).

## 2026-08-15 (kickoff)

- 선행 결정: Rev. Bang, ADR-023 Amendment A Option A(Host Executor) 채택 승인 (2026-08-15)
- Order issued: `.automation/requests/C1-TASK-ORDER-ADR023-AMENDMENT-A-HOST-EXECUTOR.md`
- Baseline:
  - `.automation/evidence/night-shift/host-executor-implementation/` — 미생성
  - `.automation/night-shift/host_executor.py` — 미생성
  - `NAE/pipeline/registration/state/registration_state.json` — 존재 여부/내용 확인 필요(파일럿 전 SHA256 기록 예정)
  - `.automation/night-shift/queue/` — 10건 대기 중 (NAE-REG-BAP-CHURCH-DAGG-001 등)
  - `git diff core/retrieval.py NAE/pipeline/registration/pipeline.py` — 비어 있음

이후 각 check-in은 이 파일 하단에 append.

## 2026-08-15 07:30 UTC — env-check PASS, host_executor.py 구현 완료

- `cli_driver-import.exit_code.txt` = 0, `raw-archive-exists` 확인 — CUE 재확인
- `host_executor.py`(152→471줄) 소스 전체 열람: state mapping table, evidence
  스키마, ALLOWED transitions 전부 작업 명령서 지시대로 정확히 구현됨
- queue/ 분리 확인: `queue/`에 Dagg 1건만, 나머지 9건은
  `pilot-queue-backup/`으로 대피 — §4/§5 정확히 준수

## 2026-08-15 07:31 UTC — 파일럿 1차: FAIL (안전, mutation 0건) → Correction Order 002

- `pilot-dagg/*-cli-driver.exit_code.txt` = 2, stderr:
  `{"error": "missing field: automation.processing_input"}`
- `register_source()` 미호출 확인: `registration_state.json` 미존재,
  `raw_checksum_ledger.jsonl` 0줄 그대로 — **fail-closed 정상 작동**
- Root cause: evidence jsonl 대조로 확정 — n8n `Code — Decide Transition`이
  task 파일 재작성 시 `automation` 객체를 `{state,failure_code,
  last_transition_id}`로 통째 교체해 `processing_input`을 지움(ADR-022 스키마만
  알던 기존 코드, ADR-023 확장 필드 보존 로직 없음)
- Correction Order 002 발행: n8n 무변경 원칙 유지, `host_executor.py`
  `process_task()`에서 병합 복구 지시
