# GS-FINAL-RPV 최종 보고서

- **상태**: `[✓ HQ]` — 2026-09-29 최종 승인, 여정 종결
- **작성**: CUE
- **범위**: Grounded Synthesis(GS) 프로젝트의 Real Pastoral Validation
  (RPV) 전체 여정 — PR #90 병합부터 GS-FINAL-RPV 최종 승인까지
- **상세 근거 문서**(본 보고서는 이들의 요약·통합본):
  [GS-FINAL-RPV-TEST-SET-DRAFT.md](GS-FINAL-RPV-TEST-SET-DRAFT.md),
  [GS-FINAL-RPV-C03-ARCHITECTURE-DECISION-BRIEF.md](GS-FINAL-RPV-C03-ARCHITECTURE-DECISION-BRIEF.md),
  [GS-FINAL-RPV-CW01-CW02-SCOPE.md](GS-FINAL-RPV-CW01-CW02-SCOPE.md),
  [GS-FINAL-RPV-CW03-SCOPE.md](GS-FINAL-RPV-CW03-SCOPE.md),
  [GS-FINAL-RPV-CW04-SCOPE.md](GS-FINAL-RPV-CW04-SCOPE.md),
  [GS-FINAL-RPV-CW04-GATE2A-SCOPE.md](GS-FINAL-RPV-CW04-GATE2A-SCOPE.md),
  [GS-FINAL-RPV-CW04-ARCHITECTURE-DECISION-BRIEF.md](GS-FINAL-RPV-CW04-ARCHITECTURE-DECISION-BRIEF.md),
  [GS-FINAL-RPV-CW04-GATE2B-IMPLEMENTATION-BRIEF.md](GS-FINAL-RPV-CW04-GATE2B-IMPLEMENTATION-BRIEF.md)

---

## 1. 요약

Grounded Synthesis(GS, P03A-P12)는 실제 사용자 질문에 대해 실측
파이프라인(HybridRetriever → EvidencePool → SynthesisInput → 실제
Ollama LLM → Claim 추출 → GroundedAnswer → 인용 검증)으로 12개
목회/신학 질문을 실행·검증했다. 진행 중 3건의 실제 결함(C-01, C-02,
C-03)과 2건의 architecture gap(RPV-05 evidence 소실, RPV-06
corpus-role 부재)을 발견했고, 각각 corrective WO(CW-01~CW-04)로
근본 원인을 추적·수정·재검증했다. 모든 corrective work는 CUE의
read-only 독립 검증(baseline 직접 재실행, C1 보고 그대로 신뢰 안 함)
을 거쳤으며, 이 과정에서 C1의 보고 오류가 5회 이상 발견·정정됐다.
**최종적으로 12개 케이스 전부 통과, GS-FINAL-RPV는 HQ 최종 승인으로
종결됐다.**

---

## 2. 최종 케이스 집계 (12개, acceptance criterion 10-20개 충족)

| 카테고리 | RPV-ID | 최종 상태 |
|---|---|---|
| Biblical Text | 01a, 01b | `[✓]` 9-case regression 통과 |
| Exegetical | 02 | `[✓]` 9-case regression 통과 |
| Theological | 03a, 03b | `[✓]` 9-case regression 통과 |
| Historical/Background | 04 | `[✓]` 9-case regression 통과 |
| Sermon Research | 07 | `[✓]` 9-case regression 통과 |
| Insufficient Evidence | 08a, 08b | `[✓]` 9-case regression 통과(통제 질의 정상 insufficient_evidence) |
| **Multi-source** | **RPV-05** | `[✓ HQ]` — 로마서 3장/야고보서 2장, CW-03 적용 후 야고보서 2:21(Fuller Vol.8) 최종 답변 반영 확인 |
| **Personal + Default Corpus** | **RPV-06a** | `[✓]` — CW-04 적용 후 route=hybrid 유효 질문으로 재선정, fixture rank 6·corpus_type=personal 확인 |
| **Personal + Default Corpus** | **RPV-06b** | `[✓]` — CW-04 적용 후 fixture rank 8·corpus_type=personal 확인 |

---

## 3. 전체 여정

