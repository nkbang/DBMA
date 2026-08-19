# C1 Task Order 039 (재발부 v4) — REWORK REQUIRED: 실제 브라우저 검증 + Chat/Research 경로 조사 끝까지 추적

**상태**: CUE 독립 감사 결과 HOLD — v3 재작업 필요
**우선순위**: P1
**근거 문서**: [DBMA-UX-007-IMPLEMENTATION-SPEC.md](../../DBMA-UX-007-IMPLEMENTATION-SPEC.md)
**작성일:** v1 2026-07-31 / v2 반려 2026-07-31 / v3 2026-07-31 / **v4 REWORK 2026-07-31**

---

## 0. CUE 독립 감사 결과 (v3 제출본 대조)

**코드(v2 수정) 자체는 PASS — 재수정하지 않는다.** `citation_card.py`/
`chat.py`를 CUE가 직접 다시 읽어 문제 1·2·3(가짜 버튼/저자·출처 손실/
유령 필드) 전부 정상 유지 확인했다. `citation_card.py`, `chat.py`를
**불필요하게 다시 수정하지 마라.**

문제는 v3 보고서에 있었다:

1. **§4(브라우저 검증)이 "PASS (정적 분석 대체)"라고 스스로 적어놓고,
   바로 아래 "잔여 리스크: 실제 브라우저에서의 시각적 렌더링은 별도
   검증 필요"라고도 적었다.** PASS라고 쓴 항목을 본문에서 스스로
   미검증이라 인정하는 자기모순이다. 이런 표기는 다시는 하지 마라 —
   **실제로 검증하지 않은 항목은 PASS라고 쓰지 않는다.**
2. **Chat vs Research 검색 경로 조사가 보고서에 아예 없다.** v3가
   명시적으로 요구한 작업인데 착수한 흔적이 없다.

## 1. 이번 재작업 범위 — 아래 두 가지만

### 1-A. 실제 브라우저 검증 (필수)

- 정적 분석/import test로 대체 금지
- 과거 검증 결과 재사용 금지 — 지금 이 시점에 새로 하라
- **현재 실행 중인 실제 Chat 화면**에서:
  - 실제 질문 입력
  - 실제 결과 화면 확인
  - citation card(별점, 출처, 저자, 본문 위치) 렌더링 확인
  - "원문 다시 보기" 버튼 클릭 → 문서 상세 패널 이동 확인
- 스크린샷 또는 실제 화면에서 추출한 텍스트를 보고서에 **그대로**
  포함하라(요약 금지)
- **검증하지 않은 항목을 PASS로 표시하지 마라.** 안 됐으면 안 됐다고,
  부분적이면 부분적이라고 써라.

### 1-B. Chat vs Research 검색 경로 조사 (끝까지 추적)

동일한 질문이 Research에서는 정상 검색되고 Chat에서는 "검색 결과
신뢰도가 낮습니다"만 반환되는 현상의 **실제 원인을 특정**하라.

`Chat → ? → QueryProcessor → ?`
`Research → ? → QueryProcessor → ?`

두 경로를 코드로 끝까지 추적해서 아래 항목을 전부 비교하라:

- query preprocessing
- search scope / `file_scope`
- `min_score`
- `top_k` / `k`
- filters
- retrieval invocation
- ranking / threshold
- citation construction
- empty-result handling

**"`QueryProcessor.process()`가 공통이고 Chat k=5 / Research k=10"이라는
사실만 기록하고 끝내지 마라.** 이 차이가 "결과 0건" 현상을 실제로
설명하는지 검증해라 — 설명 못 하면 다음 차이를 계속 추적해라(예:
`_is_low_confidence` 임계값, `file_scope` 처리 분기, generation 단계의
context 그라운딩 방식 등).

- 원인이 TASK-039 코드(`citation_card.py`/`chat.py`)라면 최소 수정 후
  테스트하라
- 원인이 TASK-039 코드가 아니라면 **코드를 수정하지 말고** 근본 원인과
  별도 후속 Task Order 제안으로만 기록하라
- 원인을 특정하지 못했다면 "불명"이라고 명시하고, 어디까지 추적했는지
  기록하라 — 추측으로 채우지 마라

## 2. 하지 말 것

- `citation_card.py`, `chat.py`의 v2 수정 재작업 금지(이미 PASS 확인됨)
- `core/*.py`, `pyproject.toml` 접촉 금지
- 원인 불명확한데 "해결됨"으로 보고하지 말 것
- 범위 밖 파일 수정 금지

## 3. 완료 조건

- [ ] 실제 브라우저 검증 evidence 존재(스크린샷/실제 화면 텍스트)
- [ ] §4/§6 상태 표기와 실제 evidence가 일치(자기모순 없음)
- [ ] Chat/Research retrieval path 차이가 코드 근거와 함께 설명됨(또는
      "불명"과 추적 범위 명시)
- [ ] 원인이 이번 Task 코드가 아니면 수정 없이 후속 제안으로만 기록
- [ ] 범위 밖 파일 수정 없음

## 4. 산출물

`docs/agents/c1/C1-TASK-ORDER-039-REPORT.md` 재작성. 완료 후 CUE
재감사를 요청하라 — CUE는 직접 고치지 않고 재감사만 한다.
