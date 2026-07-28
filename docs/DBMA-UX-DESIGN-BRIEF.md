# DBMA Deployment UX — Design Brief

**문서 상태:** AI Design Service 전달용
**작성일:** 2026-07-27
**대상:** Stitch AI (또는 유사 AI Design Tool)
**비용 원칙:** $0 (무료 tier 활용)
**범위:** P0 기능 프로토타입 (Dashboard, Navigation, Search, Help, Sample Library)

---

## 1. 프로젝트 개요

### 1.1 DBMA란?

DBMA (David Bang Ministry Archive)는 목회자를 위한 **신학 연구 및 설교 준비 지원 시스템**입니다.

- 성경 본문 연구
- 신학 자료 검색
- 설교 준비 workflow
- AI 기반 연구 보조

### 1.2 핵심 UX 원칙

> **"DBMA는 내부적으로 복잡해도 사용자에게는 단순해야 한다."**

- 기술 용어(RAG, Retrieval, Embedding, TSU 등)를 완전히 숨김
- 목회자의 실제 작업 언어(읽기, 찾기, 연구하기, 설교 준비) 사용
- 빈 화면 대신 "좋은 연구 사례"로 시작 (Sample-driven Onboarding)

---

## 2. 디자인 대상 화면 (P0 우선순위)

### 2.1 홈 / Dashboard (최초 실행 화면)

**목적:** DBMA의 기능을 설명하는 것이 아니라, "지금 무엇을 하면 되는지" 즉시 보여주기

**필수 요소:**

```
┌─────────────────────────────────────────────────────┐
│  DBMA                                               │
│                                                     │
│  🔎 성경, 책, 설교, 신학 자료를 찾아보세요.         │
│                                                     │
│  ── 최근 작업 ────────────────────────────────────  │
│  📖 로마서 8장                                      │
│  ✍️ 주일 설교                                       │
│  🔬 칭의 연구                                       │
│                                                     │
│  ── 시작하는 데 도움이 되는 예제 ──────────────────  │
│  📚 성경 연구 예제                                  │
│  ✍️ 설교 준비 예제                                  │
│  🔎 자료 찾기 예제                                  │
│                                                     │
│  💡 무엇을 도와드릴까요?                             │
│                                                     │
│  [자료 찾기]  [연구하기]  [도움말]                  │
└─────────────────────────────────────────────────────┘
```

**디자인 요구사항:**
- 깔끔하고 단순한 레이아웃
- 목회자가 즉시 이해할 수 있는 아이콘과 텍스트
- "최근 작업"과 "예제 연구" 섹션 강조
- 기술적인 통계 차트 금지 (목표 지향적)

### 2.2 Navigation (상단/측면 메뉴)

**현재 → 목표 변환:**

| 현재 라벨 | 목표 라벨 | 비고 |
|----------|----------|------|
| 시스템 대시보드 | 홈 | Dashboard |
| 문서 라이브러리 | 내 자료 | Library |
| Research Workspace | 연구하기 | Research |
| Chat | AI에게 질문 | Chat |
| Sermon Draft | 설교 준비 | Sermon |
| 도움말 | 도움말 | Help |

**디자인 요구사항:**
- 단순한 상단 또는 측면 메뉴
- 아이콘 + 목회자 언어
- 현재 페이지 강조 표시

### 2.3 통합 Search 화면

**목적:** 성경, 책, 설교, 신학 자료를 한 곳에서 검색

**필수 요소:**

```
┌─────────────────────────────────────────────────────┐
│  🔎 자료 찾기                                       │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  성경, 책, 설교, 신학 자료를 검색하세요...   │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  [검색 실행]                                        │
│                                                     │
│  ── 검색 결과 (127건) ───────────────────────────  │
│                                                     │
│  📖 로마서 8:9 - 성령의 내주                        │
│     출처: Romans 8:9 | TSU | 점수: 0.95            │
│     [열기] [연구하기] [내 자료에 저장]              │
│                                                     │
│  📚 시스템신학 2권 - 성령론                         │
│     출처: Systematic Theology | 점수: 0.87          │
│     [열기] [연구하기] [내 자료에 저장]              │
│                                                     │
│  ✍️ 주일 설교 초안 - 성령의 열매                    │
│     출처: 내 자료 | 점수: 0.82                      │
│     [열기] [설교 준비] [내 자료에 저장]             │
│                                                     │
│  ...                                                │
└─────────────────────────────────────────────────────┘
```

