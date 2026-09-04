# C1 Task Order 035 — UX-001 프로토타입 Architecture Review Report

**상태**: 완료 (GO with caveats)
**검토자**: C1 (DBMA Core Engineer)
**작성일**: 2026-07-31
**검토 대상**: `docs/design/stitch/pastoral_research_desk/` 전체 (HTML 9개 + DESIGN.md)

---

## 리뷰 질문 1: UX 프로토타입이 Core architecture를 임의로 변경하는가?

### 결론: NO (임의 변경 없음)

### 검토 방법

9개 HTML 파일을 직접 열어서 JavaScript 코드, 데이터 구조, API 호출, 백엔드 의존성을 모두 확인했습니다.

### 확인 결과

모든 HTML 파일은 **순수 정적 프론트엔드**입니다. 포함된 JavaScript는 다음만 존재:

1. **tailwind.config 테마 설정** — CSS 색상/타이포그래피/간격 토큰 정의
2. **스크롤 마이크로인터랙션** (`document_reading.html` line 317-327) — AI 어시스턴트 위치 조정
3. **텍스트 선택 이벤트** (`document_reading.html` line 330-337) — `console.log` 출력
4. **AI 어시스턴트 토글** (`document_reading.html` line 249) — `classList.toggle()`
5. **스크롤 헤더 효과** (`landing.html` line 281-290) — backdrop 투명도 변경

**어떤 파일에도 API 엔드포인트, fetch/axios 호출, WebSocket, 데이터 모델 정의가 없습니다.**

### 구체적 확인 항목

| 확인 사항 | 결과 | 근거 |
|-----------|------|------|
| `core/retrieval.py` 충돌 | 없음 | 프로토타입에 retrieval 로직 없음 |
| `core/runtime_state.py` 충돌 | 없음 | 프로토타입에 상태 관리 로직 없음 |
| 검색 결과 5분류 탭의 백엔드 매핑 | 미정의 (정적 UI) | `search_results.html` line 138-167: 정적 `<a>` 탭 |
| AI 어시스턴트 파이프라인 | UI 컴포넌트만 | `document_reading.html` line 243-277: HTML/CSS 레이아웃 |
| 자료 복사 기능 | UI 버튼만 | `my_library.html` line 101: `<button>복사하여 내 자료로</button>` |

### 검색 결과 검증 (참고)

`search_results.html`의 5분류 탭 ("성경 / 책 / 신학자료 / 설교 / 내 자료")은 정적 HTML 요소입니다. 실제 백엔드 API가 이 카테고리를 반환하는지는 Streamlit 구현 단계에서 `core/retrieval.py`와 대조해야 합니다. 프로토타입 자체는 백엔드를 변경하지 않습니다.

### 구조적 이슈 (참고)

- `search_results.html`의 5분류 탭이 현재 TSU(Gold Standard)의 실제 메타데이터 카테고리(`doc_type` 필드 값)와 일치하는지는 **Streamlit 구현 시 확인 필요**
- `document_reading.html`의 AI 어시스턴트 패널("방금 읽은 부분 요약", "내서재에게 물어보세요")은 실제 RAG 파이프라인 연동 시 설계가 필요

---

## 리뷰 질문 2: Streamlit 코드가 기존 UI 구조 (`ui/pages/*`) 와 호환되는가?

### 결론: GO with caveats

### 호환 가능한 부분

| 디자인 토큰 | DESIGN.md 값 | Streamlit 매핑 가능성 |
|-------------|-------------|---------------------|
| surface 색상 | `#fbf9f4` | `st.config.theme.backgroundColor` 또는 커스텀 CSS |
| primary 색상 | `#171e1e` | 동일 |
| sidebar-width | `280px` | 제한적 (아래 caveats 참조) |
| reading-column | `720px` | `st.columns()`으로 구현 가능 |
| font-family | Hanken Grotesk / Source Serif 4 | `st.markdown(unsafe_allow_html=True)` 필요 |
| 8px 그리드 | `spacing.unit: 8px` | CSS `gap` / `padding`으로 매핑 가능 |
| rounded | `0.125rem ~ 0.75rem` | CSS `border-radius`로 매핑 가능 |

### caveats (구현 시 대응 필요)

