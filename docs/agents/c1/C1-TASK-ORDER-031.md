# C1 Task Order 031 — 검색 결과 상세보기 Phase 3: Chat 페이지 연결

**상태**: 발급됨 — 구현 착수 가능
**우선순위**: P1
**선행 작업**: Task Order 029(Phase 1, `core/document_detail.py`)·030(Phase 2, `ui/components/detail_panel.py`)
완료·검증됨(전체 회귀 1066/1066). 두 모듈의 기존 함수/시그니처 재사용, 재정의 금지.
**근거 문서**: [docs/architecture/DBMA-Search-Result-Detail-Panel-Plan-v1.md](../../architecture/DBMA-Search-Result-Detail-Panel-Plan-v1.md)
(§0 2026-07-30 정정 내용 반드시 먼저 읽을 것)
**작성일**: 2026-07-30
**모드 제약**: `core/document_detail.py`, `ui/components/detail_panel.py`, `core/retrieval.py`,
`ui/components/source_link.py`(파일 자체) 절대 미접촉. 이번 작업 대상은 **`ui/pages/chat.py` 하나**다.

---

## 1. 배경 — 현재 상태 재확인 (착수 전 필수)

`ui/pages/chat.py`의 기존 출처 클릭 메커니즘은 다음과 같이 **일부가 죽은 코드**다:

- `_render_clickable_source()`가 클릭 시 `st.session_state["_dbma_source_nav"]`를 설정하지만, chat.py
  안에서 아무도 이 값을 읽지 않는다 (`ui.components.source_link.render_pending_source_detail()`을
  호출하는 코드가 없음).
- `_render_source_modal()`이 만드는 JS 모달을 여는 `st.session_state["modal_open_functions"]`도
  아무도 읽지 않는다 — 클릭해도 모달이 실제로 열리지 않는다.
- `_render_source()` 안의 `from ui.components.source_link import source_link` import도 실제로는
  호출되지 않는 죽은 import다.

이번 Task Order는 이 죽은 코드를 **정리하면서 동시에** Phase 1/2 산출물로 대체한다. `ui/components/
source_link.py` 파일 자체는 다른 곳에서 쓰일 수도 있으니 손대지 말고(§모드 제약), chat.py 안에서의
사용(죽은 import 한 줄)만 제거한다.

---

## 2. 구현 범위

### 2.1 상태 관리

신규 세션 키 `st.session_state["chat_detail_selection"]`:
```python
{"source_file": str, "document_id": str, "query_terms": list[str]}
```
클릭 시 이 값을 설정하고 `st.rerun()`. `_dbma_source_nav`/`modal_open_functions` 관련 코드는 삭제한다
(죽은 코드이므로 삭제해도 다른 기능에 영향 없음 — §1에서 이미 확인됨).

`query_terms`는 직전 사용자 질문(`chat_messages`에서 이 assistant 메시지 바로 앞의 user 메시지의
`content`)을 공백 기준으로 분리한 리스트로 충분하다 (정교한 형태소 분석 불필요 — Phase 1의
`get_document_detail()`도 `str.find()` 기반 단순 탐색이므로 일관성 유지).

### 2.2 레이아웃

`render_chat_page()`를 수정:
- `st.session_state.get("chat_detail_selection")`이 있으면 `st.columns([2, 1])`(또는 적절한 비율,
  C1 판단)로 2단 레이아웃 — 왼쪽엔 기존 내용(범위 선택기 + 채팅 이력 + 입력창) 그대로, 오른쪽엔
  `core.document_detail.get_document_detail(...)` 호출 후 `ui.components.detail_panel.render_detail_panel(...)`.
- 선택이 없으면 기존처럼 1단 레이아웃 그대로 (변경 없음).
- 상세 패널 상단에 "닫기" 버튼 — 클릭 시 `chat_detail_selection`을 `None`으로 지우고 `st.rerun()`.

### 2.3 `_render_source()` 계열 수정

- `_render_clickable_source()`의 버튼 클릭 동작을 §2.1의 새 상태 설정으로 교체.
- `_render_source_modal()` 함수와 그 호출부, `modal_open_functions` 관련 코드, 죽은
  `from ui.components.source_link import source_link` import를 제거한다.
- 기존 "신뢰도 표시"(`st.caption(f"신뢰도: ...")`) 등 살아있는 기능은 그대로 유지.

### 2.4 결과 목록 유지 확인

요청서 수용 기준의 핵심 — 상세 패널이 열려도 왼쪽 컬럼의 채팅 이력·범위 선택 상태가 그대로 보이는지,
그리고 다른 출처를 연속으로 클릭했을 때 상세 패널 내용만 바뀌고 왼쪽은 그대로인지 반드시 확인.

### 2.5 이번 범위에서 제외

- Research 페이지 — 계획서 결정대로 Chat 먼저, Research는 후속.
- 다중 문서 비교, 새 창/탭 — 계획서에서 이미 P1/P2로 분류, 이번 범위 밖.

---

## 3. 검증 계획

1. 기존 회귀 스위트 전체 재실행 — 1066/1066 유지 확인 (chat.py를 수정하므로 관련 테스트가 있다면 특히
   주의). pytest 출력 그대로 복사.
2. **수동 검증** (자동화 어려움 — Streamlit 실 서버 필요):
   - `streamlit run dbma_ui.py`로 Chat 탭 접속
   - 질문 1개 검색 → 결과 출처 하나 클릭 → 우측에 상세 패널이 뜨고 왼쪽 채팅 이력은 그대로인지 확인
   - 다른 출처 클릭 → 상세 패널 내용이 바뀌는지 확인 (왼쪽은 안 바뀜)
   - "닫기" 클릭 → 1단 레이아웃으로 복귀하는지 확인
   - 스크린샷 캡처
3. `git diff` 결과에 `core/document_detail.py`, `ui/components/detail_panel.py`, `core/retrieval.py`,
   `ui/components/source_link.py`가 **포함되지 않는지** 확인 (전부 빈 diff여야 함).

---

## 4. 보고 형식

1. `ui/pages/chat.py` diff (죽은 코드 삭제 부분과 신규 연결 부분 구분해서 설명)
2. `git diff core/document_detail.py ui/components/detail_panel.py core/retrieval.py ui/components/source_link.py` — 반드시 빈 diff
3. 테스트 실행 결과 — pytest 출력 그대로 복사 (개수 오보/서술 조작 재발 시 이전처럼 CUE가 코드를 직접
   대조해 확인한다는 점 참고)
4. §3.2 수동 검증 스크린샷 (결과 목록 유지 확인이 핵심이므로 반드시 첨부)
5. Research 페이지 확장 착수 전 CUE가 결정해야 할 사항이 있으면 정리

---

## 5. 다음 조치

Phase 3 완료·검증되면 계획서의 MVP(P0) 범위가 전부 끝난다. Research 페이지 확장, 원본 파일 열기 개선
등 후속 여부는 CUE가 사용자와 논의 후 결정.
