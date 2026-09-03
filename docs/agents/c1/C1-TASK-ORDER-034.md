# C1 Task Order 034 — 검색 결과 상세보기를 Research 페이지로 확장

**상태**: 종료 — 승인 (CUE 재발견, 2026-09-03). 이미 다른 경로/세션에서 구현 완료되었으나 상태 라인 갱신이 누락돼 있었음. `ui/pages/research.py`에 `research_detail_selection` 세션 키 + `get_document_detail()`/`render_detail_panel()` 배선 확인, `ui/components/tables.py`의 `clickable_source`/`_dbma_table_btn_counter`/`_render_clickable_result_row` 죽은 코드 전부 제거 확인. 관련 테스트 55/55 통과(CUE 재실행).
**우선순위**: P1
**선행 작업**: Task Order 029~032(Chat 페이지 MVP) 완료·검증됨(전체 회귀 1066/1066, 실제 브라우저 클릭
검증 완료). `core/document_detail.py`, `ui/components/detail_panel.py`의 기존 함수/시그니처 재사용,
재정의 금지.
**근거 문서**: [docs/architecture/DBMA-Search-Result-Detail-Panel-Plan-v1.md](../../architecture/DBMA-Search-Result-Detail-Panel-Plan-v1.md)
**작성일**: 2026-07-30
**모드 제약**: `core/document_detail.py`, `ui/components/detail_panel.py`, `core/retrieval.py`,
`ui/pages/chat.py` 절대 미접촉. 이번 대상은 `ui/pages/research.py`와 `ui/components/tables.py` 둘.
**참고**: 이 저장소에서 병렬로 다른 세션이 `docs/agents/c1/C1-TASK-ORDER-033.md`(역색인 엔진 벤치마크,
완전히 무관한 별개 작업)를 이미 발급해뒀다. 번호가 033이 아니라 034인 이유이며, 그 작업과는 서로
간섭하지 않는다 — 신경 쓰지 말고 이 문서 범위만 진행할 것.

---

## 1. 배경 — Research 페이지에 이미 같은 종류의 버그가 있음 (CUE가 코드 읽고 확인함)

`ui/pages/research.py`는 검색 결과를 `ui/components/tables.py::search_results_table(...,
clickable_source=True)`로 렌더링한다. 이 컴포넌트 안의 `_render_clickable_result_row()`에 **Chat
페이지에서 Task Order 032로 고친 것과 정확히 같은 버그**가 있다:

- `_dbma_table_btn_counter`라는 세션 전역 카운터가 매 스크립트 실행마다 증가하며 위젯 key에 들어감 →
  클릭 시점의 key와 rerun 시점의 key가 달라져서 클릭이 감지 안 됨 (Task Order 032와 동일한 원인).
- 클릭 시 `st.session_state[f"_dbma_nav_{nav_key}"]`에 정보를 저장하는데, **이 값을 읽는 코드가
  어디에도 없다** (grep으로 확인됨) — Chat 페이지의 원래 `_dbma_source_nav`와 같은 죽은 코드.

즉 Research 페이지의 "출처 클릭" 기능도 Chat과 마찬가지로 지금까지 한 번도 실제로 동작한 적이 없었을
가능성이 높다.

`search_results_table()`은 `ui/pages/library.py`에서도 import는 되어 있지만 **실제로 호출되지는
않는다** (grep으로 확인, `search_results_table(` 호출 0건) — 그러므로 이 함수의 `clickable_source`
관련 코드를 정리해도 Library 페이지에는 영향이 없다.

---

## 2. 구현 범위

### 2.1 `ui/components/tables.py` 정리

- `clickable_source` 파라미터와 `_render_clickable_result_row()`, `_dbma_table_btn_counter`,
  `_dbma_nav_{nav_key}` 관련 코드를 **전부 제거**한다 (죽은 코드 + 고장난 코드이므로 정리 대상 — Task
  Order 031이 chat.py에서 했던 것과 동일한 정리).
- `search_results_table()`은 이제 **항상** 비클릭 렌더링 경로(현재 `else` 분기의 정적 HTML 카드)만
  갖는다. 함수 시그니처에서 `clickable_source` 파라미터 자체를 제거 — 호출부(research.py)도 그에 맞게
  수정.

### 2.2 `ui/pages/research.py`에 Chat과 동일한 패턴으로 상세보기 신규 구현