#### Caveat 1: 사이드바 고정 너비 280px

**문제**: Streamlit의 `st.sidebar`는 최소 너비 제어가 제한적입니다. 고정 280px를 보장하려면:

```python
# 옵션 A: st.page_sidebar() (Streamlit 1.30+, 권장)
# 옵션 B: st.markdown(..., unsafe_allow_html=True) + 커스텀 CSS
```

**영향**: 기존 `ui/pages/*`의 사이드바 구현과 다른 레이아웃이 될 수 있습니다. 베이스로만 참고하는 범위内이므로 문제되지 않습니다.

#### Caveat 2: 하단 고정 푸터바

**문제**: Streamlit은 하단 고정 요소를 native로 지원하지 않습니다.

```html
<!-- 프로토타입 (help.html line 150) -->
<footer class="fixed bottom-0 ...">현재 보고 있는 화면: 도움말</footer>
```

**우회 방법**: `st.markdown(..., unsafe_allow_html=True)` + JavaScript로 구현 가능하지만, 페이지 전환 시 유지되지 않을 수 있습니다.

#### Caveat 3: 헤더 내 탭 네비게이션

**문제**: `research_workspace.html` line 171-176의 헤더 탭 ("열기 / 읽기 / 연구하기 / 설교 준비")은 Streamlit의 `st.tabs()`가 상단 탭만 지원하므로 직접 매핑 불가.

```html
<!-- 프로토타입 -->
<nav class="flex items-center gap-6 h-full">
  <a href="#">열기</a>
  <a href="#">읽기</a>
  <a href="#">연구하기</a>
  <a href="#">설교 준비</a>
</nav>
```

**대안**: `st.tabs()` 상단 배치 또는 커스텀 레이아웃으로 우회.

#### Caveat 4: Tailwind CSS CDN

프로토타입은 `cdn.tailwindcss.com`을 사용합니다. Streamlit에서 사용 시:

- `unsafe_allow_html=True`로 주입 필요
- Streamlit의 자체 스타일링과 충돌 가능성 있음
- 권장: Streamlit-native `st.css` 우선 검토 후, 필요시 CDN 병용

#### Caveat 5: Material Symbols 아이콘

Google Fonts에서 로드되며 `unsafe_allow_html=True`가 필요합니다. Streamlit에서 사용 가능하지만, 페이지 로딩 속도에 영향 줄 수 있습니다.

### Streamlit 포팅 시 권장사항

1. `st.page_sidebar()` (Streamlit 1.30+)을 사이드바 구현에 우선 사용
2. 하단 푸터바는 `st.markdown(..., unsafe_allow_html=True)` + JavaScript
3. Tailwind 대신 Streamlit-native 스타일 우선, 필요시 CDN 병용
4. Material Symbols은 Google Fonts CDN에서 로드

---

## 리뷰 질문 3: 기술 용어가 UI에 노출되지 않는가?

### 결론: GO (기술 용어 노출 없음)

### 브랜드명 확인

| 페이지 | 브랜드명 사용 | DBMA_BRAND_RULES 준수 |
|--------|-------------|----------------------|
| landing.html | "內書齋" (한자 장식), "내서재", "NAE" | ⚠️ 참고 사항 있음 (§참고 참조) |
| onboarding.html | "내서재 / NAE" | ✅ 준수 |
| home_dashboard.html | "내서재 / NAE" | ✅ 준수 |
| search_results.html | "내서재" | ✅ 준수 |
| research_workspace.html | "내서재 AI 어시스턴트" | ✅ 준수 |
| sermon_preparation.html | "내서재" | ✅ 준수 |
| document_reading.html | "내서재 / NAE" | ✅ 준수 |
| help.html | "내서재" | ✅ 준수 |
| my_library.html | "내서재" | ✅ 준수 |

### 기술 용어 노출 확인

**확인된 기술 용어 (모두 UI 미노출):**

