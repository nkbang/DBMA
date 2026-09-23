---
title: "ADR-035: NAE 목회자 서재 자동화 (Phase 2)"
category: architecture
based_on:
  - docs/NAE_PASTOR_FEATURE_REALIGNMENT_REPORT_001.md §6 (C1, 2026-09-23)
  - docs/NAE_UI_PHASE1_INTEGRATION_REPORT.md (Phase 1, PR #75, 병합됨)
  - docs/architecture/ADR-004-Research-Workspace-Layer.md (Approved 아님, Proposed — 세션 저장 선례)
  - docs/architecture/ADR-005-Research-Workspace-Memory-Governance.md (Proposed — lifecycle 결정)
  - docs/architecture/ADR-022-DBMA-N8N-Automation-State-Machine.md (Approved — 자동화 안전장치 선례, NAE 코퍼스 도메인)
  - docs/architecture/ADR-023-DBMA-N8N-Automation-Full-Processing.md (Approved — CLI 드라이버 boundary 선례)
  - ui/pages/library.py:685-707 (2026-09-07 오리판 정리 UX 사고 기록 — 자동 삭제 위험 실측 근거)
created: 2026-09-23
status: Proposed (구현 전, HQ 승인 대기)
scope_modified: docs/architecture/ only (코드 미수정)
---

# ADR-035: NAE 목회자 서재 자동화 (Phase 2)

| | |
|---|---|
| Status | **Proposed** (CUE 초안, C1 Review + Rev. Bang 승인 대기) |
| Date | 2026-09-23 |
| Deciders | CUE (초안), C1 (Review 완료 — `docs/agents/c1/C1-TASK-ORDER-071-COMPLETE.md`), Rev. Bang (승인 대기) |
| Input | `NAE_PASTOR_FEATURE_REALIGNMENT_REPORT_001.md` §6 (C1), Phase 1 UI 통합 완료(PR #75) 이후 후속 |
| Supersedes | — |
| Superseded by | — |
| **절대 변경 금지 (CLAUDE.md 원칙 재확인)** | `core/retrieval.py`(Retrieval Engine), TSU Pipeline, Embedding Engine, RAW 원본 파일, Production Registry(`core/dataset_registry.py` — ADR-023 §후속기록 인용). 이 ADR은 이들을 호출만 하는 **트리거 계층**만 추가하며, 위 5개 Authority의 내부 로직·스키마는 무수정. |
| **NAE n8n 자동화(ADR-022/023, Approved)와의 관계** | ADR-022/023은 **NAE 코퍼스 확장 트랙**(대량 소스 등록, `NAE/pipeline/registration/*`)의 자동화이며 n8n 기반이다. 이 ADR은 **목회자 개인 서재 트랙**(`ui/pages/processing.py`, `core/processing.py`, 개인 PDF/EPUB 업로드)의 UI 내 자동화로, 도메인·저장소·워크플로우 엔진이 완전히 분리되어 있다 — 서로 무관, 무변경. |

---

## 1. Context

Phase 1(화면 통합, PR #75)이 병합되어 사이드바가 3화면으로 축소됐다.
`NAE_PASTOR_FEATURE_REALIGNMENT_REPORT_001.md` §6은 이어서 "수동 작업
6건을 자동화하자"고 제안했다. 코드를 먼저 확인한 결과 제안 중 **이미
구현되어 있는 항목**과 **이미 한 번 자동화했다가 사고로 되돌린 항목**이
섞여 있어, 그대로 구현하면 중복 작업 또는 재발 사고가 된다. 이 ADR은
실제 코드 상태를 근거로 항목별 채택/기각을 결정한다.

## 2. 항목별 현재 상태 (코드 실측)

| C1 제안 항목 | 실제 상태 | 근거 |
|---|---|---|
| 휴지통 비우기 → 30일 자동 삭제 | **이미 구현됨** — 신규 작업 불필요 | `core/raw_hygiene.py::maybe_purge_expired_trash()`가 library 페이지 렌더마다 자동 호출(`ui/pages/library.py:856`, C1 Review에서 843이라 재지적됐으나 843은 `_render_trash_section()` 함수 정의/docstring 시작 줄이고 실제 호출문은 856이 맞음 — 재확인 완료), `TRASH_RETENTION_DAYS=30`(`core/config.py:326`) |
| 세션 초기화 버튼 → 자동 저장/복원 | **이미 구현됨** — 신규 작업 불필요 | `core/research_workspace.py`(ADR-004/005), 페이지 진입 시 브라우저 세션당 `create_session()` 1회 자동 호출(`ui/pages/research.py:198` — C1 Review(Task Order 071)에서 줄번호 drift 지적받아 재확인 후 정정, Phase 1 통합으로 파일 앞부분에 코드가 추가되며 이동함), 수동 초기화 버튼 없음 |
| 문서 업로드 후 "처리 시작" 버튼 → 폴더 감지 자동 인제스트 | **부분 구현** — 업로드는 "업로드 및 자동 처리" 버튼 1회 클릭으로 이미 통합됨(`ui/pages/processing.py:132`). 다만 **Finder 등으로 RAW 폴더에 직접 넣은 파일을 감지하는 폴더 워처는 없음** | `ui/pages/processing.py:428-432`(RAW 폴더 스캔은 별도 수동 "문서 처리 시작" 버튼) |
| 검색 결과 수동 선택 → 설교 연구에 자동 수집 | **미구현** — 실제 갭 | `ui/pages/research.py::_render_send_to_sermon_research_button`는 명시적 클릭 필요 |
| 인덱스 갱신 수동 트리거 → 파일 변경 감지 자동 갱신 | **미구현** — 실제 갭 | `core/index_orchestrator.py`는 `process_one_file()` 호출 시점에만 갱신, 파일시스템 워처 없음 |
| 자료 중복/오리판 수동 정리 → **주간 백그라운드 자동 정리** | **기각 대상 — 이미 한 번 시도 후 사고로 되돌림** | `ui/pages/library.py:685-707` 주석: 2026-09-07 자동/원클릭 정리 UX에서 오리판 판정 50건 중 37건이 실제로는 사용자가 되찾고 싶어한 파일이었음(13건만 진짜 정리 대상). 이후 체크박스 선택 + 명시적 확인 UX로 전환. **완전 자동(무인) 삭제로 되돌리면 동일 사고 재발 위험** |

## 3. Decision

### 3.1 채택 — 낮은 위험, additive(생성/알림)만 하는 자동화

1. **RAW 폴더 워처(신규)**: `core/raw_hygiene.py`와 동일 계층에 파일
   존재 여부만 가볍게 폴링하는 `core/raw_folder_watcher.py`(신규)를
   추가한다. 새 파일 발견 시 **자동으로 처리를 실행하지 않고**, 대시보드/
   Processing 화면에 "새 파일 N건 발견 — 처리하기" 알림만 띄운다(원클릭
   확인은 유지). 완전 무인 자동 처리가 아니라 "감지 후 원클릭"으로
   범위를 좁힌다 — 업로드 경로와 동일한 안전 수준(사용자가 최종
   트리거)을 RAW 직접 투입 경로에도 맞춘다.
   - **구현 시 반드시 지킬 조건(C1 Review RQ3 반영)**: 이미 알림을
     띄운 파일을 재알림하지 않도록 감지 결과를 마킹(중복 감지) —
     "처리하기" 클릭이 RAW 폴더에 파일을 다시 쓰는 경로(예: 업로드
     임시 복사본)와 워처의 폴링 주기가 겹치면 같은 파일을 반복
     알림할 위험이 있다. 폴링은 `maybe_purge_expired_trash()`처럼
     하루 1회 등으로 제한하고, 장시간 실행 시 파일 핸들이 누적되지
     않도록 매 폴링마다 새로 스캔하고 리소스를 즉시 해제한다.
2. **검색 결과 자동 수집(옵트인)**: 설교 연구 화면에 "최근 검색 결과
   자동 반영" 토글(기본 꺼짐)을 추가해, 켠 사용자에 한해 검색 결과
   상위 N건을 `sermon_research_selection` 버퍼에 자동 추가한다. 기존
   수동 "설교 연구에 추가" 버튼은 유지(옵트인이므로 회귀 없음).
3. **인덱스 자동 갱신**: `process_one_file()` 성공 직후
   `index_orchestrator`의 증분 갱신을 자동 호출하도록 연결한다(생성/
   갱신만 하는 additive 동작이라 삭제 자동화와 위험 등급이 다르다).
   - **구현 시 반드시 지킬 조건(C1 Review RQ3 반영)**: 여러 파일이
     동시에 업로드/감지될 경우 인덱서 갱신 호출이 겹치지 않도록
     순차 처리(큐잉) 또는 락으로 직렬화한다 — 현재 `process_one_file()`
     자체가 파일 단위 순차 호출을 전제하므로, 이 automation 계층에서
     그 전제를 깨고 병렬 트리거를 걸지 않는다(신규 동시성 제어를
     만드는 대신 기존 순차 호출 방식을 그대로 재사용).

### 3.2 기각 — 자동(무인) 삭제/정리는 도입하지 않는다

- 중복 파일·오리판 문서의 **주간 백그라운드 자동 정리는 이 ADR
  범위에서 기각**한다. 2026-09-07 사고(§2)가 보여주듯 "오리판으로 보이는
  파일"의 상당수가 실제로는 사용자가 원하는 파일이었다 — 판정 로직을
  개선하지 않는 한 자동화는 동일 실수를 반복 재생산할 뿐이다.
- 대안: 기존 체크박스+확인 UX(이미 2026-09-07에 도입되어 안정화됨)를
  유지하고, 필요하면 "정리 대상 있음" 알림 빈도만 높인다(무인 삭제
  없음).

## 4. Consequences

- 목회자 체감 자동화는 "새 파일 감지 알림"과 "인덱스 자동 갱신" 2건이
  핵심이며, 파괴적 작업(삭제)은 여전히 사람이 최종 확인한다 — 안전과
  편의의 균형을 코드 실측 근거로 결정했다.
- ADR-022/023과 도메인이 겹치지 않으므로 병행 진행 가능, 서로 참조만
  하고 무변경.
- 이미 구현된 2개 항목(휴지통/세션)은 Build Report에 "완료 확인"으로만
  기록하고 별도 구현 불필요.

## 5. 승격 조건 (Proposed → Approved)

CLAUDE.md CUE Operating Policy 기준 4개 전부 충족 시:
1. 구현 완료(§3.1 3건)
2. 회귀 테스트 통과
3. C1 독립 리뷰 완료
4. 사용자(Rev. Bang) 승인

4개 중 하나라도 미충족 시 Proposed 유지, 다른 구현의 근거로 사용하지 않음.
