# GS-FINAL-RPV-CW04 — Personal / Default Corpus Role Integrity

- **Status**: DRAFT — HQ 작성/개정, CUE 기록
- **Phase**: GS-FINAL-RPV corrective work
- **Precondition**: RPV-06a HOLD (invalid test condition) / RPV-06b OBSERVATION
  (priority mechanism absent) — [GS-FINAL-RPV-TEST-SET-DRAFT.md](GS-FINAL-RPV-TEST-SET-DRAFT.md)
  "RPV-06 Read-Only Validation 결과" 절 참고
- **Implementation**: NOT YET AUTHORIZED
- **C1**: STOP
- **CUE**: STOP

CUE는 이 문서 작성에 관여하지 않았다 — HQ가 직접 작성한 scope를 그대로
기록한다(CUE는 1차 초안에 대해 두 가지 보완 의견만 제시: C1 보고 표준
승계, retrieval-layer 변경 별도 재승인 게이트. 둘 다 아래 §10, §9에
반영됨).

---

## 1. 목적

Personal Corpus와 Default/Reference Corpus가 함께 검색되는 경우, 현재
retrieval scoring에는 corpus-role signal이 없어 Default 자료가 Personal
자료보다 높은 순위에 위치할 수 있다(RPV-06b 실측: Personal fixture
BM25=84.68이 Default 문서 BM25=10.97에게 final_score에서 역전당함).

CW-04는 이를 곧바로 "Personal Corpus를 항상 rank 1로 만든다"는
요구사항으로 해석하지 않는다.

```text
Personal Corpus
= 목회자가 선택하거나 소유한 연구 자료
= 해당 연구 질문에서 우선적으로 고려되어야 하는 사용자 지정 연구 맥락

Default / Reference Corpus
= 기본 제공 참고 자료
= Personal Corpus를 보완하는 자료
= Personal Corpus를 조용히 대체하거나 종속시키는 권위를 가져서는 안 됨
```

## 2. 핵심 제품 원칙

```text
Default Availability
    ≠ Default Priority
    ≠ Default Authority
```

```text
Personal selected evidence  → primary research context
Default / Reference evidence → supplemental reference context
```

단, 모든 검색에서 Personal 자료를 무조건 rank 1로 고정한다는 의미가
아니다. 관련성(relevance)과 corpus role은 서로 다른 개념으로 취급한다.

## 3. RPV-06a 테스트 조건 재정의

기존 RPV-06a는 질의에 "요한복음 15장"이 포함되어 `query_planner`가
`route=bible`로 분류 → `bible_index.lookup_scripture_ref()`만 사용,
`CandidateGenerator`/Default corpus 경쟁 경로를 완전히 우회했다(CUE
실측 확인). Bible direct lookup route 자체를 Personal-vs-Default
priority 검증에 사용하지 않는다.

### 3.1 유효한 RPV-06a 조건

- Personal Corpus fixture가 존재한다
- Default/Reference Corpus에도 관련 evidence가 존재한다
- 질문이 Personal과 Default 양쪽 모두의 검색 후보를 생성할 수 있다
- Bible direct lookup route에 의해 한 corpus가 구조적으로 배제되지 않는다
- Personal evidence와 Default evidence가 동일한 연구 질문에 실질적으로 관련된다
- Personal evidence가 사용자 지정 자료라는 corpus-role metadata를 보존한다
- 최종 candidate/evidence 결과에서 양 corpus의 provenance를 식별할 수 있다

## 4. CW-04가 답해야 할 질문 (조사·판정 단계 — 코드 변경 승인 아님)

- **Q1**: 현재 시스템에서 corpus role은 어디에서 표현되는가? (source
  metadata / TSU metadata / Personal-Default distinction / candidate
  metadata / EvidencePool / SynthesisInput / Claim-Evidence binding)
- **Q2**: corpus role이 retrieval 단계에서 보존되는가? (candidate 생성
  이후에도 Personal/Default 구분이 손실되지 않는지)
- **Q3**: 현재 scoring에 corpus-role signal이 없는 것이 의도된 것인가?
  기존 Retrieval authority 및 ADR-001과 충돌하지 않는지 확인
- **Q4**: 제품 요구사항을 어느 계층에서 보장해야 하는가? (Query
  Understanding / Retrieval / Candidate Generation / Evidence Assembly
  / Grounded Synthesis / Answer Generation — GS가 retrieval 문제를
  자체적으로 해결하는 구조가 되어서는 안 됨)
- **Q5**: corrective change가 실제로 필요한가?
  - A. Existing architecture already satisfies the product requirement
  - B. Retrieval-layer correction required
  - C. Metadata/provenance correction required
  - D. Test/fixture definition was incorrect
  - E. Architecture decision required before implementation

Q1-Q5는 조사·판정 단계이며, 이 단계의 완료 자체가 코드 변경 승인을
의미하지 않는다.

## 5. 금지된 해석

