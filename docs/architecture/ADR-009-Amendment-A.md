---
title: "ADR-009 Amendment A: 교단 프로파일의 답변 생성 경로 확장"
category: architecture
amends: docs/architecture/ADR-009-SIL-Theology-Engine.md
created: 2026-09-10
scope_modified: core/generation.py, core/sermon/doctrine_vocabulary.py (상수 1개 추가), tests/, resources/models/Modelfile.theology-bot-v2 (§5 개정, 2026-09-10)
---

# ADR-009 Amendment A: 교단 프로파일의 답변 생성 경로 확장

| | |
|---|---|
| Status | **Proposed** |
| Date | 2026-09-10 |
| Amends | ADR-009 (Accepted, 2026-07-22) — 대체하지 않고 적용 범위만 넓힘 |
| 승격 조건 | 구현 완료(✅) + 회귀 통과(✅) + 독립 리뷰(C1, ⬜) + 사용자 승인(⬜) |

## Context

ADR-009는 사용자의 신학적 전통을 **개혁파 침례교(1689 런던신앙고백 계열,
신자세례·회중교회론)**로 확정하고, `doctrine_filter.py`를
`ui/pages/sermon_draft.py`의 **설교 초안 경로**에 연결하는 것으로 완결됐다.

2026-09-10 답변 품질 감사에서 확인된 공백은 그 바깥이다 — **질의응답
경로(Chat/Research)에는 교단 신호가 전혀 없다.**

- `GenerationService._build_prompt()`는 교단을 언급하지 않는다.
- 모델 SYSTEM 프롬프트(`my-theology-bot-v2`)는 "복음주의 및 개혁주의"라고만
  말한다. 개혁파 침례교와 **모순되지는 않으나** 신자세례·회중교회론·1689
  언약신학을 특정하지 못한다.

즉 목회자가 실제로 답을 얻는 주 경로가 정작 자기 교단을 모르는 상태였다.
ADR-009가 이 경로를 다루지 않았기 때문에 생긴 공백이며, ADR-009의 결정과
충돌하는 지점은 없다.

> **감사 보고 정정(2026-09-10)**: 최초 감사는 ADR-009를 "Accepted(구조만),
> 어휘 미확정, 미구현"으로 기록했다. 이는 오독이다 — ADR 본문 §Decision에
> 2026-07-22 사용자 승인으로 어휘·구현·연결이 모두 완료로 기재돼 있다.
> 남아 있던 실제 공백은 위 §Context가 기술하는 답변 생성 경로뿐이다.

## Decision

### 1. 교단 프로파일 상수를 ADR 원문에서 단일 출처로 둔다

`core/sermon/doctrine_vocabulary.py::DENOMINATION_PROFILE`을 추가한다.
문자열은 ADR-009 §Decision "신학적 전통" 항목의 표현을 그대로 옮긴다 —
신학적 내용 판단은 CUE/C1의 권한 밖이므로 승인된 ADR의 표현을 벗어나지
않는다. 기존 `DOCTRINE_CATEGORY`/`BAPTIST_THEME`와 동일한 등급의 상수이며,
새로운 사용자 확인 없이 수정할 수 없다.

### 2. 답변 생성 프롬프트에 "신학 관점" 지시문을 추가한다

`core/generation.py::_DENOMINATION_DIRECTIVE`. 위 상수를 f-string으로
인용하므로 전통 표현이 두 곳에 중복되지 않는다.

### 3. 근거 강제가 교단 관점보다 **우선한다**

이 Amendment에서 가장 조심한 지점이다. "교단에 맞는 답"을 요구하면 모델은
자료에 없는 교리를 보충해 전통에 맞추려는 유혹을 받는데, 그것은 이 앱이
막으려는 바로 그 행동이다(2026-09-10 `_GROUNDING_DIRECTIVE` 도입 배경).
따라서:

- 프롬프트 배치상 `_GROUNDING_DIRECTIVE`가 **먼저** 온다.
- 지시문 §3이 "전통에 맞추려고 자료에 없는 내용을 보태지 마라 — 위 '지시'가
  이보다 우선한다"를 명시한다.
