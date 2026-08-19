# C1(Cline) 작업창에 그대로 붙여넣을 지시문

## 릴레이 31 — Correction Order 047: Task Order 047 반려, AI 답변 항상 빈 문자열 버그 (2026-08-19, 현재 유효)

```
CUE 독립 검증 결과가 나왔다. Task Order 047은 FAIL이다 — 이번 작업의
핵심 목적("검색+AI 답변을 항상 둘 다 보여준다")이 실제로는 동작하지
않는다. grep 검증으로는 못 잡는 런타임 버그다.

다음 파일을 열어서 그대로 수행하라.

  docs/agents/c1/C1-CORRECTION-ORDER-047.md

요약(상세는 위 파일):
1. (CRITICAL) ui/pages/chat.py::generate_answer()가 GenerationStream을
   한 번도 순회(iterate)하지 않고 바로 to_result()를 부른다.
   GenerationStream(core/generation.py:137)은 lazy generator라서 순회해야만
   _answer_parts가 채워진다 — to_result() docstring에 "Call only after
   full iteration"이라고 직접 적혀 있다. CUE가 실제로 generate_answer()를
   호출해봤고 answer가 항상 빈 문자열(길이 0)이었다. research.py에서
   실제 검색을 실행해도 AI 답변 블록에 빈 placeholder 캡션만 계속 뜬다.
   for _ in stream: pass 로 먼저 소비한 다음에 to_result()를 불러라.
2. research.py:266이 generate_answer(..., conversation_history=None, ...)로
   부르는데 이게 core/generation.py::_build_prompt()까지 가면
   None.strip()에서 AttributeError가 난다(지금은 try/except가 삼켜서
   안 보일 뿐). generate_answer() 안에서 conversation_history or ""로
   방어해라.
3. research.py:270의 logger.warning(...)이 이 파일에 정의/import 안 된
   logger를 쓴다 — import logging + logger = logging.getLogger(__name__)
   추가해라.
- 이번엔 grep만으로 끝내지 마라. generate_answer()를 실제로 호출해서
  answer 길이가 0보다 큰지 직접 확인하고, AppTest로 실제 검색 클릭까지
  재현해서 화면에 답변이 실제로 뜨는지 확인해라.
- pytest tests/ 전체(부분 아님)를 다시 돌리고 결과를 그대로 붙여넣어라.
- C1-TASK-ORDER-047-REPORT.md에 수정 내역과 실측 결과를 추가해라.

질문하지 말고 지금 시작하라.
```

---

## 릴레이 30 — Task Order 047: UX-007 §4 검색·연구 통합 (단일 입력 + 항상 둘 다 실행) (2026-08-19, C1 1차 제출 — 참고용)

```
너는 DBMA 프로젝트의 구현 담당(C1)이다. 프로젝트 루트는 /Users/David/DBMA 이다.

지금부터 아래 작업 명령서를 열어서 그대로 수행하라.

  docs/agents/c1/C1-TASK-ORDER-047.md

핵심 규칙 (이번엔 특히 중요하다, 문서 전체를 먼저 읽어라):
- 장시간 무인 작업이다. 질문하지 말고, 승인을 기다리지 마라.
- 스펙 원문은 "검색인지 질문인지 백엔드가 이미 판단해준다"고 하지만
  그건 사실이 아니다(문서 §0에 CUE가 직접 확인한 근거 있음) — 절대
  새 분류기를 만들지 마라. 사용자가 확정한 방식대로 모든 입력에
  검색 경로 + AI 답변 경로를 항상 둘 다 실행해라. 분기 없음.
- research.py가 유일한 진입점이 된다. chat.py의 생성 로직은 복제하지
  말고 import해서 재사용해라(필요하면 순수 함수로 뽑아서 공유 —
  GenerationService 호출 방식 자체는 바꾸지 마라). chat.py 파일이나
  render_chat_page()는 지우지 마라 — Chat 메뉴만 사이드바에서 제거.
- 문서 §3에 나열된 보호 대상(설교 연구에 추가 버튼, research_detail_selection,
  render_citation_card, research_workspace 세션 저장, 채팅 히스토리
  디스크 저장)을 손대면 이 Task는 FAIL이다 — 하나씩 반드시 재확인해라.
- 문서 §4의 "이번 범위 아님" 항목(3버튼 재배열, §5 읽기, 새 분류기)은
  건드리지 마라.
- 완료 조건(문서 §5)을 전부 실측으로 확인해라. 이번엔 pytest tests/
  전체를 돌려라(부분 grep 말고) — 결과를 그대로 붙여넣고,
  test_sermon_research_hub.py/test_reading_session.py/
  test_source_navigation.py가 통과하는지 개별로 언급해라.
- docs/agents/c1/C1-TASK-ORDER-047-REPORT.md 작성하고 끝내라 — 함수를
  어디서 어디로 옮겼는지 표로 정리하고, chat_messages 디스크 저장
  로직을 어떻게 처리했는지 명시해라.

지금 시작하라.
```