1. **Personal 무조건 rank 1** — `if personal: rank = 1` 같은 강제 순위
   정책 요구 안 함
2. **Default 자료 제거** — candidate pool에서 제거하지 않음
3. **GS에서 Retrieval 재구현** — GS가 Personal/Default ranking을 직접
   수행하도록 만들지 않음
4. **기존 scoring 임의 변경** — BM25/semantic/passage score 임의 변경
   금지
5. **corpus authority의 임의 신설** — Personal Corpus가 항상 더
   정확/권위 있다는 정책을 코드로 가정하지 않음

## 6. Baseline 보존

ADR-001(Retrieval authority), 기존 retrieval pipeline, 기존 candidate
generation architecture, TSU corpus, Qdrant, Tantivy, Default Corpus,
Personal Corpus fixture isolation, GS P03A-P12, CW-01/CW-02, CW-03,
RPV-05 — 전부 보존. "GS technical implementation = already approved"
상태를 변경하지 않는다.

## 7. Gate 0 — Worktree / Baseline Identity

```text
pwd
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
```
Expected worktree: `/Users/David/DBMA-rpv-c8f7e41a`
Expected baseline: `c8f7e41acfa0e5444d8b02ecb84da9c53a588441`
G0 불일치 시 STOP.

## 8. Gate 1 — CW-04 Investigation (현재 CW-04 승인 범위)

C1 수행 항목: (1) corpus-role 표현 위치 확인 (2) retrieval pipeline에서
role 보존 여부 확인 (3) current scoring의 실제 동작 확인 (4) ADR-001/
기존 architecture와의 관계 확인 (5) 수정 필요 계층 및 최소 수정 범위
제안 (6) RPV-06a 유효 fixture/query 제안 (7) RPV-06b 관찰 재현 조건
명시. **이 단계에서는 코드 변경을 하지 않는다.**

**Gate 1 산출물 형식**:
```text
Q1 = ...
Q2 = ...
Q3 = ...
Q4 = ...
Q5 = ...
Conclusion = A / B / C / D / E
Required change = NONE / METADATA / RETRIEVAL / OTHER
```

## 9. Gate 2 — Retrieval-Layer Re-Authorization

Q1-Q5 결론이 `Conclusion=B, Required change=RETRIEVAL`인 경우, **CW-04
Scope 승인만으로는 Retrieval 변경을 수행할 수 없다 — 별도의 HQ
Re-Authorization이 필수**다.

Gate 2에서 HQ가 별도로 결정할 사항: Retrieval-layer 변경 필요성 /
변경 대상 파일 / 변경 허용 범위 / 변경 방식 / 기존 scoring 보존 조건
/ regression 범위 / RPV-06 재검증 방법. HQ가 승인하지 않으면
`C1 = STOP`으로 종료한다. **Retrieval 변경을 자동 승인하는 것을
방지하기 위한 별도 안전장치.**

## 10. C1 보고 표준 — CW-03 승계

CW-04의 모든 C1 보고에는 CW-03에서 확정된 표준을 그대로 적용한다:

1. **Question integrity** — 실행한 질문은 canonical test question과
   정확히 일치. 축약/치환/재작성/대체 금지.
2. **Worktree identity** — `pwd` / repository root / branch(detached
   HEAD) / HEAD 명시.
3. **Execution timestamp** — 실제 실행 시각 기록.
4. **Result artifact** — 결과를 검증 가능한 artifact로 남기고 파일
   경로·identity 보고.
5. **Test question immutability** — acceptance question을 임의 변경
   금지. `canonical question ≠ C1 convenience question`인 경우 결과를
   acceptance evidence로 사용 불가.
6. **서술적 결론 ≠ evidence** — "Personal priority is fixed." /
   "Test passed." / "Retrieval is correct." 같은 문장만으로는 승인
   근거가 되지 않는다. CUE가 실제 코드/diff/artifact/실행 결과를
   독립 확인한다.

## 11. Required validation design (Gate 2 승인 후에만 수행)

- **Test A** — Personal only: 정상 검색/조립 확인
- **Test B** — Default only: 기존 검색 동작 보존 확인
- **Test C** — Personal + Default: 양쪽 evidence 모두 후보가 되는지,
  결과에 `corpus_role`/source identity/evidence identity/provenance
  보존되는지 확인
- **Test D** — Personal relevance advantage: Personal이 명백히 높은
  relevance를 가질 때 Default가 corpus role만으로 부당 대체하지 않는지
- **Test E** — Default supplementation: Personal이 불충분할 때 Default가
  정상적으로 보완되는지
- **Test F** — No silent subordination: 한쪽 존재만으로 다른 쪽을
  완전히 제거/무시하지 않는지
- **Test G** — GS boundary: GS가 retrieval/corpus ranking을 재수행하지
  않는지
- **Test H** — Regression: CW-01/CW-02/CW-03/RPV-05 regression, 기존
  retrieval tests, 기존 GS P03A-P12 tests

