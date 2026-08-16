# C1(Cline) 작업창에 그대로 붙여넣을 지시문

## 릴레이 14 — Correction Order 007: READY 큐 채우는 경로 누락 (2026-08-16 15:xx CDT, 현재 유효)

```
Work 1(unit test 31개)은 CUE가 재실행해서 PASS 확인했다. 잘했다. 다만
--worker-mode를 CUE가 직접 실행해보니 큐가 항상 비어있었다 —
worker.py 어디에도 실제 candidate를 READY로 넣는 함수가 없어서 Work 3
(실제 실행 검증)이 애초에 불가능한 상태였다.

다음 파일을 열어서 그대로 수행하라.

  .automation/requests/C1-CORRECTION-ORDER-007-PHASE3-MISSING-LOADER.md

핵심:
1. parser.py의 기존 candidate 추출 로직을 재사용해서 READY 큐를 채우는
   함수(enqueue_from_canonical 등)를 추가해라. candidate_id는 결정적으로
   생성해라.
2. runner.py에 --enqueue <identifier> 옵션을 별도로 추가해라.
   --worker-mode가 큐를 자동으로 채우게 만들지 마라 — 두 단계를 사람이
   명시적으로 거치게 해라.
3. Vol02 중 --max-candidates 20 정도로 소규모로 실제 --enqueue ->
   --worker-mode -> (의도적 실패 유발) -> --retry-failed까지 진짜로
   실행해서 raw command+output을 evidence로 남겨라. Vol02 전체를 돌리지
   마라.

질문하지 말고 지금 시작하라.
```

---

## 릴레이 13 — Phase 3 잔여 작업 재개 (2026-08-16 15:00 CDT, 완료·참고용)

```
Incident 조사는 종결됐다(RESOLVED-OBSERVED, evidence 보존 완료) — 이건
ADR-025와 완전히 별개 트랙이니 다시 언급하지 마라. 이제 Phase 3 남은
작업을 재개한다.

다음 파일을 열어서 그대로 수행하라.

  .automation/requests/C1-TASK-ORDER-PHASE3-COMPLETION.md

핵심:
1. NAE/pipeline/tsu/worker/test_worker.py 신규 작성 — 특히 FAILED->READY가
   retry_failed()를 거치지 않고는 절대 자동으로 일어나지 않음을 증명하는
   테스트가 가장 중요하다. pytest 실제 실행 결과를 evidence로 남겨라.
2. runner.py에 --worker-mode, --retry-failed <id> 옵션 추가. retry-failed는
   candidate_id를 명시적으로 받아야 한다 — 일괄 자동 재시도 옵션은 만들지
   마라.
3. 소규모(수십 candidate) 실제 실행으로 wiring을 검증해라. Fuller Vol02-08
   전체를 이걸로 돌리지 마라 — 그건 이번 작업 범위 밖이다.

state.py/worker.py의 기존 검증된 로직(자동재시도 금지 등)은 이미 CUE가
확인했다 — 재작성하지 마라. core/retrieval.py, data/제련완성본/는 이번에도
절대 건드리지 마라.

완료 후 ADR-025 §4 체크리스트를 갱신하되 "CUE Review" 항목은 체크하지
마라 — CUE가 재감사한다.

질문하지 말고 지금 시작하라.
```

---

## 릴레이 12 — Incident Evidence Capture (2026-08-16 14:20 CDT, 완료·참고용, ADR-025와 별개)

```
Phase 3 작업과 별개로 심각한 사안이 발견됐다. CUE가 test_tsu_build.py를
실행하다가 NAE 소스(Dagg)가 DBMA 코어 프로덕션 파이프라인을 거쳐
data/제련완성본/에 이미 등록돼 있었던 걸 발견했다(2026-08-15 03:07:18,
오늘 Corpus Factory 미션과 무관한 훨씬 이전 시점). CUE가 실수로 증거보존
없이 이미 일부 삭제(data/제련완성본/original_pdf.md, 관련 임시 파일)를
실행했다 — 되돌릴 수 없다. 이제부터는 증거수집만 한다.

다음 파일을 열어서 그대로 수행하라.

  .automation/requests/C1-TASK-ORDER-INCIDENT-EVIDENCE-CAPTURE.md

가장 중요한 것:
- 정리/삭제/복구/재실행 절대 금지. scripts/ns003_nae_ingestion.py,
  ns004_build_tsu.py, test_tsu_build.py는 읽기만 해라, 실행하지 마라.
- 증거 패키지가 이미 준비돼 있다:
  .automation/evidence/incidents/2026-08-16-dbma-core-nae-isolation-violation/
  (삭제 전 documents.json 백업, 세 스크립트 스냅샷, 삭제된 결과 파일 복원본)
- 12개 조사 항목 중 몇 개는 CUE가 이미 확인해서 명령서에 적어놨다(재조사
  금지 명시함) — git history(전부 미커밋 확인됨), Qdrant/registration_state
  무영향 확인, NAE 오염 범위 Dagg 1건뿐 확인 등.
- "누가/왜 실행했는가"는 절대 추정하지 마라. 코드/로그가 말해주는 사실만
  적고, 모르면 "확인 불가"라고 정직하게 적어라.

결과는 03-C1-INVESTIGATION-REPORT.md로 저장해라. 이건 ADR-025 승인과는
완전히 별개 사안이다 — ADR-025는 계속 Proposed 상태로 둔다.

질문하지 말고 지금 시작하라.
```

