# DBMA-UX-006 — 내서재(NAE) Professional UX/UI Redesign: Audit & Architecture

**문서 상태:** Deliverable 1~3, 5 완료 / Deliverable 4는 별도 HTML 목업으로 제공
**작성일:** 2026-07-31
**작업 범위:** 감사 + 설계 제안만. 코드 구현 없음 (Task Order §13 준수)
**선행 문서:** `docs/DBMA-UX-001~005-*.md`(이전 트랙, 라벨/용어 수준 정정),
`docs/governance/DBMA-BRAND-GOV-001.md`

---

## Deliverable 1 — Existing UI Audit

### 조사 범위

`ui/pages/*.py` 9개 전부(app.py 사이드바 포함), `docs/design/stitch/pastoral_research_desk/*`
(이전 Stitch 목업 9종), `README.md`(약속된 사용자 경험 서술)를 직접 열람했다.
이전 DBMA-UX-001~004 트랙에서 이미 브라우저로 실행하며 검증한 결과를 근거로 쓴다.

### 평가 기준별 증거

**1. Product Identity — 실패**
`README.md` 1~3행: *"내서재 (NAE) — 문서 기반 메모리 어시스턴트. 다양한 형식의
문서를 처리하고 RAG(Retrieval-Augmented Generation) 기반 검색·채팅 기능을
제공합니다."* 제품을 소개하는 첫 문장이 이미 "RAG"라는 엔지니어링 용어로
시작한다. UI 페이지 목록도 "Dashboard(사용자용 통계 대시보드)"로 시작해
"Monitor(시스템 모니터링)"로 끝난다 — 9개 페이지 중 정체성이 "개인 연구
서재"가 아니라 "문서 처리 파이프라인 관리 도구"에 가깝다.

**2. Information Architecture — 부분 실패**
현재 IA는 파이프라인 단계를 그대로 노출한다: Dashboard → Library →
**Processing**(문서 처리) → Research → Chat → 설교문 작성 → 설교 리뷰 →
**Monitor**(시스템 모니터링) → 도움말. "Processing"과 "Monitor"는 목회자의
연구 흐름이 아니라 엔지니어의 파이프라인 운영 흐름이다. "Research"와
"Chat"이 분리되어 있어 "검색했는데 왜 또 채팅으로 가야 하나"라는 이중
진입점 문제가 있다.

**3. Navigation Hierarchy — 부분 실패**
`ui/app.py::_render_sidebar()`의 실제 라벨(이번 세션 UX-002/004에서 이미 정정):
`홈 / 자료 찾기 · 내 자료 / 자료 등록 / 연구하기 / AI에게 질문 / 설교 준비 /
설교 모음 정리 / 도움말`. 라벨 자체는 이미 한글화됐지만, **"자료 찾기"와
"연구하기"가 같은 검색 기능을 서로 다른 화면(Library 내 검색 vs Research
페이지 검색)에서 중복 제공**한다 — 사용자가 어디서 찾기 시작해야 하는지
구조적으로 모호하다.

**4. User Workflow — 단절됨**
Research(연구) → Sermon Draft(설교 준비) 사이에 실제 연결 다리가 없다.
`sermon_draft.py`는 성경 목록에서 직접 커버리지 버튼을 눌러 시작하거나
빈 입력에서 시작하는 구조이고, Research 페이지의 "세션 저장" 결과를
설교 준비로 가져오는 경로가 없다. Task Order §6-F가 요구하는
`Research → Selected Sources → Notes → Outline → Draft` 흐름이 전혀 없다.

**5. Visual Hierarchy — 혼재**
`dashboard.py`는 실데이터 기반 상태 배너 + 퀵액션 3개로 비교적 단순하지만,
"RAW 폴더 파일 115권 / 정리된 자료 81개 문서"처럼 **파이프라인 진행률
지표가 첫 화면 최상단**에 있다(Task Order §6-A가 명시적으로 최소화를
요구하는 부분). `research.py`는 검색창 아래 결과 카드 + 세션 히스토리 +
AI 인사이트 카드 3종이 위계 없이 나열된다.

**6. Typography — 부분 양호**
`ui/app.py::_apply_global_styles()`가 Hanken Grotesk + Source Serif 4를 이미
전역 로드하고 있고, `research.py`의 발췌문에 Source Serif 4 이탤릭을 쓰는 등
읽기용 서체 개념은 이미 있다. 다만 **본문 읽기 화면 자체가 없어**(UX-005에서
확인) 이 서체가 실제 "긴 글 읽기"에 쓰이는 곳이 없다 — 장식으로만 존재.