## 12. RPV-06 재검증 Acceptance Criteria

- **AC-01** Valid fixture — RPV-06a가 Bible direct route로 인해 한
  corpus가 구조적으로 배제되는 테스트가 아닐 것
- **AC-02** Corpus distinction — Personal/Default evidence를 결과에서
  식별 가능
- **AC-03** Personal role preserved — corpus role이 평탄화로 사라지지
  않음
- **AC-04** No Default authority escalation — Default가 단지
  Default라는 이유로 더 높은 권위를 갖도록 설계되지 않음
- **AC-05** No forced Personal rank-1 rule — 하드코딩된 강제 1위 없음
- **AC-06** Relevance preserved — 기존 relevance mechanism 불필요하게
  파괴되지 않음
- **AC-07** Supplemental Default — Default가 Personal을 보완할 수 있음
- **AC-08** GS boundary preserved — GS 내부 ranking logic으로 해결하지
  않음
- **AC-09** Regression GREEN — 기존 승인 영역 regression 전부 GREEN
- **AC-10** Actual pastoral validation — 수정 후 실제 RPV-06 질문 재실행,
  사람이 "무엇이 Personal/Default evidence인가, Personal이 실제
  반영되는가, Default가 적절히 보완하는가, 한쪽이 부당 제거되는가,
  최종 답변의 주장과 provenance가 연결되는가" 확인

## 13. CUE 독립 검증

CUE는 C1 보고서를 그대로 승인 근거로 사용하지 않는다. 최소 확인 항목:
실제 변경 파일 / 실제 diff / corpus-role metadata 흐름 / retrieval-
candidate 경계 / scoring 변경 여부 / GS boundary / RPV-06a fixture
validity / RPV-06b 재현 여부 / regression / 실제 canonical RPV-06 실행
결과. C1이 "Personal priority is fixed."라고 주장해도 그 문장 자체를
acceptance evidence로 인정하지 않는다.

## 14. Scope 제한

**14.1 현재 Gate 1에서 허용**: read-only architecture investigation,
RPV-06 fixture/query 분석, corpus-role metadata 흐름 분석, retrieval/
candidate 흐름 분석, scoring 동작 확인, validation plan 작성, CW-04
documentation.

**14.2 Gate 2 별도 승인 후에만 허용 가능**: 필요한 최소 metadata/
provenance correction, corpus-role 보존에 필요한 최소 retrieval-layer
correction, 해당 correction 검증 테스트, RPV-06 재검증.

**14.3 금지**: 신규 retrieval engine, 신규 embedding model, Qdrant 구조
변경, corpus reprocessing, TSU 재생성, 대규모 ranking rewrite, GS
architecture 변경, GS P03A-P12 재설계, Default Corpus 내용 변경,
Personal/Default corpus 물리적 병합, unrelated refactoring.

## 15. 완료 흐름

```text
CW-04 Scope
    ↓
HQ 승인
    ↓
Gate 0
    ↓
Gate 1 — Read-only Investigation
    ↓
C1 Report
    ↓
CUE Independent Verification
    ↓
┌──────────────────────────────────┐
│ Q1–Q5 conclusion                 │
│ A/C/D → RPV-06 validation path   │
│ B     → Gate 2 required          │
│ E     → Architecture Decision    │
└──────────────────────────────────┘
    ↓ [필요한 경우]
HQ Retrieval Re-Authorization (Gate 2)
    ↓
최소 corrective implementation
    ↓
C1 Report
    ↓
CUE Independent Verification
    ↓
RPV-06 Revalidation
    ↓
HQ Decision
```

## 16. 정상 종료 상태

`[✓ HQ] CW-04` + `[✓ HQ] RPV-06`, 또는 `[HOLD] Architecture Decision
Required`, 또는 (Retrieval 변경이 필요하나 HQ 재승인 미획득 시)
`[HOLD] Retrieval Re-Authorization Required`.

## 17. 현재 상태

```text
CW-04 = APPROVED (Gate 1 scope)
Gate 1 = AUTHORIZED (2026-09-28 HQ 승인)
Gate 2 = NOT AUTHORIZED
C1 = Gate 1 investigation 착수 가능 (read-only만)
CUE = C1 Gate 1 보고 대기 → 독립 검증 예정
Implementation = NOT AUTHORIZED
Retrieval-layer change = NOT AUTHORIZED
```

**2026-09-28 HQ Gate 1 착수 승인.** C1은 §7 Gate 0(G0 worktree identity
확인) 통과 후 §8 Gate 1 조사(Q1-Q5)만 수행한다 — 코드 변경 없음.
Gate 1 산출물(§8 형식)을 C1이 보고하면 CUE가 §13 기준으로 독립
검증한다. Q1-Q5 결론이 `B(Retrieval-layer correction required)`로
나오더라도 §9 Gate 2 HQ Re-Authorization 없이는 어떤 코드도 수정하지
않는다.