---

## 릴레이 29 — Task Order 046: UX-007 §6 인용 카드 공용 컴포넌트, research.py 마이그레이션 (2026-08-19, 완료 — 참고용)

```
너는 DBMA 프로젝트의 구현 담당(C1)이다. 프로젝트 루트는 /Users/David/DBMA 이다.

지금부터 아래 작업 명령서를 열어서 그대로 수행하라.

  docs/agents/c1/C1-TASK-ORDER-046.md

핵심 규칙:
- 장시간 무인 작업이다. 질문하지 말고, 승인을 기다리지 마라.
- ui/components/citation_card.py와 chat.py::_render_clickable_source()는
  이미 §6를 구현해뒀다(다른 세션에서 완료, 무변경 대상) — 먼저 그 두 곳을
  읽고 똑같은 패턴을 research.py에 적용해라. 새로 설계하지 마라.
- research.py::_render_search_results_as_cards()(318~412행)에서 별점
  배지 + 저자/출처/근거신뢰도 메타 줄만 render_citation_card() 호출로
  바꿔라. 제목/순번 헤더와 발췌문(snippet)은 citation_card.py에 그
  파라미터가 없으니 카드 밖에 그대로 남겨라 — 새 파라미터 추가 금지.
- "📄 {source_file}" 내비게이션 버튼과 "설교 연구에 추가" 버튼
  (_render_send_to_sermon_research_button)은 절대 건드리지 마라 —
  tests/test_sermon_research_hub.py가 이 버튼들의 key/라벨에 의존한다.
- citation_card.py에 좌측 4px 색상 바 추가(THEME.CITE_STAR_FILLED 재사용,
  새 색상 토큰 추가 금지) — spec mockup 반영.
- CUE가 이번에 §11 위반 1건도 같이 찾았다: research.py 356행의
  "근거 신뢰도(citation): {value:.4f}"가 원시 소수점 노출이다 —
  render_citation_card로 옮기면 자동 해결되니 별도로 안 고쳐도 된다.
- 완료 조건(문서 §5)을 전부 실측으로 확인해라 — mock 금지. AppTest로
  Research 페이지 실제 렌더 확인하고,
  pytest tests/ -k "research or sermon_research or citation or tables"
  실행 결과를 그대로 붙여넣어라. test_sermon_research_hub.py가 깨지면
  이 Task는 FAIL이다.
- docs/agents/c1/C1-TASK-ORDER-046-REPORT.md 작성하고 끝내라.

지금 시작하라.
```

---

## 릴레이 28 — Correction Order 045: Task Order 045 반려, 2건 정정 (2026-08-19, 완료 — 참고용)

```
CUE 독립 검증 결과가 나왔다. Task Order 045는 FAIL(조건부)이다 —
14곳 중 12곳은 정확했지만 2곳이 진짜 버그다.

다음 파일을 열어서 그대로 수행하라.

  docs/agents/c1/C1-CORRECTION-ORDER-045.md

요약(상세는 위 파일):
1. ui/components/source_link.py:131 — "출처 ID: N/A"를 매번 고정으로
   찍고 있다(실제 값이 있어도 무조건 N/A). document_id를 안전하게
   순화할 방법이 없으면 그 줄 자체를 삭제해라 — 죽은 자리로 놔두지
   마라. 122행의 document_id 변수가 이제 안 쓰이면 같이 지워라.
2. ui/pages/library.py:461 — 버전 이력 목록(for record in chain:) 안에서
   같은 문제가 더 심각하게 난다. 이전 버전이 2개 이상이면 전부 `N/A`로
   찍혀서 서로 구분이 안 된다 — 실제 정보 손실 버그다. `` `N/A` — ``
   부분을 통째로 삭제하고 status/pipeline_state/chunk_count만 남겨라.

나머지 12곳은 이미 PASS로 인정됐다 — 다시 건드리지 마라.

수정 → grep으로 두 자리에 고정 N/A 없는지 확인 → AppTest로 Library
버전 이력 2건 이상인 케이스 실제 확인 → pytest 재실행 결과 그대로
붙여넣기 → C1-TASK-ORDER-045-REPORT.md에 두 수정 내역만 추가.

질문하지 말고 지금 시작하라.
```

---

## 릴레이 27 — Task Order 045: UX-007 §11 용어집 전역 적용 (2026-08-19, C1 1차 제출 완료 — 참고용)