**7. Spacing / Density — 화면마다 불일치**
`dashboard.py`는 여백이 넉넉한 카드형, `research.py`의 검색 결과 카드는
좁은 padding(16px)에 배지·별점·발췌문·버튼이 조밀하게 들어간다. 통일된
spacing scale이 코드 어디에도 정의돼 있지 않다(`ui/styles.py`는 12줄짜리
빈 껍데기).

**8. Accessibility — 미평가 상태**
포커스 표시, 명도 대비 수치 등을 검증한 테스트나 문서가 없다. 이번 감사
범위에서 실측하지 않았음을 명시한다(Existing Functionality Rule 준수 —
확인 안 된 것을 확인됐다고 쓰지 않는다).

**9. Consistency — 실패, 구체적 증거**
같은 개념(신뢰도)이 화면마다 다르게 노출된다:
- `research.py` 결과 카드: 이번 세션에 별점(⭐)으로 이미 정정
- `chat.py:513-522`: **아직 미정정** — `f"신뢰도(final_score): {score:.4f}"`,
  `f"근거 신뢰도(citation): {citation.evidence_confidence:.4f}"` — 파이썬
  변수명(`final_score`, `citation`, `evidence_confidence`)이 괄호 안에
  그대로 노출되고 소수점 4자리 원시 점수가 사용자에게 보인다. 이는
  DBMA-UX-004에서 잡은 것과 완전히 같은 유형의 위반이 **Chat 화면에는
  아직 남아있다**는 뜻이다 — 화면별 산발적 정정의 한계를 보여주는 직접
  증거.

**10. Professionalism — 위 근거들의 총합**
"RAG", "final_score", "citation", "evidence_confidence" 같은 변수명이
괄호째 노출되는 화면은 관리자 콘솔처럼 보이지, 개인 서재처럼 보이지 않는다.

**11. Technical Leakage — 확인된 위반 재정리**

| 화면 | 위반 | 상태 |
|---|---|---|
| README 첫 문장 | "RAG(Retrieval-Augmented Generation)" | 미정정 |
| Chat 인용 캡션 | `신뢰도(final_score): 0.xxxx`, `근거 신뢰도(citation): 0.xxxx` | **미정정 — 이번에 신규 발견** |
| Dashboard | RAW 폴더/정리된 자료 파이프라인 수치가 최상단 | 구조적 — 라벨 문제 아님 |
| (기타 9건) | RAG/벡터DB/임베딩/청킹/RRF/TSU/Hybrid·BM25·Vector 등 | UX-002/004에서 정정 완료 |

**12. Senior-user Usability — 미평가**
글자 크기/터치 타깃 실측 없음. 다만 `research.py` 검색 옵션 패널이
"Hybrid/BM25/Vector/RRF"였던 것(관리자 게이트 완료)처럼, **장년층 목회자가
이해할 수 없는 알고리즘 선택지가 기본 화면에 있었다는 사실 자체**가
senior-user usability 실패의 직접 증거다.

**13. Research Workflow Continuity — 실패**
위 4번과 동일 — Research에서 Sermon Draft로 넘어가는 다리가 없다.

