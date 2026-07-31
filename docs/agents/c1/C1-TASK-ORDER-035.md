# C1 Task Order 035 — UX-001 프로토타입 Architecture Review (구현 착수 아님, 리뷰만)

**상태**: 발급됨 — 리뷰 착수 가능
**우선순위**: P1
**근거 문서**: [DBMA-UX-001-EXECUTION-PLAN.md](../../DBMA-UX-001-EXECUTION-PLAN.md) §3 Step 6,
[DBMA-UX-DESIGN-BRIEF.md](../../DBMA-UX-DESIGN-BRIEF.md) §6.2
**작성일**: 2026-07-30

---

## 0. 배경

Stitch로 확보한 P0 UX 프로토타입 9화면(홈/검색/연구하기/설교 준비/자료 읽기/
도움말/내 자료/온보딩/랜딩)이 브랜드(내서재/NAE) 정정과 §5.2 체크리스트
검증까지 완료됐다. 원래 절차(v2, 80/20)는 Figma 반입 → 팀 리뷰를 거친 뒤
C1 Architecture Review로 넘어가는 것이었으나, HQ 판단으로 **Figma 반입
단계를 건너뛰고** 바로 이 Review로 진행한다. Figma 오토레이아웃/토큰
맵핑 없이 raw HTML 상태로 리뷰한다는 뜻이므로, 그 점을 감안해서 검토할 것.

**중요**: 이 Task Order는 **구현 착수가 아니다.** Streamlit 코드 작성,
`ui/pages/*` 수정 금지. 아래 3개 질문에 답하는 리뷰 보고서만 작성한다.

## 1. 검토 대상

`docs/design/stitch/pastoral_research_desk/` 전체:
- `landing.html`, `onboarding.html`, `home_dashboard.html`,
  `search_results.html`, `research_workspace.html`, `sermon_preparation.html`,
  `document_reading.html`, `help.html`, `my_library.html`
- `DESIGN.md` (디자인 토큰), `README.md` (Figma 임포트 안내 — 리뷰와 무관,
  참고만)

## 2. 리뷰 질문 (Design Brief §6.2 그대로)

1. **UX 프로토타입이 Core architecture를 임의로 변경하는가?** (안 되어야
   함 — 이 프로토타입은 순수 프론트엔드 HTML이라 Core를 건드릴 수 없는
   구조이지만, 혹시 프로토타입이 암시하는 데이터 모델/흐름이 `core/retrieval.py`,
   `core/runtime_state.py` 등 기존 구조와 근본적으로 안 맞는 부분이 있는지
   확인할 것 — 예: 검색 결과 화면의 "성경/책/신학자료/설교/내 자료" 5분류
   탭이 현재 검색 파이프라인이 실제로 반환하는 카테고리와 일치하는지)
2. **Streamlit 코드가 기존 UI 구조(`ui/pages/*`)와 호환되는가?** — 향후
   구현 시 그대로 포팅하는 게 아니라 "베이스로만 참고"한다는 전제다.
   사이드바(280px 고정)/헤더/하단 고정 푸터바 같은 레이아웃 컨셉이
   Streamlit 컴포넌트 모델(특히 `st.sidebar`, 페이지 전환 방식)로
   구현 가능한 형태인지, 아니면 구조적으로 다시 설계해야 하는 부분이
   있는지 짚어줄 것
3. **기술 용어가 UI에 노출되지 않는가?** — CUE가 이미 1차 검증(§5.2)을
   완료했으나(RAG/Retrieval/Embedding/TSU/Chunk 등 미노출, 브랜드
   내서재/NAE 통일 확인), 독립적으로 재확인할 것

## 3. 하지 말 것

- `ui/pages/*`, `core/*` 코드 수정
- 브랜드/카피 수정 (이미 확정됨, 문제 발견 시 보고만)
- Figma 관련 작업 (이번 라운드에서 생략됨)

## 4. 산출물

`docs/agents/c1/C1-TASK-ORDER-035-REPORT.md` — 위 3개 질문에 대한 답변
+ 발견된 구조적 이슈(있다면) 목록. "구현 시작해도 되는가"에 대한
최종 판단(GO / GO with caveats / NO-GO)을 명시할 것.

## 5. 다음 조치

이 리뷰가 GO로 나오면 `DBMA-UX-002 — Implementation` Task Order를
CUE가 발행한다 (실행계획 §3 Step 7).
