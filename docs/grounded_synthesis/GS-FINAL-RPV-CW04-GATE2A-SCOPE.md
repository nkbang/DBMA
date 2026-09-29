# CW-04 Gate 2A — Retrieval Role Design Scope

- **Status**: AUTHORIZED (2026-09-28 HQ 발행)
- **Parent**: [GS-FINAL-RPV-CW04-SCOPE.md](GS-FINAL-RPV-CW04-SCOPE.md) §18
  ("CW-04 Gate 1 종료 — CUE 독립 검증 및 HQ 최종 판정")
- **Precondition**: CW-04 Gate 1 `[✓ HQ]` — 기술적 결론 VALIDATED,
  절차 준수(G0) FAILED로 기록됨
- **Implementation**: **NOT AUTHORIZED** — Gate 2A는 설계안 제출까지만
- **C1**: 설계 제안 착수 가능 (코드 수정 금지)
- **CUE**: C1 설계 산출물 대기 → 독립 검증

---

## 0. Gate 2A의 목적과 경계

Gate 2A는 코드를 고치지 않는다. **"Personal/Default를 어떤 authoritative
metadata로 구분하고, 그 role을 retrieval candidate까지 어떻게
전달하며, Personal primary / Default supplemental이라는 제품 원칙을
어떤 최소 메커니즘으로 구현할 것인가"**를 설계안 수준에서 결정하기
위한 조사·제안 단계다.

C1은 여러 설계 옵션을 비교·제안하되 **하나를 임의로 선택해 구현하지
않는다.** 설계안이 HQ 승인을 받은 뒤에만 별도의 **Gate 2B**(구현
재승인)로 넘어간다.

## 1. Gate 0 — 여전히 예외 없이 적용

Gate 1 종료 시 확정된 원칙을 그대로 승계한다:

> **G0는 read-only investigation/design 조사에도 예외 없이 적용된다.
> G0 불일치 후 C1이 임의로 작업을 계속한 결과물은 그 자체로 acceptance
> evidence가 아니다.**

```text
pwd
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
```
Expected: `/Users/David/DBMA-rpv-c8f7e41a`, detached HEAD,
`c8f7e41acfa0e5444d8b02ecb84da9c53a588441`. **불일치 시 예외 없이
STOP** — "read-only니까 괜찮다"는 판단을 C1이 다시 내려서는 안 된다
(Gate 1에서 실제로 이 판단이 줄번호 오류를 낳았음, CW-04 §18 참고).

## 2. 핵심 설계 질문 (Q1-Q8)

Gate 1에서 확정된 사실을 전제로 한다: `Evidence.corpus_type`은 정의만
있고 adapter가 항상 `CORPUS_DEFAULT`로 하드코딩하며, `RankedCandidate`/
`CandidateRef`에는 필드 자체가 없어 retrieval lineage 어디에도 corpus
role이 전달되지 않는다(`core/hybrid_candidate_pipeline.py:234-241`,
`core/evidence_adapters/tsu_adapter.py:200-207` 등, Gate 1 CUE 독립
검증 완료).

### **Q8 — Personal/Default membership의 authoritative SSOT (핵심)**

Personal Corpus와 Default/Reference Corpus 구분을 **어디서, 무엇을
근거로** 판별할 것인가? 특히:

- `source_file` 문자열 패턴(경로/파일명 convention)을 SSOT로 사용할
  것인가? — **개인 자료의 파일명이나 경로 관습에 의존하는 방식은
  장기적으로 위험할 수 있다**(사용자가 파일명을 바꾸거나, 향후 업로드
  경로 구조가 바뀌면 깨짐). 이 위험을 명시적으로 검토할 것.
- 업로드 시점에 별도 필드(예: DB 컬럼, TSU record의 명시적 태그)로
  기록하는 방식이 더 안정적인가?
- 현재 업로드 파이프라인(`ui/pages/processing.py`,
  `core/index_orchestrator.py`)에 Personal Corpus 여부를 판별할 수
  있는 기존 신호가 이미 존재하는가? (예: 업로드 경로, 사용자 계정
  구분) — 없다면 어디에 추가해야 하는가?

### Q1(D1) — Corpus membership SSOT (Q8과 연결)
Personal/Default 구분의 근거 데이터가 무엇이어야 하는지 Q8의 결론을
구체적인 구현 지점(파일/필드/스키마)으로 좁힌다.

### Q2(D2) — Role propagation
최소한 다음 경로에서 role identity가 보존되어야 하는지 결정한다:
```text
TSU → RankedCandidate → CandidateRef → Evidence
```
각 단계에서 실제로 어떤 필드/구조 변경이 필요한지 구체적으로 제시한다
(Gate 1에서 이미 각 단계의 정확한 코드 위치가 확인됨).

### Q3(D3) — Retrieval semantics
Personal은 "항상 더 높은 relevance"가 아니라 **"사용자가 선택한
연구 맥락으로서 primary context"**라는 제품 정의를, retrieval
semantics로 어떻게 표현할지 결정한다.

### Q4(D4) — Ranking mechanism 후보 비교
다음 중 어떤 방식인지, 각각의 장단점을 비교한다:
- A. score adjustment(scoring 공식에 corpus-role 가중치 추가)
- B. candidate quota/composition(top-k 내 Personal 슬롯 보장)
- C. two-stage retrieval(Personal 우선 조회 후 Default 보충)
- D. primary Personal + supplemental Default(명시적 구조 분리)
- E. other