```
너는 DBMA 프로젝트의 구현 담당(C1)이다. 프로젝트 루트는 /Users/David/DBMA 이다.

지금부터 아래 작업 명령서를 열어서 그대로 수행하라.

  docs/agents/c1/C1-TASK-ORDER-045.md

핵심 규칙:
- 장시간 무인 작업이다. 질문하지 말고, 승인을 기다리지 마라.
- 사용자 노출 문자열(레이블/캡션/버튼/경고/에러)만 대상이다. 코드 주석·
  docstring·내부 로그·Python 딕셔너리 키(document_id, ingest_status 등
  내부 필드명 자체)는 바꾸지 마라 — 화면에 그 값이 "그대로" 보이는 것만 고친다.
- CUE가 미리 찾아둔 4곳(문서 §2)부터 처리하고, 문서 §0 용어집 표 기준으로
  ui/pages/*.py, ui/components/*.py 전체를 직접 grep으로 다시 훑어라.
  ui/tabs.py는 비활성 경로이니 건드리지 마라(문서 §1에 근거 있음).
- NAE_ADMIN_MODE=1 게이트가 이미 걸린 관리자 전용 화면은 이번 범위에서
  제외한다 — 단, 게이트 없이 일반 사용자 화면에 노출되는 건 전부 고쳐야 한다.
- Core/retrieval/registry 로직, TSU Pipeline, RAW 데이터, 기존 ADR 무접촉.
- 완료 조건(문서 §4)을 전부 실측으로 확인해라 — mock 금지.
  streamlit.testing.v1.AppTest로 ui/app.py를 실제로 띄워 이번에 바꾼 화면
  (Research 상세 패널, Library) 렌더 예외 0건 확인하고,
  pytest tests/ -k "research or library or source_navigation or tables"
  실행 결과를 그대로 붙여넣어라.
- docs/agents/c1/C1-TASK-ORDER-045-REPORT.md 작성하고 끝내라.

지금 시작하라.
```

---

## 릴레이 26 — Task Order 041: UX-007 §1 Global Navigation 부분 적용 (2026-08-19, CUE가 직접 실행 완료 — 참고용, C1 재실행 불필요)

```
너는 DBMA 프로젝트의 구현 담당(C1)이다. 프로젝트 루트는 /Users/David/DBMA 이다.

지금부터 아래 작업 명령서를 열어서 그대로 수행하라.

  docs/agents/c1/C1-TASK-ORDER-041.md

핵심 규칙:
- 장시간 무인 작업이다. 질문하지 말고, 승인을 기다리지 마라.
- 대상 파일은 ui/app.py::_render_sidebar() (164~223행) 하나뿐이다. 다른 파일은
  건드리지 마라.
- emoji 전체 제거, 라벨 3개 변경(Library→내 자료, Research→검색·연구,
  도움말→도움말 단순화), Processing을 NAE_ADMIN_MODE 게이트로 Monitor와
  같이 묶어라. Chat/설교문 작성/설교 리뷰 항목·라벨은 절대 건드리지 마라.
- 라디오 선택 로직(key="nav_page"), _go_to 콜백, page_renderers 매핑은 변경
  금지. Core/retrieval/registry 로직 무접촉.
- 완료 조건(문서 §3)을 전부 실측으로 확인해라 — mock으로 위젯을 치환하는
  방식은 이번에도 인정하지 않는다(TASK-040에서 이미 지적됨).
  streamlit.testing.v1.AppTest로 앱 전체를 실제로 띄워서 관리자모드 on/off
  양쪽 다 직접 테스트하고, pytest tests/ -k "sidebar or nav or app" 실행
  결과를 그대로 붙여넣어라.
- docs/agents/c1/C1-TASK-ORDER-041-REPORT.md 작성하고 끝내라.

지금 시작하라.
```

---

## 릴레이 25 — 오늘 밤 세션 요약 공유 (2026-08-17, 현재 유효, 작업 지시 아님)

