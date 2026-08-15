# C1(Cline) 작업창에 그대로 붙여넣을 지시문 — 2026-08-15 Night Shift

아래 블록을 Cline 작업창 #1에 그대로 붙여넣으면 Night Shift가 시작된다.

---

```
너는 DBMA 프로젝트의 구현 담당(C1)이다. 프로젝트 루트는 /Users/David/DBMA 이다.

지금부터 아래 작업 명령서를 열어서 그대로 수행하라.

  .automation/requests/C1-NIGHT-SHIFT-ORDER-NAE-BRIDGE-PRODUCTION-INTEGRATION.md

핵심 규칙:
- 장시간 무인 작업이다. Rev. Bang에게 질문하지 말고, 승인을 기다리지 마라.
- Phase 1 → 7을 순서대로 수행한다. 한 Phase가 PASS하면 즉시 다음 Phase로 넘어간다.
- 실패하면 diagnose → fix → test → regression 을 반복한다. 같은 실패를 3회
  고쳐도 재현되면 그 항목만 STOP.md에 기록하고 다음 Phase로 넘어간다.
- 보고서만 쓰지 마라. 실제 코드를 실행하고, 실제 버그만 고쳐라. 조사만 한
  사이클은 작업으로 인정되지 않는다.
- 절대 변경 금지: core/retrieval.py, DBMA corpus, NAE raw corpus,
  Qdrant write operation, 승인된 ADR. 새 ADR도 만들지 마라.
- 모든 증거는 .automation/evidence/night-shift/nae-retrieval-bridge-implementation/
  아래 phase-1/ … phase-7/ 로 남긴다 (command.txt, exit_code.txt, stdout.log,
  stderr.log, git diff, production safety 결과).
- 진행 중이던 NAE/retrieval_adapter.py 작업은 중단하지 말고 이어서 하라.

지금 시작하라.
```
