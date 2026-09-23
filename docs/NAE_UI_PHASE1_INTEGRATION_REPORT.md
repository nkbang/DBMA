# NAE UI Phase 1 — 화면 통합 Build Report

**작성일:** 2026-09-23
**작성자:** CUE
**근거:** `docs/NAE_PASTOR_FEATURE_REALIGNMENT_REPORT_001.md`(C1) §4,
`docs/NAE_COMMERCIAL_APP_UX_SCREEN_BENCHMARK_001.md`(상업용 앱 화면 구조
검증), 사용자 승인 계획(탭 래퍼 방식, 위험 낮은 순 진행).

---

## 사전 조치: base 브랜치 동기화

이 세션의 워크트리 브랜치가 `main`(30커밋 뒤처짐, `sermon_library.py` 자체가
없는 구식 상태)을 기준으로 만들어져 있던 것을 발견해, 구현 착수 전
`origin/dev/dbma-engine`으로 fast-forward 동기화(충돌 없음). 실제 활성
통합 브랜치 기준으로 작업했다.

## Before / After

| 항목 | Before | After |
|---|---|---|
| 최상위 사이드바 메뉴 수 | 11개 (Dashboard/Library/Processing/Research/AI에게 질문/설교 연구/설교문 작성/저장된 설교/설교 리뷰/Monitor(admin)/도움말) | 8개 (Dashboard/Library/Processing/Research/설교 준비/설교 리뷰/Monitor(admin)/도움말) |
| 연구→설교 흐름 화면 전환 | Research → AI에게 질문(별도) → 설교 연구 → 설교문 작성 → 저장된 설교(별도) | Research(연구/채팅 탭) → 설교 준비(연구/작성 뷰) → (같은 화면에서 저장 확인은 Library 탭) |
| 내부 로직 변경 | — | 없음 (기존 `render_*_page` 함수/session_state 키/private 함수 전부 무변경, 탭·뷰 전환 wrapper만 추가) |

## 구현 방식 (3 Step)

기존 `render_a_page()`/`render_b_page()` 본문은 그대로 두고, 얇은
wrapper 함수를 만들어 화면을 묶었다. `st.tabs`는 코드에서 활성 탭을
바꿀 수 없다는 Streamlit 제약이 있어, 화면 간 자동 전환이 필요한 두
곳(설교 연구→작성 "이어가기", Dashboard "질문하기")은 이미 코드베이스가
쓰던 `nav_page` 패턴과 동일한 "session_state 키 + `st.radio`"로 구현했다.

| Step | 병합 | 방식 | 신규/변경 함수 |
|---|---|---|---|
| 1 | `library.py` + `sermon_library.py` | `st.tabs` (자동 전환 불필요) | `render_library_hub_page()` (`ui/pages/library.py`) |
| 2 | `sermon_draft.py` + `sermon_research.py` | `st.radio` + `sermon_workspace_view` | `render_sermon_workspace_page()` (`ui/pages/sermon_research.py`), `_go_to_sermon_draft` 수정 |
| 3 | `research.py` + `chat.py` | `st.radio` + `research_workspace_view` | `render_research_workspace_page()` (`ui/pages/research.py`), `dashboard.py::_go_to_chat()`, `onboarding.py` 상단 네비 분기 |

## 테스트

| Step | pytest 서브셋 | 결과 |
|---|---|---|
| 1 | orphan_notice/provenance/sermon_artifact/onboarding_topnav | 22 passed |
| 2 | sermon_research_hub/sermon_draft_claim_guard/save_artifact/repeat_penalty/onboarding_topnav | 30 passed |
| 3 | chat×5/research×3/onboarding_topnav/reading_session/sermon_research_hub | 68 passed |
| 전체 회귀 | `pytest tests/ -q` | **3155 passed, 17 skipped(기존), 0 failed** |

각 Step 모두 AppTest 헤드리스 렌더로 예외 없음(`ElementList()`)과 탭/뷰
전환 정상 동작을 추가 확인. **브라우저 시각 확인(Streamlit preview)은
이번 세션에서 로컬 서버 접속 시도가 권한 정책 게이트에 막혀 완료하지
못함** — 코드 레벨(pytest + AppTest) 검증만으로 완료 처리, 다음 세션에서
사람이 실제 브라우저로 3개 화면(내 서재/설교 준비/연구·채팅) 클릭 확인을
권장.

## 수정 파일

`ui/app.py`, `ui/pages/library.py`, `ui/pages/sermon_research.py`,
`ui/pages/research.py`, `ui/pages/dashboard.py`, `ui/pages/onboarding.py`,
`tests/test_sermon_research_hub.py`, `tests/test_onboarding_topnav.py`.
신규 문서: `docs/NAE_COMMERCIAL_APP_UX_SCREEN_BENCHMARK_001.md`,
본 문서.

## 제외 범위 (다음 HQ 결정 대기)

- `monitor.py`/`onboarding.py`/`sermon_review.py`/`NAE/benchmark/` 제거·분리
  — 이전 검토에서 보류 권고(모니터는 이미 `NAE_ADMIN_MODE` 게이트로
  처리돼 있어 추가 조치 불필요, 나머지는 실사용 근거 부족).
- research.py↔chat.py 공용 함수(`generate_answer` 등)를 별도 모듈로
  리팩터링하는 것 — 상업 앱 벤치마크에서도 확인된 "채팅을 검색 결과에
  완전히 인라인화"하는 더 급진적인 통합은 코드 재구성이 필요해 Phase 2
  이후 과제.

## Next

1. 사람이 실제 브라우저에서 3개 통합 화면 클릭 확인(권한 게이트로 이번
   세션에서 못한 부분).
2. HQ가 Phase 2(자동화 방안, §6) 착수 여부 결정.