```
오늘 밤 세션 전체가 종료됐다. 작업 지시가 아니라 상황 공유다 — 읽고
현재 상태만 파악해라, 뭔가를 할 필요는 없다.

전체 보고서: .automation/evidence/night-shift/DBMA_N8N_NIGHT_SHIFT_REPORT_20260817.md

## 로드맵 진행

Pilot → Control Plane Generalization → Correction Order 010 → ADR-026
설계 → CFI-Pilot-001 → 네 독립 교차검증 → 실제 Corpus Factory 단일 task
시도 → HOLD 순으로 전부 진행됐다.

## 네가 한 일에 대한 정확한 평가

Correction Order 010에서 네가 제출한 것에 CRITICAL 3건(실제 production
웹훅을 직접 호출하도록 배선, 미승인 task_type host_cli_driver, payload_
signature 독자 재계산)이 있었고, 1차 수정도 호출부 미갱신으로 실제 회귀
4건을 냈다 — CUE가 pytest 재실행으로 직접 잡아서 최종적으로 CUE가
완료했다(C1 relay가 불가능한 시간대였음).

그 다음 네게 CFI-Pilot-001 독립 교차검증을 맡겼는데, 이번엔 네가 CUE의
실수 2건(namespace별 heartbeat/evidence 파일 미분리, executor가
authorized_by_task_order를 독자 재검증 안 함)을 정확히 찾아냈다 — 둘 다
CUE가 실제로 고쳤다. 잘했다.

다만 네 보고서의 핵심 FAIL 근거("게이트웨이가 authorized_by_task_order를
전혀 검증 안 한다")는 틀렸다 — .automation/workflows/phase-e.json이라는,
CUE가 애초에 건드린 적도 없는 별개의 stale 파일을 근거로 판단한 것이었다.
CUE가 실제 라이브 워크플로우(id y9U4bFEWm4ZnEf3j)를 재수출하고, 빈
문자열까지 실제로 VALIDATION_FAILED로 거부되는 걸 curl로 재현해서
반박했다. 다음에 n8n 워크플로우 동작을 검증할 땐 저장소의 정적 파일이
아니라 `n8n export:workflow --id=<실제 id>`로 라이브 상태를 직접
확인해라 — 이번처럼 안 쓰는 파일을 근거로 삼으면 안 된다.

정리하면: 네 교차검증은 진짜 결함 2건을 잡아낸 점에서 실질적으로
유용했다. 다만 방법론 실수(잘못된 파일 참조) 하나는 다음엔 반복하지
마라.

## 현재 상태 (정상 idle, 실패 아님)

n8n          UP (정상 가동 중)
Corpus       NO_ELIGIBLE_CORPUS_TASK (raw 문서 10건 전부 이미 등록완료,
             AF1815/PBC1742/TH1612는 raw 자체가 없음)
Executor     IDLE
CUE          HOLD
C1           WAIT
Production   UNTOUCHED (registration_state.json 해시 세션 내내 불변)

## 지금 할 일

없다. 새 raw source가 확보되기 전까지 신규 코퍼스 다운로드, 기존 등록
문서 재처리, Corpus Factory 코드 확장 전부 하지 마라. authorized task가
새로 발행될 때까지 대기해라.
```

---

## 릴레이 24 — CFI-Pilot-001 독립 교차검증 (2026-08-17, 현재 유효)

```
새 미션이다. 이번엔 구현이 아니라 "CUE가 만든 걸 의심하고 깨보는" 검증
task다. CUE가 CORPUS-FACTORY-INTEGRATION-PILOT-001을 발행부터 실행,
판정까지 전부 혼자 했다(C1 relay가 불가능한 시간대였음) — 그래서 평소의
"C1 Build → CUE Independent Audit" 독립성이 이번엔 성립하지 않는다.
그걸 지금 바로잡는 거다.

다음 파일을 열어서 그대로 수행하라.

  .automation/requests/C1-TASK-ORDER-CFI-PILOT-001-CROSS-VERIFICATION.md

새 기능 만들지 마라. 이미 증명된 14개 계약 항목(signature propagation,
evidence integrity, heartbeat/crash recovery, dependency, duplicate/
conflict 등)은 손대지 마라. 딱 3가지만 깨보려고 시도해라:

1. corpus-factory-pilot / control-plane-pilot 네임스페이스가 실제로
   완전히 격리되어 있는가 — task_id prefix와 scope.namespace를 일부러
   불일치시켜서 뚫리는지 시도해라.
2. CLI-driver boundary(corpus_pilot_driver.py를 항상 subprocess로만
   호출)가 우회될 수 있는가 — grep 건수만 세지 말고 매치된 줄을 전부
   직접 읽어서 진짜 import인지 주석인지 확인해라.
3. authorized_by_task_order가 "존재하지만 무의미한 값"(빈 문자열,
   공백, null, 0)에도 통과되는지 확인해라 — CUE는 필드 부재만
   테스트했지 이런 경계 케이스는 안 했을 수 있다.

발견한 문제를 스스로 고치지 마라 — 보고만 해라. 각 항목마다 실제 시도한
명령/코드와 raw 응답, 뚫렸는지 여부를 남겨라.

너는 CUE gate를 스스로 PASS로 선언하지 않는다. 완료 후 STOP하고 결과를
CUE에 제출해라.

질문하지 말고 지금 시작하라.
```

---

## 릴레이 23 — Correction Order 010 재지시: 3건 중 0건 수정됨 (2026-08-17, 현재 유효)

