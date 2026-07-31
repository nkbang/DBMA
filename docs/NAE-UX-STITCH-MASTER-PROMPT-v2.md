# DBMA-UX Stitch 마스터 프롬프트 v2

**문서 상태:** 사용 준비 완료
**작성일:** 2026-07-30
**대체 대상:** `docs/DBMA-UX-DESIGN-BRIEF.md` §5.1 (v1 프롬프트)
**변경 사유:** v1 프롬프트 실행 결과 발견된 2개 오류를 반영해 정제
  1. 브랜드 오류 — "DBMA"가 사용자-facing으로 노출됨
     (`docs/governance/DBMA-BRAND-GOV-001.md` 위반)
  2. 화면 누락 — Help·Sample Library 2개 화면이 생성되지 않음

---

## 현재 진행 상태 (이 프롬프트를 쓰기 전에 알아야 할 것)

- Stitch 프로젝트 "Pastoral Research Desk"에 이미 9개 화면 확보 완료
  (랜딩/온보딩/홈/검색 결과/연구하기/설교 준비/자료 읽기/도움말/내 자료)
- 디자인 시스템은 **이미 확정됨** — `Theological Archive System`
  (Hanken Grotesk + Source Serif 4, cream `#fbf9f4` 배경, tonal layering,
  그림자·그라디언트 없음). **새로 만들지 말고 그대로 유지**
- 브랜드는 **내서재 (NAE)**로 이미 6화면 정정 완료, 저장소 커밋됨
  (`89f686a`)
- 지금 이 프롬프트는 **신규 화면 추가나 기존 화면 수정**용으로 사용.
  전체 재생성 프롬프트가 아님

---

## Stitch에 붙여넣는 프롬프트 (신규/수정 요청 시 공통 헤더)

```text
Continue working in the EXISTING "Pastoral Research Desk" project. Do not
create a new design system — reuse the exact tokens already established:

- Design system name: "Theological Archive System"
- Fonts: Hanken Grotesk (UI/labels/headers), Source Serif 4 (reading content)
- Background: #fbf9f4 (warm cream), no gradients, no drop shadows
- Elevation: tonal layering + 1px outline borders only
- Corner radius: 4px-8px (soft but not bubbly)
- Grid: 8px spacing unit, sidebar 280px, reading column capped at 720px

BRAND (frozen, do not change):
- Korean product name: "내서재"
- English product name: "NAE" (all caps)
- Combined form when needed: "내서재 (NAE)" or "내서재 · NAE"
- NEVER use "DBMA", "Theology Desk", "Pastoral Scholar", or any other name
  as the user-facing brand. DBMA is an internal engineering identifier only
  and must never appear in visible UI text.

LANGUAGE RULES (frozen):
- All visible UI text must be Korean, written in plain pastoral language
  (읽기, 찾기, 연구하기, 설교 준비 — not academic or technical phrasing)
- NEVER expose technical/system terms in UI: RAG, Retrieval, Embedding,
  TSU, Chunk, Vector, Pipeline, Workspace, similarity score numbers
- No empty states — every screen shows realistic sample content already
  used elsewhere in this project (로마서 8장, 성령의 열매, 칭의 연구, etc.)
- Every screen must have a clear next-action button — no dead ends

SHARED COMPONENTS (reuse exactly, do not redesign):
- Sidebar (280px, fixed left): "내서재" title + "NAE" subtitle, 6 nav items
  (홈/자료 찾기/내 자료/연구하기/설교 준비/도움말)
- Top header (64px): page title, search bar where applicable
- Bottom footer bar (40px, tertiary-container background): current-item
  label + "내서재에게 물어보세요" link
- Result/resource cards: badge (성경=primary-container / 책=primary-fixed /
  신학자료=secondary-container / 설교=tertiary-container) + title + snippet
  + 2 action buttons

[여기에 이번에 요청할 신규/수정 내용을 구체적으로 작성]
```

---

## 사용 예시 1 — 기존 화면 수정 요청

```text
[공통 헤더 위 내용에 이어서]

TASK: On the "연구하기" (research_workspace) screen, the right-side
"선택한 자료 모음" panel currently has no empty state. Add one: when no
resources are selected, show a centered icon + "선택한 자료가 없습니다"
+ a ghost button "자료 찾기에서 추가하기". Keep the same panel width and
tonal-layering style as the rest of the screen.
```

## 사용 예시 2 — 신규 화면 추가 요청

```text
[공통 헤더 위 내용에 이어서]

TASK: Create a new screen "설정" (Settings), reachable from a gear icon
next to "도움말" in the sidebar. Sections:
1. "계정" — email(읽기 전용), "로그아웃" ghost button
2. "표시 설정" — 다크 모드 토글, 본문 글자 크기 슬라이더(작게/보통/크게)
3. "데이터" — "내 자료 내보내기" primary button, "전체 삭제" destructive
   ghost button (red outline, red text on hover)
Use the same sidebar/header/footer shared components as other screens.
```

---

## 체크리스트 (Stitch 결과 받으면 항상 이걸로 1차 검증)

- [ ] "DBMA"/"Theology Desk"/"Pastoral Scholar" 문자열이 화면 어디에도 없음
- [ ] "내서재"/"NAE" 브랜드만 사용됨
- [ ] RAG/Retrieval/Embedding/TSU/Chunk/Vector 등 기술 용어 없음
- [ ] 모든 텍스트가 목회자 언어(한국어)로 되어 있음
- [ ] 빈 화면 없이 샘플 데이터로 채워져 있음
- [ ] 각 화면에 다음 행동 버튼 존재 (Dead End 없음)
- [ ] 사이드바/헤더/푸터가 기존 화면과 동일한 컴포넌트 재사용됨