**신규 retrieval engine이나 대규모 ranking rewrite는 제외한다.**

### Q5(D5) — Default supplementation 보장
Personal 자료가 불충분/부족할 경우 Default supplementation이 정상
작동해야 한다:
```text
Personal → insufficient/incomplete → Default supplementation
```
"Personal 우선"을 "Default 차단"으로 구현하면 안 된다.

### Q6(D6) — GS boundary 유지 증명
최종 설계에서도 다음 경계가 유지됨을 증명한다:
```text
Retrieval decides evidence set/order
GS synthesizes supplied evidence
```
GS(P4-P9)에 Personal/Default ranking logic을 넣지 않는다.

## 3. C1 산출물 (설계 제안 — 구현 아님)

C1은 다음 10개 항목을 제출한다. **코드 수정 금지.**

1. Personal/Default membership SSOT 후보(Q8 답변, 복수 옵션 비교)
2. role propagation 설계(Q1-Q2, 구체적 파일/필드 수준)
3. retrieval layer 적용 지점 후보(정확한 파일:함수:줄번호로 지목)
4. scoring vs candidate composition 비교(Q4, A-E 중 비교 분석)
5. Default supplementation 방식(Q5)
6. GS boundary 영향 없음의 증명(Q6)
7. 최소 변경 파일 목록(실제 구현 시 예상되는 것 — 지금 수정하지 않음)
8. 예상 regression 범위
9. RPV-06a 유효 query/fixture(§CW-04 §3.1 조건 전부 충족, **Bible
   route로 분류되지 않는 것으로 재선정** — Q6에서 제안했던 "요한복음
   15장..." 질문은 Gate 1에서 무효 처리됨, `core/query_planner.py::classify()`
   로 사전 검증할 것)
10. 구현하지 않은 상태의 최종 design recommendation(하나를 추천하되
    "이것이 Gate 2B에서 그대로 구현 승인된다는 의미가 아님"을 명시)

## 4. C1 보고 표준 (CW-03/CW-04 Gate 1 승계, 예외 없이 적용)

1. **Question integrity** — RPV-06a 후보 질문 등은 §3.1 조건을 그대로
   사용, 임의 변형 금지
2. **Worktree identity** — `pwd`/toplevel/branch/HEAD 전부 명시
3. **Execution timestamp** — 실제 작업 시각
4. **Result artifact** — 검증 가능한 산출물 경로
5. **Test question immutability** — 임의 변경 금지
6. **서술적 결론 ≠ evidence** — "이 방식이 맞다"는 문장만으로는
   근거가 되지 않는다. 코드 인용(파일:줄번호, Gate 1에서와 같이 CUE가
   실제 baseline에서 재확인 가능한 형태)과 구체적 근거를 포함할 것

## 5. CUE 독립 검증 (Gate 1과 동일 원칙)

CUE는 C1의 설계 제안을 그대로 승인 근거로 쓰지 않는다. 최소 확인:
1. 제안된 SSOT 후보가 실제 baseline 코드/데이터에서 타당한지
2. role propagation 설계가 Gate 1에서 확인된 실제 코드 경로와 부합하는지
3. Q4 각 옵션의 trade-off 서술이 정확한지(과장/누락 없는지)
4. RPV-06a 제안 질문이 실제로 `route=hybrid`이고 Personal/Default
   candidate가 모두 baseline에서 존재하는지 **직접 재실행해 확인**
5. GS boundary 증명(Q6)이 실제로 GS 코드(core/grounded_*.py) 무변경을
   전제로 하는지
6. G0 준수 여부(Gate 1 위반 재발 여부)

CUE 검증 완료 후 **HQ Architecture Decision**으로 넘어가며, HQ가
승인해야만 Gate 2B(구현)가 열린다.

## 6. 금지 사항 (CW-04 본문 §5, §14.3 그대로 승계)

Personal 무조건 rank 1 하드코딩 제안 금지, Default 자료 제거 제안
금지, GS에서 retrieval 재구현 제안 금지, 기존 scoring 임의 변경 제안
(코드 실행 없이 설계안으로도) 시 반드시 대안과 비교, corpus authority
임의 신설(Personal이 항상 더 정확/권위 있다는 가정) 금지. 신규
retrieval engine, 신규 embedding model, Qdrant 구조 변경, corpus
reprocessing, TSU 재생성, 대규모 ranking rewrite, GS architecture
변경, GS P03A-P12 재설계, Default Corpus 내용 변경, Personal/Default
물리적 병합, unrelated refactoring — 설계안에도 포함하지 않는다.

## 7. 완료 흐름

```text
Gate 2A Design Scope (본 문서)
    ↓
Gate 0 확인 (예외 없음)
    ↓
C1 설계 제안 (10개 산출물, §3)
    ↓
CUE 독립 검증 (§5)
    ↓
HQ Architecture Decision
    ↓
[승인] → Gate 2B Implementation Authorization (별도 문서/승인)
[반려] → 설계 재작업 또는 [HOLD] Architecture Decision Required
```

## 8. 현재 상태

```text
CW-04 Gate 1     [✓ HQ]
CW-04 Gate 2A    [AUTHORIZED — 설계 제안만, 구현 금지]
CW-04 Gate 2B    [NOT AUTHORIZED]
C1               [Gate 2A 설계 제안 착수 가능]
CUE              [C1 산출물 대기 → 독립 검증 예정]
RPV-06           [HOLD]
GS-FINAL-RPV     [HOLD]
```
