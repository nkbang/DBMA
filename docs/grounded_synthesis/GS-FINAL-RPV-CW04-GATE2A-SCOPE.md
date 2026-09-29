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

## 8. 현재 상태 (2026-09-28 1차 제출 후 — 최신은 §9 참고)

```text
CW-04 Gate 1     [✓ HQ]
CW-04 Gate 2A    [AUTHORIZED — 설계 제안만, 구현 금지]
CW-04 Gate 2B    [NOT AUTHORIZED]
C1               [Gate 2A 설계 제안 착수 가능]
CUE              [C1 산출물 대기 → 독립 검증 예정]
RPV-06           [HOLD]
GS-FINAL-RPV     [HOLD]
```

## 9. 1차 제출 CUE 독립 검증 + HQ 판정 (2026-09-28)

**C1 1차 제출**: 산출물 1-10 전부 제출. G0는 이번엔 위치 자체는 정상이었으나
(CUE가 `/Users/David/DBMA-rpv-c8f7e41a` 직접 재확인) **확인 명령 출력
자체를 보고서에 포함하지 않음** — 절차상 재지적 대상.

**CUE 독립 검증**: 산출물 1-8, 10의 코드 인용(`evidence_model.py`,
`tsu_adapter.py`, `evidence_assembly.py`, `evidence_pool.py`,
`hybrid_candidate_pipeline.py`, `retrieval.py:1792-1798`,
`grounded_synthesis_input.py`, `query_planner.py`)을 baseline에서
전부 직접 대조 — 정확함(Gate 1 때의 줄번호 오류 재발 없음). 그러나
**산출물 9(RPV-06a/06b 재선정 질문)는 사실관계 오류로 반증됨** — CUE가
제안 질문을 baseline에서 직접 라이브 재실행한 결과, `route=hybrid`는
맞지만 **fixture A/B가 top-10 candidate에 전혀 등장하지 않음(0/10
둘 다)**. C1이 route 분류만 확인하고 실제 검색 결과는 검증하지 않은
것이 원인.

**HQ 최종 판정**:
```text
CW-04 Gate 2A
  산출물 1   [✓ CUE]
  산출물 2   [✓ CUE]
  산출물 3   [✓ CUE]
  산출물 4   [✓ CUE — design candidate]
  산출물 5   [✓ CUE — design candidate]
  산출물 6   [✓ CUE]
  산출물 7   [✓ CUE — proposal]
  산출물 8   [✓ CUE]
  산출물 9   [HOLD — REWORK]
  산출물 10  [✓ CUE — subject to Q8/architecture decision]

Gate 2A final decision     [HOLD]
Gate 2B                    [NOT AUTHORIZED]
C1                         [REWORK ONLY — 산출물 9만]
CUE                        [NEXT — 산출물 9 재검증]
```

**중요(HQ)**: 산출물 10의 "quota-based two-stage retrieval"도 승인된
것이 아니다 — 여전히 설계 후보다. Q8 SSOT와 Personal/Default semantics가
Architecture Decision으로 확정되기 전에는 quota나 boost를 구현안으로
승격하지 않는다.

### 산출물 9 재작업 지시

```text
STATUS
  기존 산출물 1–8, 10       유지
  산출물 9                  REWORK REQUIRED
  Gate 2A 최종 승인          HOLD
  Gate 2B                   NOT AUTHORIZED

허용 범위
  - RPV-06a/06b 질문 재선정
  - route=hybrid 확인
  - 실제 retrieval 실행
  - fixture candidate 등장 여부 확인
  - 필요한 경우 fixture/query 관계 재설계
  - 결과 문서 작성

금지
  - 코드 수정 / retrieval 수정 / ranking 수정 / fixture 내용 변경
  - corpus/index 변경 / GS 변경 / quota·boost 구현
```

**RPV-06a**: fixture A의 실제 주제(요한복음 15장 포도나무 비유, 거함,
가지치기)와 의미적으로 연결되면서 scripture reference를 직접 포함하지
않는 자연어 질문 필요(예시 후보일 뿐, 채택 전 검증 필수):
"포도나무와 가지의 비유에서 열매를 맺기 위해 주님 안에 거한다는
의미를 설명해 주세요"

**RPV-06b**: fixture B의 실제 주제(성령의 은사, 고린도전서 12장)와
맞는 질문 필요(예시 후보):
"성령께서 교회에 다양한 은사를 주신다는 관점에서 은사의 종류와
목적을 정리해 주세요"

**증명해야 할 3가지**: (1) route=hybrid (2) fixture가 실제 retrieval
candidate에 등장 (3) fixture의 관련 내용과 질문이 실제로 연결됨 —
이 셋을 라이브 실행으로 증명해야 하며, 예시 질문을 그대로 채택하는
것이 목적이 아니다.

