# UI 기능 재배치 제안 v1 (2026-08-25)

**작성**: CUE — 전수 조사 기반 제안 문서. 코드 미수정, 사용자 확정 전까지
어떤 항목도 착수하지 않음.
**조사 근거**: UI 탭 10개 + 온보딩 전수(`ui/app.py:274-337` 기준),
core/*.py 전 모듈의 UI import 배선 grep, dead 코드 참조 0 직접 재확인.
**전제**: CLAUDE.md "UI는 탭 구조를 유지한다" — 탭 구조 자체는 유지하고,
탭 안의 기능 배치와 노출 여부만 다룬다. 브랜드 동결(내서재/NAE) 준수.

---

## A. 현황 요약

- 탭 구성: 홈 / 내 자료 / 자료 등록 / 자료 찾기 / AI에게 질문 / 연구하기 /
  설교 준비 / 설교 모음 정리 / (Monitor, admin 전용) / 도움말
- 최근 추가 기능 3종(RAW 중복 경고·휴지통 자동 비우기·원본 삭제 감지)은
  전부 "내 자료" 탭에 정상 배선돼 있음 — 재배치 불필요.
- 문제는 세 갈래: **(1) 죽은 UI 코드가 4개 파일 남아있음, (2) 설정 UI가
  아예 없음(dead 파일이 설정 화면이었음), (3) 구현 완료된 검색 인프라
  전체가 UI에서 잠겨 있음.**

## B. 제안 항목 (우선순위순)

### P1 — 설정 화면 부재 (실사용 영향 최대)

`ui/sidebar.py`(chunk_size/overlap/use_ocr 조정 UI)가 어디서도 import되지
않는 dead 코드로 확인됨(참조 0, CUE 직접 재검증). 즉 **현재 사용자는 UI에서
어떤 설정도 바꿀 수 없다.** config.yaml 주석 스스로도 "GEN_MODEL_OPTIONS
기반 UI 모델 선택 필요"라고 지적한 상태.

**제안**: "설정" 섹션 신설(별도 탭 또는 사이드바 하단 expander — 탭 구조
유지 원칙상 후자 권장). 1차 노출 대상(전부 config.yaml에 이미 존재):
- 생성 모델 선택(`ollama.default_gen_model` + `gen_model_options`)
- `rag.top_k`, `default_temperature`
- 휴지통 보관기간(`maintenance.trash_retention_days` — 현재 표시만 되고
  조정 불가)
- chunk_size/overlap/use_ocr (dead sidebar가 하던 것 복원)

**위임 경로**: 설계·배치는 CUE, 항목별 위젯 배선은 확정 후 C1 조건부
(단순 폼 배선, 항목당 스니펫 단위로 쪼개서).

### P2 — 죽은 UI 코드 정리 (혼동 원인 제거)

참조 0으로 확인된 파일: `ui/tabs.py`(203줄, 구 처리 탭),
`ui/sidebar.py`(44줄, P1에서 기능 복원 후), `ui/components/source_link.py`
(136줄), `ui/theme` aggregate(`__init__.py`/`typography.py`/`spacing.py` —
전 페이지가 `ui.theme.colors`만 직접 사용).

**제안**: `archive/legacy/`로 이동(과거 `dbma.py` 격리와 동일 절차,
ADR-001/003 선례). 삭제가 아니라 격리 — 파일 관리 규칙("이름이 비슷한
임시 파일은 정리 대상") 부합.

**위임 경로**: 이동 자체는 C1 조건부(단순 파일 이동 + import 무결성
테스트), 사전에 CUE가 이동 목록 확정.

### P3 — 잠긴 검색 인프라의 단계적 노출

`USE_INVERTED_INDEX` env var가 기본 false라 Tantivy BM25·Query Planner·
RRF·SearchResultCache·BibleIndex 경로 전체가 프로덕션에서 실행 자체가 안
됨. 오늘 커밋 2건(`5c38d1b` bible route file_scope, `ca5e8a4` 인덱스
staleness)으로 이 경로의 알려진 결함이 줄었지만, **gold standard 96개
재검증(TASK-ORDER-050 §5 blocker #2)이 아직 미완**이라 지금 켜는 건 이르다.

**제안(순서 고정)**:
1. gold standard 96개 재실행으로 precision@1 회귀 확인 (CUE 전담 —
   벤치마크 판정)
2. 통과 시 Monitor 탭(admin 전용)에 하이브리드 경로 A/B 토글 + Search
   Telemetry 통계 화면(현재 클릭 기록만 하고 조회 화면이 없음) 추가
3. 실사용 검증 후에야 기본 경로 전환 논의 — 이건 별도 승인 사안

### P4 — 중복 정리 (소규모)

- 사이드바 라벨 "자료 찾기"(Research)와 `library.py:106` 페이지 제목
  "자료 찾기"가 충돌 — 내 자료 쪽 제목 변경으로 해소(단순 문자열 치환,
  C1 적합).
- 검색 진입점 3중화(홈/내 자료/자료 찾기)와 chat↔research의 답변 경로
  공유는 **의도된 공유로 판단, 통합 제안 안 함** — 근거 없는 구조 변경
  금지 원칙.

### 제안하지 않는 것

- 탭 통합/분리/순서 변경 — CLAUDE.md 탭 구조 유지 원칙.
- dormant core 4종(hierarchical_chunk_builder 등)의 UI 노출 — 프로토타입
  단계, Evidence Before Promotion.
- scripts/ 터미널 기능의 UI 이식 — Ops Dashboard scope discipline
  (충분하면 확장 중단) 적용.

## C. 확정 요청

| 항목 | 결정 필요 사항 |
|---|---|
| P1 | 설정 위치(사이드바 expander vs 새 탭), 1차 노출 항목 범위 |
| P2 | 4개 파일 격리 승인 |
| P3 | gold standard 재검증 착수 승인 |
| P4 | 라벨 치환 승인 |

---

## D. 실행 결과 (2026-08-25, 사용자 승인 후 CUE 직접 구현)

승인: "P1 사이드바 expander로, P2 P4 승인, 전부 진행하라". P3은 별도 승인
대기(미착수).

### P1 — 범위 정정 후 구현

**§B의 P1 노출 목록은 과했다.** 구현 직전 실제 코드를 확인한 결과 4개 중
2개는 이미 다른 탭에 있었다:

| 제안했던 항목 | 실제 | 조치 |
|---|---|---|
| 생성 모델 선택 | UI 어디에도 없음 | **추가함** |
| temperature | UI 어디에도 없음 | **추가함** |
| chunk_size/overlap/OCR | `ui/pages/processing.py:298-327`에 이미 있음 | 제외(중복 방지) |
| top_k | `ui/pages/research.py:228` 슬라이더로 이미 있음 | 제외(중복 방지) |
| 휴지통 보관기간 | config.yaml을 읽는 모듈 상수 — 재시작 없이 반영 불가 | 제외 |

즉 §B가 "dead sidebar.py가 하던 것 복원"이라고 쓴 부분은 틀렸다 — 그
파일은 없어진 기능이 아니라 **처음부터 중복이었고 아무도 호출하지 않던
코드**였다(하드코딩 기본값을 반환만 하고 config.yaml도 읽지 않았음).

구현: `ui/app.py::_render_settings_expander()` (사이드바 하단 expander,
탭 구조 불변) + `ui/pages/chat.py::_settings_overrides()`로 답변 생성
경로에 배선. 세션 범위 — config.yaml에 쓰면 재시작해야 반영되고 git 추적
파일을 런타임에 고쳐 쓰게 된다.

배선을 실제로 한 이유: 설정 위젯이 렌더는 되는데 아래로 전달되지 않는
것이 정확히 격리된 `ui/sidebar.py`의 실패 방식이었다. 회귀 테스트
`tests/test_chat_settings_overrides.py` 8개로 고정(위젯 렌더링 +
값 전달 + 키 이름 계약, temperature=0.0이 falsy로 버려지지 않는지 포함).

### P2 — 5개 파일 격리 (제안 4개 + 1개)

`archive/legacy/ui/` 아래로 `git mv`: `tabs.py`, `sidebar.py`,
`components/source_link.py`, `theme/typography.py`, `theme/spacing.py`.
`ui/theme/__init__.py`는 격리한 두 모듈을 import하고 있어 colors만 남기고
정리(패키지 자체는 유지 — 전 페이지가 `ui.theme.colors`를 직접 import).

### P4 — 라벨 충돌 해소

`ui/pages/library.py:106` 페이지 제목 "자료 찾기" → "내 자료"(사이드바
라벨과 일치, Research 탭과의 충돌 해소).

### 검증

`~/envs/dbma311`로 전체 `pytest tests/` — **2579 passed, 2 failed, 4
skipped**. 실패 2건은 `test_control_plane.py::TestN8NGateway`의
ConnectionRefused(로컬 n8n 웹훅 미기동)로, UI를 전혀 참조하지 않는
기존 환경 문제다(C1-TASK-ORDER-050-REPORT.md §4에 동일 실패 기록).
설정 위젯 렌더링은 Streamlit AppTest로 실제 실행 확인(모델 4종 선택
가능, 기본값 config.yaml과 일치).

**미착수**: P3(하이브리드 경로 노출) — gold standard 96개 재검증이
선행 조건이며 별도 승인 사안.
