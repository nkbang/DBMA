# DBMA-UX-007 — 내서재(NAE) UX Implementation Specification

**문서 상태:** Gate 6 — 구현 계약(Implementation Contract)
**작성일:** 2026-07-31
**선행 문서:** `docs/DBMA-UX-006-PROFESSIONAL-REDESIGN-AUDIT.md`(Deliverable 1-5),
`docs/design/nae-professional-redesign/mockup.html`(시각 참조)
**성격:** 이 문서는 **구현 권한(implementation authority)**이다. mockup.html은
시각 참조(visual reference)일 뿐이며, C1은 mockup의 HTML 구조를 그대로
프로덕션에 이식하지 않는다 — 아래 컴포넌트 스펙을 따른다.

---

## Gate 상태

| Gate | 내용 | 상태 |
|---|---|---|
| 1 | Audit | PASS |
| 2 | Product Identity | PASS |
| 3 | IA | PASS |
| 4 | Visual Direction | PASS |
| 5 | Architecture Safety | PASS |
| 6 | Implementation Specification | **PASS (본 문서)** |
| — | HQ 승인 | **대기** |
| — | C1 Implementation | **BLOCKED — HQ 승인 후 착수** |

---

## 0. UX Invariant — 기술적 leakage 금지 (제품 경계 선언)

> Internal variable names, ranking scores, embedding scores, confidence
> calculations, algorithm names, and implementation identifiers MUST NOT
> appear in user-facing UI, in any form — including inside parentheses,
> labels, tooltips, captions, or error messages.

이것은 문구 수정 사항이 아니라 **제품 경계 규칙**이다. 앞으로 어떤 화면을
새로 만들거나 수정하든 이 규칙이 우선한다. 위반 예시(현재 `chat.py`에
존재, 수정 대상):

```text
❌ 신뢰도(final_score): 0.8734
❌ 근거 신뢰도(citation): 0.9102
❌ RRF 0.5102 / TSU / Hybrid·BM25·Vector·RRF / ROM 8:1-4
```

허용되는 대체 표현: **관련성**(별점 또는 "높음/보통/낮음"), **출처**,
**근거**, **원문**, **인용 정보**. 원시 숫자·영문 알고리즘명·내부
변수명은 어떤 형태로도 노출하지 않는다.

---

## 1. Global Navigation Specification

**사이드바 구성 (5메뉴, 고정)**

```text
🏠 홈
📚 내 자료
🔎 검색·연구
✍️ 설교 연구
💡 도움말
```

- Processing("자료 등록")과 Monitor("시스템 모니터링")는 사이드바에서
  제거. `NAE_ADMIN_MODE=1`일 때만 별도 "관리자" 섹션으로 사이드바
  하단에 노출(기존 Monitor 게이트 패턴 재사용 — `ui/app.py:188`)
- Chat은 독립 메뉴 항목이 아니다 — §4 "검색·연구" 스펙에 흡수
- 현재 상태 위젯("자료 검색: 정상" 등)은 사이드바 최하단에 유지하되
  시각적 강조 제거(캡션 크기, 구분선 위)
- 선택된 메뉴 항목의 활성 표시는 기존 `st.radio` 방식 유지(key="nav_page"
  프로그램 전환 패턴, `ui/app.py:195` 그대로 재사용 가능)

**라우팅 키 매핑** (기존 → 신규, 기존 내부 page_renderers 키는 유지해
회귀 위험 최소화):

| 신규 메뉴 | 내부 라우팅 키(유지) | 비고 |
|---|---|---|
| 홈 | `Dashboard` | 유지 |
| 내 자료 | `Library` | 유지 |
| 검색·연구 | `Research` (Chat 흡수) | 수정 |
| 설교 연구 | 신규 `SermonResearch` | 신규, `설교문 작성`(`Sermon Draft`)은 그 하위 단계로 연결 |
| 도움말 | `도움말` | 유지 |

---

## 2. Home Specification

**목적**: "무엇을 할 수 있는가"가 아니라 "내 연구가 어디 와 있는가".

**구성 순서(위→아래)**
1. 인사 헤드라인 (`h1`) — 정적 문구, 데이터 의존 없음
2. **이어서 읽기 카드** (existing but incomplete) — 가장 최근 연구
   세션의 마지막 위치. 데이터 소스: 신규 세션 상태 필요(§13 참고).
   자료 없으면 카드 자체를 숨기고 "빠른 시작"만 표시(Empty state, §9)
