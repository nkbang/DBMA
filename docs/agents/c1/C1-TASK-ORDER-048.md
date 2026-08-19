# C1 Task Order 048 — UX-007 §5 읽기 (연구 워크스페이스)

**상태**: 발급됨 — 착수 가능
**우선순위**: P1
**근거 문서**: [DBMA-UX-007-IMPLEMENTATION-SPEC.md](../../DBMA-UX-007-IMPLEMENTATION-SPEC.md) §5(Reading Specification)

---

## 0. 착수 전 확인 사항 (스펙과 실제 코드가 다른 부분)

스펙 §5는 "본문 영역은 신규 — 현재 어떤 화면에도 전체 본문 표시
기능 없음"이라고 적혀 있지만 **사실이 아니다**. `ui/components/
detail_panel.py::render_detail_panel()`가 이미 제목/메타데이터(문서
유형/작성자/생성일)/태그/`match_locations` 캡션/**전체 본문**(검색어
하이라이트 포함, "본문 처음부터 보기" expander)/`source_path`까지
전부 그리고 있다(Search Detail Panel v1, `research.py::
_render_research_page_with_detail()`와 `chat.py::
_render_chat_page_with_detail()`가 이미 씀). **이 컴포넌트를 다시
만들지 마라** — 아래 §2에서 다듬기만 한다.

**중요**: `chat.py::_render_chat_page_with_detail()`은 Task Order
047로 Chat 메뉴가 사이드바에서 사라진 뒤 **더 이상 UI에서 도달
불가능한 죽은 경로**다(파일 자체는 `generate_answer()` 공유 때문에
남아있음). 이번 작업은 **`research.py` 쪽만** 고친다 —
`chat.py`의 해당 함수는 건드리지 마라(죽은 코드 정리는 이번 범위
아님).

## 1. 목표 — `research.py::_render_research_page_with_detail()` 재구성

현재 구조(`cols = st.columns([2, 1])`, 왼쪽=검색 인터페이스 전체,
오른쪽=문서 상세)는 스펙의 3영역 레이아웃과 반대다 — 스펙은 "본문을
읽으면서 그 자리에서 관련 자료를 찾는" 화면을 원한다. 아래처럼
재구성한다:

```text
┌─────────────────────────┬───────────────┐
│                         │  연구 영역     │
│      본문 영역           │  - 관련 자료   │
│  (기존 detail_panel      │  - 이어서 질문 │
│   재사용, 타이포만 보강)  │               │
├─────────────────────────┴───────────────┤
│      행동 영역 (하단, 3버튼 고정)          │
│  인용하기 / 연구에 추가 / 설교 연구로 보내기│
└─────────────────────────────────────────┘
```

- 좌우 비율은 본문이 주가 되도록(`st.columns([2, 1])`을 본문 쪽에
  주는 방향으로 — 지금과 반대) 조정.
- "닫기" 버튼은 유지(현재 위치 그대로 둬도 되고 상단으로 옮겨도 됨,
  기능만 유지).

### 1.1 본문 영역

`render_detail_panel()`은 그대로 호출하되, 스펙이 요구하는 타이포
(`Source Serif 4`, 17px, 본문 최대 폭 640px, 줄간격 1.85)가 지금
없다 — `detail_panel.py`에 스타일 블록을 추가해라. 새 컴포넌트를
만들지 말고 기존 `render_detail_panel()` 내부(또는 호출 직전에
`st.markdown("<style>...</style>")`)에 CSS만 추가.

### 1.2 연구 영역(우측 패널)

- **관련 자료**: 완전히 새로 검색하지 마라 — `research_detail_
  selection`에 이미 있는 `query_terms`(이 문서로 오게 된 원래 검색어)
  로 `_execute_research_query()`를 그대로 재사용해서 재실행하고,
  결과 중 **지금 보고 있는 문서(`document_id` 또는 `source_file`
  일치)만 제외**하고 카드로 보여준다. 카드는 §4.2/Task Order 046에서
  이미 만든 `render_citation_card()`를 그대로 쓰되, 버튼은 "읽기"
  하나만(스펙 명시) — `on_view_original=True`로 설정하고, 클릭 시
  `research_detail_selection`을 그 문서로 갱신(같은 화면 안에서
  전환, `st.rerun()`).
- **이어서 질문**: Task Order 047에서 고친 `chat.py::generate_answer()`
  를 그대로 가져다 쓴다. `file_scope=[source_file]`을 넘겨서 "현재
  문서를 문맥으로 우선"하라는 스펙 요구를 만족시켜라(새 우선순위
  로직을 만들지 말고 이미 있는 `file_scope` 파라미터로 해결—
  `generate_answer(question, file_scope=[source_file])`). 입력창 +
  답변 표시만 있으면 된다, 대화 히스토리는 필요 없음(단발성 질문).

### 1.3 행동 영역 (3버튼, 순서 고정)

- **인용하기**(신규): 클릭 시 출처/저자/위치 정보를 텍스트로 펼쳐
  보여줘서 사용자가 직접 복사할 수 있게 한다(Streamlit엔 클립보드
  API가 없다 — `st.code()`로 표시해 사용자가 복사 버튼을 누르게
  하는 정도면 충분, 새 JS 붙이지 마라).
- **연구에 추가**: `core/research_workspace.py::add_query_result()`
  (기존 함수, Core 무변경)를 재사용 — `st.session_state
  ["research_session_id"]`(이미 있음)에 현재 문서를 참조로 추가.
  `response_package` 인자 형태를 맞추기 까다로우면, 문서 참조 하나만
  담은 최소 dict(`{"top_k_results": [...]}` 형태, `add_query_result`
  구현부 참고)를 만들어 넘겨라 — `add_query_result` 함수 자체는
  손대지 마라.
- **설교 연구로 보내기**: 기존 `sermon_research_selection` 버퍼에
  append(Task Order 042 패턴 그대로). **주의**: `DocumentDetail`
  (`core/document_detail.py`)에는 `tsu_id` 필드가 없다 — 흡수 로직
  (`sermon_research.py::_absorb_selection()`)이 `tsu_id`로 중복
  제거를 하니, 여기선 `tsu_id` 자리에 `document_id`를 넣어서 append해라
  (`{"tsu_id": document_id, "document_id": document_id, "excerpt": ...,
  "source_label": source_file, "added_at": ...}`) — 흡수/렌더링 쪽
  코드(`sermon_research.py`)는 건드릴 필요 없다, 이미 dict 아무
  값이나 받는다.

## 2. 반드시 보호할 것 (건드리면 FAIL)

- `research_detail_selection`을 세팅하는 다른 모든 호출부(검색
  결과 카드의 "📄" 버튼, Home의 "이어서 읽기" 카드) — 필드 이름/
  구조 무변경.
- `_render_send_to_sermon_research_button()`, `sermon_research_
  selection` 소비 로직(`sermon_research.py`) — 무변경, 이번엔 그냥
  같은 패턴으로 새 호출 지점만 추가.
- `render_citation_card()`, `generate_answer()` — 함수 시그니처
  무변경, 호출만 추가.
- `chat.py::_render_chat_page_with_detail()` — 안 건드림(§0 참고).
- Task Order 047의 검색 페이지 본문(`render_research_page()`의
  검색어 없을 때 흐름, AI 답변+카드 목록) — 무변경, 이번 건 오직
  "상세 보기 모드"(`research_detail_selection is not None`)일 때만
  적용.
- Core/retrieval/registry 로직, TSU Pipeline, RAW 데이터, 기존 ADR —
  전부 무변경.

## 3. 완료 조건

- [ ] 문서 상세를 열면 본문이 좌측 주 영역에 크게 표시(타이포 반영)
- [ ] 우측에 관련 자료 카드(현재 문서 제외) + 질문 입력창이 보임,
      질문 시 실제 답변이 나옴(빈 문자열 아님 — Task Order 047과
      같은 검증 방식으로 실측)
- [ ] 하단에 3버튼(인용하기/연구에 추가/설교 연구로 보내기) 순서
      고정으로 존재, 각각 클릭 시 예외 없이 동작
- [ ] §2 보호 대상 grep + 개별 재현으로 무손상 확인
- [ ] `streamlit.testing.v1.AppTest`로 실제 흐름 재현: 검색 →
      결과 카드 "📄" 클릭 → 상세 보기 진입 → 관련 자료 카드 존재 확인
      → 질문 입력 → 답변 비어있지 않음 확인 → 3버튼 각각 클릭 →
      예외 0건
- [ ] `pytest tests/` **전체** 실행(부분 배치 금지 — Task Order 047
      에서 두 번이나 지적된 사항이다, 이번엔 반드시 지켜라) — 결과
      그대로 붙여넣기
- [ ] `docs/agents/c1/C1-TASK-ORDER-048-REPORT.md` 작성

## 4. 완료 후

CUE가 diff 대조 + 실제 함수 호출/AppTest 재현 + 전체 pytest로 독립
검증한다.