```
GS-00 ~ GS-P12 (Grounded Synthesis 기술 구현)          [✓ HQ]
    ↓
Current-State Reconciliation — 전부 PR #90 미병합 발견
    ↓
PR #90 merge (c8f7e41a)                                 [✓ HQ]
    ↓
GS-FINAL-RPV 정의 (13→11→12개 질문, 격리 워크트리 프로토콜 확정)
    ↓
RPV preflight 1차(c2cdf147, G0 오염) → 무효 판정 → 격리 워크트리
(/Users/David/DBMA-rpv-c8f7e41a) 재구축
    ↓
9-case real RPV 1차 실행 → 결함 발견: C-01/C-02/C-03              [HOLD]
    ↓
CW-01(claim parsing 프롬프트 지시문 혼입)/
CW-02(evidence_id marker 사용자 노출)                    [✓ HQ]
    ↓
9-case 2차 regression 전부 GREEN                          [✓ HQ]
    ↓
RPV-05(Multi-source) 최초 실행 → Fuller Vol.8 인용은 되나
답변에 미반영 → HOLD → 근본원인 추적(read-only)            [✓ CUE]
    ↓
CW-03(parse_llm_claims() paragraph-scope binding 결함 수정)  [✓ HQ]
    ↓
RPV-05 재검증 — 야고보서 2:21 내용이 최종 답변에 정상 반영    [✓ HQ]
    ↓
RPV-06(Personal+Default) 최초 실행 → HOLD/OBSERVATION
(fixture 미검색 · corpus-role signal 부재)
    ↓
CW-04:
  Gate 1  — 원인 read-only 조사(corpus_type 정의만 있고 retrieval
            lineage에 미연결 확인, G0 위반 1회 발생·재발방지 조치)  [✓ HQ]
  Gate 2A — RPV-06a/06b 유효 fixture/query 재설계 + 설계 옵션 비교
            (산출물 9는 C1 오보고 2회 → CUE 재현으로 정정)          [✓ HQ]
  Architecture Decision — AD-01(Membership SSOT)/AD-02(Retrieval
            Role Policy), CUE 권고안(HQ 명시적 예외 승인) → HQ 승인  [✓ HQ]
  Gate 2B — 구현(commit 4192d94), CUE 독립 검증 — 세션 최초로
            C1 보고 전 항목 baseline과 완전 일치                    [✓ CUE]
    ↓
RPV-06a/06b 재검증 — rank 불변 + corpus_type=personal 확인          [✓]
    ↓
GS-FINAL-RPV                                            [✓ HQ 최종 승인]
```

---

## 4. 발견된 결함과 corrective work

| ID | 결함 | 위치 | 수정 | 검증 |
|---|---|---|---|---|
| C-01 | LLM이 프롬프트 지시문을 반복한 줄이 Claim으로 오추출 | `scripts/grounded_synthesis_integration_demo.py::parse_llm_claims()` | CW-01 — `_is_prompt_echo()` 추가 | CUE 라이브 재실행(RPV-03a/04/03b) GREEN |
| C-02 | `[evidence_id: ...]` 내부 마커가 사용자 노출 텍스트에 잔존 | 동일 파일 | CW-02 — `_clean_evidence_markers()` 추가 | 동일 |
| C-03 | `grounded` 상태가 구조적 검증만 의미, 의미적 지지 여부는 별도(ADR-036 B6 원 설계 재확인) | `core/grounded_answer.py`, `core/grounded_citation.py` | 정책 결정 사항으로 분류, corrective WO 대상 아님 | [C03 Architecture Decision Brief](GS-FINAL-RPV-C03-ARCHITECTURE-DECISION-BRIEF.md) — 4개 정책 옵션 제시, HQ가 "구조적/의미적 검증 분리 유지" 결정 |
| RPV-05 evidence 소실 | claim_text는 첫 문단만 채택(local scope), evidence_id는 전체 출력 전역 스캔(global scope) — 스코프 불일치로 다른 문단의 evidence가 잘못 바인딩 | `parse_llm_claims()`(190-266번째 줄) | CW-03 — 문단(paragraph) 단위 파싱으로 재작성, binding scope를 synthesis unit 기준으로 일치 | CUE가 실제 캡처된 raw LLM output으로 unit-level 재현 + 실제 RPV-05 질문 전체 파이프라인 라이브 재실행, 4개 claim 각각 정확히 1개 evidence_id에만 대응 확인 |
| RPV-06 corpus-role 부재 | `Evidence.corpus_type`은 정의만 있고 모든 adapter가 항상 `"default"`로 하드코딩. `RankedCandidate`/`CandidateRef`에는 필드 자체가 없어 retrieval lineage 전체에 corpus role이 전달 안 됨 | `core/evidence_adapters/tsu_adapter.py`, `core/retrieval.py`, `core/candidate_generator.py` | CW-04 — AD-01(registry 명시적 membership 필드) + AD-02(ranking 무변경, corpus role은 metadata로만 전달) | CUE가 구현 전/후 rank·score 완전 동일 확인(ranking 미변경), corpus_type이 default→personal로 정확히 전환 확인 |

---

## 5. Architecture Decision 요약

### C-03 — "grounded" 상태의 의미 (정책 결정, 코드 변경 없음)

ADR-036 B6이 "결정적 검사"(P7, 자동)와 "의미 지지 판정"(사람/CUE
표본 검토)을 이미 분리해 뒀음을 확인. RPV-02가 이 설계의 실사용
함의를 처음 드러낸 것 — 버그가 아니라 원래 설계의 자연스러운 결과.
CUE는 4개 정책 옵션(A~D)을 제시했으나 권고하지 않았고, HQ가 "구조적
검증과 의미적 지지 판정을 분리 유지"로 결정, corrective WO 대상에서
제외했다.

### AD-01/AD-02 (CW-04) — Personal/Default Corpus Role

