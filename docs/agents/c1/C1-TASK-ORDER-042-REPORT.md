# C1 Task Order 042 — 완료 보고 (CUE 무인 실행)

**상태**: PASS
**실행 주체**: CUE(Claude Code, `dev/dbma-engine`) — 2026-08-19 야간 무인 작업 계속
(041과 동일하게 사용자 부재로 CUE가 build+audit 겸행)
**근거 문서**: [DBMA-UX-007-SessionState-Design.md](../../DBMA-UX-007-SessionState-Design.md)
Tier A / Tier B (§7 허브 화면, 수동 입력까지 — §7 어댑터·Tier C는
명시적으로 이번 범위 밖)

## 1. Tier A — Home "최근 검색" 카드

- `ui/pages/dashboard.py::_render_recent_search_card()` 신규 —
  `core/research_workspace.list_sessions()`를 읽기 전용으로 조회,
  가장 최근 세션의 마지막 검색어를 카드로 표시 + "이어서 검색하기"
  버튼(`_go_to` 패턴 재사용). 저장된 세션이 없으면 카드 자체를
  렌더하지 않음(Empty state).
- 신규 저장소/스키마 없음 — 기존 `research.py`의 "세션에 저장" 버튼
  (수동, `research.py:297`)으로 기록된 항목만 대상.

## 2. Tier B — 설교 연구 허브 (§7, 수동 입력 UI까지)

- **`ui/pages/research.py`**: 결과 카드마다 "설교 연구에 추가" 버튼
  추가(`_render_send_to_sermon_research_button`) — 클릭 시
  `sermon_research_selection`(전환 버퍼, list)에 append, 화면은
  그대로 유지(§4.5 명시 사항), `st.toast`로 확인.
- **`ui/pages/sermon_research.py`**(신규 파일) — 설교 연구 허브 페이지:
  - 진입 시 `sermon_research_selection`을 흡수해 `sermon_research_state`
    (`materials`/`notes`/`outline_draft`)에 병합(tsu_id 기준 중복 제거,
    버퍼는 흡수 후 비움)
  - 자료 없으면 Empty state 안내만 표시
  - 좌: 자료 카드(발췌 표시 + 메모 textarea + 제거 버튼)
  - 우: 개요 초안(줄 단위 입력 textarea → 리스트로 파싱)
  - "설교 작성으로 이어가기" 버튼 — `nav_page`를 "설교문 작성"으로
    전환만 함(어댑터 없음, 자동 전달 안 됨을 화면에 캡션으로 명시)
- **`ui/app.py`**: import 추가, 사이드바 `pages` 딕셔너리에 "설교 연구"
  항목 추가(041에서 "§7 구현 후 별도 Task Order"로 보류했던 항목),
  `page_renderers`에 매핑 추가. `Chat`/`설교문 작성`/`설교 리뷰`
  기존 항목·라벨·구조는 무변경.

## 3. 검증

- `AppTest` 실구동(mock 없음): 비관리자 모드 8개 메뉴(신규 "설교 연구"
  포함) 전체 클릭 예외 0건.
- 전체 플로우 재현: 검색 결과에 "설교 연구에 추가" 클릭 → 버퍼 적재
  확인 → 허브 진입 → 자료 흡수·중복 제거 확인 → 메모/개요 입력 반영
  확인 → 제거 버튼 동작 확인 → "이어가기" 클릭 → `nav_page`가
  "설교문 작성"으로 정확히 전환됨을 확인.
- 신규 회귀 테스트 [`tests/test_sermon_research_hub.py`](../../../tests/test_sermon_research_hub.py)
  8건 추가(사이드바 진입/빈 상태/전송·흡수·중복제거/메모·개요/제거/
  Home 카드 표시·숨김) — 전부 PASS.
- `pytest tests/ -k "sidebar or nav or app or dashboard or library or research or source_navigation"` → **229 passed** (회귀 없음).
- 전체 스위트 `pytest tests/` 실행 확인 중 — 별도 기록.

## 4. 범위 밖 — 손대지 않음

- §7 어댑터(자료·메모·개요를 `sermon_draft_state`로 자동 전달) — 설계
  문서 §4 표에 따라 별도 Task Order.
- Tier C(`core/reading_session.py`, "이어서 읽기" 영속화) — C1 Review
  권장 후 별도 착수.
- Core/retrieval/registry 로직, RAW, 기존 ADR — 전부 무변경.
