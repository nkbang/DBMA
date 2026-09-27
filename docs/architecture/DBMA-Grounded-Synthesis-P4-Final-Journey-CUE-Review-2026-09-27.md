# Grounded Synthesis P4 → Final Conclusion 여정 지시서 — CUE 검토

- 날짜: 2026-09-27
- 대상: HQ 작성 "DBMA/NAE Grounded Synthesis P4 → Final Conclusion 전체 작업여정 및 심층 점검 지시서"
- 검토자: CUE (READ-ONLY — 코드 변경 없음)
- 기준 코드: `origin/feat/peb-v0.1` @ `db677ac6` (P1 `2dd40d2e` + P2), `origin/main` @ `8e9c5241`

## 판정

**방향 수용 / 원문 그대로 C1 전달은 HOLD.**
아래 보정 조항 A1~A7을 원문 뒤에 붙여 전달하면 전달 가능(RELAY OK).
이 중 A1은 **현재 진행 중인 P3에 즉시 영향**이 있으므로 우선 전달해야 한다.

원문의 골격(Retrieval authority 불변, C1 자체 GREEN 금지, STOP 조건,
"Insufficient Evidence는 정상 결과", 역방향 추적 Answer→Claim→Evidence→Source)은
기존 거버넌스·코드와 일치한다. 문제는 원문이 **현재 코드가 실제로 보장하지 않는 것**을
전제로 삼은 곳 3군데와, **이미 존재하는 생성 경로를 언급하지 않은 것**이다.

## 발견 사항

### F1 [HIGH · P3 즉시] 최종 질문 3번과 4번이 현재 P2 계약에서 서로 충돌

- 원문 §15-3 "다중 질의 조립 시 provenance 손상 없음"과 §15-4/§8-D "P2 중복 정책
  (last association retained) 유지"는 동시에 만족될 수 없다.
- 근거: `core/evidence_pool.py:84-86` — 같은 `evidence_id`가 다시 들어오면
  `(eid, evidence, build_query)` 튜플 전체를 덮어쓴다. build_query도 마지막 값만 남는다.
- 실측(CUE, feat/peb-v0.1 코드로 실행):
  ```
  add(E1, "A") → add(E3, "C") → add(E1, "B")
  by_query("A") = []        ← 질의 A가 E1을 찾았다는 사실이 사라짐
  by_query("B") = ['E1']
  by_query("C") = ['E3']
  ```
- 추가로 RankedCandidate 경로의 Evidence 자체도 질의 출처를 갖지 않는다:
  `core/evidence_adapters/tsu_adapter.py:282-283` — `retrieval_query=None`,
  `retrieval_method="hybrid"`(QueryProcessor 비하이브리드 경로여도 상수).
  원문 §4.2가 "유지되어야 한다"고 적은 `retrieval_query`/`retrieval_method`는
  Evidence 안에 애초에 실제 값으로 들어 있지 않다.
- 결론: EvidencePool(P2 공개 계약)을 바꾸지 않고 다중 질의 출처를 보존하려면,
  **P3 조립 계층이 질의→evidence_id 연관을 별도로 기록**해야 한다(보정 A1).
  P1/P2 계약은 재심사하지 않는다 — 그 위에서 해결한다.

### F2 [HIGH · P4 전제] 운영 중인 "생성 권위(Generation authority)"가 이미 존재한다

원문은 Retrieval authority 보존만 규정하고, 이미 운영 중인 근거 강제 생성 경로를 언급하지 않는다.

| 이미 있는 것 | 위치 |
|---|---|
| 근거 한정 지시문(부족하면 밝히고 멈춤, "이 질문은 현재 등록된 자료로는 답할 수 없습니다.") | `core/generation.py:188` `_GROUNDING_DIRECTIVE`, `:238` `_NO_CONTEXT` |
| 답변 후 위험 주장 점검 | `core/generation.py:244` `_run_claim_guard` (호출 `:358`, `:491`, `:748`, `:826`) |
| 절대주장 탐지기 | `core/claim_guard.py` (어휘 기반 — claim↔evidence 결속 아님) |
| 회귀 테스트 | `tests/test_grounding_directive_stop_on_insufficiency.py`, `test_chat_evidence_hold.py`, `test_sermon_insufficient_evidence.py`, `test_generation_claim_guard.py` |

- 위험: 규칙 없이 P4~P6을 진행하면 운영 경로와 병렬인 **두 번째 프롬프트/생성 경로**가
  생긴다. 이는 "새 retrieval 경로 금지"와 같은 종류의 위험이다.
- ClaimGuard는 어휘 매칭 기반이라 P5의 Claim–Evidence Binding과 기능이 겹치지는 않는다.
  다만 이름(`Claim*`)과 호출 지점이 겹치므로 P5는 ClaimGuard를 대체·개명·우회하지 않는다고 명시해야 한다.