**디자인 요구사항:**
- 단순한 검색창 (고급 옵션은 "더 자세히 찾기"로 숨김)
- 결과 유형별 분류 (성경/책/설교/신학자료/내 연구)
- 각 결과에 동일한 행동 버튼 ([열기], [연구하기], [내 자료에 저장])
- 기술적인 점수 표시 금지 (점수 대신 ★ 또는 단순 바)

### 2.4 Help 화면

**목적:** Help + Tutorial + Sample의 결합체

**필수 요소:**

```
┌─────────────────────────────────────────────────────┐
│  💡 도움말                                          │
│                                                     │
│  ── 처음 시작하는 분들을 위해 ────────────────────  │
│                                                     │
│  📖 DBMA는 무엇인가?                                │
│     목회자의 연구와 설교를 돕는 신학 지원 시스템    │
│     [보기]                                          │
│                                                     │
│  🔎 자료 찾는 방법                                 │
│     성경, 책, 설교, 신학 자료를 검색하세요          │
│     [보기]                                          │
│                                                     │
│  🔬 연구하는 방법                                  │
│     자료를 찾고 → 중요한 내용을 모으고 → 연구       │
│     [보기]                                          │
│                                                     │
│  ✍️ 설교 준비하는 방법                              │
│     연구한 자료를 설교 준비로 자연스럽게 연결        │
│     [보기]                                          │
│                                                     │
│  ── 실제 예제 보기 ───────────────────────────────  │
│                                                     │
│  📚 로마서 8장 연구 예제 (완성된 연구 사례)         │
│     [예제 보기]                                     │
│                                                     │
│  ✍️ 설교 준비 예제 (연구 → 설교 workflow)           │
│     [예제 보기]                                     │
└─────────────────────────────────────────────────────┘
```

**디자인 요구사항:**
- 단계별 학습 구조
- "보기" 버튼 클릭 시 실제 Sample 연구 보여줌
- 매뉴얼 형식보다 Tutorial 형식

### 2.5 Sample Library (기본 자료 영역)

**목적:** 최초 실행 시 "좋은 연구가 이미 시작되어 있는 상태" 제공

**필수 요소:**

```
┌─────────────────────────────────────────────────────┐
│  📚 기본 자료 (Read-Only)                           │
│                                                     │
│  ── 성경 연구 예제 ──────────────────────────────  │
│                                                     │
│  📖 로마서 8장 - 성령의 자유                       │
│     완성된 연구 workflow                            │
│     [보기] [복사하여 내 자료로]                     │
│                                                     │
│  📖 필립보서 2:13 - 하나님이 역사하시는 것           │
│     완성된 연구 workflow                            │
│     [보기] [복사하여 내 자료로]                     │
│                                                     │
│  ── 설교 준비 예제 ──────────────────────────────  │
│                                                     │
│  ✍️ 주일 설교 - 성령의 열매                        │
│     연구 → 설교 완성 사례                           │
│     [보기] [복사하여 내 자료로]                     │
│                                                     │
│  ── 신학 연구 예제 ──────────────────────────────  │
│                                                     │
│  🔬 칭의 연구 - 바울 신학 중심                     │
│     신학 주제 연구 사례                             │
│     [보기] [복사하여 내 자료로]                     │
└─────────────────────────────────────────────────────┘
```

**디자인 요구사항:**
- "기본 자료"와 "내 자료" 시각적으로 구분 (예: 기본 자료는 회색 배경)
- "복사하여 내 자료로" 버튼으로 사용자가 수정 가능 버전 생성
- 삭제 시 복원 기능 (Read-Only 영역이므로 원본은 항상 보존)

---

## 3. 디자인 시스템 요구사항

### 3.1 색상 팔레트 (Streamlit 호환)

```css
/* 기본 색상 */
--primary: #1976D2 (파란색 - 주요 액션)
--secondary: #757575 (회색 - 보조 액션)
--success: #2E7D32 (초록색 - 성공/저장)
--warning: #F57C00 (주황색 - 경고)
--error: #C62828 (빨간색 - 오류)

/* 배경 */
--bg-primary: #FFFFFF (흰색)
--bg-secondary: #F5F5F5 (연한 회색)
--bg-readonly: #FAFAFA (Read-Only 영역 배경)

/* 텍스트 */
--text-primary: #212121 (주요 텍스트)
--text-secondary: #757575 (보조 텍스트)
```