3. **최근 연구** 2열 그리드 — 최근 검색어 1건 + 최근 설교 연구 1건.
   데이터 소스: `research.py`의 세션 저장(existing) + 신규 설교 연구
   세션(§13)
4. **빠른 시작** 버튼 3개 — 검색·연구로 이동 / 내 자료 열기 / 설교
   연구 계속하기. `on_click=_go_to` 패턴 재사용(existing,
   `dashboard.py:39`)
5. 최하단 **조용한 통계** 1줄 — "내 서재 · 자료 81건 정리됨 · 자세히
   보기"(내 자료로 링크). 기존 `_render_library_summary()`의 파이프라인
   진행률 상세(RAW 폴더/처리 완료 등)는 이 화면에서 완전히 제거 —
   내 자료 화면으로 이동(§3)

**Mockup ↔ 컴포넌트 매핑**: `mockup.html` `.continue-card` → 신규
`_render_continue_card()`, `.home-grid` → 기존 `_render_library_summary()`
로직을 "최근 연구"용으로 재작성, `.action-row` → 기존
`_render_quick_actions()` 재사용.

---

## 3. Library Specification ("내 자료")

**기존 `library.py`(811줄) 유지·확장** — 전면 재작성 아님.

- Sample Library 섹션(기존, UX-003) 그대로 유지 — 이미 스펙에 부합
- 파이프라인 진행률 상세(RAW 카운트, 유형별 문서 등, 현재
  `dashboard.py`에 있는 것)를 **내 자료 화면 상단으로 이전** — Home에서
  뺀 자리를 여기서 받는다(§2와 대응)
- 검색창(`_render_search_bar`, existing)은 유지하되, 라벨을 "문서
  검색"에서 "내 자료에서 찾기"로 변경해 §4의 전역 검색·연구와 구분
- 문서 상세 패널의 "청킹 미리보기"(관리자 전용, 기존 게이트 유지)는
  그대로

---

## 4. Search & Research Specification ("검색·연구") — 핵심 신규 스펙

이 화면이 Chat + Research 통합의 실질적 계약이다.

### 4.1 단일 진입점

화면 상단에 검색창 하나만 존재한다. Placeholder: "성경 구절, 주제,
질문을 입력하세요…" — 검색어와 질문을 구분하지 않는다(사용자가 "로마서
8장"을 입력하든 "성령의 내주하심이 무슨 뜻인가요?"를 입력하든 같은
입력창).

**동작 분기 (내부 로직, 사용자에게는 안 보임)**:
- 입력이 검색에 가까우면(기존 `research.py`의 `_execute_research_query`
  경로) → §4.2 결과 카드 목록 표시
- 입력이 질문형이면(기존 `chat.py`의 RAG 답변 경로) → §4.2 카드 목록
  **위에** AI 답변 블록을 추가로 표시, 카드 목록은 그 아래 "참고한 자료"로
  이어짐
- 분기 판단 로직은 기존 백엔드(`core/retrieval.py`) 그대로 사용 —
  UI가 새로 판단하지 않는다. 이미 두 경로 모두 동일한
  `RankedCandidate`/`ParsedQuery` 모델을 쓰므로 병합 가능(Deliverable 5
  근거)

### 4.2 결과 카드 구조 (고정 스펙)

```text
┌─────────────────────────────────────────┐
│ [제목/본문 참조]              [★★★☆☆]   │  ← 관련성, 원시 점수 금지(§0)
│ "발췌문…"                                │  ← Source Serif 4 이탤릭
│ 출처: [파일명]                           │
│ [읽기] [인용·출처 보기] [설교 연구로 보내기] │
└─────────────────────────────────────────┘
```

- 카드당 행동 버튼은 정확히 3개, 순서 고정: 읽기 → 인용·출처 보기 →
  설교 연구로 보내기
- "읽기" 클릭 시 §5 읽기(연구 워크스페이스) 화면으로 전환하며 해당
  자료가 로드된 상태로 진입 (기존 `research_detail_selection` 세션
  상태 패턴 재사용, `research.py:151`)

### 4.3 AI 응답 블록 (질문형 입력일 때만)