### F3 [HIGH · 거버넌스] 같은 날 확정된 기존 로드맵과 Phase 번호·범위가 다르다

| Phase | 기존 로드맵 (HQ 2026-09-27) | 이번 지시서 |
|---|---|---|
| P4 | Context Expansion | Grounded Synthesis Boundary |
| P5 | Evidence Classification | Claim–Evidence Binding |
| P6 | Multi-Source Evidence Assembly (Personal/Default) | Grounded Answer Generation |
| P7 | Grounded Synthesis | Citation / Provenance Validation |
| P8 | Claim–Evidence Binding | Negative / Failure-path |
| P9 | Grounded Answer + Citation | Full Integration Test |
| P10 | Regression / Grounding Validation | Regression / Architecture Audit |
| P11~12 | — | Production Safety / Scope Audit |

- 이번 지시서에서 **빠진 것**: Context Expansion(관련 ADR-034 Sentence-Window는 Proposed),
  Evidence Classification, Multi-Source(Personal/Default) Assembly.
- 저장소에는 Grounded Synthesis 로드맵 문서나 ADR이 **하나도 없다**
  (`docs/` 전체에서 "grounded synthesis" 검색 0건). 로드맵은 채팅/메모리에만 있다.
- → HQ 결정 D1 필요.

### F4 [HIGH · ADR] P4 이후는 "새 Architecture Layer"다 — ADR이 먼저 필요

- CUE Operating Policy: 새 Architecture Layer 추가 시 ADR 작성과 C1 Review가 필요하다.
  P1~P3은 retrieval 결과의 표현·저장·조립이지만, P4부터는 LLM 입력 계약과
  claim 결속이라는 새 계층이다.
- 권고: P4 착수 전 **ADR-036(Proposed)** "Grounded Synthesis Boundary"를 작성한다.
  이 ADR은 F2의 생성 권위 관계, F5의 입력 선택 규칙, F6의 검증 방법을 확정한다.
  (다음 ADR 번호: ADR-035가 `claude/adr-035-pastoral-library-automation`에서 사용 중)

### F5 [MED · P4] 합성 입력 선택이 곧 "새 ranking 로직"이 될 수 있다

- 다중 질의 풀(N개 질의 × top_k)은 LLM 컨텍스트 예산을 넘는다. 그중 무엇을 넣을지
  고르는 행위는 STOP 조건 #6("New ranking logic")에 해당할 수 있다.
- 필요: 점수를 새로 계산하지 않는 **결정적(deterministic) 절단 규칙**을 ADR에 명시한다.
  예: 질의별 원래 순위 순서로 라운드로빈 + 호출자가 정한 상한. 그리고 무엇을 넣고
  뺐는지를 입력 manifest에 기록한다.
- 부수: `Evidence.to_dict()`는 text를 500자로 자른다(`core/evidence_model.py:117`, 디버깅용).
  합성 입력은 `Evidence.text`를 사용해야 하며, 절단이 있으면 manifest에 기록한다.

### F6 [MED · P5/P7] "Evidence fidelity" 검증 방법이 정의되지 않았다

- 원문 §7 "Citation된 Evidence가 실제 claim을 뒷받침하는가?"를 LLM이 판정하면,
  생성한 LLM 계열이 스스로를 채점하는 구조가 된다(C1 자체보고와 같은 문제).
- 필요: 검증을 두 층으로 나누고 **PASS 수치에 섞지 않는다.**
  - 결정적 검사(자동 가능): evidence_id가 존재하는가 / 합성 입력 집합에 속하는가 /
    인용 구간이 Evidence.text에 실제로 있는가
  - 의미 지지 판정: 사람 또는 CUE의 표본 검토. 별도 수치로 보고한다.
- 참고: P0-5 채점에서 대표 질의의 70%(17/24)가 NOT VERIFIED였다. 따라서
  **근거 부족 경로가 주 경로**가 된다. P8은 예외 처리가 아니라 핵심 검증 대상이다.

### F7 [MED · 테스트] LLM 결정성

- P4~P9 단위 테스트는 stub/fake LLM으로 결정적으로 작성한다.
- 실제 모델(Ollama) 실행 결과는 별도 증거로 분리한다. stub 결과를 "합성 품질"로
  보고하지 않는다. 실제 모델 실행은 GPU 가용 여부에 의존한다.

### F8 [MED · P10] 회귀 기준 커밋 고정

- `feat/peb-v0.1`은 `origin/main`보다 retrieval 변경 8커밋이 뒤처져 있다
  (예: `6bd97b2f` 구절 질의 번역, `877b19b0`, `3f64027f` 권말 색인 강등, `ae822afd`).
- "기존 retrieval 결과 = Grounded Synthesis 이전"을 비교할 때 기준 커밋을 고정하지 않으면,
  main 동기화로 생긴 retrieval 변화가 Grounded Synthesis 탓으로 잘못 기록된다.
