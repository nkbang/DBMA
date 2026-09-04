# C1 Task Order 032 — Phase 3 버그 수정: 출처 클릭이 감지되지 않는 위젯 key 문제

**상태**: 발급됨 — 구현 착수 가능
**우선순위**: P0 (Phase 3의 핵심 기능이 동작하지 않는 블로킹 버그)
**선행 작업**: Task Order 031(Phase 3) — 배선 자체는 맞게 됐으나 클릭이 감지되지 않는 버그가 있음.
**근거 문서**: [docs/architecture/DBMA-Search-Result-Detail-Panel-Plan-v1.md](../../architecture/DBMA-Search-Result-Detail-Panel-Plan-v1.md)
(Phase 3 항목 — CUE가 실제 브라우저로 재현 확인한 버그 내용 참고)
**작성일**: 2026-07-30
**모드 제약**: 이번에도 `ui/pages/chat.py` 하나만 수정. 다른 파일 미접촉.

---

## 1. 버그 원인 (CUE가 코드 읽기 + 브라우저 재현으로 확인함)

`_render_clickable_source()`(약 442~449행)에서 버튼 `key`를 다음과 같이 만든다:

```python
_counter_key = "_dbma_source_btn_counter"
if _counter_key not in st.session_state:
    st.session_state[_counter_key] = 0
_instance_idx = st.session_state[_counter_key]
st.session_state[_counter_key] += 1
btn_key = f"nav_src_{_instance_idx}_{abs(hash(candidate.tsu_id)) & 0xFFFFFFFF:x}"
```

`_dbma_source_btn_counter`는 **세션 전역 상태**라서 스크립트가 재실행될 때마다(사용자가 버튼을 클릭해서
발생하는 rerun 포함) 계속 증가한다. 문제는:

1. 첫 렌더링에서 어떤 출처 버튼이 `nav_src_7_abcd1234` 같은 key로 그려진다.
2. 사용자가 그 버튼을 클릭한다 → Streamlit이 rerun을 트리거한다.
3. 그 rerun 스크립트가 실행되면서 `_render_clickable_source()`가 다시 호출되고, 카운터가 한 번 더
   증가한 상태에서 실행되므로 **같은 버튼인데 이번엔 `nav_src_8_abcd1234`라는 다른 key**로 그려진다.
4. Streamlit은 클릭 이벤트를 원래 key(`nav_src_7_...`)에 대해 발생시켰는데, 이번 rerun에서는 그 key를
   가진 위젯이 존재하지 않으므로 `st.button(...)`이 `False`를 반환한다 — **클릭이 사실상 무시된다.**

CUE가 실제 `streamlit run dbma_ui.py`로 브라우저에서 출처 버튼을 클릭해 재현 확인함 — 클릭해도
`chat_detail_selection`이 설정되지 않고 상세 패널이 열리지 않음.

---

## 2. 수정 범위

### 2.1 위젯 key를 매 rerun마다 바뀌지 않는 안정적인 값으로 변경

`_counter_key` 방식을 버리고, **같은 렌더링 컨텍스트에서 항상 같은 key가 나오도록** 만든다. 후보:

- `candidate.tsu_id` + 이 출처가 속한 메시지의 인덱스(`chat_messages` 리스트에서의 위치)를 조합.
  같은 tsu_id가 여러 메시지에 걸쳐 나올 수 있으므로 메시지 인덱스로 구분하면 충분히 안정적이다.
- 구체적으로: `_render_source()`/`_render_clickable_source()` 호출부(현재 `chat_messages` 순회하며
  `_render_source(candidate)`를 부르는 두 곳, §1의 배경 참고)에서 **메시지 인덱스**와 **그 메시지 내
  source 목록에서의 순번**을 인자로 넘겨받아 key 생성에 사용한다:
  ```python
  btn_key = f"nav_src_{msg_index}_{source_index_in_msg}_{abs(hash(candidate.tsu_id)) & 0xFFFFFFFF:x}"
  ```
  이 값은 몇 번을 재실행해도 항상 동일하다(메시지 리스트가 안 바뀌는 한).
- `_dbma_source_btn_counter` 세션 상태와 그 증가 로직은 완전히 제거한다.

### 2.2 호출부 수정

`_render_source(candidate)`를 호출하는 곳들(스트리밍 중 실시간 렌더 1곳 + `_render_chat_history()`의
과거 메시지 재렌더 1곳, 또는 몇 곳이 있는지 코드 확인 후 전부)에서 `enumerate()`로 메시지 인덱스와
source 인덱스를 함께 넘기도록 시그니처를 조정한다. 시그니처를 바꾸는 게 자연스러우면 그렇게 하고,
전역 카운터를 인자로 바꾸는 최소 변경이면 그렇게 해도 됨 — 핵심은 **"key가 렌더링 위치에만 의존하고,
그 위치가 바뀌지 않는 한 재실행 횟수와 무관하게 항상 동일해야 한다"**는 성질만 지키면 된다.

### 2.3 검증 (반드시 실제 브라우저로 할 것 — 이번엔 자동화 테스트만으로 완료 처리하지 말 것)

- 기존 회귀 스위트 재실행 — 1066/1066 유지.
- **`streamlit run dbma_ui.py`로 직접 브라우저 테스트**: 질문 검색 → 출처 클릭 → 우측 상세 패널이
  실제로 열리는지 확인. 열리면 스크린샷. 안 열리면 어떤 증상인지 구체적으로 기록하고, 원인을 더 파서
  다시 수정할 것 (이번에도 안 되면 "완료"로 보고하지 말 것 — 지난 Task Order에서 실제 동작 확인 없이
  완료로 보고된 사례가 있었음, 이번엔 반드시 클릭이 실제로 먹히는 것까지 확인).
- 두 번째 출처도 클릭해서 패널 내용이 바뀌는지, "닫기" 버튼이 실제로 패널을 닫는지도 확인.

---

## 3. 보고 형식

1. `ui/pages/chat.py` diff (key 생성 로직 변경 부분 명확히)
2. 테스트 실행 결과 (pytest 출력 그대로 복사)
3. **브라우저 클릭 테스트 스크린샷 — 클릭 전/후 반드시 둘 다 첨부.** "닫기"까지 눌러본 스크린샷도.
4. 만약 여전히 안 되면, 무엇을 시도했고 어떤 증상이었는지 정직하게 기록 (완료로 보고하지 말 것)

---

## 4. 다음 조치

이 버그가 실제로 고쳐지고 브라우저에서 클릭이 확인되면, 계획서의 MVP(P0) 범위가 비로소 완료된다.