---

## 릴레이 11 — Correction Order 006: 작은 잔여 이슈 (2026-08-16 13:30 CDT, 완료·참고용)

```
Correction 005 재검증 결과 핵심은 통과했다 — CUE가 phase2-upper-bound-recount.py를
직접 재실행해서 8개 Layer 카운트(852/1153/1/15/4/0/8/374)와 합집합
1,536건(28.2%)까지 전부 일치 확인했다. 잘했다.

작은 것 하나만 남았다:

  .automation/requests/C1-CORRECTION-ORDER-006-PHASE2-UNVERIFIED-SUM.md

§1 표/§4 결론의 "단순 합산 2,257건(41.4%)"이 스크립트 출력 어디에도 없고
손으로 더해도 안 맞는다(L0 포함 2407, L0 제외 1555 — 둘 다 2257이 아님).
스크립트에 실제로 계산해서 print하도록 추가하거나, 결론에 불필요하면
그 행/문장을 그냥 삭제해라(§4는 이미 1,536을 "실제 이론적 상한선"으로
쓰고 있어서 이 비교 수치가 없어도 결론엔 지장 없다). 합집합 1,536(28.2%)은
다시 손대지 마라.

이거 하나 고치면 Phase 2는 끝이다. Phase 3(TSU Extraction Pipeline 분리)로
넘어가라.

질문하지 말고 지금 시작하라.
```

---

## 릴레이 10 — Correction Order 005: Phase 2 재현 안 되는 카운트 (2026-08-16 07:15 CDT, 완료·참고용)

```
Phase 1 정정은 정확했다(Q1/Q2 잘 고침, 다시 손대지 마라). Phase 2도 설계
원칙은 좋다 — 상한선/검증효과 구분을 문서 전체에 일관되게 적용한 것 좋았다.
다만 §6 "Upper Bound 요약" 표의 카운트 2개를 CUE가 문서에 적힌 그 정규식
그대로 재현해봤더니 크게 달랐다:
- page number 패턴 매칭: 문서 291건 vs CUE 재현 1,153건
- 소문자 시작: 문서 666건 vs CUE 재현 374건
- candidate 총수(5,452)는 정확히 일치했다 — 이 2개만 문제다.

다음 파일을 열어서 그대로 수행하라.

  .automation/requests/C1-CORRECTION-ORDER-005-PHASE2-UNVERIFIED-COUNTS.md

CUE의 재현 스크립트도 참고용으로 남겨뒀다:
  .automation/evidence/night-shift/corpus-factory-transition/cue-phase2-recount.py

§6 표 8개 행 전부를 실제로 실행한 코드+raw output으로 다시 만들어서
evidence로 남기고, CUE 재현값과 차이가 나면 어느 패턴 정의가 맞는지
문서에 명확히 적어라. "~42%" 합계도 재계산하고, Layer 간 중복(겹치는
candidate)도 합집합으로 계산해서 표기해라.

§0-5, §7(설계 원칙, layer 구조, benchmark 설계)은 PASS다 — 다시 손대지
마라. §6 표만 고쳐라.

질문하지 말고 지금 시작하라.
```

---

## 릴레이 9 — Correction Order 004: Phase 1 재계산 (2026-08-16 07:05 CDT, 완료·참고용)