- 기존 `chat.py`의 답변 렌더링 로직 재사용
- 답변 하단 "출처 (N개)" expander는 §6 인용 카드 스펙을 그대로 따른다
  (현재는 `chat.py:521-522`의 원시 점수 노출 — 반드시 교체)
- "이어서 물어보기" — 후속 질문 입력을 답변 바로 아래 배치(현재
  `chat.py`의 대화형 흐름 유지, 검색 결과 카드와 같은 화면에서 자연스럽게
  이어지도록 배치만 조정)

### 4.4 빈 결과 / 오류 상태

| 상황 | 표시 |
|---|---|
| 검색어 없음 | "무엇을 찾아드릴까요?" + 최근 검색어 칩(있으면) |
| 결과 0건 | "관련 자료를 찾지 못했습니다. 다른 표현으로 다시 찾아보세요." + 검색창 포커스 유지 |
| 처리 중 오류 | "잠시 문제가 있었습니다. 다시 시도해주세요." (원본 예외 메시지는 로그에만, 화면에는 안 보임 — 현재 `research.py`의 `f"에러: {str(e)}"` 패턴은 위반, 교체 대상) |

### 4.5 검색 → 설교 연구 전환

카드 또는 답변의 "설교 연구로 보내기" 클릭 → 신규 세션 상태(§13)에
자료 추가 → 토스트 "설교 연구에 추가되었습니다" → 화면은 그대로 유지
(이동하지 않음, 계속 검색 가능하도록)

---

## 5. Reading Specification ("읽기") — Research Workspace로 확정

**결정**: 읽기 화면은 "문서 뷰어"가 아니라 **연구 워크스페이스**다.
목적은 원문을 읽는 동시에 그 자리에서 관련 자료를 찾고 인용하는 것.

**레이아웃 (3영역)**

```text
┌─────────────────────────┬───────────────┐
│                         │  연구 영역     │
│      본문 영역           │  - 관련 자료   │
│  (제목/저자/판본/본문)    │  - 이어서 질문 │
│                         │               │
├─────────────────────────┤───────────────┤
│      행동 영역 (하단 고정)               │
│  인용하기 / 연구에 추가 / 설교 연구로 보내기│
└─────────────────────────┴───────────────┘
```

- **본문 영역**: `eyebrow`(출처 파일명) → 제목 → 본문(Source Serif 4,
  17px, 최대 폭 640px, 줄간격 1.85). 저자/판본 정보는 있으면 제목 아래
  캡션으로 — 현재 등록된 메타데이터(`title`/`author`/`book`/`chapter`)
  기반, 없는 필드는 표시하지 않음(추측 금지, 기존 원칙과 일치)
- **연구 영역(우측 패널)**: 현재 읽는 본문 기준 관련 자료 카드
  (§4.2와 동일한 카드 컴포넌트 재사용, 다만 버튼은 "읽기"만) + 하단에
  질문 입력창(§4.3 AI 응답 블록 재사용, 이 화면에서 물으면 현재 문서를
  문맥으로 우선함)
- **행동 영역**: 3버튼 고정, §4.2와 동일 순서 원칙 유지

**existing/신규 구분**: 본문 영역은 **신규**(현재 어떤 화면에도 전체
본문 표시 기능 없음, UX-005에서 확인된 공백). 연구 영역은 §4.2/4.3
컴포넌트 **재사용**. 행동 영역 중 "인용하기"/"설교 연구로 보내기"는
**신규**, "연구에 추가"는 기존 세션 저장(`add_query_result`,
`research.py`) 개념 확장.

---

## 6. Citation / Provenance Component Specification

전역에서 재사용되는 단일 컴포넌트 — §4.2 카드의 "인용·출처 보기",
§5 읽기의 "인용하기", 답변 하단 "출처" expander가 전부 이 컴포넌트를
호출한다.

```text
┌───────────────────────────────────┐
│▐ "원문 발췌 (이탤릭)"               │  ← 좌측 4px 색 바
│                                    │
│  출처        [파일명]               │
│  본문 위치    [예: 로마서 8:1-4]     │
│  자료 유형    [예: 성경 주석]         │
│                                    │
│  ★★★☆☆ 관련성                     │  ← §0 invariant 적용
│                                    │
│  [원문 다시 보기]  [설교 연구에 저장] │
└───────────────────────────────────┘
```

