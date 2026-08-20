# Pastoral Research Desk — Figma 반입용 화면 목록

브랜드 거버넌스(`docs/governance/DBMA-BRAND-GOV-001.md`, 내서재/NAE) 반영
완료된 P0/P1 화면 12종. [html.to.design](https://html.to.design) Figma 플러그인으로
한 파일씩 불러와 프레임을 구성한다. 각 파일은 독립적으로 열리는 완전한 HTML
문서이며, 동일한 디자인 시스템(`DESIGN.md` — Theological Archive System,
Hanken Grotesk + Source Serif 4, cream `#fbf9f4` 배경)을 공유한다.

## 임포트 순서 (권장 Figma 프레임 이름)

| 순서 | 파일 | Figma 프레임명 | 비고 | 검증 |
|---|---|---|---|---|
| 1 | `landing.html` | 01. 랜딩 | 로그인 전 마케팅 페이지, 앱 셸과 다른 상단 nav 사용 | ✅ 2026-08-20 |
| 2 | `onboarding.html` | 02. 온보딩 | | ✅ 2026-08-20 |
| 3 | `home_dashboard.html` | 03. 홈 | | ✅ 2026-08-20 |
| 4 | `my_library.html` | 04. 내 자료 | Sample Library 포함 | ✅ 2026-08-20 |
| 5 | `search_results.html` | 05. 검색 결과 | | ✅ 2026-08-20 |
| 6 | `research_workspace.html` | 06. 연구하기 | 검색+AI답변 병렬 | ✅ 2026-08-20 |
| 7 | `chat_ai_question.html` | 07. AI에게 질문 | **신규** — RAG 채팅 화면 | ✅ 2026-08-20 |
| 8 | `sermon_research_hub.html` | 08. 설교 연구 | **신규** — 설교 연구 허브 | ✅ 2026-08-20 |
| 9 | `sermon_preparation.html` | 09. 설교 준비 | | ✅ 2026-08-20 |
| 10 | `sermon_review.html` | 10. 설교 리뷰 | **신규** — 설교 모음 검수 | ✅ 2026-08-20 |
| 11 | `document_reading.html` | 11. 자료 읽기 | | ✅ 2026-08-20 |
| 12 | `help.html` | 12. 도움말 | CUE 보완 제작 (Stitch 미생성) | ✅ 2026-08-20 |

검증 기준: 브라우저 렌더링 확인 + 콘솔 에러 0건 (신규 3종은 6항목 nav 통일·토큰 색상 정정 후 재검증 완료).

## 임포트 방법 (html.to.design)

1. Figma에서 새 파일 생성 (예: "내서재 P0 프로토타입")
2. 플러그인 메뉴 → html.to.design 실행
3. "Import from code" 선택 후 위 표 순서대로 각 `.html` 파일 내용을 붙여넣기
4. 프레임 이름을 표의 Figma 프레임명으로 변경
5. 12개 화면 모두 임포트 후 오토레이아웃 정리 진행 (§3 아래 참고)

## 오토레이아웃 정리 시 확인할 공통 컴포넌트

아래는 12개 화면 대부분에 반복되므로, Figma 컴포넌트로 먼저 추출하면 이후
정리가 빨라진다.

- **사이드바** (`w-sidebar-width`, 280px 고정): 로고("내서재"/"NAE") + 6개 nav 항목(홈/자료 찾기/내 자료/연구하기/설교 준비/도움말)로 12개 화면 전체 통일
- **상단 헤더** (`h-16`): 페이지 타이틀 + (검색 화면은 검색창 포함)
- **하단 고정 푸터바** (`h-10`, `tertiary-container` 배경): "현재 보고 있는 자료/화면" + "내서재에게 물어보세요" 링크
- **자료 카드**: 뱃지(성경/책/신학자료/설교) + 제목 + 발췌 + 행동 버튼 2개
- **뱃지 색상 매핑**: 성경=`primary-container`, 책=`primary-fixed`, 신학자료=`secondary-container`, 설교=`tertiary-container`

## 토큰 맵핑 참고

`DESIGN.md`의 색상/타이포 토큰을 기존 DBMA 디자인 시스템(있는 경우)과
1:1로 대조할 때는 이 파일의 `colors:` / `typography:` 블록을 기준으로 삼는다.
임의로 값을 바꾸지 말고, 충돌 발견 시 Human HQ에 보고한다(거버넌스 §10과
동일한 원칙 적용).