```
Phase 1 분석 중 계산 오류 1건과 과대해석 1건을 CUE가 발견했다.

다음 파일을 열어서 그대로 수행하라.

  .automation/requests/C1-CORRECTION-ORDER-004-PHASE1-BOTTLENECK-ANALYSIS.md

요약:
1. Q1의 "15.84s/call"은 계산 오류다. extract_claim()은 candidates_evaluated
   5,452건 전부에 호출된다(3,644건이 아니다 — 그건 결과가 있었던 건수일
   뿐). 57726.8/5452=10.59s/call로 정정해라 — 이미 같은 문서 Processing
   표에 적힌 값과 일치시켜라.
2. Q2의 "33% 절감"은 이미 검증된 효과처럼 썼는데, 1,808건이라는 숫자
   자체가 LLM을 실제로 돌려서 나온 사후 결과다. 이게 "저비용 rule로
   사전에 걸러낼 수 있다"는 증거가 아니다. "달성 가능한 상한선(benchmark
   검증 필요)"으로 정정하고, 종합결론 표의 확정형 표현도 고쳐라.

Q3-Q10은 CUE가 재계산해서 전부 정확함을 확인했다 — 다시 손대지 마라.

정정 후 Phase 2(Candidate Filtering 설계)로 넘어가라. Phase 2에서도
benchmark 없이 절감 효과를 확정형으로 쓰면 안 된다.

질문하지 말고 지금 시작하라.
```

---

## 릴레이 8 — NAE Corpus Factory 전환 (완료·참고용)

**Vol.1이 아직 완료되지 않았다면 이 블록을 붙여넣지 마십시오.** CUE가 Vol.1
완료를 자동 감지해 `PHASE0-VOL01-BASELINE.md`를 먼저 생성한 뒤 이 릴레이를
사용하라고 별도로 알려드립니다.

```
NAE Corpus Factory 전환 미션이다. 아래 파일을 열어서 §0 실행 조건부터
확인하고, Phase 1부터 순서대로 진행하라.

  .automation/requests/C1-TASK-ORDER-NAE-CORPUS-FACTORY-TRANSITION.md

핵심:
- Vol.1 baseline은 이미 .automation/evidence/night-shift/corpus-factory-transition/
  PHASE0-VOL01-BASELINE.md 에 CUE가 자동 생성해뒀다 — Phase 0을 다시 만들지
  마라, 그 파일의 실측 수치로 Phase 1(병목 분석)부터 시작해라.
- Vol.2를 그냥 순차로 다시 도는 게 아니다 — Book 단위 순차 처리를 Pipeline
  단위 동시 처리로 바꾸는 게 이번 미션이다.
- 병렬화(worker 수 변경)는 제안만 해라, 직접 실행하지 마라 — CUE 승인 필요.
- 새 ADR/schema 변경이 필요하면 C1이 만들지 말고 CUE에게 먼저 제안해라.
- core/retrieval.py, DBMA Core, 기존 Qdrant schema, ADR 경계는 절대 건드리지
  마라.
- Dashboard(http://127.0.0.1:8799)는 계속 read-only로 유지, write route
  추가 금지.
- 중요한 결과는 서술로 끝내지 말고 CUE가 재실행할 수 있는 형태(command,
  exit code, 실제 output)로 evidence를 남겨라.

Phase 1부터 시작하되, 각 Phase 끝날 때마다 CUE 검증을 기다려라(자동으로
다음 Phase까지 몰아서 진행하지 말고, 이번엔 Phase 경계마다 보고).

질문하지 말고 지금 시작하라.
```

---

## 릴레이 7 — Night Shift Order 003: TSU Processing 연결 (2026-08-15 07:58 UTC, 완료·참고용)

```
새 미션이다. 아래 파일을 열어서 그대로 수행하라.

  .automation/requests/C1-NIGHT-SHIFT-ORDER-003-NAE-TSU-PROCESSING-CONNECTION.md

가장 중요한 것 먼저: CUE가 확인해보니 등록한 10건 중 Dagg와 Hiscox는 이미
2026-08-09에 TSU 생성/embedding/Qdrant indexing이 끝나 있었다(Qdrant에 실제
포인트 존재, work_id 확인함). 게다가 그 기존 레코드의 work_id 스킴이 어젯밤
Registration이 새로 계산한 work_id와 다르다(identity 불일치). 그래서 파일럿은
Dagg가 아니라 Fuller_Complete_Works_Vol01로 해야 한다 — Dagg/Hiscox를 다시
처리하면 중복 임베딩이 생긴다. Fuller Vol01-08 8건은 TSU가 아직 없다(확인함)
— 이게 진짜 신규 처리 대상이다.

기존 컴포넌트를 그대로 재사용해라(새 코드 작성 없음, 이미 완성돼 있음):
1. python -m NAE.pipeline.tsu.runner --identifier Fuller_Complete_Works_Vol01
   (canonical.json은 이미 존재 — 추출은 끝나 있음, TSU만 생성하면 됨)
2. python scripts/nae_incremental_ingest.py --identifier Fuller_Complete_Works_Vol01
   (dry-run 먼저, 그 다음 --apply로 실제 embedding+Qdrant indexing)
3. Qdrant points 수를 실행 전후 직접 재확인해서 기록해라(스크립트 출력만
   믿지 마라).
4. 성공하면 Vol02~Vol08 순차 반복. Dagg/Hiscox는 절대 건드리지 마라.

builder.py/embedding.py/indexing.py/pipeline.py 코드는 수정하지 말고 호출만
해라. 어느 한 건이 이미 TSU가 있는 걸로 드러나면 건너뛰고 계속해라.

질문하지 말고 지금 시작하라.
```

