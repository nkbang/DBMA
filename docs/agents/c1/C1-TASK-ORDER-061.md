# C1 Task Order 061 — B-1 안전장치 독립 대조검증

- 발주: CUE · 일자: 2026-09-15
- 모드: **PLAN MODE만 — 코드 수정 금지, 대조검증 결과 보고만**
- 사용 모델: `dbma-planner-r1-q6:70b`(분석용) — 코드 작성이 아니라 검증이므로
- 성격: **범위 고정 검증형 Q&A** — 아래 파일만 근거로 삼는다. 그 밖으로 나가지 마라.

## 배경

CUE가 배포 차단 항목 B-1(자료 0건 시 설교 생성 차단)을 구현·커밋·PR #37까지
진행한 뒤에야, TDD 게이팅 코드 수정이라 C1에 먼저 위임을 제안했어야 했음을
사용자가 지적했다(라우팅 기준 "TDD 게이팅 코드 수정" 행). 이미 구현은
되돌리지 않고, 대신 C1이 그 결과물을 **독립적으로** 대조검증한다.

## 대상 파일 (이 범위만 볼 것)

- `ui/pages/sermon_draft.py` — 특히 `_SERMON_NO_EVIDENCE_TEXT` 상수,
  `_generate_outline()`, `_render_expansion_step()`
- `tests/test_sermon_insufficient_evidence.py`
- `core/generation.py`의 `SermonDraftService.generate_outline()` /
  `expand_point()` (변경하지 않았음 — 변경 없음을 확인하는 대조 대상)

## 질문 (번호별로 각각 답할 것 — Q1에 D-1 식으로 다른 번호 답 금지)

**Q1.** `_generate_outline()`에서 `response.top_k_results`가 빈 리스트일 때,
`service.generate_outline(...)` 호출까지 도달하는 코드 경로가 실제로
존재하는가? (즉 가드가 실제로 모든 도달 경로를 막는가, 우회 가능한 분기가
남아있는가) — 함수 본문을 직접 읽고 답하라. "가드가 있다"는 진술만으로
충분하다고 보지 말고, 가드 이후에 `service.generate_outline`을 호출하는
코드가 정말 없는지 라인 번호로 확인하라.

**Q2.** `_render_expansion_step()`의 `if not state["candidates"]:` 가드는
`for i, point in enumerate(outline.points):` 루프보다 **먼저** 실행되는가?
(즉 가드가 루프 진입을 막는 위치에 있는가, 루프 내부/이후에 있어 이미
늦은 것은 아닌가)

**Q3.** `tests/test_sermon_insufficient_evidence.py`의 5개 테스트 중,
실제로 가드 코드가 없으면 실패하는 테스트는 몇 개이며 어느 것인가?
(가드와 무관하게 항상 통과하는 "무의미한 테스트"가 섞여 있는지 판정)

**Q4.** `core/generation.py::SermonDraftService.generate_outline()` /
`expand_point()` 자체는 이번 변경으로 수정되지 않았음을 확인하라(diff
대상 파일 목록에 `core/generation.py`가 없음 — 이것이 사실인지 저장소
상태로 직접 확인). 사실이면 "확인함"만 답하라.

## 제출물

`docs/agents/c1/C1-TASK-ORDER-061-RESPONSE.md` — Q1~Q4 각각 번호를 달아
답하고, 근거 라인 번호를 반드시 명시하라. 결론만 있고 라인 번호가 없는
답은 CUE가 반려한다.
