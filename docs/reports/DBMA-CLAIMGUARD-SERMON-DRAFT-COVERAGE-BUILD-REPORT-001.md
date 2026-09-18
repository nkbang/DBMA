---
title: ClaimGuard 커버리지 확대 — SermonDraftService(개요/대지 확장) 연결
created: 2026-09-17
author: CUE
status: 구현 완료 · 회귀 통과
audit_item: 답변 신뢰도 검증 (제안서 개발 현황 "개선 중" 항목)
base: dev/dbma-engine
scope: core/generation.py, ui/pages/sermon_draft.py, tests/test_sermon_draft_claim_guard.py
---

# ClaimGuard 커버리지 확대 — 설교 개요/대지 확장 경로

## 착수 전 확인 (재검증)

- `git log` / `docs/architecture/` 확인 결과, P0-4(TrustTier 위장 제거,
  `core/claim_guard.py`)와 P0-6(근거 0건 유보, PR #13)은 dev/dbma-engine에
  이미 병합돼 있고 메모리 기록과 일치했다.
- P0-5(A1 근거누출/오염) 관련 PR #26(`script-contamination-broaden-ranges`)
  도 이미 병합 완료 상태였다 — 재작업 불필요.
- ADR-030 Amendment D(authority_tier 3축)는 **PROPOSED(DRAFT)** 상태이며
  이번 작업과 무관 — Architecture Freeze Rule 대상 아님, 건드리지 않음.
- 결론: 메모리 기록은 유효했고, 실제 코드 상태와 일치했다.

## 문제 (재확인된 공백)

`ClaimGuard`(위험 표현 탐지 + TrustTier 근거 등급 판정)는
`GenerationService.generate()` / `generate_stream()`(Chat·Research
경로)에만 연결돼 있었다. `SermonDraftService.generate_outline()` /
`expand_point()`(설교 개요·대지 확장 경로)는 `ClaimGuard`를 전혀 호출하지
않아, "성경 전체에서 유일한 사례입니다" 같은 절대·최상급 주장이 근거
등급 검증 없이 그대로 설교 원고에 들어갈 수 있었다.

특히 `expand_point()`는 사람이 검토하는 단계 없이 바로 최종 설교문
초안에 조립되므로(`ui/pages/sermon_draft.py`의 확장 단계는 `st.markdown()`
으로 즉시 표시 — 수정 UI 없음), 이 공백이 Chat/Research보다 실질적으로
더 크다.

## 변경

### 1. `core/generation.py`

- `_run_claim_guard(answer, response)` → `_run_claim_guard(answer,
  candidates: list[RankedCandidate])`로 시그니처 일반화 — Chat/Research의
  `ResponsePackage.top_k_results`와 SermonDraftService에 전달되는
  candidates 목록 양쪽에서 재사용 가능하게 함. 기존 두 호출부
  (`GenerationStream.to_result`, `GenerationService.generate`)는
  `response.top_k_results`를 넘기도록 갱신 — 동작 변화 없음.
- `SermonOutline`에 `claim_guard_result: ClaimGuardResult | None = None`
  필드 추가. `generate_outline()`은 파싱된 개요(제목+서론+대지+결론)
  전체 텍스트로 `_run_claim_guard()`를 실행해 이 필드를 채운다.
  반환 타입 `tuple[SermonOutline, Optional[str]]`은 그대로 — 호출부
  변경 없이 적용됨(`scripts/run_sermon_eval.py`,
  `scripts/run_golden_set_expansion.py` 등 기존 2-tuple unpack 그대로 동작).
- `expand_point()` 반환값을 `tuple[str, Optional[str]]` →
  `tuple[str, Optional[str], ClaimGuardResult | None]`로 확장. 프로덕션
  호출부는 `ui/pages/sermon_draft.py` 1곳뿐이라 파급 범위가 작음(테스트는
  반환값을 unpack하지 않아 영향 없음).

### 2. `ui/pages/sermon_draft.py`

- `expand_point()` 호출부를 3-tuple로 갱신하고, 대지별
  `claim_guard_result`를 `state["expanded_claim_guard"][i]`에 저장.
- `_render_outline_claim_guard_warning()` 신설 — 개요 검토 단계
  (`_render_outline_step`)에서 `_render_doctrine_warning()` 바로 뒤에
  호출. Chat/Research의 `_render_claim_guard_warning()`을
  `ui.pages.chat`에서 그대로 import해 재사용(research.py가 이미 같은
  패턴으로 chat.py 헬퍼를 재사용 중).
- 대지 확장 단계(`_render_expansion_step`)의 "이미 생성됨" 렌더링에도
  동일한 경고를 추가. "다시 생성" 시 저장된 `claim_guard_result`도 함께
  제거.

모두 **사후 탐지·안내 배너**다 — `absolute_claim_blocked`가 True여도
개요/대지 확장 생성 자체를 막지 않는다. 이는 기존 Chat/Research 경로의
설계(및 P0-4 빌드 보고서가 명시한 "ClaimGuard는 사후 탐지만 한다")와
동일한 계약을 설교 초안 경로로 확장한 것이며, 생성을 차단하는 새로운
정책을 도입한 것이 아니다.

## 범위 밖 (후속)

- `has_t3`는 여전히 계산만 되고 미사용 — P0-4 빌드 보고서가 이미 명시한
  후속 정리 대상, 이번 변경 범위 밖.
- `absolute_claim_blocked=True`가 실제로 답변 텍스트를 재작성/차단하도록
  바꾸는 것(현재는 캡션 경고만)은 UX/정책 판단이 필요한 별도 결정 —
  이번 작업은 기존 "경고만" 설계를 새 경로로 확장했을 뿐, 그 설계 자체를
  바꾸지 않았다.
- AT-4/AT-5 사후확인, P0-5 21건 실제 채점 실행은 사람의 실행(질의
  채점)이 필요한 항목으로 이번 세션 범위 밖.

## 검증

```bash
~/envs/dbma311/bin/python -m pytest -q tests/
```

- 신규 파일 `tests/test_sermon_draft_claim_guard.py`: 7 passed
  (generate_outline 저위험/고위험/예외 3건, expand_point 저위험/고위험/
  예외/ClaimGuard 자체 실패 4건).
- 기존 관련 파일 6개(`test_claim_guard.py`,
  `test_generation_claim_guard.py`, `test_sermon_draft_repeat_penalty.py`,
  `test_sermon_no_fabricated_illustration.py`,
  `test_sermon_insufficient_evidence.py`,
  `test_script_contamination_broadened_ranges.py`): 124 passed, 회귀 없음.
- 전체 회귀: **3083 passed, 2 skipped, 4 failed** (216s).
  실패 4건은 이번 변경과 무관 — `git stash`로 변경분을 제거한 베이스라인
  에서도 동일하게 실패함을 직접 확인(`test_indexer_review_gate_wiring`,
  `test_m2_source_registry_governance` ×2, `test_nae_pilot_human_review_intake`).
  전부 Production 인덱서/리뷰 게이트/M2 레지스트리의 데이터 상태
  드리프트(예: 예상 인덱싱 건수 3319 vs 실측 8936)이며,
  `core/generation.py` / `core/claim_guard.py` / `ui/pages/sermon_draft.py`
  를 참조하지 않는 별도 영역 — 이번 작업 범위 밖이라 손대지 않았다.