---

## 릴레이 6 — Correction Order 003 (2026-08-15 07:45 UTC, 완료·참고용)

```
10건 파일럿/확대 실행이 전부 exit 0/QUALITY_PASSED로 나왔지만, 등록 결과가
어디에도 영구 저장되지 않는 버그를 CUE가 발견했다. pilot-summary.json에
네가 직접 "registration_state_json NOT WRITTEN"이라고 정직하게 적어놓은 건
잘했다 — 다만 원인 설명("manifest_writer가 authority 파일에 쓴다")은 틀렸다.

다음 파일을 열어서 그대로 수행하라.

  .automation/requests/C1-CORRECTION-ORDER-003-CLI-DRIVER-EPHEMERAL-STATE.md

요약 (원인은 이미 CUE가 코드로 확정했다 — 재조사하지 마라):
cli_driver.py가 매 호출마다 tempfile.mkdtemp()로 새 임시 디렉터리를 만들고
거기에 state_store와 manifest_path를 둔다 — 프로세스 종료와 함께 전부
사라진다. 수정 2건:
1. state_store를 config.DEFAULT_REGISTRATION_STATE_PATH로 바꿔라(이미
   RegistrationStateStore의 기본값으로 설계돼 있다 — 그냥 그거 써라).
2. manifest_path는 resources/theological_sources/baptist/source_manifest.yaml
   에 쓰지 마라 — 그건 사람이 큐레이션한 다른 목적의 파일이고, 지금 등록하는
   10건은 그 안에 없다. 대신 config.py에
   DEFAULT_SOURCE_MANIFEST_PATH = STATE_DIR / "source_manifest.yaml"을
   추가하고 그걸 써라(기존 CHECKSUM_LEDGER_PATH/REGISTRATION_STATE_PATH와
   같은 패턴).

수정 후 10건을 다시 처리해라 — 안전하다(같은 source_id는 duplicate로 안
잡힘, chmod는 멱등, 체크섬 원장은 append-only). 이번엔 registration_state.json
과 source_manifest.yaml에 실제로 10개 항목씩 기록되는지 evidence로 남겨라.

NAE/authority/*.yaml과 resources/theological_sources/ 아래는 절대 건드리지
마라.

질문하지 말고 지금 시작하라.
```

---

## 릴레이 5 — Night Shift Order 002: NAE Production Ingestion (2026-08-15 07:40 UTC, 완료·참고용)

```
새 장기 Night Shift 미션이다. 아래 파일을 열어서 Phase 1부터 순서대로
끝까지 수행하라. 한 Phase가 PASS하면 즉시 다음 Phase로 넘어가라. 응답을
기다리지 마라.

  .automation/requests/C1-NIGHT-SHIFT-ORDER-002-NAE-PRODUCTION-INGESTION.md

가장 중요한 것: 이번 미션은 Registration까지만 다룬다(RAW -> register_source()
-> QUALITY_PASSED). TSU 생성/embedding/Qdrant write는 절대 시도하지 마라 —
그 연결부는 어떤 Approved ADR에도 구현돼 있지 않다. 그 단계가 필요하다고
판단되면 코드를 쓰지 말고 evidence에만 기록하고 멈춰라.

순서:
0. 아직 안 했다면 릴레이 4(Correction Order 002)의 processing_input 버그부터
   고쳐라 — n8n 노드는 건드리지 말고 host_executor.py의 process_task()에서
   원본 processing_input을 재병합해라.
1. Dagg 파일럿을 다시 돌려서 registration_state.json에 실제 QUALITY_PASSED가
   기록되는지 확인해라.
2. 성공하면 pilot-queue-backup/의 나머지 9건을 queue/로 되돌려 순차 실행해라
   (동시 실행 금지, 1건 실패해도 나머지는 계속 진행).
3. ADR-022 회귀(run-all-cycle.sh) + tests/nae/registration/ + production
   mutation 경계 확인(core/retrieval.py, pipeline.py, Qdrant points 수,
   NAE/corpus/tsu/ 전부 무변화)을 실행해라.
4. 10건이 전부 처리되면 미션 완료다 — 억지로 다음 batch를 만들지 마라.

모든 증거는 .automation/evidence/night-shift/host-executor-implementation/
아래 남겨라. Qdrant mutation을 시도하게 되면(원래는 시도하면 안 되지만) 그
즉시 멈추고 STOP.md에 기록해라.

질문하지 말고 지금 시작하라.
```