| 결정 | 채택안 | 핵심 근거 |
|---|---|---|
| AD-01 Membership SSOT | **Option C** — 업로드/등록 시점 명시적 membership 필드(registry `documents.json`, 기존 `document_id` 연결 재사용) | 우선순위 원칙(①기존 Architecture 보존, ②Membership authority > ⑥변경범위최소화) 적용 시, 경로 패턴 추론(옵션 A)은 암묵적이라 authority 미충족, 기존 Registry 전용(옵션 B)은 원 설계 의도(sample curation)를 왜곡할 위험(Q8-4 "불확실") |
| AD-02 Retrieval Role Policy | **Option D** — Relevance retrieval + role-aware merge, **ranking 자체는 변경하지 않음** | 옵션 A(score boost)/B(fixed quota)는 relevance integrity(③)를 직접 위반할 위험으로 우선순위상 배제. 옵션 C(two-stage retrieval)도 목표는 달성하나 `HybridRetriever.retrieve()` 재구조화가 필요해 ①에서 D보다 불리 |

이 결정은 CUE가 Decision Matrix(사실/근거/리스크, 점수화 없음)를
근거로 권고안을 작성하고(HQ의 명시적 예외 요청에 의함), HQ가 검토 후
제한 조건을 붙여 승인하는 절차를 거쳤다.

**명시적으로 채택하지 않은 것들**(AD-02 승인 시 HQ가 재확인):
Personal score boost, Personal rank-1 강제, 고정 quota(4:6 등),
Default corpus 제거, 신규 retrieval engine, GS 내부에서의 corpus
분류 — 전부 배제.

---

## 6. 검증 방법론 — CUE 독립 검증 원칙

세션 전체에서 다음 원칙이 반복 적용·강화됐다:

1. **C1(구현 담당)의 완료 보고를 그대로 신뢰하지 않는다** — 매번
   baseline에서 직접 재실행/재현해 독립 확인.
2. **G0(worktree identity) 확인은 read-only 조사에도 예외 없다** —
   Gate 1에서 C1이 "read-only니까 괜찮다"며 G0 불일치를 무시하고
   진행해 실제 코드 인용 오류(줄번호 96줄 차이)로 이어진 사례 발생,
   이후 exception 없음으로 원칙 강화.
3. **서술적 결론은 evidence가 아니다** — "정상 동작함", "테스트
   통과함" 같은 문장이 아니라 raw 실행 결과·코드 인용(파일:줄번호)을
   요구.
4. **질문/fixture는 임의 변경 금지** — CW-03 Case E에서 C1이 구
   RPV-05a(산상수훈) 질문으로 치환해 보고한 사례 발견 후 명문화.

이 원칙들 덕분에 세션 중 발견·정정된 C1 보고 오류: (1) CW-03 1차
완료 보고 — 실제로는 코드 미변경(잘못된 디렉터리에서 작업), (2)
CW-03 Case E — 질문 치환, (3) Gate 1 — 코드 인용 줄번호 오류, (4)
Gate 2A 산출물 9 1차 — RPV-06b fixture 미등장 오보고(실제로는 등장),
(5) Gate 2A G0 확인 출력 생략. **Gate 2B 구현 보고는 세션 중 처음으로
전 항목이 CUE 독립 재현과 완전히 일치했다.**

---

## 7. 알려진 잔여 사항 (GS-FINAL-RPV 범위 밖)

- **bible-route bypass**: scripture reference를 포함한 질의는
  `query_planner.classify()`가 `route="bible"`로 분류해
  `CandidateGenerator`(Default corpus 포함)를 완전히 우회한다. 이는
  기존 아키텍처 특성이며 이번 corpus_membership 도입과는 별개 이슈로
  남아있다.
- **Registry backfill 미포함**: CW-04의 `corpus_membership` 필드는
  신규 업로드/RPV fixture에만 명시적으로 적용됐다. 기존 대량 코퍼스에
  대한 일괄 재분류(backfill)는 이번 범위에 포함되지 않았다(Gate 2B
  Implementation Brief §1.3에서 명시적으로 배제).
- **citation span_not_found**: LLM의 evidence paraphrase로 인한 exact
  substring 불일치는 C-03에서 이미 문서화된 한계(옵션 D — 사람/CUE
  표본 검토 정례화)이며, 아직 제품 운영에 정례화되지 않은 상태로
  남아있다.

---

## 8. 최종 상태

```
GS technical implementation (P03A-P12)   [✓ HQ]
CW-01/CW-02                              [✓ HQ]
CW-03                                    [✓ HQ]
RPV-05                                   [✓ HQ]
CW-04 (Gate1/2A/AD/Gate2B)               [✓ HQ]
RPV-06a                                  [✓]
RPV-06b                                  [✓]
GS-FINAL-RPV                             [✓ HQ] — 2026-09-29 최종 승인
```

C1/CUE 모두 STOP. GS-FINAL-RPV는 이 시점 기준으로 종결됐으며, 향후
재개는 새로운 HQ 지시(신규 corrective WO, RPV 확장, backfill 작업
등)를 통해서만 이루어진다.
