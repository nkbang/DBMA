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