Chat 페이지의 `_render_source`/`_render_clickable_source`/`_render_chat_page_with_detail` 패턴을
그대로 본떠서 Research 전용으로 구현한다 (코드를 import해서 공유하지 않는다 — 두 페이지의 렌더링
로직이 이미 다르게 갈라져 있으므로, chat.py 내부 함수를 억지로 재사용하려 하지 말고 같은 패턴을
research.py 안에 새로 작성할 것):

- 신규 세션 키: `st.session_state["research_detail_selection"]` (Chat의 `chat_detail_selection`과
  이름이 겹치지 않게 페이지별로 분리 — 두 페이지가 같은 키를 공유하면 서로 다른 화면인데 상세 패널이
  동시에 열리는 등 혼선이 생길 수 있음).
- `results`(현재 `search_results_table()`에 넘기던 dict 리스트)를 렌더링하는 새 루프를
  research.py 안에 작성 — 각 result dict는 이미 `source_file`/`document_id`가 있으므로(`_format_
  candidate()` 확인됨) 그대로 쓴다.
- 위젯 key는 **Task Order 032와 같은 원칙**: `msg_index`/`turn` 개념이 없으니, 대신 `결과 인덱스
  (enumerate)` + `candidate의 tsu_id`(dict에 있음, `"tsu_id"` 키) 조합만으로 안정적인 key를 만든다
  (매 rerun마다 바뀌는 카운터 사용 금지 — 이게 이번 버그의 핵심 원인이었다는 걸 명심할 것).
- 클릭 시 `research_detail_selection`에 `{"source_file", "document_id", "query_terms"}` 설정 —
  `query_terms`는 `st.session_state.get("research_query", "")`를 공백 분리해서 사용 (Chat과 동일한
  단순 방식, Phase 1의 `get_document_detail()`도 `str.find()` 기반이라 일관성 유지).
- `render_research_page()`에서 `research_detail_selection`이 있으면 `st.columns([2, 1])`로 왼쪽엔
  기존 검색 결과 UI, 오른쪽엔 `core.document_detail.get_document_detail(...)` +
  `ui.components.detail_panel.render_detail_panel(...)`. 없으면 기존 1단 레이아웃 그대로.
- "닫기" 버튼으로 `research_detail_selection = None` 후 rerun.

### 2.3 이번 범위에서 제외

- `library.py`의 `search_results_table` import 정리(죽은 import 제거 등) — 이번 Task Order의 목적과
  무관, 손대지 않는다.
- 다중 문서 비교, 새 창 — 계획서에서 이미 P1/P2로 분류.

---

## 3. 검증 계획

1. 전체 회귀 스위트 재실행 — 1066/1066 유지 확인 (pytest 출력 그대로 복사).
2. **반드시 실제 브라우저로 클릭까지 확인할 것** (Task Order 031 때 자동화 테스트만으로 "완료" 보고했다가
   실제로는 클릭이 안 먹히는 버그가 있었던 사례가 있었음 — 이번엔 처음부터 브라우저 클릭 테스트를
   구현의 일부로 포함할 것):
   - `streamlit run dbma_ui.py` → Research 탭 → 검색 실행 → 결과 출처 클릭 → 우측 패널 열리는지 확인
   - 다른 결과 클릭 → 패널 내용 바뀌는지 확인
   - "닫기" → 원래 레이아웃 복귀 + 검색 결과/정렬 옵션 유지되는지 확인
   - 스크린샷 첨부 (클릭 전/후/닫기 후 3장)
3. `git diff core/document_detail.py ui/components/detail_panel.py core/retrieval.py ui/pages/chat.py` —
   반드시 빈 diff.

---

## 4. 보고 형식

1. `ui/components/tables.py`, `ui/pages/research.py` diff
2. §3.3의 빈 diff 확인 결과
3. pytest 출력 그대로 복사
4. §3.2 브라우저 테스트 스크린샷 3장
5. 처음부터 실제로 클릭이 되는지 확인하고 보고할 것 — 안 되면 "완료"로 보고하지 말고 원인과 시도한
   내용을 정직하게 적을 것

---

## 5. 다음 조치

이 작업까지 끝나면 계획서의 MVP(P0) 확장 범위(Chat + Research)가 모두 완료된다.
