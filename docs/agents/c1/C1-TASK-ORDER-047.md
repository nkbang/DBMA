# C1 Task Order 047 — UX-007 §4 검색·연구 통합 (핵심: 단일 입력 + 항상 둘 다 실행)

**상태**: 발급됨 — 착수 가능
**우선순위**: P1
**근거 문서**: [DBMA-UX-007-IMPLEMENTATION-SPEC.md](../../DBMA-UX-007-IMPLEMENTATION-SPEC.md) §4(Search & Research)
**선행 확인(중요, CUE가 사용자와 확정한 사항)**: §4.1 원문은 "입력이
검색인지 질문인지 기존 백엔드가 이미 판단해준다"고 적혀 있으나,
**실제로 그런 분류기는 없다** — `core/retrieval.py`의 `ParsedQuery.intent`
필드는 영어 정규식 기반의 "주제 유형"(exegesis/comparison/devotional/
theological/cross-reference) 분류일 뿐, "검색 vs 질문"을 가르는
이진 판단이 아니다(정규식도 영어 전용이라 한국어 입력에 사실상 안
먹는다). **새 분류기를 만들지 마라** — 검증 안 된 분류기 위에 여러
처리 경로를 얹는 건 이 프로젝트에서 이미 사고 이력이 있는 위험한
설계다. 대신 사용자가 직접 결정한 대체 방식을 쓴다:

> **모든 입력에 대해 검색 경로와 AI 답변 경로를 항상 둘 다 실행한다.**
> 분기 없음. §4.1의 "질문형이면 카드 목록 위에 AI 답변 블록 추가"라는
> 표현을 "항상 그렇게 한다"로 읽어라.

---

## 1. 목표 구조

`ui/pages/research.py`("검색·연구", 사이드바 라벨은 Task Order 041에서
이미 이렇게 바뀜)가 유일한 진입점이 된다:

1. 검색창 하나(기존 `_render_search_interface()`의 입력창 재사용,
   placeholder만 §4.1 문구로 조정: "성경 구절, 주제, 질문을
   입력하세요…")
2. 제출 시 **항상 둘 다** 실행:
   - 기존 `_execute_research_query()`(검색 경로, cards)
   - 기존 `chat.py::_handle_user_message()`가 쓰는 생성 경로(AI 답변) —
     **로직을 복제하지 말고 import해서 재사용**. `chat.py`의 함수를
     그대로 가져다 쓸 수 없는 부분(예: `chat_messages` 세션 상태에
     의존하는 부분)이 있으면, 그 부분만 두 페이지가 공유할 수 있게
     최소한으로 리팩터링해라(예: `_generate_answer(question) ->
     (answer_text, sources, citations)` 같은 순수 함수로 뽑아서
     `chat.py`/`research.py` 양쪽이 호출) — 이 리팩터링은 GenerationService
     호출 방식 자체는 바꾸지 않는, 함수 경계 재배치일 뿐이다.
3. 화면 순서: AI 답변 블록(있으면 위) → 그 아래 "참고한 자료"로
   검색 카드 목록(§4.1 원문 구조 그대로, "질문형일 때"라는 조건만
   제거해서 항상 이 순서).
4. AI 답변이 비어있거나 생성 실패해도(예: 관련 자료가 아예 없는
   순수 검색어) 카드 목록은 그대로 보여준다 — 답변 생성 실패가 검색
   결과 표시를 막으면 안 된다(독립적으로 실패 처리).

## 2. 사이드바 정리

`ui/app.py::_render_sidebar()`의 `pages` 딕셔너리에서 `"Chat"` 항목을
제거한다(Task Order 041 §0에서 "§4 구현 전까지는 유지"라고 명시했던
바로 그 조건이 지금 충족됨). `page_renderers`에서도 `"Chat":
render_chat_page` 매핑 제거. **`chat.py` 파일 자체나
`render_chat_page()` 함수를 삭제하지 마라** — 위 §1.2에서
`research.py`가 그 안의 생성 로직을 계속 import해서 쓴다. 죽은
진입점만 없애는 것이지 죽은 코드를 만드는 게 아니다.

`ui/app.py::_render_page_content()`의 `page_renderers`에서도 동일하게
정리.

## 3. 반드시 보호할 것 (건드리면 이 Task는 FAIL)

- `_render_send_to_sermon_research_button()`과 그 키 패턴
  (`send_sermon_{index}_...`, 라벨 "설교 연구에 추가") — Task Order
  042/043, `tests/test_sermon_research_hub.py`가 의존.
- `research_detail_selection` 세션 상태 패턴과 그걸 쓰는 "📄" 내비게이션
  버튼 — Task Order 044(이어서 읽기)와 `tests/test_reading_session.py`가
  의존.
- `render_citation_card()` 사용(Task Order 046) — 카드에 이미 붙어있는
  별점/메타 표시는 그대로 유지, 새로 만들지 마라.
- `core/research_workspace.py`의 "세션에 저장" 버튼(`add_query_result`
  호출) — Home의 "최근 검색" 카드(Tier A, `dashboard.py::
  _render_recent_search_card`)가 이 데이터를 읽는다.
- `chat_session_history.json` 디스크 저장 로직(`_save_chat_history`/
  `_load_chat_history`) — 사이드바에서 Chat 메뉴가 없어져도, 기존에
  저장된 대화 기록을 읽는 다른 코드가 있는지 먼저
  `grep -rn "chat_messages\|_CHAT_HISTORY_FILE"` 로 확인하고 판단해라
  (있으면 유지, 없으면 이번 통합 후 이 파일이 계속 갱신되는 게
  맞는지 CUE에게 보고서로 남기고 임의로 삭제하지 마라).
- Core/retrieval/registry 로직, TSU Pipeline, RAW 데이터, 기존 ADR —
  전부 무변경.

## 4. 이번 범위가 아닌 것 (하지 마라)

- §4.2 카드의 "정확히 3버튼(읽기/인용·출처 보기/설교 연구로 보내기)"
  구조로 재배열하는 것 — 현재 카드는 이미 내비게이션 버튼("📄", 사실상
  "읽기")과 "설교 연구에 추가"가 있고 인용 정보는 `render_citation_card`
  로 항상 표시 중이다. 이 버튼 구조를 스펙 그림과 똑같이 맞추는 건
  별도 Task Order(048 후보)로 다룬다 — 이번엔 손대지 마라.
- §5 읽기(연구 워크스페이스) 3영역 레이아웃 — 사용자가 보류 지시,
  여전히 미착수.
- 새 질문/검색 분류기 설계 — 위 경고 참고, 절대 만들지 마라.

## 5. 완료 조건

- [ ] 검색창 하나에 검색어를 넣었을 때: AI 답변 블록 + 검색 카드
      목록이 항상 같이 뜬다(둘 중 하나가 비어도 나머지는 정상 렌더)
- [ ] `ui/app.py` 사이드바에 "Chat" 항목이 더 이상 없음(육안 + grep)
- [ ] §3의 보호 대상 전부 무손상 확인(각 항목 개별 재현)
- [ ] `streamlit.testing.v1.AppTest`로 `ui/app.py` 전체 실행 — mock
      금지, 실제 결과 데이터(연구 카드 + 답변 둘 다 있는 상황)를
      세션 상태에 심어서 렌더 예외 0건 확인. 사이드바에서 "Chat"
      옵션 자체가 목록에 없는지도 `AppTest`로 확인
- [ ] `pytest tests/` 전체 실행(이번엔 변경 범위가 넓으니 관련 키워드
      grep만으로는 부족하다 — 전체 스위트를 돌려라) — 결과 그대로
      붙여넣기, 특히 `test_sermon_research_hub.py`/
      `test_reading_session.py`/`test_source_navigation.py` 통과 여부
      개별 언급
- [ ] `docs/agents/c1/C1-TASK-ORDER-047-REPORT.md` 작성 — 어떤 함수를
      어디서 어디로 옮겼는지(리팩터링 내역) 표로 정리, `chat_messages`
      디스크 저장 로직 처리 방침도 명시

## 6. 완료 후

CUE가 diff 전체 대조 + §3 보호 항목 개별 재현 + `AppTest`/전체
`pytest` 재실행으로 독립 검증한다. 범위가 넓은 만큼 이번엔 CUE도
꼼꼼히 볼 것 — 대충 넘어가지 않는다.
