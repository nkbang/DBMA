# 내서재 UX Stitch 참고자료 v3 — 실제 코드 대비 화면 갭 분석

**작성일:** 2026-08-19
**목적:** 현재 Streamlit 코드베이스(`ui/`)에 구현된 실제 기능/페이지를 기준으로,
Stitch("Pastoral Research Desk" 프로젝트)에 이미 있는 화면과 비교해
추가/보완이 필요한 항목을 정리한다.
**전제:** 브랜드·용어·디자인시스템 규칙은 `docs/NAE-UX-STITCH-MASTER-PROMPT-v2.md`를
그대로 따른다(내서재/NAE 고정, DBMA 노출 금지, 기술 용어 노출 금지).

---

## 1. Stitch 기존 화면 (v2 문서 기준, 9개)

랜딩 · 온보딩 · 홈(대시보드) · 검색 결과 · 연구하기 · 설교 준비 ·
자료 읽기 · 도움말 · 내 자료

## 2. 실제 코드에 있는 페이지 (`ui/app.py` 사이드바 기준, 10개)

| 코드 페이지 | 한글 라벨 | Stitch 대응 화면 | 상태 |
|---|---|---|---|
| Dashboard | 홈 | 홈 | 있음 |
| Library | 내 자료 | 내 자료 | 있음 (세부 기능 갭 있음, §3) |
| Research | 검색·연구 | 검색 결과 + 연구하기 | 있음 |
| Chat | AI에게 질문 | (없음) | **누락** |
| 설교 연구 | 설교 연구 | (없음, "설교 준비"와 다른 화면) | **누락** |
| 설교문 작성 | 설교 준비 | 설교 준비 | 있음 (세부 기능 갭, §3) |
| 설교 리뷰 | 설교 모음 정리 | (없음) | **누락** |
| 도움말 | 도움말 | 도움말 | 있음 |
| Processing | 자료 등록 | (없음) | 관리자 전용, Stitch 불필요 |
| Monitor | 시스템 모니터링 | (없음) | 관리자 전용, Stitch 불필요 |

`Processing`/`Monitor`는 `NAE_ADMIN_MODE=1`일 때만 노출되는 개발자 진단
화면이라 사용자용 Stitch 목업 대상이 아니다.

---

## 3. Stitch에 전달할 신규/보완 요청 (우선순위 순)

### 3-1. [신규] "AI에게 질문" (Chat) 화면 — 최우선
Stitch에 아직 없는 화면. 실제 코드(`ui/pages/chat.py`)의 핵심 요소:
- 대화형 질의응답 (사용자 질문 → 답변 + 근거자료 카드)
- 답변 아래 **출처 카드**: 배지(성경/책/신학자료/설교) + 발췌문 +
  "자세히 보기" 액션
- **신뢰도 안내**: 검색 결과 신뢰도가 낮을 때 "관련 문서를 찾지 못했을
  수 있습니다" 같은 경고 배너(기술 용어 없이, 예: "이 답변은 확실하지
  않을 수 있어요")
- **주장 검증(claim guard) 안내**: 답변 문구가 근거와 다를 때 "이렇게
  표현하는 게 더 정확해요" 식 안내 문구 노출 지점
- 우측 또는 하단에 **상세 패널**(자료 원문 하이라이트 표시, §3-4 참고)

### 3-2. [신규] "설교 연구" 허브 화면
"설교 준비(설교문 작성)"와 별개의 화면. `ui/pages/sermon_research.py` 기준:
- 설교 주제/본문 입력 → 관련 자료 발췌문 목록(연구 허브 카드형)
- 여기서 자료를 골라 "설교 준비"로 넘기는 흐름(다음 행동 버튼 필요)

### 3-3. [신규] "설교 모음 정리" (설교 리뷰) 화면
`ui/pages/sermon_review.py` 기준 — 과거 설교 원고 모음을 불러와 정리:
- 여러 설교가 합쳐진 파일을 업로드 → 자동으로 개별 설교 단위로 분리
- 목록 탐색 UI: "N / 전체 M편" 페이지네이터
- 분리 지점(제목/날짜/성구)을 자동 추출 시도 → 실패 시 "직접 입력"
  안내 문구와 수동 입력 폼
- 완료된 개별 설교를 저장하는 액션

### 3-4. [보완] "내 자료" (Library) 화면 — 세부 기능 반영
- 검색창 + **유형 필터**(전체/성경/책/신학자료/설교 등 selectbox) +
  **정렬 기준** selectbox — 현재 Stitch 화면에 필터/정렬 컨트롤이
  명확히 있는지 확인 필요