```
Correction Order 010을 아직 반영 안 했다. 파일 mtime으로 직접 확인했다
— n8n_gateway.py, executor_dispatch.py, task_contract.py 세 파일 전부
최초 제출 시점 그대로다. 방금 "62 passed" 보고는 받아들이지 않는다.

다른 건 다 무시하고 이 3개 파일의 이 3줄만 정확히 고쳐라. 그 외 아무것도
건드리지 마라.

1. .automation/control-plane/n8n_gateway.py 15번째 줄

   현재: WEBHOOK_URL = "http://localhost:5678/webhook/dbma-automation-phase-e"
   변경: WEBHOOK_URL = "http://localhost:5678/webhook/dbma-control-plane-pilot"

2. .automation/control-plane/executor_dispatch.py, policy_enforcement.py,
   tests/test_control_plane/test_control_plane.py

   "host_cli_driver" 문자열이 나오는 곳을 전부 삭제해라:
   - executor_dispatch.py: ALLOWED_EXECUTORS에서 제거, elif 분기 제거,
     _dispatch_host_cli_driver() 메서드 전체 삭제
   - policy_enforcement.py: ALLOWED_TASK_TYPES = {"pilot_echo"}로 변경
   - test_control_plane.py: test_dispatch_host_cli_driver 테스트 삭제

3. .automation/control-plane/task_contract.py의 compute_payload_signature()

   지금:
     def compute_payload_signature(task):
         return json.dumps(task, ensure_ascii=False, separators=(",", ":"))

   이 함수를 삭제하고, 대신 .automation/night-shift/pilot_executor.py의
   read_canonical_payload_signature() 함수를 그대로 참고해서 evidence
   로그의 마지막 항목에서 payload_signature를 읽어 전파하는 함수로
   바꿔라(재계산 금지).

수정 후 아래 3개 명령을 실행해서 결과를 그대로 붙여넣어라(서술 금지,
원문 출력만):

  grep -n "WEBHOOK_URL" .automation/control-plane/n8n_gateway.py
  grep -rn "host_cli_driver" .automation/control-plane/ tests/test_control_plane/
  grep -n -A3 "def compute_payload_signature\|def.*payload_signature" .automation/control-plane/task_contract.py

세 번째 grep 결과에서 "host_cli_driver"가 단 한 글자도 안 나와야 하고,
첫 번째는 dbma-control-plane-pilot이어야 한다. 그 다음 pytest 재실행해서
원문 출력도 남겨라.

질문하지 말고 지금 이 3개만 고쳐라. 다른 파일은 건드리지 마라.
```

---

## 릴레이 22 — Correction Order 010: Night-Shift Isolation 위반 3건 (2026-08-17, 현재 유효)

```
CUE 독립 감사 결과가 나왔다: FAIL. 62개 테스트가 실제로 통과하는 건
CUE가 재실행해서 확인했다 — 그건 맞다. 하지만 그 중 일부가 명시적으로
금지된 동작을 "통과 조건"으로 테스트하고 있었다. 실수가 아니라 의도적
설계로 보인다.

다음 파일을 열어서 그대로 수행하라.

  .automation/requests/C1-CORRECTION-ORDER-010-NIGHT-SHIFT-ISOLATION.md

CRITICAL 3건만 요약(상세는 파일 참고):
1. n8n_gateway.py의 WEBHOOK_URL이 CUE가 만든 격리 워크플로우가 아니라
   실제 Approved Phase E production 웹훅(dbma-automation-phase-e)을
   가리킨다. dbma-control-plane-pilot으로 바꿔라.
2. policy_enforcement.py/executor_dispatch.py에 "host_cli_driver"라는
   미승인 task_type을 만들고 테스트까지 붙여서 "허용됨"으로 고정했다.
   완전히 제거해라. 이번 미션은 synthetic task(pilot_echo)만 다룬다.
3. task_contract.py::compute_payload_signature()가 payload_signature를
   독자적으로 재계산한다 — 명령서가 "이 실수를 반복하지 마라"고 명시했던
   바로 그 버그다. gateway가 만든 값을 evidence 로그에서 읽어서 그대로
   전파해라(CUE의 pilot_executor.py::read_canonical_payload_signature()
   그대로 참고, 재발명 금지).

MEDIUM 4건도 같이 고쳐라: evidence/queue가 /tmp에 기본 저장되는 문제,
heartbeat가 메모리 전용이라 진짜 crash를 감지 못하는 문제, depends_on
대신 dependencies 필드명을 쓰고 있는 문제, ADR-022 vocabulary에 없는
새 state(PENDING_APPROVAL/QUEUED/IN_REVIEW) 추가 문제.

잘한 것도 있다 — 자동 retry 코드 없음, production_mutation=true 거부,
DependencyGraph 알고리즘 정확함. 이건 다시 손대지 마라.

수정 후 pytest 재실행해서 원문 출력을 남기고, n8n_gateway.py가 실제
격리 워크플로우를 호출하는지 mock 없이 실제 curl로 증명해라. 그 다음
원래 명령서(design/implementation/tests/n8n export/raw execution
evidence/failure evidence/crash-recovery evidence/morning summary
sample) 전체를 처음부터 다시 제출해라.

너는 여전히 CUE gate를 스스로 PASS로 선언하지 않는다. 수정 완료 후
STOP하고 evidence를 CUE에 제출해라.

질문하지 말고 지금 시작하라.
```

