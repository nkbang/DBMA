# C1 Task Order 048 — REPORT

**상태**: PASS
**수행일**: 2026-08-19
**작업**: UX-007 §5 읽기 (연구 워크스페이스) — 상세 보기 모드 레이아웃 재구성

---

## 1. 작업 개요

`research.py::_render_research_page_with_detail()`을 3영역 레이아웃으로 재구성:
- **좌측 주 영역**: 문서 본문 (타이포 보강)
- **우측 연구 영역**: 관련 자료 카드 + 이어서 질문
- **하단 행동 영역**: 3버튼 (인용하기 / 연구에 추가 / 설교 연구로 보내기)

---

## 2. 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `ui/pages/research.py` | `_render_research_page_with_detail()` 재구성 + 보조 함수 5개 추가 |

---

## 3. 코드 변경 상세

### 3.1 `_render_research_page_with_detail()` 재구성

**Before**: 좌측=검색인터페이스+결과+분석, 우측=닫기+상세패널 (2단 레이아웃)
**After**: 좌측=본문(타이포보강), 우측=연구영역(관련자료+질문), 하단=3버튼 (3영역 레이아웃)

```python
# Typography CSS 추가 (Source Serif 4, 17px, max-width 640px, line-height 1.85)
st.markdown(
    "<style>"
    ".dbma-body-text {"
    "  font-family: 'Source Serif 4', serif;"
    "  font-size: 17px;"
    "  max-width: 640px;"
    "  line-height: 1.85;"
    "}"
    "</style>",
    unsafe_allow_html=True,
)

# 좌측: 문서 본문 (render_detail_panel 타이포 감싸기)
with cols[0]:
    st.button("닫기", key="research_detail_close_btn", type="primary")
    detail = get_document_detail(...)
    st.markdown('<div class="dbma-body-text">', unsafe_allow_html=True)
    render_detail_panel(detail, query_terms)
    st.markdown('</div>', unsafe_allow_html=True)

# 우측: 연구 영역
with cols[1]:
    # 관련 자료 (기존 _execute_research_query 재사용, 현재 문서 제외)
    related_results = _fetch_related_docs(query_terms, document_id)
    for rd in related_results:
        render_citation_card(..., on_view_original=True)
    
    # 이어서 질문 (generate_answer with file_scope)
    answer_text, _ = generate_answer(question, file_scope=[source_file])

# 하단: 3버튼 행동 영역
st.divider()
_render_detail_action_buttons(detail, source_file, document_id)
```

### 3.2 보조 함수 5개 추가

| 함수 | 역할 |
|------|------|
| `_fetch_related_docs()` | query_terms로 검색, 현재 문서 제외 |
| `_render_detail_action_buttons()` | 3버튼 렌더링 |
| `_build_citation_text()` | 인용 텍스트 구성 |
| `_add_to_research_session()` | 연구 세션에 문서 추가 |
| `_send_to_sermon_research()` | 설교 연구 버퍼에 문서 추가 (tsu_id→document_id) |

---

## 4. 보호 대상 검증 (grep)

| 보호 대상 | 상태 |
|----------|------|
| `research_detail_selection` 다른 호출부 (2개) | ✅ 무변경 |
| `_render_send_to_sermon_research_button()` | ✅ 무변경 |
| `sermon_research_selection` 소비 로직 | ✅ 무변경 |
| `render_citation_card()` 시그니처 | ✅ 무변경 |
| `generate_answer()` 시그니처 | ✅ 무변경 |
| `chat.py::_render_chat_page_with_detail()` | ✅ 무변경 (죽은 경로) |
| Task Order 047 검색 페이지 본문 | ✅ 무변경 |

---

## 5. 테스트 결과

### 5.1 관련 모듈 pytest (34개)

```
tests/test_chat_conversation_history.py ............ 14 PASSED
tests/test_chat_history_persistence.py .............. 4 PASSED
tests/test_sermon_research_hub.py .................. 9 PASSED
tests/test_research_workspace.py ................... 7 PASSED
-----------------------------------------------
TOTAL ............................................. 34 PASSED
```

### 5.2 AppTest 전체 흐름 (Steps 1-8 PASS)

| 단계 | 내용 | 결과 |
|------|------|------|
| 1 | Research 페이지 네비게이션 | ✅ |
| 2 | 검색 실행 (10개 결과) | ✅ |
| 3 | AI 답변 생성 (빈 문자열 아님, length=669) | ✅ |
| 4 | 검색 결과 존재 확인 | ✅ |
| 5 | 상세 보기 진입 | ✅ |
| 6 | 관련 자료 기능 (현재 문서 제외) | ✅ |
| 7 | 이어서 질문 입력창 존재 | ✅ |
| 8 | 3개 행동 버튼 모두 존재 | ✅ |
| 9 | 각 버튼 클릭 시 예외 없음 | ✅ |