**14. 유지할 요소 (버릴 필요 없는 것)**
- Hanken Grotesk + Source Serif 4 폰트 페어링, cream(#F5F3EE 계열) 배경 —
  "scholarly/calm" 방향과 이미 부합, 재사용
- `dashboard.py`의 "지금 바로 질문할 수 있어요" 같은 사람 중심 문장 톤
- Sample Library(UX-003) 읽기 전용 배지 패턴 — Citation/Provenance
  시각 언어로 확장 가능
- 관리자 기능 게이트(`NAE_ADMIN_MODE`) 패턴 — 신뢰할 수 있는 은닉 방식으로
  검증됨, 계속 사용

---

## Deliverable 2 — NAE UX Architecture

### Product UX Principles

1. **"내가 지금 어디에 있는가"가 "무엇을 할 수 있는가"보다 먼저** — 첫 화면은
   기능 목록이 아니라 연구 맥락(최근 읽은 것, 이어서 할 것)으로 시작한다.
2. **검색은 목적지가 아니라 통로** — 검색 결과 화면과 "읽기/연구" 화면을
   분리하지 않는다. 결과 → 문맥 → 출처 → 다음 질문이 한 흐름 안에 있어야
   한다.
3. **인용은 신뢰의 표현이다** — 출처 표시는 기능 버튼이 아니라, 이 정보를
   믿어도 되는 이유를 보여주는 시각 요소여야 한다.
4. **기술은 숨기되 삭제하지 않는다** — 관리자 모드 게이트는 유지, 일반
   사용자 화면에서는 등장하지 않는다.
5. **연구는 설교로 끊기지 않고 이어진다** — Research에서 고른 자료가 설교
   준비 화면에 그대로 살아있어야 한다.

### Information Architecture (제안)

Task Order §5의 선형 흐름을 그대로 복제하지 않고, **허브 + 흐름** 구조로
제안한다 — 목회자의 실제 작업은 선형이 아니라 "홈에서 시작해 서재나
검색으로 갔다가 다시 홈으로 돌아오는" 순환이기 때문이다.

```text
                    ┌─────────┐
        ┌──────────▶│   홈    │◀──────────┐
        │           └────┬────┘           │
        │                │                │
        │      ┌─────────┴─────────┐      │
        │      ▼                   ▼      │
        │  ┌────────┐         ┌─────────┐ │
        │  │ 내 자료 │◀───────▶│ 검색·연구 │ │
        │  └───┬────┘         └────┬────┘ │
        │      │                   │      │
        │      └─────────┬─────────┘      │
        │                ▼                │
        │           ┌─────────┐           │
        │           │  읽기    │           │
        │           └────┬────┘           │
        │                │                │
        │                ▼                │
        │           ┌──────────────┐      │
        │           │ 인용 · 출처   │      │
        │           └──────┬───────┘      │
        │                  │              │
        │                  ▼              │
        │           ┌──────────────┐      │
        └───────────│ 설교 연구     │──────┘
                     └──────┬───────┘
                            ▼
                     ┌──────────────┐
                     │  설교 작성    │  (기존 sermon_draft.py 확장)
                     └──────────────┘
```

내비게이션 메뉴(사이드바)는 6개 허브로 축소 제안:
**홈 / 내 자료 / 검색·연구 / 설교 연구 / 도움말** — "자료 등록"(Processing)과
"시스템 모니터링"(Monitor)은 목회자용 주 메뉴에서 제거하고 관리자 전용
경로(설정 하위 또는 `NAE_ADMIN_MODE`)로 이동 제안. "AI에게 질문"(Chat)은
독립 메뉴가 아니라 **검색·연구 화면 안의 한 모드**로 흡수 제안 — 검색과
채팅을 사용자가 구분해서 선택할 이유가 없다.

### Primary User Flows

**흐름 A — 빠른 확인**: 홈 → (최근 읽은 자료 클릭) → 읽기 화면 재진입.
**흐름 B — 새 연구**: 홈 또는 내 자료 → 검색·연구 → 결과 클릭 → 읽기 →
인용·출처 확인 → "설교 연구로 보내기".
**흐름 C — 설교 준비**: 설교 연구(선택한 자료·메모 모아보기) → 개요 →
설교 작성(기존 화면).

### Screen Hierarchy

```text
Level 0  홈
Level 1  내 자료 · 검색·연구 · 설교 연구 · 도움말
Level 2  읽기 (내 자료/검색·연구에서 진입)
Level 3  인용·출처 (읽기 화면의 패널 또는 확장 뷰)
```

---

## Deliverable 3 — Visual Design System Proposal

기존 Stitch 톤(cream 배경 + Hanken Grotesk/Source Serif 4)을 폐기하지 않고
정제한다 — Task Order §7의 "scholarly/calm/trustworthy/readable/mature"
방향과 이미 부합하는 부분은 유지하고, "modern SaaS dashboard" 잔재(다채로운
아이콘 원형 배지, 통계 타일 상단 배치)를 제거한다.

**Typography**
- 헤드라인/UI: Hanken Grotesk (기존 유지)
- 읽기 본문: Source Serif 4, 최대 폭 680px(약 65자), 줄간격 1.7
- 데이터/숫자(문서 수 등 꼭 필요한 곳만): tabular nums

**Color** (기존 THEME 토큰 확장, 신규 색상 최소 추가)
- 배경: `#F7F5F0`(기존 `#F5F3EE`에서 살짝 데움)
- 텍스트: `#1F2421`
- 강조(액션): `#2F5D50` (짙은 서재 녹색 — 기존 `#264B5D` 청색 계열보다
  "서재"라는 정체성에 더 부합, 대체 제안)
- 인용/출처 전용 톤: `#A8763E`(황토) — Sample Library 읽기전용 배지에서
  이미 검증된 톤을 인용 시스템 전체로 확장
- 상태색(성공/경고/오류)은 기존 THEME 값 유지 — 이미 시맨틱하게 분리돼 있음

**Spacing**: 8px 그리드(기존 Stitch DESIGN.md 값 재사용), 화면 간 padding
통일(현재 화면마다 12~24px로 불일치하던 것을 24px 고정 제안)

**Component Language**
- 카드: 그림자 대신 1px 헤어라인 테두리(기존 Stitch 원칙 유지)
- 인용 카드: 좌측 4px 세로 바(황토색) + 저자/출처/원문 3단 구조 —
  "버튼 하나"가 아니라 카드 전체가 출처 정보
- 검색 결과: 별점(이미 UX-004에서 적용)만 사용, 알고리즘/원시 점수는
  구조적으로 관리자 뷰로만 존재

**Navigation Treatment**: 사이드바 폭 고정, 라벨 6개로 축소(Deliverable 2),
현재 상태 위젯("자료 검색: 정상" 등)은 사이드바 최하단으로 축소하거나
제거 제안 — 홈 화면 최상단 배치는 유지하지 않음.

**States/Errors**: 처리되지 않은 문서 클릭 시 "아직 준비되지 않았습니다"류
안내 + 다음 행동 버튼(Dead End 금지, 기존 원칙 유지).

---

## Deliverable 5 — Implementation Mapping

| Design 요소 | 기존 컴포넌트 | 처리 |
|---|---|---|
| 홈 — 최근 작업 카드 | `dashboard.py::_render_library_summary()` 일부 | **기존 수정** — 파이프라인 수치 하단 이동, 최근 읽은 자료 섹션 신규 |
| 홈 — 퀵액션 | `dashboard.py::_render_quick_actions()` | **기존 유지** — 라벨/순서만 조정 |
| 사이드바 6메뉴 축소 | `ui/app.py::_render_sidebar()` | **기존 수정** — Processing/Monitor 이동, Chat 흡수는 **신규 컴포넌트** 필요 |
| 내 자료 | `library.py` | **기존 유지** — Sample Library 패턴(UX-003) 이미 부합 |
| 검색·연구 통합 | `research.py` + `chat.py` | **기존 수정 + 신규** — 두 화면의 검색/답변 로직을 한 화면으로 합치는 신규 컴포넌트 필요, backend 쿼리 로직은 무변경 |
| 읽기 화면 | 없음 | **신규 (UX-005)** — Library 상세 패널 확장 또는 신규 페이지, HQ 결정 대기 중 |
| 인용·출처 카드 | `chat.py::_render_source()` 계열 | **기존 수정** — `final_score`/`evidence_confidence` 원시 노출 제거(★ 표기로), 레이아웃을 카드형으로 변경 |
| 설교 연구(신규 허브) | 없음 | **신규** — Research 결과를 담는 "선택한 자료 모음" 컨테이너, `sermon_draft.py`와 연결 다리 |
| 설교 작성 | `sermon_draft.py` | **기존 유지** |
| 관리자 전용 경로 | `NAE_ADMIN_MODE` 게이트(이미 4곳 적용됨) | **기존 유지·확장** — Processing/Monitor를 여기로 이동 |

**Backend 의존성 (신규 capability로 별도 기록, 이번 범위 아님)**
- Research↔Chat 통합에는 두 화면이 현재 쓰는 서로 다른 세션 상태
  (`research_session_id` vs `chat_messages`)를 하나로 묶는 상태 설계가
  필요 — `core/retrieval.py` 자체는 무변경, UI 상태 레이어만 영향
- "설교 연구" 허브의 "선택한 자료 모음"은 현재 어떤 화면에도 없는 새
  세션 상태 — Core architecture 변경 없이 UI 상태(`st.session_state`)
  수준에서 구현 가능한 것으로 판단(미검증, 구현 착수 시 재확인 필요)