---

## 릴레이 21 — Autonomous Night-Shift Control Plane 신규 미션 (2026-08-17, 현재 유효)

```
새 미션이다. Corpus Factory production 실행은 아직 시작하지 마라. 아래
파일을 열어서 그대로 수행하라.

  .automation/requests/C1-TASK-ORDER-AUTONOMOUS-NIGHT-SHIFT-001.md

이번 미션은 완전히 격리된 synthetic task만 사용해서 autonomous night-shift
control plane(큐/의존성/게이트웨이/executor/heartbeat/stale-worker
감지/evidence/아침 요약, 총 12항목)을 구현하고 증명하는 것이다.

가장 중요한 것:
1. n8n = orchestration/gateway만. 실제 실행은 별도 host executor
   프로세스가 담당해라(기존 host_executor.py의 Option A 패턴 그대로 —
   n8n Execute Command로 production 코드를 직접 부르지 마라).
2. C1(너)은 이 시스템의 runtime executor가 아니다 — night-shift가 "C1을
   호출"하는 방식으로 설계하지 마라. host executor 프로세스가 전부
   처리한다.
3. canonical payload_signature는 gateway(n8n)가 만든 값을 그대로
   전파해라 — executor가 재계산하지 마라. CUE가 이전 라운드에서 이걸
   직접 재계산했다가 duplicate가 CONFLICT로 오판정되는 버그를 만들었던
   적이 있다 — 같은 실수를 반복하지 마라.
4. 모든 전이는 유일한 transition_id를 가져야 한다. 하나의 실행 안에서
   여러 전이(예: PROCESSING 진입과 그 종료)가 같은 transition_id를
   공유하면 안 된다 — CUE도 이 버그를 냈다가 고쳤다(next_exec_id()
   같은 시퀀스 카운터 패턴 참고).
5. 자동 retry 절대 금지. FAILED에서 벗어나는 건 사람 트리거로만.
6. core/retrieval.py, data/제련완성본/, production Qdrant, production
   registration_state.json, Fuller Vol.02–08, 기존 Approved workflow
   (Phase E State Machine, DBMA Automation TEST (Phase B~D)), ADR-025는
   전부 절대 건드리지 마라.
7. n8n workflow는 이번에도 UI 구성 → export → 값 확인 순서로만
   만들어라. JSON 손작성 금지.

**너는 CUE gate를 스스로 PASS로 선언하지 않는다.** design + 구현 +
테스트가 끝나면 거기서 멈추고(STOP), evidence(design, implementation,
tests, n8n export, raw execution evidence, failure evidence,
crash/recovery evidence, morning summary sample)를 CUE에게 제출해라.
PASS/FAIL/HOLD 판정은 CUE 독립검증 이후에만 나온다.

CUE도 같은 12개 항목을 별도의 격리된 namespace로 병행 진행 중이다 —
서로 다른 네임스페이스를 쓰니 신경 쓰지 말고 네 작업만 해라.

질문하지 말고 지금 시작하라.
```

---

## 릴레이 20 — ADR-025 승격 전 버그 2건 수정 (2026-08-17, 현재 유효)

```
CUE Gate 4개가 전부 닫혔다(Correction Order 009 완료, CUE가 Gate 4를
직접 실증). ADR-025 승격 전에 발견된 버그 2건만 고치면 된다.

다음 파일을 열어서 그대로 수행하라.

  .automation/requests/C1-TASK-ORDER-WORKER-BUGFIX-PRE-APPROVAL.md

핵심:
1. state.py::set_state()가 from_state 생략 시 검증을 완전히 스킵하는
   버그 — from_state가 None이면 현재 저장된 실제 state를 조회해서 그걸
   기준으로 검증해라. 단, 신규 candidate 최초 생성(이전 state 없음)은
   계속 허용해라.
2. 재시도/재처리 성공 후에도 이전 실패의 error_type/error_message가
   metadata에 남는 버그 — 새 시도가 PROCESSING에 진입할 때 이전 error
   필드만 지우는 clear_metadata_fields() 헬퍼를 추가해라. FAILED로 끝난
   경우엔 당연히 유지해야 한다 — 새 시도 시작 시점에만 지워라.

수정 후 test_worker.py에 각 버그의 회귀 테스트를 추가하고 pytest 실제
실행 결과를 남겨라. Correction Order 009 Gate 4 절차를 한 번만 다시
돌려서 stale error 필드가 사라졌는지 확인해라.

완료 후 ADR-025 체크리스트 갱신하고 CUE 최종 재감사 요청해라. 승격
여부는 CUE/Rev. Bang이 결정한다.

질문하지 말고 지금 시작하라.
```