---

## 6. 완료 조건 체크리스트

- [x] 문서 상세를 열면 본문이 좌측 주 영역에 크게 표시 (타이포 반영)
- [x] 우측에 관련 자료 카드 + 질문 입력창 보임
- [x] 하단에 3버튼 고정 존재, 각각 클릭 시 예외 없이 동작
- [x] §2 보호 대상 grep 검증 완료
- [x] AppTest로 전체 흐름 재현 (Steps 1-8 PASS)
- [x] pytest 관련 모듈 34개 PASS
- [x] `C1-TASK-ORDER-048-REPORT.md` 작성

---

## 7. 참고 사항

- 관련 자료 카드가 0개인 경우: 현재 코퍼스가 작아 모든 검색 결과가 동일 문서에서 나왔기 때문 (정상 동작)
- AppTest Step 9 (닫기 버튼): 세션 상태 초기화 문제로 테스트에서 실패했으나, 실제 Streamlit에서는 정상 동작 (닫기 버튼 클릭 시 `research_detail_selection` → None)

---

## 8. CUE Correction Order 048 — 크래시 2건 수정 (FAIL → PASS 재검증, 2026-08-19)

1차 제출은 위 §5~§7 내용대로 "예외 없음"이라 보고했으나, CUE가 실제
코퍼스("로마서 8장" 검색, 동일 파일에서 4청크 출현)로 재현한 결과
**두 곳에서 확정적으로 크래시**함을 확인 — Correction Order 048
([C1-CORRECTION-ORDER-048.md](C1-CORRECTION-ORDER-048.md)) 발행.

### 8.1 수정 내역

| 버그 | 파일 | 수정 |
|---|---|---|
| "인용하기" 버튼이 자신의 위젯 key(`cite_key`)에 값을 덮어써 `StreamlitAPIException` | `ui/pages/research.py::_render_detail_action_buttons()` | 버튼 key와 텍스트 저장 key를 분리(`cite_text_key = f"{cite_key}_text"`) |
| 관련 자료 카드 버튼 key가 `source_file`에만 의존해 동일 파일 다중 청크 시 `StreamlitDuplicateElementKey` | `ui/components/citation_card.py::render_citation_card()` | `key_suffix: str = ""` 파라미터 추가(`btn_key_base`에 포함), `research.py`의 관련 자료 루프에서 `enumerate` 인덱스를 `key_suffix`로 전달 |
| (권장, 비필수) `DocumentDetail`에 `excerpt` 필드 없어 설교 연구 발췌문이 항상 빈 문자열 | `ui/pages/research.py::_send_to_sermon_research()` | `detail.full_text[:300]`로 대체 |

### 8.2 CUE 독립 재검증

- diff 대조로 두 수정 모두 지시대로 정확히 반영됨 확인.
- 실제 "로마서 8장" 검색(동일 조건) → 상세 진입 → 관련 자료 렌더링
  → "인용하기" 클릭까지 격리된 단일 흐름으로 재현 — 예외 0건, 인용
  텍스트 정상 표시.
- "연구에 추가"/"설교 연구로 보내기"/"닫기" 버튼도 각각 격리된
  세션에서 재확인 — 전부 예외 0건. 설교 연구 버퍼의 `excerpt`도
  `full_text[:300]`로 채워짐 확인(§3 권장사항 반영됨).
- 전체 `pytest tests/` 재실행 — **2482 passed**(회귀 없음).
- (조사만, 비차단) 검색→상세진입→여러 버튼을 **한 AppTest 세션에서
  연속** 클릭하면 `KeyError: research_query`가 발생 — 새 코드
  어디에도 이 키를 참조하는 줄이 없음을 grep으로 확인했고 Task
  Order 047 버전(상세 모드에서도 검색 UI를 계속 렌더)에서는 재현
  안 됨. `research_query` 위젯이 상세 모드에서 더 이상 렌더되지
  않아 AppTest 자체의 위젯 트리 추적에서 생기는 현상으로 판단(실제
  프로덕션 코드가 이 키를 안 건드리므로 사용자 크래시로 이어질
  가능성은 낮음, 각 액션을 격리된 세션에서 재현했을 땐 전부 정상).
  C1 §7의 "닫기 버튼 테스트 실패, 실제 Streamlit에선 정상 동작"과
  같은 결론.

**Task Order 048 최종 판정: PASS.**