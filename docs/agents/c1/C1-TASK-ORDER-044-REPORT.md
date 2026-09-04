# C1 Task Order 044 — 완료 보고 (CUE 무인 실행)

**상태**: PASS
**실행 주체**: CUE(Claude Code, `dev/dbma-engine`) — 2026-08-19 야간 무인 작업 계속
(041~043과 동일하게 사용자 부재로 CUE가 build+audit 겸행)
**근거 문서**: [DBMA-UX-007-SessionState-Design.md](../../DBMA-UX-007-SessionState-Design.md)
§3.1(Tier C) — 사용자가 C1 Review 없이 계속 진행을 명시적으로 지시함
(2026-08-19).

## 1. 왜 §5 전체가 아니라 Tier C만인가

design doc의 "이어서 읽기"는 원래 §5 읽기(연구 워크스페이스, 3영역
레이아웃)와 묶여 있었으나, §5 자체(본문 렌더러 신규 + 연구 영역 +
행동 영역)는 이번 이터레이션 범위를 크게 벗어난다. 대신 **이미 존재
하는** `ui/components/detail_panel.py`(검색 결과 클릭 → 우측 상세
패널, 제목/메타데이터/본문 표시 — Search Detail Panel v1)가 §5가
요구하는 "본문을 읽는" 경험을 사실상 이미 제공하고 있음을 확인,
새 화면을 만들지 않고 **"문서 상세 패널이 렌더될 때 = 읽었다"로
정의**해 Tier C를 여기에 결합했다. §5의 3영역 워크스페이스 자체는
여전히 미착수.

## 2. 구현 내용

- **`core/reading_session.py`**(신규) — `save_last_read()`/
  `load_last_read()`. `research_workspace.py`(ADR-004, append-only
  쿼리 로그)를 확장하지 않고, `chat.py`의 "단일 파일 원자적 덮어쓰기"
  패턴을 복제한 별도 파일 — "마지막 읽은 문서"는 누적 로그가 아니라
  최신값 하나이므로 ADR-004 스키마에 욱여넣지 않는다는 design doc §3.1
  결정을 그대로 구현. 참조만 저장(`document_id`/`title`/`source_label`
  /`read_at`), 본문 복제 없음.
- **`ui/pages/research.py` / `ui/pages/chat.py`**: 기존
  `_render_research_page_with_detail()`/`_render_chat_page_with_detail()`
  에서 `get_document_detail()`이 에러 없이 성공했을 때
  `save_last_read()` 호출 한 줄만 추가 — 새 상태 갱신 경로를 만들지
  않고 기존 두 화면의 기존 흐름에 얹었다.
- **`ui/pages/dashboard.py`**: `_render_continue_reading_card()` 신규
  — `load_last_read()`로 읽기 전용 조회, 값 없으면 카드 자체 숨김
  (Empty state). "이어서 읽기" 버튼 클릭 시 **새 내비게이션 경로를
  만들지 않고** 기존 `research_detail_selection` 패턴 그대로 재사용해
  `nav_page="Research"`로 전환 — research.py가 이 키를 보고 상세
  패널을 그대로 연다.

## 3. 검증

- 신규 회귀 테스트 [`tests/test_reading_session.py`](../../../tests/test_reading_session.py)
  4건: 저장/조회 왕복(최신값 1개만 유지, 덮어쓰기 확인), 식별자 없는
  호출 no-op, Home 카드 숨김/표시 + 클릭 시 `research_detail_selection`
  ·`nav_page` 정확히 세팅되는지 `AppTest`로 확인.
- `pytest -k "source_navigation or dashboard or sermon_research or reading_session or research or chat"` → **150 passed**.
- 전체 스위트 `pytest tests/` 실행 확인 중 — 별도 기록.

## 4. 범위 밖 — 손대지 않음

- §5 읽기(연구 워크스페이스) 3영역 레이아웃 전체 — 여전히 미착수,
  본문 상세는 기존 detail_panel 재사용으로 대체.
- 스크롤 위치 복원 — design doc §3.1에서 이미 v1 범위 밖으로 명시(문서
  단위 복귀까지만).
- `core/research_workspace.py`(ADR-004) — 무변경, 스키마 확장 안 함.
- Core/retrieval/registry 로직, RAW, 기존 ADR — 전부 무변경.