### 3.2 타이포그래피

- 본문: 14px (가독성 우선)
- 제목: 18-24px
- 부제목/설명: 12px

### 3.3 아이콘

- 📖 성경/문서
- 🔎 검색
- 🔬 연구
- ✍️ 설교/작성
- 💡 도움말
- 📚 자료/라이브러리
- ⭐ 즐겨찾기
- 📥 저장/백업

### 3.4 레이아웃 원칙

- 단일 컬럼 또는 2컬럼 (복잡한 그리드 금지)
- 모바일 반응형 (선택사항, 우선순위 낮음)
- 여백 충분히 확보 (지나친 정보 밀집 금지)

---

## 4. Sample 데이터 요구사항

### 4.1 기본 자료에 포함될 Sample 연구

**중요:** 실제 목회자 언어로 작성된 예제여야 함. 기술 용어 금지.

#### Sample 1: 로마서 8장 연구 (성경 연구 예제)

```
제목: 로마서 8장 - 성령의 자유

본문: 로마서 8:1-17
핵심 내용:
  - 그리스도 안에 있으면 죄와 사망의 법에서 해방됨
  - 성령의 내주로 인한 새로운 생명
  - 성령의 인도하심과 하나님의 자녀 됨

관련 신학 자료:
  - 성령론 (Systematic Theology)
  - 로마서 주석 (Commentary on Romans)

연구 질문:
  - 바울은 성령을 어떻게 이해하는가?
  - 성령의 자유는 실제 삶에서 어떻게 구현되는가?

설교 준비 연결:
  - 성령의 열매를 주제로 설교 발전 가능
```

#### Sample 2: 주일 설교 초안 (설교 준비 예제)

```
제목: 성령의 열매 - 삶의 변화

본문: 갈라디아서 5:22-23
주제: 성령의 열매가 일상에서 어떻게 나타나는가
구조:
  1. 서론: 성령의 열매에 대한 오해
  2. 본론 1: 사랑의 열매 (실제 사례)
  3. 본론 2: 기쁨과 평화의 열매 (성경적 근거)
  4. 결론: 일상의 적용
출처: 갈라디아서 5:22-23, Systematic Theology Vol.2
```

#### Sample 3: 칭의 연구 (신학 연구 예제)

```
제목: 칭의 교리 - 바울 신학 중심

주제: 로마서에서 칭의의 의미와 현대적 적용
연구 방법: 본문 분석, 신학적 비교, 현대 적용
주요 자료:
  - Romans 3:21-26 (칭의의 근거)
  - Systematic Theology - Justification 장
  - Commentary on Romans - 로마서 해석사
결론:
  - 칭이는 하나님의 은혜로 인한 법적인 선언
  - 믿음으로 받는 선물
  - 삶의 변화가 아닌 삶의 시작
```

---

## 5. AI Design Service (Stitch AI) 사용 가이드

### 5.1 프롬프트 예시

```
Create a Streamlit dashboard for a pastoral research system called DBMA.

Requirements:
1. Clean, simple layout suitable for non-technical pastors
2. Color scheme: Primary #1976D2, Background #FFFFFF, Secondary #F5F5F5
3. Typography: Body 14px, Headings 18-24px
4. Icons: Use emoji icons (📖 🔎 🔬 ✍️ 💡 📚)

Screens to create:

Screen 1 - Home Dashboard:
- Title "DBMA" at top
- Search prompt: "성경, 책, 설교, 신학 자료를 찾아보세요."
- Section "최근 작업" with 3 sample items (로마서 8장, 주일 설교, 칭의 연구)
- Section "시작하는 데 도움이 되는 예제" with 3 sample research examples
- Three action buttons: [자료 찾기] [연구하기] [도움말]

Screen 2 - Search Results:
- Large search input at top
- Filter options (hidden by default, "더 자세히 찾기" button)
- Search results list with type badges (성경/책/설교/신학자료)
- Each result shows: title, source, score (simple bar), action buttons ([열기] [연구하기] [내 자료에 저장])

Screen 3 - Help/Tutorial:
- Section "처음 시작하는 분들을 위해" with 4 help topics
- Section "실제 예제 보기" with sample research examples
- Each topic has a "보기" button to expand details

Screen 4 - Sample Library:
- Two sections: "기본 자료 (Read-Only)" and "내 자료"
- Basic materials have light gray background (#FAFAFA)
- Each item has [보기] and [복사하여 내 자료로] buttons

Design principles:
- Never show technical terms (RAG, Retrieval, Embedding, TSU, Chunk)
- Use pastoral task language (읽기, 찾기, 연구하기, 설교 준비)
- Sample-driven onboarding (show good research examples, not empty state)
```