- 필드는 데이터가 있을 때만 표시(메타데이터 없는 자료는 "출처"만 남고
  나머지 행 생략 — 빈 값 "N/A" 같은 placeholder 금지)
- "원문 다시 보기" → §5 읽기 화면으로 이동, 해당 위치로 스크롤(가능하면;
  스크롤 위치 복원이 기존 인프라에 없으면 문서 상단 진입으로 폴백 —
  Mockup only로 표시하고 구현 시 재확인)
- 이 컴포넌트가 `chat.py`의 `_render_source`/`_render_clickable_source`
  (현재 원시 점수 노출 위반 지점)를 **대체**한다

---

## 7. Sermon Research Hub Specification ("설교 연구") — 신규

**목적**: Research에서 고른 자료가 끊기지 않고 설교 준비로 이어지는
staging 공간.

**레이아웃 (2열)**

```text
좌: 선택한 자료 (카드 목록, §4.2 카드에서 "보내기"로 쌓인 것)
    + 메모 (자유 텍스트, 자료별 또는 전체)
우: 개요 초안 (단계 리스트, 향후 자동 생성 가능성 — 지금은 수동 입력)
    → [설교 작성으로 이어가기] 버튼
```

- "설교 작성으로 이어가기" 클릭 시 **기존** `sermon_draft.py`로 이동,
  선택한 자료·메모를 초기 컨텍스트로 전달(현재 `sermon_draft.py`가
  받는 입력 형식에 맞춰 어댑터 필요 — §13 gap)
- 이 화면 자체는 **전체 신규** — 현재 어떤 코드에도 대응 없음
- 개요(outline) 자동 생성은 **Proposed future capability**로 표시,
  이번 스펙 범위는 수동 입력 UI까지만

---

## 8. Search → Reading → Citation → Sermon Research Transition

상태는 하나의 신규 세션 오브젝트로 관리한다(§13에 정의). 화면 전환은
기존 `st.session_state["nav_page"]` 프로그램 전환 패턴을 그대로 쓰고,
전달할 데이터(선택된 문서/자료 목록)는 별도 키에 보관한다 — 기존
`research_detail_selection`, `chat_detail_selection` 패턴과 동일한
방식으로 신규 키 `sermon_research_selection`을 추가하는 형태(기존
컨벤션 재사용, 새 아키텍처 도입 아님).

---

## 9. Empty / Loading / Error States (전역 원칙)

| 상태 | 원칙 |
|---|---|
| 빈 화면 | Dead End 금지 — 항상 다음 행동 버튼 1개 이상 |
| 로딩 중 | 기존 `st.spinner`/progress 패턴 재사용, 새 패턴 도입 안 함 |
| 오류 | 원인 설명 대신 "무엇을 다시 하면 되는지"를 문장으로 — 원본 예외 메시지 화면 노출 금지(§0과 동일 원칙의 연장) |
| 처리되지 않은 문서 클릭 | "아직 준비되지 않았습니다" + "자료 등록으로 이동"(관리자 경로 안내는 제외, 일반 사용자에게는 "곧 준비됩니다" 수준으로만) |

---

## 10. Responsive Behavior

**범위 제한**: Design Brief §3.4가 이미 "모바일 반응형은 우선순위 낮음"으로
명시했다. 이번 스펙도 데스크톱 우선을 유지한다. 다만 §5 읽기 화면의
2열 레이아웃(본문+연구 영역)은 좁은 화면에서 연구 영역이 접히는 정도의
최소 대응만 제안(Mockup only — 실제 breakpoint 값은 구현 시 C1이 기존
Streamlit 컬럼 동작 범위 내에서 결정).

---

## 11. User-facing Terminology (용어집 — 고정)

| 사용자 노출 용어 | 내부 개념 | 금지 표현 |
|---|---|---|
| 검색·연구 | Research + Chat 통합 | "Retrieval", "RAG" |
| 관련성 (★) | ranking score | "신뢰도(final_score)", "RRF", 원시 소수점 |
| 출처 | source_file, document_id | "TSU", "document_id" 노출 |
| 자료 유형 | doc_type | 내부 enum 원문("tsu" 등) |
| 내 자료 | RAW + registry 문서 | "RAW 폴더", "registry" |
| 정리됨 | ingest_status=PROCESSED | "PROCESSED", "ingest_status" |
| 설교 연구 | 신규 staging 세션 | — |
| 인용하기 | citation 생성 액션 | "Citation"(영문 그대로 노출 금지) |