**보고 필수 항목** (단순히 `fixture_id in top_10`만 보고 금지):
```text
Query → ParsedQuery → route → retrieval candidate count
→ fixture candidate count → fixture rank(s) → fixture source_file
→ corpus_type → BM25 / semantic / final score
```
그리고 왜 그 fixture가 질문에 적합한 evidence인지 fixture 원문과
검색 결과를 대조해 확인할 것(코드 근거가 아니라 원문 대조).

### G0 절차 재교정 (2차 지적)

작업 위치가 실제로 맞았더라도 G0 확인 명령의 실제 출력을 보고서에
포함하지 않은 것은 절차 준수 실패다. "컨텍스트를 알고 있다"는 G0
증거를 대체할 수 없다. 다음 보고서에는 `pwd`, `git rev-parse
--show-toplevel`, `git branch --show-current`, `git rev-parse HEAD`의
실제 출력을 반드시 포함한다.

## 10. 산출물 9 확정 + Gate 2A 종료 (2026-09-28)

**C1 2차 제출**: 단일 스크립트로 두 후보 질문(RPV-06a/06b)을 라이브
재실행. RPV-06a는 `route=hybrid`, fixture A가 rank 6(bm25=18.854)에
등장 — 목표 달성으로 보고. RPV-06b는 `route=hybrid`이나 fixture B가
top-10에 **"0건, 미등장"**으로 보고.

**CUE 독립 재현**: `/Users/David/DBMA-rpv-c8f7e41a`(G0 재확인 완료)
에서 동일 두 질문을 직접 재실행.

| 질문 | route | C1 보고 | CUE 실측 재현 | 판정 |
|---|---|---|---|---|
| RPV-06a 후보("포도나무와 가지의 비유에서...") | hybrid | rank 6, bm25=18.854 | **rank 6, bm25=18.854 — 완전 일치** | ✅ 확인 |
| RPV-06b 후보("성령께서 교회에...") | hybrid | **0건, 미등장** | **rank 8, bm25=14.216, theological=0.232, final=0.04265 — 실제로 등장** | ❌ **C1 보고 오류, CUE가 정정** |

**결론**: 두 후보 질문 모두 CW-04 §3.1 조건(route=hybrid, fixture가
실제 candidate pool에 등장)을 충족한다. C1의 RPV-06b "미등장" 보고는
사실과 반대였으며, CUE의 직접 재현으로 정정됐다 — 이 결과(rank 6 /
rank 8, raw 스코어 포함)를 산출물 9의 최종 확정본으로 채택한다.

### RPV-06a/06b 확정 질문 (산출물 9 최종)

- **RPV-06a**: "포도나무와 가지의 비유에서 열매를 맺기 위해 주님 안에
  거한다는 의미를 설명해 주세요" — route=hybrid, fixture A
  (`TSU-JHN-6f323b08ce388551d2fa772c756a828e_chunk_00003`) rank 6
- **RPV-06b**: "성령께서 교회에 다양한 은사를 주신다는 관점에서 은사의
  종류와 목적을 정리해 주세요" — route=hybrid, fixture B
  (`TSU-UNK-5ce2824e947da15da8893fbb45c07239_chunk_00002`) rank 8

### C1 보고 정확성 — 반복 기록

이번 세션에서 C1의 실행 결과 보고가 CUE의 직접 재현과 불일치한 사례가
누적됐다(CW-03 완료 보고 허위, RPV-05 질의 치환, Gate 1 줄번호 오류,
이번 RPV-06b "미등장" 오보). CW-03/CW-04 C1 보고 표준(§10)의
"서술적 결론 ≠ evidence" 원칙이 계속 유효함을 재확인 — CUE의 독립
재현 없이는 C1 단독 보고를 acceptance evidence로 채택하지 않는다는
운영 원칙이 이번에도 정당화됐다.

## 11. Gate 2A 최종 상태 — 전체 종료

```text
CW-04 Gate 2A
  산출물 1   [✓ CUE]
  산출물 2   [✓ CUE]
  산출물 3   [✓ CUE]
  산출물 4   [✓ CUE — design candidate]
  산출물 5   [✓ CUE — design candidate]
  산출물 6   [✓ CUE]
  산출물 7   [✓ CUE — proposal]
  산출물 8   [✓ CUE]
  산출물 9   [✓ CUE — CUE 재현으로 확정, RPV-06a rank6/RPV-06b rank8]
  산출물 10  [✓ CUE — subject to Q8/architecture decision]

Gate 2A final decision     [✓ CUE — 전체 종료]
Gate 2B                    [NOT AUTHORIZED]
C1                         [STOP]
CUE                        [STOP — HQ Architecture Decision 대기]
```

**다음 단계**: HQ Architecture Decision — Q8(SSOT), Q1-Q6(D1-D6) 설계
질문에 대한 정책 결정. 산출물 10의 "quota-based two-stage retrieval"을
포함한 특정 구현 방식은 이 Architecture Decision에서 확정되기 전까지
승인된 것이 아니다. Architecture Decision 승인 후에만 별도 Gate 2B
(구현 재승인)로 진행한다.