- 필요: P10 기준 = 명시한 커밋의 retrieval 출력 스냅샷. main 동기화는 그 전후로
  따로 기록한다(main 병합은 HQ 승인 사항).

### F9 [LOW · 효율] 감사 게이트 중복

- P10(Regression) / P11(Production Safety) / P12(Scope Audit)은 모두 read-only 감사다.
  한 게이트에 3개 섹션으로 합치면 C1→CUE→HQ 게이트 사이클이 3회에서 1회로 줄어든다.
- 권고 사항일 뿐 차단 사유는 아니다.

## HQ 결정 필요

- **D1 로드맵 정본**: 이번 지시서가 기존 P4~P10 로드맵을 대체하는가?
  대체한다면 빠진 3개(Context Expansion / Evidence Classification / Multi-Source)는
  폐기인가, 후속 여정으로 보류인가?
- **D2 생성 권위**: Grounded Synthesis는 (a) P9까지 UI와 분리된 병렬 검증 계층인가,
  (b) 최종적으로 `core/generation.py` 프롬프트 경로를 대체하는가?
  CUE 권고는 **(a)**이다 — 운영 경로 교체는 P9 이후 별도 ADR과 HQ 승인으로 다룬다.
- **D3 감사 게이트 병합**(F9): P10~P12를 단일 게이트로 운영할지.

## C1 전달용 보정 조항 (원문 뒤에 그대로 첨부)

```text
[CUE 보정 조항 A1~A7 — 원문 지시서보다 우선한다]

A1 (P3 즉시 적용) 다중 질의 출처 보존
- EvidencePool은 같은 evidence_id를 덮어쓰며 build_query도 마지막 값만 남긴다
  (core/evidence_pool.py:84-86). 실측: E1을 질의 A→B 순으로 넣으면 by_query("A")=[].
- 따라서 core/evidence_assembly.py는 EvidencePool과 별개로
  "질의 → [evidence_id]" 연관 기록(assembly manifest)을 반환해야 한다.
  한 evidence가 여러 질의에서 발견되면 모든 질의를 기록한다.
  질의별 원래 순위(rank)와 호출자가 신고한 processor 종류(QueryProcessor/Hybrid)도 기록한다.
- EvidencePool/Evidence 코드는 수정하지 않는다(수정이 필요하면 STOP).
- Evidence.retrieval_query(None)와 retrieval_method("hybrid" 상수)를
  질의 출처의 근거로 사용하지 않는다.
- 테스트 필수: A→E1, B→E1 입력에서 manifest가 E1의 질의로 A와 B를 모두 보존하는지 검증.

A2 생성 권위
- core/generation.py(_GROUNDING_DIRECTIVE, _run_claim_guard)와 core/claim_guard.py는
  운영 경로다. P4~P8에서 수정·대체·우회하지 않는다.
- 새 LLM client나 새 프롬프트 경로가 필요하면 STOP(추가 STOP 조건 #19).

A3 ADR 선행
- P4 구현 전에 ADR-036(Proposed) "Grounded Synthesis Boundary"가 있어야 한다.
  ADR이 없으면 P4는 설계 보고서까지만 작성하고 STOP한다.

A4 합성 입력 선택 = ranking 금지
- 합성 입력에 넣을 evidence는 새 점수 계산 없이 결정적 규칙으로만 고른다.
- 입력 manifest에 포함/제외된 evidence_id와 절단 여부를 기록한다.
- Evidence.to_dict()(text 500자 절단)를 합성 입력으로 사용하지 않는다.

A5 검증 분리
- 결정적 검사(ID 존재, 입력 집합 소속, 인용 구간 실재)와 의미 지지 판정을
  분리해서 보고한다. LLM 자기판정 결과를 PASS 수치에 포함하지 않는다.

A6 LLM 테스트
- 단위 테스트는 stub LLM으로 결정적으로 작성한다.
- 실제 모델 실행 결과는 별도 섹션에 적고, stub 결과를 품질 근거로 쓰지 않는다.

A7 회귀 기준 고정
- P10 비교 기준은 보고서에 명시한 단일 커밋의 retrieval 출력이다.
- main 동기화로 생긴 retrieval 변화는 Grounded Synthesis 변화와 분리해서 기록한다.
```

## 다음 조치

1. HQ: D1~D3 결정
2. HQ → C1: 원문 + A1~A7 전달(A1은 P3 진행 중이므로 우선 전달)
3. C1 P3 보고서 수신 → CUE read-only 재검증(A1 manifest 테스트 포함 여부 확인)
4. P3 승인 후, P4 착수 전 ADR-036 초안 작성(CUE)

진행률: 여정 문서 검토 100% / Grounded Synthesis 전체 여정 약 20% (P1·P2 승인, P3 진행 중)
