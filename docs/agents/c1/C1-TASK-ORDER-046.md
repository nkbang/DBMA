# C1 Task Order 046 — UX-007 §6 인용 카드 공용 컴포넌트: research.py 마이그레이션

**상태**: 발급됨 — 착수 가능
**우선순위**: P1
**근거 문서**: [DBMA-UX-007-IMPLEMENTATION-SPEC.md](../../DBMA-UX-007-IMPLEMENTATION-SPEC.md) §6(Citation/Provenance Component)
**선행 상태 확인 (중요)**: `ui/components/citation_card.py`와
`ui/pages/chat.py::_render_clickable_source()`의 §6 적용은 **이미
완료돼 있다**(2026-08-18, 별도 세션 — 커밋 이력에 Task Order로 안
남아있어 CUE가 이번에 grep으로 재발견함). 이 Task Order는 §6를
**새로 구현하는 게 아니라**, 아직 이 컴포넌트를 쓰지 않는
`research.py` 한 곳만 같은 패턴으로 옮기는 작업이다.

---

## 0. 왜 필요한가

`ui/pages/research.py::_render_search_results_as_cards()`가 여전히
자체 raw HTML로 별점 배지 + 저자/출처/신뢰도를 그리고 있다 — §12
Reuse Map이 명시한 "전역 재사용 컴포넌트"를 안 쓰고 있다. 게다가
CUE가 이번에 확인한 **§11 위반 1건도 여기 섞여 있다**: 356행
`f'근거 신뢰도(citation): {result.get("evidence_confidence"):.4f}'`
— 원시 소수점 신뢰도 노출(Task Order 045 grep이 이 표현을 놓쳤음,
"RRF"/"TSU" 같은 정확한 키워드로만 찾았기 때문). `render_citation_card()`
로 옮기면 별점 시스템이 이 값도 흡수하므로 두 문제가 한 번에
해결된다.

## 1. 참고 패턴 (그대로 따라 하되 똑같이 베끼지는 말 것)

`ui/pages/chat.py::_render_clickable_source()`(461~535행 부근)를
먼저 읽어라. 그 함수가 이미:
- 헤드라인 클릭형 버튼(`st.button(f"📄 {display_label}", ...)`)은
  citation card **밖에서** 따로 렌더링
- `render_citation_card(source_file=..., text_location=..., doc_type=...,
  author=..., citation_title=..., relevance_score=..., on_view_original=True,
  on_copy_citation=False)`로 메타데이터+별점만 카드에 위임
- 반환값 없는 `st.button`의 클릭 상태를 `st.session_state[view_btn_key]`
  로 사후 확인하는 패턴(543~551행 부근) — 이미 동작 확인됨, 그대로
  재사용 가능

## 2. 대상 파일 — `ui/pages/research.py::_render_search_results_as_cards()` (318~412행)

### 2.1 유지할 것 (건드리지 마라)

- **제목/순번 헤더**(`"{i+1}. {title}"`) — `render_citation_card()`에는
  title 파라미터가 없다. 새 파라미터를 추가하지 말고, 카드 밖에
  별도 `st.markdown`으로 남겨라(chat.py도 헤드라인을 카드 밖에 둔다,
  같은 원칙).
- **발췌문(snippet) 표시** — citation_card.py에는 snippet 필드가
  없다. 마찬가지로 카드 밖 별도 요소로 유지.
- **"📄 {source_file}" 내비게이션 버튼**(363~383행,
  `research_detail_selection` 세팅) — 완전히 무변경.