| 기술 용어 | UI 노출 여부 | 근거 |
|-----------|-------------|------|
| RAG | ❌ 없음 | 어디에도 등장하지 않음 |
| Retrieval | ❌ 없음 | 어디에도 등장하지 않음 |
| Embedding | ❌ 없음 | 어디에도 등장하지 않음 |
| TSU | ❌ 없음 | 어디에도 등장하지 않음 |
| Chunk | ❌ 없음 | 어디에도 등장하지 않음 |
| Vector DB | ❌ 없음 | 어디에도 등장하지 않음 |
| API | ❌ 없음 | 어디에도 등장하지 않음 |
| JSON | ❌ 없음 | 어디에도 등장하지 않음 |
| Markdown | ❌ 없음 | 어디에도 등장하지 않음 |

**AI 어시스턴트 패널 확인:**

- `document_reading.html` line 247: `"내서재 AI 어시스턴트"` — "AI"는 제품 기능명으로서 기술 용어가 아님
- `help.html` line 152: `"내서재에게 물어보세요"` — 자연어 표현
- `my_library.html` line 152: `"내서재에게 물어보세요"` — 자연어 표현

**검색 카테고리 확인:**

- `search_results.html` line 138-167: `"성경 / 책 / 신학자료 / 설교 / 내 자료"` — 실제 메타데이터 카테고리명, 기술 용어 아님

### 참고: landing.html "內書齋" 한자 타이틀

**상태**: NO-GO 사유 아님 / 개선 권고

`landing.html` line 139, 176-178에서 "內書齋" (한자)가 장식적 타이틀로 사용됩니다:

```html
<div class="font-display-lg text-title-lg font-bold text-primary">內書齋</div>
...
<h1 class="font-body-reading-lg text-[80px] leading-tight text-primary font-light tracking-widest opacity-90">
    內書齋
</h1>
```

이것은 기능적 브랜드 라벨이 아닌 **타이포그래피 장식 요소**이나, DBMA_BRAND_RULES에서 확정된 브랜드명("내서재" / "NAE")과 혼동될 소지가 있습니다. Streamlit 구현 시 제거 또는 "내서재"로 치환하는 것을 권장합니다.

---

## 최종 판단: GO with caveats

### 판단 근거

1. **Core architecture 영향**: 없음 — 프로토타입은 정적 HTML이며 Core를 변경하거나 암시하지 않음
2. **Streamlit 호환성**: 일부 제한 사항 있으나 구현 가능
3. **기술 용어 노출**: 없음 — 브랜드 규칙 준수

### caveats (구현 시 대응 필요)

| # | 항목 | 대응 방법 | 우선순위 |
|---|------|----------|---------|
| C1 | 사이드바 고정 280px | `st.page_sidebar()` 또는 커스텀 CSS | 높음 |
| C2 | 하단 고정 푸터바 | `unsafe_allow_html` + JavaScript | 보통 |
| C3 | 헤더 내 탭 네비게이션 | `st.tabs()` 상단 배치 또는 커스텀 | 보통 |
| C4 | Tailwind CSS CDN 충돌 | Streamlit-native 스타일 우선 | 낮음 |
| C5 | Material Symbols 로드 | Google Fonts CDN, `unsafe_allow_html` 필요 | 낮음 |
| C6 | landing.html "內書齋" | "내서재"로 치환 권장 | 낮음 |

### 구조적 이슈 목록

| # | 페이지 | 이슈 | 설명 |
|---|--------|------|------|
| S1 | search_results.html | 5분류 탭 vs 백엔드 카테고리 | Streamlit 구현 시 `core/retrieval.py`의 실제 반환 카테고리 대조 필요 |
| S2 | document_reading.html | AI 어시스턴트 파이프라인 | RAG 연동 시 별도 설계 필요 |
| S3 | my_library.html | "복사하여 내 자료로" 기능 | 백엔드 API 엔드포인트 정의 필요 |

---

## 수정된 파일 없음

이 Task는 리뷰만 수행했으며, `ui/pages/*` 또는 `core/*` 코드를 수정하지 않았습니다.

## 테스트 실행 없음

리뷰만 수행했으므로 테스트는 실행하지 않았습니다.

## 벤치마크 영향 없음

프로토타입 검토이므로 벤치마크에 영향 없습니다.

## 남은 차단 사항 (Blocker) 없음

이 리뷰는 GO with caveats로 나왔습니다. Blocker는 없으며, caveats는 Streamlit 구현 단계에서 대응하면 됩니다.