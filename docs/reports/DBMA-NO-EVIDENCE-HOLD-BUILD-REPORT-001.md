---
title: 근거 부족 시 유보 응답 빌드 보고서
created: 2026-09-10
author: CUE
status: 구현 완료 · 회귀 통과
audit_item: PM 정렬 감사 R6 / P0-6 (선결 로직 #2)
base: claude/p0-4-trust-tier-honesty (← claude/p0-1-quality-integration ← origin/dev/dbma-engine)
scope: ui/pages/chat.py, ui/pages/research.py, tests/test_chat_evidence_hold.py
---

# 근거 부족 시 유보 응답

## 문제

`ui/pages/chat.py`의 두 생성 경로 모두 검색이 근거를 하나도 반환하지 못해도
LLM 생성을 강행했다.

- `generate_answer()` (research.py 공용): 주석까지 달려 있었다 —
  `# Even if retrieval returns no results, try generation (may still
  produce a useful answer from system prompt / prior context).`
- `_handle_user_message()` (chat 페이지): `_is_low_confidence()`로 캡션
  경고만 띄우고 답변은 그대로 생성.

RetrievalEngine에는 relevance floor가 없어 보통 top-k를 채워 반환하지만,
코퍼스가 비었거나 파일 스코프가 전부 제외한 경우 등에서 0건이 나온다.
그 상태에서 생성하면 답은 오직 70B 모델 내장 지식(출처 불명 웹 학습
데이터)에서만 나온다 — "등록·처리된 자료에 근거해서만 답한다"는 제품
원칙을 정면으로 어기는 유일한 경로였다.

## 변경

### 하드 게이트: 검색 0건 → 유보 문구, LLM 미호출

`_NO_EVIDENCE_HOLD_TEXT` 신설:

> 현재 등록된 자료에서 이 질문에 답할 근거를 찾지 못했습니다.
> 이 앱은 등록·처리된 자료에 근거해서만 답변하도록 설계되어 있어,
> 관련 자료가 없을 때는 일반 지식만으로 답을 만들지 않습니다.
> 관련 문서를 추가하거나, 검색 범위를 넓히거나, 질문을 다르게 표현해
> 다시 시도해 주세요.

| 경로 | 게이트 조건 |
|---|---|
| `generate_answer()` | `not response.top_k_results and not smith_results` → `return (_NO_EVIDENCE_HOLD_TEXT, [])` (Smith 사전 컨텍스트가 있으면 근거로 인정) |
| `_handle_user_message()` | `not response.top_k_results` → 유보 메시지 렌더 + `chat_messages`에 `evidence_hold=True`로 append 후 return |

### research.py — 중복 캡션 억제

유보 문구가 표시될 때는 "검색 결과 신뢰도가 낮습니다" 저신뢰 캡션을
중복 표시하지 않는다(AI 답변 블록·이어서 질문 블록 양쪽).

## 의도적으로 하지 않은 것

**저점수(0건 아님) 케이스는 게이트하지 않는다.** `_is_low_confidence()`의
임계값(weighted-sum 0.45 / theological 0.15)은 4개 샘플로 보정한
provisional 값이다. `feedback_avoid_risky_uncertain_design`("신뢰 안 된
분류기 위에 처리 경로를 얹지 말 것")에 따라 그 신호는 기존처럼 캡션
경고로만 남긴다. 이번 변경은 "0건"이라는 사실만 본다 — 새 분류기·새
임계값 없음.

## 검증

```bash
~/envs/dbma311/bin/python -m pytest -q tests/
```

- 신규 `tests/test_chat_evidence_hold.py`: 4건
  - 검색 0건 + Smith 0건 → 유보, GenerationService 미호출
  - 검색 0건 + Smith 컨텍스트 있음 → 정상 생성
  - 결과 있음(점수 낮아도) → 정상 생성
  - 유보 문구가 사유("등록", "일반 지식")를 명시
- 전체 회귀: **2885 passed, 15 skipped** (기존 2881 + 4)

## 범위 밖 (후속)

- `_handle_user_message`는 대화 이력을 받지만 유보 게이트는 이력을 보지
  않는다 — 0건은 드물고, 후속 질문도 보통 top-k가 채워지므로 오작동
  위험은 낮다. 이력 기반 예외가 필요하면 별도 항목.
- Smith 외 다른 보조 컨텍스트(향후 추가 시)도 근거로 인정할지는 그때 판단.
