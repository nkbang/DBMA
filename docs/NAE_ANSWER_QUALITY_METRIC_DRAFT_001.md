---
title: "NAE 답변 품질 지표 설계 초안 (rag_judge fluency / completeness)"
created: 2026-09-10
status: DRAFT — 설계 초안. 구현은 별도 TO + C1 Review (ADR-010 Phase 2).
audit_item: PM 정렬 감사 선결 #4 / 옵션 A — Task Order §5-2
adr_refs: ADR-010 (RAG Evaluation & Quality) — Accepted(구조)
---

# NAE 답변 품질 지표 설계 초안

## 0. 범위

Task Order §5-2에 따라 **설계 초안만** 작성한다. `core/evaluation/rag_judge.py`
에 LLM 기반 `judge_fluency()` / `judge_completeness()`를 추가하는 것은
ADR-010 Phase 2 범위이며, 지표 정의(특히 `question_answering_quality`
reference-free 재정의)는 ADR-010 미확정 항목이다. 이 문서는 그 확정을 위한
입력이다.

본 트랙의 AT-5 판정은 이 문서가 아니라 **`core/evaluation/answer_completeness.py`
규칙 판정기 + 고정 질의셋 육안 평가**로 한다(구현 완료, `test_answer_completeness.py`).

## 1. 현행 (감사 §7)

- `rag_judge.py`는 `groundedness` **단일 지표**(0~5)만 낸다.
- 연결 지점이 **설교 초안 경로뿐**. chat/research 답변은 자동 채점 안 됨.
- 교단 정합성·문장 완성도·인용 정확도 지표 없음.

## 2. 제안 지표 (ADR-010 지표명 체계 안에서)

| 지표 | 정의 | 스케일 | reference |
|---|---|---|---|
| `groundedness` | (기존) 답변 문장이 제공된 `<자료>` 문단에 정합하는가 | 0~5 | reference-free (제공 문단) |
| `fluency` | 한국어 문법·문체 자연스러움(번역투·파편·경어체) | 0~5 | reference-free |
| `completeness` | 질문이 요구한 범위를 문단형으로 충분히 다루는가 | 0~5 | reference-free |
| `citation_fidelity` | 본문의 "저자·저작" 언급이 실제 `<자료>` 서지와 일치 | 0~5 | 제공 서지 |

`answer_completeness.py`(규칙)는 `fluency`/`completeness`의 **하한 게이트**로
동작한다 — 규칙 위반이 있으면 LLM 채점 이전에 이미 fail.

## 3. `judge_fluency()` 프롬프트 골격 (초안)

```
아래 [답변]을 한국어 문체·문법 기준으로 0~5로 채점하라.
5 = 설교/교육 자료로 즉시 쓸 수 있는 완결된 문단.
3 = 뜻은 통하나 번역투·어색한 연결이 있음.
0 = 문장 파편·비문·외국어 원문 노출.
반드시 JSON만: {"score": <0-5>, "reasons": ["..."]}
[답변]
{answer}
```

`sermon_judge.py`의 JSON-schema-prompt + brace-extraction + fail-soft 패턴을
그대로 따른다(TSU config 주석의 기존 관례).

## 4. `judge_completeness()` — reference 문제

`question_answering_quality`의 reference-free 재정의가 ADR-010 Phase 4까지
보류이므로, 그때까지 `completeness`는:

- 입력: `question` + `answer` + 제공 `<자료>` 문단 목록.
- 판정: "질문이 물은 것 중 제공 자료로 답할 수 있었던 부분을 답변이 실제로
  다뤘는가" (자료에 없는 것까지 요구하지 않음 — 근거 강제와 정합).
- reference로 **제공 문단**을 사용(정답 문서가 아니라 "가용 근거").

## 5. chat/research 연결 (ADR-010 Phase 2)

- `generate_answer()`(공용) 반환 후 비동기/후처리로 채점 → `GenerationResult`에
  부가, UI 캡션. **생성 차단 안 함**(feedback_avoid_risky_uncertain_design).
- F2(GPU 점유) 실행 중에는 대량 rag_judge 보류(TO §9).

## 6. 미해결 (Phase 2 TO에서 결정)

1. 채점 모델 — `my-theology-bot-v2`(부하 시 CJK 코드스위칭, 감사 §3.3) 대신
   별도 judge 모델? 
2. 임계값 — `fluency ≥ 3` / `completeness ≥ 3`을 배포 게이트로?
3. 교단 정합성 지표 — 별도 트랙(ADR-009 SIL). 이 문서 범위 밖.
