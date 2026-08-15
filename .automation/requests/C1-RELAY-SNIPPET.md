# C1(Cline) 작업창에 그대로 붙여넣을 지시문

## 릴레이 2 — Correction Order 001 (2026-08-15 07:15 UTC, 현재 유효)

```
CUE 독립 검증 결과가 나왔다. Phase 1~3은 PASS로 인정됐고, Phase 4~6은 반려됐다.

다음 파일을 열어서 그대로 수행하라.

  .automation/requests/C1-CORRECTION-ORDER-001-BRIDGE-TEST-INTEGRITY.md

요약 (상세는 위 파일):
1. (CRITICAL) tests/test_nae_retrieval_bridge_integration.py의 3개 테스트가
   docstring과 정반대다 — 전부 NaePdModuleDisabledError만 확인하고 실제
   retrieval 경로를 한 줄도 타지 않는다. monkeypatch로 module gate를 열고
   실제 bridge_query()가 Citation을 반환하는지, Citation 필드가 실제로 채워지는지
   assert 하도록 다시 써라. config.yaml 파일 자체는 절대 건드리지 마라.
2. 테스트 수를 오보고했다. payload_contract는 104가 아니라 43이고, 총계는
   136이 아니라 75다. 앞으로 pytest 출력 마지막 줄을 그대로 붙여넣어라.
3. phase-5/, phase-6/에 stdout.log와 exit_code.txt가 없다. 서술은 evidence가
   아니다. exit_code.txt에는 숫자만 적어라.
4. config.yaml이 YAML round-trip으로 주석이 전부 삭제됐다. semantics는 동일하니
   `git checkout -- config.yaml` 로 복구하고, 앞으로 모듈 토글은 반드시
   core/module_registry.set_enabled()를 써라.

이미 PASS로 인정된 것은 다시 하지 마라: bridge_query 구현, module gating,
Qdrant read-only, core/retrieval.py 무변경, research.py의 _render_nae_section().

수정 → 실제 pytest 실행 → Phase 4/5/6 evidence 재작성 → SUMMARY.md 갱신.
질문하지 말고 지금 시작하라.
```

---

## 릴레이 1 — 최초 Mission Order (2026-08-15 07:03 UTC, 전달 완료)

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