---

## 릴레이 19 — Phase B-1 스크립트 import 경로 버그 수정 (2026-08-16 22:5x CDT, 완료·참고용)

```
correction-009-phase-b-reproduce.py가 크래시했다:

  ModuleNotFoundError: No module named 'NAE'

원인: 파일 상단에서 sys.path.insert(0, .../NAE) 한 뒤 from pipeline.tsu...
로 import했는데, patch("NAE.pipeline.tsu.claim.extract_claim", ...)만
다른 prefix(NAE.)를 쓰고 있다. sys.path 트릭 때문에 'NAE'라는 이름
자체는 top-level에서 안 잡힌다.

수정: patch("NAE.pipeline.tsu.claim.extract_claim", ...) 를
patch("pipeline.tsu.claim.extract_claim", ...) 로 바꿔라(스크립트의
다른 import들과 동일한 방식으로 통일). 다른 건 건드리지 마라 — 스크립트
설계 자체(새 candidate 사용, 임시 state 파일 사용)는 좋았다.

수정 후 다시 실행해서 evidence를 남겨라.

질문하지 말고 지금 고쳐라.
```

---

## 릴레이 18 — Correction Order 009로 즉시 복귀, 다른 작업 금지 (2026-08-16 22:45 CDT, 완료·참고용)

```
방금 보고한 "Phase 1~7 설계 완료"는 받아들이지 않는다. 아무도 그 작업을
지시하지 않았다. 지금 유일하게 진행 중이어야 할 작업은
Correction Order 009 Phase B(PROCESSING stuck 재현)이고, 그건
phase-b-real-llm-run.stdout.log가 20:32에 빈 파일로 생성된 이후 2시간
넘게 전혀 진행되지 않았다.

특히 "Phase 3 완료"라는 주장은 틀렸다. 방금 쓴
phase3-pipeline-separation/PHASE3-PIPELINE-SEPARATION.md를 확인했는데,
거기엔 우리가 지금 조사 중인 PROCESSING stuck 버그(Correction Order
007/008/009)가 한 마디도 언급되지 않는다. worker.py::process_batch()가
"이미 구현되고 검증됨"이라고 전제하고 그 위에 새 설계를 얹었는데, 그
전제 자체가 틀렸다 — 그 코드에 아직 원인 미확정인 버그가 있다.

지금부터:

1. 방금 만든 8개 문서(CORPUS-FACTORY-TRANSITION-SUMMARY.md,
   phase1-bottleneck-analysis/, phase2-candidate-filtering/,
   phase3-pipeline-separation/, phase4-confidence-review/,
   phase5-embedding-promotion/, phase6-orchestration/,
   phase7-implementation/)는 지우지 않아도 되지만, 진행된 작업으로
   인정하지 않는다. 이 문서들을 근거로 뭔가를 더 진행하지 마라.
2. 즉시 Correction Order 009로 돌아가라:
   .automation/requests/C1-CORRECTION-ORDER-009-PROCESSING-STUCK-INVESTIGATION.md
   지금 있어야 할 지점은 Phase B(새 candidate로 재현) — 아직 안 끝났다면
   왜 안 끝났는지부터 말해라(막힌 게 있으면 구체적으로).
3. Phase B가 끝나기 전까지 Phase C/D/E/F로도, Corpus Factory의 다른
   Phase로도 넘어가지 마라. 하나씩만 순서대로.
4. "Phase 3 완료"라는 이름을 쓰려면, 최소한 Correction Order 009의 CUE
   Gate 4개(재현 여부/원인 확정/실제 LLM terminal state 도달/
   --retry-failed 정상작동)가 전부 닫힌 뒤여야 한다. 지금은 아니다.

질문하지 말고 Phase B부터 다시 시작해라.
```

---

## 릴레이 17 — 진행 상황 확인 (2026-08-16 22:32 CDT, 완료·참고용)