- 지시문의 성격을 "자료를 어느 자리에서 읽을 것인가"(관점)로 한정하고,
  "무엇을 답에 넣을 것인가"(내용)로 확장하지 않는다.

### 4. ADR-009 §Decision-4의 원칙을 프롬프트 수준에서 반복한다

- 전통과 다른 견해가 자료에 있으면 **감추지 않고** 누구의 견해인지 밝힌다
  (검열 방지).
- 다른 교단을 정죄하지 않는다.
- 최종 신학적 판단 권한은 목회자에게 있다 — 자동 차단 없음.
- 점수화하지 않는다(백분율 등 거짓 정밀도 금지).

### 5. 채택하지 않은 것

- **질의응답 경로에 `doctrine_filter.check()`를 연결하지 않는다.** 답변마다
  LLM 호출이 한 번 더 붙고, ADR-009 §Decision-4가 규정한 것은 `SermonOutline`
  검토다. 새 아키텍처 계층에 해당하므로 별도 ADR과 실사용 근거가 먼저다.
- ~~**모델 SYSTEM 프롬프트를 고쳐 재빌드하지 않는다.**~~ **[2026-09-10 개정]**
  이 결정을 사용자 승인으로 뒤집었다(PM 정렬 감사 선결 #6). 앱 쪽 지시문만으로는
  종전 SYSTEM 문구("복음주의 및 개혁주의")가 매 답변의 바탕에 남아 확정 전통과
  어긋난 채 작동했다. `resources/models/Modelfile.theology-bot-v2`의 SYSTEM 1행을
  `DENOMINATION_PROFILE`과 같은 표현("개혁파 침례교 — 1689 런던신앙고백 계열,
  신자세례·회중교회론")으로 교체했다. 저장소 파일 변경이며, 실제 반영은 사용자가
  `ollama create`를 실행해야 한다 — 그 전까지 실행 중인 모델은 종전 SYSTEM을
  쓰고 `_DENOMINATION_DIRECTIVE`가 매 질의마다 전통을 명시한다. 앱 쪽 지시문은
  재빌드 후에도 유지한다(버전관리·테스트 대상이며, SYSTEM 한 줄보다 구체적이다).
- ADR-009 §Decision-1(Retrieval Engine 무변경) 유지 — `core/retrieval.py`
  무수정.

## Consequences

- 질의응답 답변이 개혁파 침례교 관점에서 자료를 읽는다. 자료가 그 전통과
  다르면 숨기지 않고 차이를 드러낸다.
- 프롬프트가 길어진다(지시문 6줄). `num_ctx` 32768 기준 여유가 있으나
  top_k를 크게 올리는 경우와 함께 관찰이 필요하다.
- **미측정**: 모델이 이 지시문을 실제로 얼마나 지키는지는 아직 평가되지
  않았다. `core/evaluation/rag_judge.py`는 groundedness 단일 지표이고 설교
  초안 경로에만 연결돼 있다. 교단 정합성 지표는 존재하지 않는다.

## 검증

```
tests/test_generation_denomination.py  → 13 passed (신규)
pytest tests/ (전체)                    → 2,758 passed, 15 skipped, 0 failed
```

13건 중 4건(`TestGroundingStillWins`)은 근거 강제가 교단 관점에 밀리지
않는지만 검사한다 — 이 Amendment의 가장 큰 위험이 그것이기 때문이다.

## 개정 이력

- **2026-09-10**: §5 두 번째 항목("모델 SYSTEM 재빌드 안 함")을 사용자
  승인으로 뒤집었다. `Modelfile.theology-bot-v2`의 SYSTEM 1행을
  `DENOMINATION_PROFILE`과 같은 전통 표현으로 교체(저장소 파일 변경, 실제
  반영은 `ollama create` 필요). 근거·경위는 §5 개정 항목 참고. Amendment
  전체는 여전히 **Proposed** — C1 리뷰·사용자 승인 전까지 다른 구현의
  근거로 쓰지 않는다.