---

## 릴레이 4 — Correction Order 002 (2026-08-15 07:31 UTC, 완료·참고용)

```
파일럿 1차 실행 결과가 나왔다. exit 2, "missing field: automation.processing_input"
— 그러나 register_source()는 호출 전에 막혔으므로 production mutation은 0건이다
(안전하게 fail-closed됨).

다음 파일을 열어서 그대로 수행하라.

  .automation/requests/C1-CORRECTION-ORDER-002-HOST-EXECUTOR-PROCESSING-INPUT.md

요약 (근본 원인은 이미 CUE가 evidence로 확정했다 — 재조사하지 마라):
n8n의 Code — Decide Transition 노드가 task 파일을 다시 쓸 때
`automation: {state, failure_code, last_transition_id}`로 통째로 교체해서
`processing_input`을 지운다. n8n 노드는 건드리지 마라. host_executor.py의
process_task()에서, cli_driver에 넘기기 직전에 queue_item이 갖고 있던 원본
processing_input을 task_data.automation에 다시 병합해 넣어라(양쪽 진입
경로 — webhook 신규 제출 / 이미 VALIDATION_PASSED된 task 파일 재사용 — 둘
다에서 적용되게).

수정 후:
1. NAE-REG-BAP-CHURCH-DAGG-001의 기존 task/evidence 파일을 지우고 INITIATED로
   재제출해서 파일럿을 다시 돌려라.
2. 이번에도 실패하면 멈추고 evidence만 남겨라. 성공(exit 0, QUALITY_PASSED)
   해야만 pilot-queue-backup/의 9건을 queue/로 되돌려 확대해라.

질문하지 말고 지금 시작하라.
```

---

## 릴레이 3 — Host Executor Runtime (2026-08-15 07:25 UTC, 완료·참고용)

```
NAE Retrieval Bridge 미션은 종료됐다(커밋 4a3e616, 더 이상 손대지 마라).

새 미션이다. 아래 파일을 열어서 그대로 수행하라.

  .automation/requests/C1-TASK-ORDER-ADR023-AMENDMENT-A-HOST-EXECUTOR.md

배경: n8n의 executeCommand 노드는 2.29.9에서 기본 비활성화되어 있고, n8n
컨테이너에는 Python도 NAE 소스도 없다 — ADR-023이 지정한 "n8n이 cli_driver를
직접 호출"하는 경로는 실행 불가능하다는 게 CUE 실측으로 확인됐다. Rev. Bang이
Option A(Host Executor — n8n은 orchestrator, 별도 host 프로세스가 cli_driver를
직접 호출)를 승인했다.

핵심 요구사항 (전체는 위 파일 참고, 재조사 금지 — 계약은 이미 다 정리되어 있다):
1. .automation/night-shift/host_executor.py 신규 구현. n8n 워크플로우 노드는
   1개도 건드리지 마라.
2. state mapping(exit code -> COMPLETED/FAILED+failure_code), evidence entry
   스키마, 허용된 전이(VALIDATION_PASSED->PROCESSING->COMPLETED/FAILED만,
   FAILED->RETRY_PENDING 자동승격 절대 금지)는 작업 명령서 표에 정확히 적혀
   있다 — 그대로 구현해라, 재설계하지 마라.
3. cli_driver는 subprocess로 호출해라(import 금지 — 프로세스 경계 유지).
4. .automation/night-shift/queue/NAE-REG-BAP-CHURCH-DAGG-001.json 1건만
   먼저 end-to-end로 실행해라. 이건 실제 production mutation이다
   (registration_state.json에 실제로 기록된다). 성공하면 나머지 9건으로
   확대하고, 실패하면 멈추고 원인만 기록해라 — 자동으로 다음 건에 진행하지 마라.
5. core/retrieval.py, NAE/pipeline/registration/pipeline.py는 절대 건드리지
   마라. 새 ADR도 만들지 마라.
6. 모든 증거는 .automation/evidence/night-shift/host-executor-implementation/
   아래 남겨라 (command.txt, exit_code.txt 숫자만, stdout.log, stderr.log).

질문하지 말고 지금 시작하라.
```

---

## 릴레이 2 — Correction Order 001 (완료, 참고용)

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

## 릴레이 1 — 최초 Mission Order (완료, 참고용)

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
