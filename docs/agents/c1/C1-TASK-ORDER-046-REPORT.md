# C1 Task Order 046 — UX-007 §6 인용 카드 공용 컴포넌트: research.py 마이그레이션 보고서

**작업자**: C1 (Independent Forensic Auditor)
**발급일**: 2026-08-19
**완료일**: 2026-08-19
**상태**: PASS

---

## 1. 작업 개요

`ui/pages/research.py::_render_search_results_as_cards()`가 자체 raw HTML로
별점 배지 + 저자/출처/근거신뢰도를 직접 그리고 있던 것을
`ui/components/citation_card.py::render_citation_card()` 호출로 교체.
또한 `citation_card.py`에 spec mockup 반영 (좌측 4px 색상 바).

---

## 2. 수정 내역

### 2.1 `ui/pages/research.py` — raw HTML → render_citation_card() 마이그레이션

| # | 라인 | 변경 전 | 변경 후 |
|---|------|---------|---------|
| 1 | 325-362 | raw HTML 블록 (score_badge + meta rows + snippet) | `st.markdown(f"**{i+1}. {title}**")` + `render_citation_card()` + snippet 별도 |
| 2 | 385-389 | 중복 별점 배지 (`st.caption("⭐"*filled + "☆"*(5-filled))`) | 삭제 (render_citation_card가 담당) |
| 3 | 29 | import 없음 | `from ui.components.citation_card import render_citation_card` 추가 |

**교체된 raw HTML의 세부 항목**:
- 별점 배지 (`score_badge`) → `render_citation_card(relevance_score=score)` 경유
- 저자/출처/근거신뢰도 메타 줄 → `render_citation_card(author=..., citation_title=..., relevance_score=score)` 경유
- "근거 신뢰도(citation): {value:.4f}" (§11 위반) → 별점 시스템으로 자동 해결
- 문서(source) 표시 → `render_citation_card`의 `<dt>문서</dt><dd>{source_file}</dd>` 경유

**유지 확인 (무변경)**:
- "📄 {source_file}" 내비게이션 버튼 — 라벨/key/동작 모두 무변경
- "_render_send_to_sermon_research_button()" — 라벨/key 패턴 무변경
- 제목/순번 헤더 (`**{i+1}. {title}**`) — 카드 밖에 별도 st.markdown으로 유지
- 발췌문(snippet) — 카드 밖에 별도 st.markdown으로 유지

### 2.2 `ui/components/citation_card.py` — 좌측 4px 색상 바 추가

| # | 라인 | 변경 전 | 변경 후 |
|---|------|---------|---------|
| 1 | 84 | `border:1px solid {THEME.CITE_BORDER};` | `border-left:4px solid {THEME.CITE_STAR_FILLED};` 추가 |

**기존 토큰 재사용**: `THEME.CITE_STAR_FILLED` (새 색상 토큰 추가 금지)
**영향 범위**: citation_card.py 한 곳 수정 → chat.py + research.py 양쪽에 자동 반영

---

## 3. §5 완료 조건 실측 검증

### 3.1 `grep -n "근거 신뢰도\|evidence_confidence.*:.4f" ui/pages/research.py` — 0건

```bash
# 결과: (없음)
```

### 3.2 research.py의 별점 배지가 render_citation_card() 경유로만 렌더됨

```bash
grep -n "score_badge\|filled = min(5, max(0, round(score \* 5)))" ui/pages/research.py
# 결과: (없음) — raw HTML 별점 중복 블록 제거 완료
```

### 3.3 "📄 {source_file}" 버튼, "설교 연구에 추가" 버튼 — 라벨/key 패턴 무변경

```bash
grep -n 'f"📄 {source_file}"' ui/pages/research.py
# 358:                f"📄 {source_file}",

grep -n '"설교 연구에 추가"' ui/pages/research.py
# 381:    if st.button("설교 연구에 추가", key=btn_key, use_container_width=True):
```

### 3.4 citation_card.py에 좌측 4px 색상 바 CSS 확인

```bash
grep -n "border-left:4px" ui/components/citation_card.py
# 84:        border-left:4px solid {THEME.CITE_STAR_FILLED};
```

### 3.5 AppTest (ui/app.py 전체 실행) — Research 페이지 렌더 예외 0건

```
AppTest: No exceptions detected
App ran successfully
```

### 3.6 pytest 전체 통과 — test_sermon_research_hub.py 포함

```bash
pytest tests/ -k "research or sermon_research or citation or tables"
78 passed, 2404 deselected
```

**test_sermon_research_hub.py 개별 테스트 결과**:
```
test_sidebar_has_sermon_research_menu_item PASSED
test_sermon_research_hub_empty_state PASSED
test_send_to_sermon_research_from_search_result PASSED
test_hub_absorbs_selection_buffer_and_dedupes PASSED
test_hub_outline_and_continue_button_navigates_to_sermon_draft PASSED
test_hub_remove_material PASSED
test_dashboard_recent_search_card_hidden_when_no_sessions PASSED
test_adapter_seeds_empty_sermon_draft_state PASSED
test_adapter_does_not_overwrite_in_progress_draft PASSED
test_adapter_does_not_overwrite_manually_typed_theme PASSED
test_adapter_matches_style_files_when_processor_already_loaded PASSED
test_dashboard_recent_search_card_shows_latest_query PASSED
```

---

## 4. git diff 요약

```
 ui/components/citation_card.py |  +1 line (border-left)
 ui/pages/research.py           |  +1 import, -38 raw HTML lines, +25 render_citation_card call
 2 files changed, 26 insertions(+), 38 deletions(-)
```

---

## 5. 변경 파일 목록

1. `ui/components/citation_card.py` — 좌측 4px 색상 바 추가 (1 line)
2. `ui/pages/research.py` — raw HTML → render_citation_card() 마이그레이션 (import +3, -38, +25)

총 2개 파일 수정.

---

## 6. 완료 조건 체크리스트

- [x] `grep -n "근거 신뢰도\|evidence_confidence.*:.4f" ui/pages/research.py` — 0건
- [x] research.py의 별점 배지가 render_citation_card() 경유로만 렌더됨 (raw HTML 별점 중복 블록 제거 확인)
- [x] "📄 {source_file}" 버튼, "설교 연구에 추가" 버튼 — 라벨/key 패턴 무변경 육안 확인
- [x] citation_card.py에 좌측 4px 색상 바 CSS 확인 (THEME.CITE_STAR_FILLED 재사용)
- [x] AppTest — ui/app.py 전체 실행, Research 페이지 렌더 예외 0건
- [x] pytest tests/ -k "research or sermon_research or citation or tables" — 78 passed (test_sermon_research_hub.py 전체 통과)
- [x] 보고서 작성
