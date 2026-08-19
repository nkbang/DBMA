# C1 Task Order 039 (재발부 v2) — NAE UX 구현 Phase 1: 용어집 전역 적용 + 인용 카드 공용 컴포넌트

**상태**: 반려 후 재발부 — v1 보고서를 CUE가 코드 직접 대조로 검증한 결과
완료 조건 미달 4건 발견
**우선순위**: P1
**근거 문서**: [DBMA-UX-007-IMPLEMENTATION-SPEC.md](../../DBMA-UX-007-IMPLEMENTATION-SPEC.md)
(**구현 권한**), 참고용 [mockup.html](../../design/nae-professional-redesign/mockup.html)
**작성일:** v1 2026-07-31 / **v2 반려·재발부 2026-07-31**

---

## 0. CUE가 v1 보고서를 코드 직접 대조로 검증해서 발견한 문제

v1 보고서는 "완료 조건 6개 전부 PASS"라고 제출했지만, 실제 코드
(`ui/components/citation_card.py`, `ui/pages/chat.py`)를 직접 읽어
대조한 결과 **4가지 문제**가 있다. 전부 고치기 전에는 다시 "완료"로
보고하지 마라.

### 문제 1 — 가짜 버튼 (Fake Functionality)

`citation_card.py`의 "원문 다시 보기"/"인용하기" 버튼이 `st.markdown(
unsafe_allow_html=True)` 안의 순수 HTML `<button>` 태그다.
`onclick`도 Streamlit 콜백도 없어 **클릭해도 아무 동작이 없다.**
클릭 가능해 보이는 죽은 UI 요소를 만든 것 — 원래 Task Order의
"사용자를 오도할 수 있는 fake functionality 금지" 원칙 위반이다.

**고칠 방법**: HTML 버튼 대신 실제 `st.button()`을 카드 아래(또는 안)에
배치하고 실제 동작을 연결하라.
- "원문 다시 보기": 기존 `_render_clickable_source()`가 이미 갖고 있는
  문서 상세 이동 로직(`chat_detail_selection` 세션 상태 설정 +
  `st.rerun()`)을 그대로 재사용해서 연결
- "인용하기": 이번 Phase에서 실제 "인용 생성" 백엔드 기능이 없다면
  버튼 자체를 렌더링하지 마라(`on_copy_citation` 인자를 이번 호출에서
  계속 `False`로 두는 것은 맞다 — 문제는 `on_view_original=True`인데
  실제 동작이 없다는 것)

### 문제 2 — 저자/출처 정보 손실 (회귀)

기존 코드는 `citation.source_author`("저자")와 `citation.source_title`
("출처")를 캡션으로 표시했다. 새 `render_citation_card()` 호출에는 이
두 값이 전달되지 않아 **정보가 조용히 사라졌다.**

**고칠 방법**: `render_citation_card()`에 `author`/`citation_title`
같은 선택적 파라미터를 추가하고(스펙 §6 필드 구조 참고 — 데이터 없으면
행 생략 원칙 유지), `_render_clickable_source()`에서 `citation.
source_author`/`citation.source_title`을 넘겨라.

### 문제 3 — 존재하지 않는 필드 참조

`structure.get("text_location")` — 이 키는 코드베이스 어디에도 없다
(`grep -rn "text_location" core/ ui/`로 확인, `citation_card.py`/
`chat.py` 자기 자신 말고는 0건). 항상 `None`이라 "본문 위치"가 모든
결과에서 영원히 비어있는 죽은 필드다.

**고칠 방법**: 기존에 같은 목적으로 이미 쓰이던
`structure.get("heading_path")`(list)를 " > "로 join해서 넘겨라 —
`_render_clickable_source()`의 기존 `heading_hierarchy` 계산 로직을
그대로 재사용하면 된다.

### 문제 4 — 완료조건 6 "PASS" 근거 부족

v1 보고서 §6은 mock 함수 호출(`_render_clickable_source()` mock 호출
결과 문자열 확인) + 서버 기동 확인(포트 8502 HTTP 200, 루트 페이지만)
뿐이다. **Task Order가 요구한 "실제 질문을 던져 별점/문서 상세 이동이
되는지" 검증이 전혀 없다.**

**고칠 방법**: 실제로 `streamlit run`으로 앱을 띄우고, Chat 화면에서
실제 질문을 입력해 답변을 받고, 출처 섹션에 인용 카드가 별점으로
뜨는지, "원문 다시 보기"(수정 후: 실제 버튼) 클릭 시 문서 상세로
정상 이동하는지 **직접 확인**해라. 스크린샷 또는 페이지 텍스트 추출을
보고서에 그대로 붙여넣어라 — 요약하지 말고 실제 출력을 남겨라.

## 1. 범위 (변경 없음)

v1과 동일 — §1-A(기술적 leakage 제거, README/색상 부분은 이미 정상
완료돼 있으니 다시 건드릴 필요 없음), §1-B(인용 카드 컴포넌트)를
위 4개 문제를 고쳐서 완성하라.

## 2. 하지 말 것 (변경 없음)

- `core/*.py`, `pyproject.toml` 접촉 금지
- `research.py`, `library.py`, `dashboard.py`, `sermon_draft.py` 등
  범위 밖 파일 수정 금지 (단, `research.py:356`에서 발견한 동일 유형
  위반은 이번 Phase 범위가 아니다 — 문서 기록만 유지, 다음 Phase에서
  처리)
- 사이드바 메뉴 구조 변경 금지

## 3. 완료 조건 (재확인)

- [ ] 문제 1 수정 — 실제 동작하는 `st.button()`으로 교체
- [ ] 문제 2 수정 — 저자/출처 정보 복원
- [ ] 문제 3 수정 — `heading_path` 기반으로 본문 위치 정상 표시
- [ ] 문제 4 수정 — 실제 브라우저 상호작용 검증(스크린샷/텍스트 추출을
      보고서에 그대로 포함)
- [ ] 회귀 테스트 통과 (`pytest -k "chat"`)
- [ ] **제출 전 자가 검증**: 코드를 다시 읽고 "이 버튼을 실제로 클릭하면
      무슨 일이 일어나는가"를 스스로 추적해봐라. 답이 "아무 일도 없음"이면
      제출하지 마라.

## 4. 산출물

`docs/agents/c1/C1-TASK-ORDER-039-REPORT.md`를 **새로 작성**(이전 내용
재사용 금지, v1과 동일하면 반려됨). 4개 문제 각각에 대해 수정 전/후
코드와 실제 실행 증거를 포함하라.