이 표는 §0 invariant의 실행 도구다 — 새 문구를 쓸 때 이 표에 없는
내부 용어가 그대로 노출되면 위반으로 간주한다.

---

## 12. Existing Component Reuse Map

| 컴포넌트 | 파일 | 재사용 방식 |
|---|---|---|
| 사이드바 라디오 전환 | `ui/app.py::_render_sidebar` | 그대로, 라벨/항목 수만 조정 |
| 퀵액션 버튼 | `dashboard.py::_render_quick_actions` | 그대로 |
| 검색 실행 로직 | `research.py::_execute_research_query` | 그대로(백엔드 무변경) |
| RAG 답변 로직 | `chat.py`의 응답 렌더링 | 그대로, 배치 위치만 이동 |
| 별점 변환 | `research.py`(UX-004에서 구현됨) | 그대로, `chat.py` 인용 캡션에도 적용 |
| Sample Library 배지 | `library.py::_render_sample_library_section` | 그대로 |
| 관리자 게이트 패턴 | `NAE_ADMIN_MODE` (app.py/library.py/processing.py) | 그대로, Monitor/Processing 전체 이동에 재사용 |
| 문서 선택 상태 전달 | `research_detail_selection`/`chat_detail_selection` | 패턴 재사용해 `sermon_research_selection` 신설 |

## 13. New Component Inventory

| 신규 컴포넌트 | 소재 화면 | 의존성 |
|---|---|---|
| 이어서 읽기 카드 | 홈 | 신규 세션 상태(마지막 읽은 위치) |
| 본문 읽기 렌더러 | 읽기 | 없음 — 기존 처리된 .md 파일 읽어서 표시(파일 접근 로직은 이미 `library.py`의 청킹 미리보기가 쓰는 것과 동일 패턴) |
| 통합 검색창(검색+질문 단일 입력) | 검색·연구 | 없음 — 기존 두 백엔드 경로 병렬 호출 |
| 인용·출처 카드 컴포넌트 | 전역 공용 | 없음 |
| 설교 연구 세션 상태 | 설교 연구 | 신규 `st.session_state` 키, Core 무변경 |
| Research→Sermon Draft 어댑터 | 설교 연구→설교 작성 | `sermon_draft.py`의 기존 입력 형식 확인 필요(구현 착수 시 재확인 항목) |

## 14. Mockup → Production Component Mapping

| mockup.html 요소 | 프로덕션 대상 |
|---|---|
| `.continue-card` | 신규 `_render_continue_card()` (dashboard.py) |
| `.home-grid` | `_render_library_summary()` 재작성 |
| `.search-bar` + `.result` | 신규 통합 검색 컴포넌트 (research.py 확장) |
| `.reader-body` 3영역 레이아웃 | 신규 `render_reading_workspace()` (신규 파일 또는 library.py 확장 — 구현 착수 시 배치 결정) |
| `.cite-card` | 신규 `render_citation_card()` — `ui/components/`에 공용 함수로 배치 제안 |
| `.sr-col` 2열 | 신규 `render_sermon_research_hub()` (신규 파일) |

mockup.html의 색상 토큰(`--accent:#2F5D50`, `--cite:#A8763E` 등)은
`ui/theme/colors.py::DBMADesignSystemColors`에 필드 추가로 반영 —
새 디자인 시스템 도입이 아니라 기존 THEME 확장.

---

## 15. 다음 조치

1. HQ가 본 문서(Gate 6) 승인
2. 승인 시 C1 Task Order 발행 — 본 문서 §1~§14를 그대로 구현 계약으로
   전달, mockup.html은 "시각 참조"로만 명시
3. 구현 순서 제안(위험도 낮은 것부터): §11 용어집 전역 적용(단순 치환,
   C1 가능) → §6 인용 카드(공용 컴포넌트, 먼저 만들어야 §4/§5가
   재사용 가능) → §2 홈 → §3 내 자료 이관 → §5 읽기 → §4 검색·연구
   통합 → §7 설교 연구 허브