- **`_render_send_to_sermon_research_button()`**(394~412행, Task
  Order 042/043) — 완전히 무변경. `tests/test_sermon_research_hub.py`
  가 이 버튼의 key 패턴(`send_sermon_{index}_...`)과 라벨("설교
  연구에 추가")에 의존한다 — 조금이라도 바뀌면 그 테스트가 깨진다.

### 2.2 교체할 것

333~360행의 raw HTML 블록 중 **별점 배지 + 저자/출처/근거신뢰도
메타 줄**(342~349행의 점수 배지, 353~357행의 저자/출처/신뢰도 줄)을
`render_citation_card()` 호출로 교체한다:

```python
render_citation_card(
    source_file=source,
    text_location=None,  # research.py 결과엔 heading_path 없음, 있으면 채워도 됨(확인 후 판단)
    doc_type=None,        # doc_type이 "tsu" 고정이라 표시 가치 없음(기존 주석 327~329행과 동일 판단 유지)
    author=result.get("author") or None,
    citation_title=result.get("source_title") or None,
    relevance_score=score,
    on_view_original=False,  # 내비게이션은 아래 기존 "📄" 버튼이 이미 담당 — 중복 버튼 만들지 마라
    on_copy_citation=False,
)
```

`on_view_original=False`로 두는 이유: citation_card의 "원문 다시
보기" 버튼과 기존 "📄 {source_file}" 버튼이 똑같은 내비게이션을
중복으로 만들면 안 된다 — 기존 버튼이 이미 있으니 카드 쪽 버튼은
끈다. 385~389행(중복으로 별점을 한 번 더 찍던 부분)도 이제
`render_citation_card`가 담당하니 삭제.

제목/순번 헤더와 발췌문은 §2.1대로 별도 `st.markdown`으로 남기고,
카드 컨테이너 배경/테두리 스타일(334~341행)은 필요하면 유지하되
중복 스타일링이 되지 않도록 `render_citation_card`가 이미 그리는
카드 배경과 시각적으로 겹치지 않게 배치 확인.

## 3. `ui/components/citation_card.py` — 좌측 색상 바 추가 (spec mockup 반영)

§6 mockup은 카드 좌측에 4px 색상 바를 명시한다(`▐`). 현재 구현엔
없다. `THEME.CITE_STAR_FILLED`(기존 토큰, 새 토큰 추가 금지)를 써서
카드 컨테이너에 `border-left: 4px solid {THEME.CITE_STAR_FILLED};`
추가. 이 변경은 `citation_card.py` 한 곳만 고치면 되고 chat.py/
research.py 양쪽에 자동 반영된다.

## 4. 하지 않을 것

- `chat.py` — 이미 완료됨, 무변경.
- `sermon_research.py`의 자료 카드(Task Order 042) — 별도 설계,
  이번 범위 아님.
- `citation_card.py`에 title/snippet 파라미터 추가 — 새 컴포넌트
  설계 확장은 이번 범위 밖(§2.1 참고, 카드 밖에 유지하는 쪽으로).
- Core/retrieval/registry 로직 — 무변경.

## 5. 완료 조건

- [ ] `grep -n "근거 신뢰도\|evidence_confidence.*:.4f" ui/pages/research.py` — 0건
- [ ] research.py의 별점 배지가 `render_citation_card()` 경유로만
      렌더됨(raw HTML 별점 중복 블록 제거 확인)
- [ ] "📄 {source_file}" 버튼, "설교 연구에 추가" 버튼 — 라벨/key
      패턴 무변경 육안 확인
- [ ] `citation_card.py`에 좌측 4px 색상 바 CSS 확인(육안 + diff)
- [ ] `streamlit.testing.v1.AppTest` — `ui/app.py` 전체 실행,
      Research 페이지에서 검색 결과 카드가 있는 상태로 렌더 예외
      0건(mock 금지)
- [ ] `pytest tests/ -k "research or sermon_research or citation or tables"` 전체 통과 —
      특히 `test_sermon_research_hub.py`의 "설교 연구에 추가" 관련
      테스트가 그대로 통과하는지 반드시 확인(깨지면 이 Task는 FAIL)
- [ ] `docs/agents/c1/C1-TASK-ORDER-046-REPORT.md` 작성

## 6. 완료 후

CUE가 diff 대조 + grep 재현 + `AppTest`/pytest 재확인으로 독립
검증한다. PASS 시 STATE.md/TODO.md 갱신.
