---
title: Build Report — 교단 프로파일의 답변 생성 경로 확장
created: 2026-09-10
status: 구현 완료 · 전체 회귀 통과 · ADR-009 Amendment A는 **Proposed**(C1 리뷰·사용자 승인 대기)
scope: core/generation.py, core/sermon/doctrine_vocabulary.py, resources/models/, tests/
baseline: `f8a5c8d`
venv: `~/envs/dbma311`
---

# Build Report — 교단 프로파일 (감사 §9 우선순위 5번)

## 착수 전 정정 — 감사 보고의 오류

지시 수행 전 ADR-009를 정독한 결과 **감사 보고가 틀렸다.**

| 감사가 기록한 것 | 실제 |
|---|---|
| ADR-009 "Accepted(구조만), 어휘 미확정, 미구현" | §Decision에 2026-07-22 사용자 승인으로 어휘·구현·연결 **완료** 기재 |
| "교단 확정이 선행 결정 사항" | **이미 확정돼 있었다** — 개혁파 침례교(1689 런던신앙고백 계열, 신자세례·회중교회론) |
| "ADR-009 되살리기, 규모 대(大)" | `doctrine_vocabulary.py`·`doctrine_filter.py` 존재, `sermon_draft.py` 연결, 테스트 10건 |

원인은 헤더 Status 줄과 §Context의 "별도 승인 대상으로 미확정" 문장만 읽고
2026-07-22 개정분을 놓친 것이다. 2026-09-10 사용자가 지정한 "침례교 기준"은
새 결정이 아니라 **2026-07-22 결정의 재확인**이다.

**실제 공백은 적용 범위였다** — doctrine 계층이 설교 초안 경로에만 붙어 있고,
목회자가 실제로 답을 얻는 질의응답(Chat/Research)에는 교단 신호가 전혀 없었다.
모델 SYSTEM 프롬프트도 "복음주의 및 개혁주의"라고만 말해(모순은 아니나)
신자세례·회중교회론·1689 언약신학을 특정하지 못한다.

이 정정에 따라 작업 범위를 "ADR-009 신규 구현"에서 **"확정된 프로파일의 답변
경로 확장"**으로 좁혔다.

## 변경

| 파일 | 내용 |
|---|---|
| `core/sermon/doctrine_vocabulary.py` | `DENOMINATION_PROFILE` 상수 추가 — 문구는 ADR-009 §Decision 원문 그대로. 신학 내용은 승인된 ADR이 단일 출처 |
| `core/generation.py` | `_DENOMINATION_DIRECTIVE` 추가, `_build_prompt()`의 근거 지시문 **뒤**·질문 **앞**에 삽입 |
| `resources/models/Modelfile.theology-bot-v2` | SYSTEM 문구와 확정 전통의 불일치 및 재빌드하지 않기로 한 근거를 주석에 기록 |
| `docs/architecture/ADR-009-Amendment-A.md` | 신규 (Proposed) |
| `tests/test_generation_denomination.py` | 신규 13건 |

## 가장 조심한 지점 — 근거 강제와의 충돌

"교단에 맞는 답"을 요구하면 모델은 자료에 없는 교리를 보충해 전통에 맞추려
한다. 그것이 정확히 이 앱이 막으려는 행동이다(2026-09-10 `_GROUNDING_DIRECTIVE`
도입 배경). 세 겹으로 막았다:

1. **배치** — `_GROUNDING_DIRECTIVE`가 먼저 온다(순서가 우선순위 신호).
2. **명시** — 지시문 §3이 "전통에 맞추려고 자료에 없는 내용을 보태지 마라 —
   위 '지시'가 이보다 우선한다".
3. **범위 한정** — 지시문을 "자료를 어느 자리에서 읽을 것인가"(관점)로
   묶고 "무엇을 답에 넣을 것인가"(내용)로 넓히지 않았다.

신규 테스트 13건 중 4건(`TestGroundingStillWins`)이 이것만 검사한다.

## ADR-009 원칙의 프롬프트 수준 반복

- 전통과 다른 견해가 자료에 있으면 **감추지 않고** 누구의 견해인지 밝힌다(검열 방지)
- 다른 교단을 정죄하지 않는다
- 최종 신학적 판단 권한은 목회자에게 — 자동 차단 없음
- 점수화 금지(백분율 등 거짓 정밀도)

## 채택하지 않은 것

- **질의응답에 `doctrine_filter.check()` 연결 안 함** — 답변마다 LLM 호출이
  하나 더 붙고, ADR-009 §Decision-4가 규정한 대상은 `SermonOutline`이다.
  새 아키텍처 계층이므로 별도 ADR과 실사용 근거가 먼저다.
- **모델 SYSTEM 재빌드 안 함** — `ollama create`가 필요해 즉시 되돌릴 수 없고
  설교 경로 포함 전 경로가 한꺼번에 바뀐다. 앱 쪽 지시문은 버전관리·테스트
  대상이라는 이점도 있다.
- `core/retrieval.py` 무수정 (ADR-009 §Decision-1 유지).

## 검증

```
tests/test_generation_denomination.py  → 13 passed (신규)
pytest tests/ (전체)                    → 2,758 passed, 15 skipped, 0 failed (73s)
```

## 남은 위험

- **모델이 지시문을 실제로 얼마나 지키는지 미측정.** `rag_judge.py`는
  groundedness 단일 지표이고 설교 초안 경로에만 연결돼 있다. 교단 정합성
  지표는 존재하지 않는다 — 이것이 다음 우선순위 후보다.
- 프롬프트가 6줄 길어졌다. `num_ctx` 32768 기준 여유가 있으나 top_k를 크게
  올리는 경우와 함께 관찰이 필요하다.

## Amendment 상태

ADR-009 Amendment A는 **Proposed**다. Evidence Before Promotion Rule의 4개
조건 중 구현·회귀는 충족했고 **독립 리뷰(C1)와 사용자 승인이 남아 있다.**
승격 전까지 이 Amendment를 다른 구현의 근거로 사용하지 않는다.