- 문서 클릭 시 **우측 상세 패널**: 원문 발췌 + 검색어 하이라이트(`<mark>`
  스타일), "저장" 액션
- 문서별 **처리 버전 이력**("버전 3개" 같은 뱃지) 및 **실패 기록**
  뱃지 노출 지점
- 미처리 문서는 "메타데이터 수정은 처리 완료 후 가능" 안내 문구로
  비활성 상태 표시
- 자료 삭제 시 "RAW 원본은 삭제되지 않습니다" 안내 문구 필요(안심 카피)

### 3-5. [보완] "연구하기" (Research) 화면 — 세부 기능 반영
- 검색 결과 리스트 + **세션 저장** 기능(★☆ 별점 평가 포함)
- **저장된 세션** 목록 재진입 카드
- "공개 신학 자료(Beta)" 별도 섹션 — 내 자료 검색과 구분된 카드
  (배지로 구분: 내 자료 vs 공개 자료)

### 3-6. [보완] "설교 준비" (설교문 작성) 화면 — 세부 기능 반영
- 설교 형식 선택 표시("설교 형식: …")
- 초안 작성 중 **맞춤법/표현 검사** 결과 리스트(오류 단어 위치 +
  추천 표현 최대 3개) — 인라인 카드나 사이드 패널로
- 관련 범주 + 신뢰도 배지가 붙은 검토 리포트 섹션
- 최종 "완성된 설교문 초안" 프리뷰 섹션

### 3-7. [보완] "홈" (대시보드) 화면 — 세부 기능 반영
- 3개 퀵 액션 버튼: "질문하기"(→AI에게 질문), "자료 검색"(→연구하기),
  "문서 추가"(→관리자 전용이므로 일반 사용자 화면에서는 제외 검토)
- 문서 유형 자동 추정 안내 문구("처리하면 유형이 자동으로 추정되어
  붙습니다")

---

## 4. 공통 컴포넌트 관련 참고

- **본문 하이라이트**: 검색어와 일치하는 부분을 강조 표시하는 패턴이
  Library·Chat 상세 패널에 공통으로 쓰인다 — Stitch 컴포넌트 라이브러리에
  "하이라이트 텍스트" 스타일을 하나 확정해두면 여러 화면에서 재사용 가능
- **빈 상태 없음 원칙 재확인**: 저장된 세션 없음, 검색 결과 없음 등
  실제 코드에도 안내 문구가 있다 — Stitch도 반드시 실제 문구
  기준으로 빈 상태 디자인(아이콘 + 안내 + 액션 버튼)을 채워야 함
- **관리자 전용 화면 제외**: "자료 등록(Processing)", "시스템
  모니터링(Monitor)"은 일반 사용자에게 노출되지 않으므로 Stitch
  목업 대상에서 제외해도 된다(내부 진단 전용)

---

## 5. Stitch에 붙여넣을 다음 요청 예시 (헤더는 v2 문서 공통 헤더 사용)

```text
[v2 문서의 공통 헤더 그대로 붙여넣기]

TASK: Add 3 new screens to the existing project, reusing the shared
sidebar/header/footer components exactly as-is:

1. "AI에게 질문" (ai_chat) — a conversational Q&A screen. User question
   at top, AI answer below with inline evidence cards (badge: 성경/책/
   신학자료/설교 + snippet + "자세히 보기" button). Include a low-confidence
   banner ("이 답변은 확실하지 않을 수 있어요") and a right-side detail
   panel showing the source document with the matched terms highlighted.

2. "설교 연구" (sermon_research_hub) — separate from "설교 준비". Topic/
   passage input at top, list of related resource snippets below as
   cards, each with a "설교 준비로 보내기" action button.

3. "설교 모음 정리" (sermon_review) — upload a merged sermon file, auto-
   split into individual sermons, paginated list ("1 / 12편"), each item
   showing title/date/passage (auto-detected, with a manual-entry fallback
   when detection fails), and a save action per sermon.

Add nav items for these 3 screens to the existing 6-item sidebar.
```

---

## 6. 체크리스트 (v2 문서 그대로 적용)

- [ ] "DBMA" 등 내부 식별자 노출 없음
- [ ] "내서재"/"NAE" 브랜드만 사용
- [ ] RAG/Retrieval/Embedding/TSU/Chunk/Vector 등 기술 용어 없음
- [ ] 모든 텍스트 한국어, 목회자 언어
- [ ] 빈 화면 없이 샘플 데이터로 채워짐
- [ ] 각 화면에 다음 행동 버튼 존재
- [ ] 기존 사이드바/헤더/푸터 컴포넌트 재사용