### 5.2 출력물 검증 체크리스트

- [ ] 기술 용어(RAG, Retrieval 등)가 UI에 노출되지 않음
- [ ] 목회자 언어(읽기, 찾기, 연구하기 등) 사용
- [ ] 빈 화면이 없고 Sample 데이터 표시
- [ ] 각 화면에 "다음 행동" 버튼 존재 (Dead End 없음)
- [ ] 기본 자료와 내 자료 시각적 구분 있음
- [ ] Search 결과에 유형 분류와 행동 버튼 있음

---

## 6. Acceptance Criteria (HQ 테스트 기준)

### 6.1 프로토타입 검토 기준

1. **첫 30초** — Dashboard를 본 사용자가 DBMA의 목적을 이해하는가?
2. **첫 3분** — Search 화면에서 자료를 찾을 수 있는가?
3. **첫 연구** — Sample 연구를 열어볼 수 있는가?
4. **Help** — 도움말이 매뉴얼이 아닌 Tutorial 형식인가?
5. **Sample Library** — 기본 자료와 내 자료가 구분되는가?

### 6.2 C1 Architecture Review 기준

1. UX 프로토타입이 Core architecture를 임의로 변경하는가? (안 되어야 함)
2. Streamlit 코드가 기존 UI 구조(ui/pages/*)와 호환되는가?
3. 기술 용어가 UI에 노출되지 않는가?

---

## 7. 다음 단계

### Step 1: AI Design Service에서 프로토타입 생성
- Stitch AI (또는 대체 도구)에 프롬프트 입력
- P0 화면 4개(Dashboard, Search, Help, Sample Library) 생성

### Step 2: HQ 프로토타입 검토
- Section 6 Acceptance Criteria로 검토
- 피드백 반영 요청

### Step 3: C1 Architecture Review
- UX 프로토타입이 Core에 미치는 영향 검토
- 통과 시 CUE가 Streamlit 코드 구현

### Step 4: CUE Implementation
- P0 기능 Streamlit 코드 구현
- ui/pages/* 파일 수정/신규 생성

---

## 8. 제한사항 및 주의사항

### 금지 사항

1. **기술 용어 노출 금지** — RAG, Retrieval, Embedding, TSU, Chunk, Vector DB, Pipeline, Workspace 등
2. **빈 화면 제공 금지** — Sample 데이터 없이 시작하지 않음
3. **복잡한 레이아웃 금지** — 그리드, 다중 컬럼 과다 사용 금지
4. **Core architecture 변경 금지** — UX 프로토타입이 Core 코드를 임의로 변경하지 않음

### 허용 사항

1. **Streamlit 컴포넌트 활용** — st.metric, st.button, st.text_input 등 기본 컴포넌트
2. **커스텀 CSS** — Streamlit의 `st.markdown(unsafe_allow_html=True)`로 스타일링
3. **Sample 데이터** — 실제 목회자 언어로 작성된 예제 데이터

---

## 9. 참고 문서

- `docs/DBMA-UX-DEPLOYMENT-001.md` — 본 Design Brief의 기반이 된 제안서
- `ui/pages/dashboard.py` — 현재 Dashboard 구현
- `ui/pages/library.py` — 현재 Library 구현
- `ui/pages/research.py` — 현재 Research 구현
- `core/runtime_state.py` — StateStore / library_selected_doc (Core 참조용)

---

**본 Design Brief는 AI Design Service에게 전달하여 P0 화면 프로토타입 생성의 기준으로 사용합니다.**

**프로토타입 생성 후 HQ 검토 → C1 Architecture Review → CUE Implementation 순으로 진행됩니다.**