# C1 Task Order 002 — Chunk Overflow 수정 Preflight (설계 검토, 코드 없음)

발급: CUE (2026-07-20)
대상: C1 (Cline 작업창 #1, Ollama `dbma-planner-r1-q6:70b`)
성격: **분석/설계 검토(Preflight)** — `C1_AGENT_PROFILE.md`의 Allowed
범위(Analysis, Planning, Architecture review, Risk identification,
Validation criteria definition) 안에서만 수행. Forbidden(Direct code
modification, Git operation)은 이 작업에 적용되지 않음 — 실제 구현은
CUE가 별도로 한다.

---

## 1. 배경 (VERIFIED — C1이 그대로 신뢰해도 되는 사실)

- `docs/PREFLIGHT-split-sentences-mixed-chunk-overflow.md`가 근본 원인을
  확정했다: `core/text_normalizer.py::split_sentences_mixed()`가
  개행(`\n`)에만 의존해 문장을 나누는데, `split_paragraphs()`가 만드는
  문단은 내부 개행이 전부 제거돼 있어 이 함수가 production에서 항상
  무분할(1개 결과)을 반환한다.
- `scripts/shadow_chunk_overflow_audit.py` 실측(2026-07-20): Beta
  corpus 12개 문서 중 영문 학술 주석서 4개에서, 전체 청크의 4.6%
  (352/7736)가 chunk_size(1200)의 1.5배(1800자)를 초과. 최악 사례
  "2 Kings, Volume 13" 6511자(target의 5.4배). 한국어 8개 문서는 0건.
- `core/chunking_optimizer.py:294-333`(`_split_by_paragraphs`)의 두
  분기:
  - 원어/혼합 언어 문단(303-321행): `_slice_preserving_words()`로
    폴백 — chunk_size 상한은 지켜짐(안전).
  - 순수 단일 언어 장문단(324-329행, `_merge_sentence_fragments`
    경유): `core/text_normalizer.py:404-406`에서 oversized 단일
    "문장"을 자르지 않고 그대로 append — **상한이 지켜지지 않음
    (오늘 실측으로 확인된 심각도)**.

## 2. 요청 사항 — CUE가 이미 제안한 두 옵션에 대한 설계 검토

CUE가 제안한 수정 방향 두 가지:

```
(a) 근본 수정: split_sentences_mixed()가 입력에 "\n"이 없으면
    split_sentences()(정규식 `(?<=[.!?。！？])\s+|\n+` 기반, 이미
    이 조건에서 정상 동작 확인됨)로 자동 위임.

(b) 안전망 보강: _merge_sentence_fragments()의 oversized 단일 항목
    케이스에 _slice_preserving_words()와 동일한 word-safe hard
    slice를 적용 — 원어/혼합 언어 분기(하위 결함 A)에 이미 있는
    안전망을 순수 언어 분기(하위 결함 B)에도 동일하게 적용.
```

CUE는 "(b)를 먼저(작은 범위, 안전망), (a)는 corpus 전체 문장분할
동작을 바꾸므로 별도 벤치마크 검증 후 나중에"로 잠정 판단했다. **이
판단 자체를 C1이 독립적으로 검토하라** — 동의해도 되고, 다른 순서/
다른 위험 평가를 제시해도 된다.

## 3. C1이 산출해야 할 것 — `C1_RESPONSE_PROTOCOL.md` 형식 준수

아래 6개 절을 그 순서대로, 그 형식으로 작성하라. 코드는 쓰지 마라
(diff, 함수 시그니처 스케치까지는 허용 — 실제 실행 가능한 patch는 아님).

```
1. Current State
   - 현재 chunking_optimizer.py/text_normalizer.py의 관련 부분이
     실제로 어떻게 동작하는지 (위 §1 VERIFIED 사실만 근거로, 추측 금지)

2. Evidence Classification
   VERIFIED / REPORTED / UNKNOWN 으로 분류
   - CUE가 준 위 사실들은 VERIFIED로 취급 가능
   - C1이 직접 코드를 열어보지 못하는 부분(예: chunk_overlap과
     hard-slice의 상호작용 세부)은 UNKNOWN으로 명시하고 추측하지 말 것

3. Risk Assessment
   - (a), (b) 각각의 리스크를 구체적으로: 어떤 문서군에, 어떤 방식으로
     영향을 줄 수 있는가. "기존 정상 동작 중인 8개 한국어 문서에
     의도치 않은 변화가 생길 가능성"을 반드시 포함해서 평가할 것.

4. Architecture Impact
   - One Pipeline / One Config / One Retrieval Engine / One Execution
     State 4대 원칙에 대한 영향 평가

5. Recommendation
   - CUE의 "(b) 먼저, (a) 나중" 순서에 동의하는지, 동의한다면 왜,
     동의하지 않는다면 대안 순서와 근거
   - (b)를 구현할 때 지켜야 할 최소 요구사항(예: 기존
     _slice_preserving_words와 동일한 규칙 재사용 여부, overlap 처리
     방식 등) — 구현 코드가 아니라 "구현자가 지켜야 할 조건" 형태로

6. Human Approval Required
   - 이 중 어떤 항목이 Human HQ(사용자) 승인 없이는 진행 불가한지 명시
```

## 4. C1에게 보낼 프롬프트 (그대로 복사해서 Cline에 붙여넣기)

```text
이 작업에는 어떤 도구(파일 읽기/쓰기/편집, 코드 실행)도 사용하지 마라.
채팅 응답으로 텍스트만 답하라. 파일을 수정하지 마라 — 이것은 분석/설계
검토(Preflight)이며, 실제 구현은 CUE(다른 에이전트)가 한다.

너는 C1-DBMA-PLANNER다. DBMA Planning and Architecture Governance
Agent 역할만 수행한다. 코드 수정 제안이 아니라 분석/계획만 산출한다.

배경(VERIFIED로 취급):
- core/text_normalizer.py::split_sentences_mixed()가 개행(\n)에만
  의존해 문장을 나누는데, split_paragraphs()가 만드는 문단은 내부
  개행이 전부 제거돼 있어 이 함수가 production에서 항상 무분할(1개
  결과)을 반환한다.
- 실측(scripts/shadow_chunk_overflow_audit.py, 2026-07-20): Beta
  corpus 12개 문서 중 영문 학술 주석서 4개에서 전체 청크의 4.6%
  (352/7736)가 chunk_size(1200)의 1.5배(1800자)를 초과. 최악 사례
  6511자(target의 5.4배). 한국어 8개 문서는 0건.
- core/chunking_optimizer.py의 원어/혼합 언어 문단 분기는
  _slice_preserving_words()로 폴백해 chunk_size 상한이 지켜짐(안전).
  순수 단일 언어 장문단 분기는 core/text_normalizer.py의
  _merge_sentence_fragments()를 거치는데, 이 함수는 oversized 단일
  "문장"을 자르지 않고 그대로 통과시켜 상한이 깨진다.

CUE가 제안한 두 수정 옵션:
(a) split_sentences_mixed()가 "\n" 없으면 split_sentences()(정규식
    기반, 이미 정상 동작 확인됨)로 위임하는 근본 수정.
(b) _merge_sentence_fragments()의 oversized 단일 항목에
    _slice_preserving_words()와 동일한 word-safe hard slice를 적용하는
    안전망 보강.

CUE의 잠정 판단: "(b)를 먼저(작은 범위, 안전망), (a)는 corpus 전체
문장분할 동작을 바꾸므로 별도 벤치마크 검증 후 나중에".

요청: 이 판단을 독립적으로 검토하고, 아래 형식으로만 답하라. 다른
형식이나 코드 diff는 출력하지 마라.

1. Current State
2. Evidence Classification (VERIFIED / REPORTED / UNKNOWN)
3. Risk Assessment (기존 정상 동작 중인 한국어 8개 문서에 미칠 영향
   반드시 포함)
4. Architecture Impact (One Pipeline / One Config / One Retrieval
   Engine / One Execution State)
5. Recommendation (CUE의 순서에 동의/비동의 + 근거, (b) 구현 시
   지켜야 할 최소 요구사항 — 코드 아닌 조건 형태로)
6. Human Approval Required
```

## 5. CUE 사후 처리

1. C1의 응답을 받으면, **그 자체로 실행하지 않는다.** CUE가 6개 절을
   모두 검토한다.
2. C1이 "Forbidden" 범위(코드 수정 실행, Git 작업)를 넘었다면 그 부분은
   무시하고 분석 내용만 참고한다.
3. C1의 Risk Assessment/Recommendation을 CUE의 실제 구현 계획에
   반영할지 여부를 사용자에게 보고 후 결정한다.
4. 이 시도는 오늘 처음 테스트하는 작업 유형(자유 서술형 분석 리포트)
   이라 `feedback_c1_routing_criteria.md`의 검증된 안전 범위(단순 값
   치환) 밖이다 — 결과 품질과 무관하게 shadow 카운터에는 반영하지
   않고, 새로운 카테고리로 별도 기록한다.