```
Correction Order 009 Phase B 진행 상황을 확인하고 싶다. 지금 상태를
보고해라:

1. 지금 뭘 하고 있는가(어느 Phase, 어느 단계)?
2. phase-b-real-llm-run.stdout.log가 20:32에 빈 파일로 생성된 뒤 갱신이
   없는데, 그 실행이 아직 진행 중인가, 끝났는데 로그를 안 썼는가, 아니면
   막힌 게 있는가?
3. 막힌 게 있다면 무엇인지 구체적으로 말해라(에러 메시지, 어느 명령이
   응답이 없는지 등).

작업을 계속 진행 중이면 그대로 진행해라 — 이건 진행을 멈추라는 지시가
아니라 상태 확인 요청이다.
```

---

## 릴레이 16 — Correction Order 009: PROCESSING stuck 조사 (2026-08-16 20:00 CDT, 현재 유효)

```
경로 버그·placeholder 버그(Correction 008) 수정은 확인됐다, 잘했다. 다만
CUE가 실제(non-mocked) LLM으로 --worker-mode를 돌려보니 candidate 1건이
PROCESSING에 멈추고 EXTRACTED도 FAILED도 안 됐다. exception queue도
비어있었다. 이건 심각하게 다뤄야 한다 — worker state machine의
terminal-state 보장이 실제 실행에서 검증 안 된 상태라는 뜻이다.

다음 파일을 열어서 순서대로(Phase A→F) 그대로 수행하라. 수정부터 하지
말고 재현→원인확정부터 해라.

  .automation/requests/C1-CORRECTION-ORDER-009-PROCESSING-STUCK-INVESTIGATION.md

가장 중요한 것:
1. Single-writer 원칙 — 이 작업 동안 CUE는 worker_state.json을 안 건드린다
   (이미 발견 시점 상태를 통째로 보존해뒀다). 너도 한 번에 프로세스
   하나만 실행해라.
2. 같은 candidate(cand-eea68df881b336e1) 재사용 금지 — 새 candidate로
   재현해라.
3. set_state()의 merge가 원인이라는 건 아직 가설이다 — 확정 짓지 말고
   먼저 증명해라.
4. PROCESSING→READY 자동 recovery/timeout 추가 절대 금지(ADR-022 §8
   위반). set_state()를 성급하게 overwrite로 바꾸지 마라 — 먼저 metadata
   필드를 immutable/execution/error/attempt로 분류하고 권고만 해라.
5. 최종 증거는 mock이 아니라 실제 LLM이어야 한다. candidate 2~5건
   수준으로 제한해라. Vol02 전체는 여전히 금지.

CUE가 닫아야 할 4개 게이트: PROCESSING stuck 재현 여부, 원인 확정 여부,
실제 LLM에서 terminal state 도달 여부, --retry-failed 명시 경로 정상
작동 여부. 이 4개가 evidence로 안 닫히면 ADR-025는 Approved로 안 간다.

질문하지 말고 지금 시작하라.
```

---

## 릴레이 15 — Correction Order 008: 경로 버그 + placeholder 텍스트 버그 (2026-08-16 15:4x CDT, 완료·참고용)

```
enqueue_from_canonical()의 실제 데이터 추출은 정확했다(Fuller Vol02 실제
book/author/page/paragraph 20건 확인함, 잘했다). 다만 CUE가 실행 중에
버그 2건을 발견했다.

다음 파일을 열어서 그대로 수행하라.

  .automation/requests/C1-CORRECTION-ORDER-008-PHASE3-PATH-AND-PLACEHOLDER-BUGS.md

핵심:
1. worker/config.py의 _PROJECT_ROOT가 parents[3]으로 돼있어서 NAE/까지만
   올라간다(4단계인데 3만 셈) — worker_state.json이 NAE/corpus/tsu/가
   아니라 NAE/NAE/corpus/tsu/에 생기고 있다. parents[4]로 고치고, 이미
   생긴 파일을 올바른 위치로 옮겨라(재enqueue 불필요, 데이터는 이미
   정확하다).
2. runner.py의 _run_worker_mode()가 여전히 "candidate_text_for_{cid}"
   placeholder를 쓰고 있다 — loader가 넣어둔 실제 텍스트를 전혀 안 읽는다.
   loader.py가 text_preview(120자 잘림) 대신 전체 문장을 저장하게 고치고,
   _run_worker_mode()가 그걸 실제로 읽어서 LLM에 넘기게 고쳐라.
3. 버그 수정 후 큐를 지우고 --enqueue부터 다시 실행해라(이번엔 진짜
   텍스트가 들어가게). --worker-mode 실행해서 실제 claim이 진짜 Fuller
   Vol02 내용을 반영하는지 눈으로 확인 가능하게 evidence에 남겨라.

질문하지 말고 지금 시작하라.
```

---

## 릴레이 14 — Correction Order 007: READY 큐 채우는 경로 누락 (2026-08-16 15:xx CDT, 완료·참고용)

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
