# NAE PHASE 1 — ADR-029 GATE RECONCILIATION & TRUE BLOCKER AUDIT

**작업명**: ADR-029 Gate Reconciliation & True Blocker Audit
**작성자**: CUE (Architecture / Governance / Independent Verification)
**작성일**: 2026-08-26
**Governing Authority**: `docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md` (ACCEPTED, 2026-08-25)
**Mode**: READ-ONLY RECONCILIATION — 이 문서는 어떤 해결책도 구현하지 않는다.

---

## 1. Executive Summary

이 감사는 ADR-029 원문을 1차 근거로 삼아 PHASE 1의 공식 completion criteria를
독립적으로 재추출하고, 기존 CUE/C1 문서 체인 전체(6개 문서, 2026-08-25~26)를
재조정(reconcile)한다. 결론은 **기존 가장 최신 CUE governance review
(`CUE-ADR029-PHASE1-GATE-INDEPENDENT-REVIEW.md`)의 판정과 실질적으로 일치**하며,
이번 감사는 그 판정을 맹신하지 않고 ADR-029 원문에서 독립적으로 재도출했다.

### Q1 — PHASE 1 공식 completion criteria

> **VERIFIED**. ADR-029 §3: `Gate: canonical term validation PASS`. §4.4가 그
> "canonical term"의 정의를 고정한다: `term_id, english_term, korean_term,
> aliases, definition, source, provenance, confidence` 스키마를 가진 레코드가
> §4.3 우선순위에 따라 검증 가능한 authoritative source를 가져야 한다.

### Q2 — Korean↔English terminology authority가 PHASE 1의 필수 Gate인가

> **VERIFIED (체인적으로)**. ADR-029는 "Korean 소스를 반드시 획득하라"고 문자
> 그대로 명령하지 않는다. 그러나 §4.4 스키마는 모든 레코드에 `korean_term`과
> `english_term`을 **동시에** 요구하고, §4.2는 "AI가 임의로 번역한 용어를
> authoritative terminology로 사용하지 않는다"고 명시적으로 금지한다. 따라서 최소
> 1건의 canonical term이라도 성립하려면 §4.3 우선순위(1: 한국어 사전, 2: 한국어
> 학술 용례, 3: 영어 원문 cross-reference, 4: AI translation 보조)에 따라 검증된
> authoritative source가 있어야 한다. 현재 그런 source가 하나도 없다(Korean 측)
> — 이 사실이 Gate를 막는다. "Korean source 획득 자체가 명시적 mandatory
> requirement"라는 문장은 ADR-029에 **문자 그대로는 없다** — 이는 Gate 요구사항의
> **논리적 귀결**이며, 이 구분을 §7에서 명확히 표시한다.

### Q3 — English Baptist source acquisition(EN-BAP)이 PHASE 1 필수 조건인가

> **NOT VERIFIED as core requirement — PARALLEL TRACK / PIPELINE VALIDATION로
> 판정**. ADR-029 §3/§4 어디에도 "N개의 영어 신학사전을 획득하라"는 요구사항이
> 없다. EN-BAP 후보군은 ADR-029 자체가 아니라 CUE의 `PHASE1-AUTHORITATIVE-
> SOURCE-INVENTORY.md`(CUE의 파생 조사 문서)에서 §4.3 priority-3("영어 원문과
> 한국어 용어의 cross-reference") 후보 자료로 도입되었다. 그러나 EN-BAP-001/002
> 실제 pilot 작업(C1)은 Smith와 동일한 **reference corpus 전체 ingestion**
> 방식을 취했다 — 이는 §4.4가 명시적으로 분리하라고 요구하는 "Terminology
> layer"가 아니라 "Dictionary/Commentary = research evidence layer"에 해당한다.
> 따라서 EN-BAP 작업은 PHASE 0(Smith)의 연장선상에 있는 **research corpus
> expansion / pipeline validation**이지, PHASE 1 core requirement가 아니다.

### Q4 — TRUE BLOCKER와 다음 authorized action

> **TRUE BLOCKER**: ADR-029 §4.4 스키마를 만족하는 canonical term 레코드가
> **0건** 존재한다. 그 레코드를 만들 수 있는 §4.3 우선순위 1/2 authoritative
> Korean source도 **0건 verified/acquired**다 (`PHASE1-KOREAN-AUTHORITY-
> RESOLUTION.md`, `PHASE1-KOREAN-AUTHORITY-ACQUISITION.md`). 이는 기존
> `CUE-ADR029-PHASE1-GATE-INDEPENDENT-REVIEW.md`의 결론과 **일치**하며, 이번
> 감사는 이를 독립적으로 재확인했다.
>
> **NEXT AUTHORIZED ACTION**: `WAIT FOR HUMAN ACQUISITION` (최소 1건의
> authoritative Korean theological terminology source의 legitimate acquisition)
> — 자동화된 학술 DB 접근 경로가 이미 전부 실패로 기록되어 있으므로(§8, §9
> 아래) 이는 CUE/C1이 반복 조사로 풀 수 있는 문제가 아니다. 부차적으로,
> EN-BAP 트랙을 병행 계속할지 여부는 `REQUEST HQ DECISION` 대상이다(§18).

---

## 2. Investigation Scope

### IN SCOPE
- ADR-029 원문 재분석 (1차 근거)
- PHASE 1 completion criteria 재추출
- Korean/English source track의 ADR-029상 역할 재판정
- Smith baseline의 정확한 역할 재판정
- EN-BAP-001/002의 Gate 매핑
- 기존 6개 CUE/C1 문서 간 reconciliation
- Contradiction audit
- True blocker 판정
- Next authorized action 제안 (구현 아님)

### OUT OF SCOPE (이번 task에서 절대 수행하지 않음)
- Code/architecture/corpus/embedding/Qdrant/manifest mutation
- Source acquisition
- Git add/commit
- 발견된 문제의 직접 수정

---

## 3. Governing Documents

| # | Document | 작성자/일 | 역할 |
|---|----------|-----------|------|
| 1 | `docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md` | HQ 승인 2026-08-25 | **1차 근거(primary source)** — 이 문서가 모든 판정의 기준 |
| 2 | `docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-INDEPENDENT-VERIFICATION.md` | CUE, 2026-08-25 | 1차 검증 — ADR DRAFT 상태 지적, C1 사실관계 확인 |
| 3 | `docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-REVALIDATION.md` | CUE, 2026-08-25 | 재검증 — "NOT READY/GOVERNANCE BLOCKED", THEME_KEYWORDS 등을 PHASE1 blocker로 오분류(Interpretation A) |
| 4 | `docs/agents/cue/CUE-ADR029-PHASE1-GATE-INDEPENDENT-REVIEW.md` | CUE, 2026-08-25 | **문서 #3의 scope 오류를 정정**(Interpretation B) — 진짜 PHASE1 blocker = terminology dictionary corpus 부재 |
| 5 | `docs/agents/cue/PHASE1-KOREAN-AUTHORITY-RESOLUTION.md` | CUE, 2026-08-25 | Korean 후보 6개 조사 — 0건 fully verified |
| 6 | `docs/agents/cue/PHASE1-KOREAN-AUTHORITY-ACQUISITION.md` | C1, 2026-08-26 | Korean acquisition 시도 — 0건 획득 (모든 외부 DB 접근 실패) |
| 7 | `docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-INVENTORY.md` / `-VALIDATION.md` | CUE, 2026-08-25 | EN-BAP 20→9 후보 선정 (§4.3 priority-3 cross-reference용으로 도입) |
| 8 | `docs/agents/cue/PHASE1-EN-BAP-001-PILOT-ACQUISITION.md` | C1, 2026-08-26 | EN-BAP-001 = ACQUISITION BLOCKED — PIPELINE READY |
| 9 | `docs/agents/cue/CUE-PHASE1-NEXT-CANDIDATE-EN-BAP-002-READINESS-AUDIT.md` | CUE, 2026-08-26 (이전 세션) | EN-BAP-002 동일 결론 + 이번 감사가 형식화하는 governance tension을 최초 제기 |
| 10 | `docs/agents/cue/PHASE1-SMITH-BASELINE-APPLICATION-GATE.md` | C1, 2026-08-26 | Smith 실제 질문 테스트 7/7 PASS — PHASE0→1 전환의 기술적 precondition 충족 근거 |
| 11 | `docs/agents/cue/PHASE1-ENGLISH-BAP-PIPELINE-AUDIT.md`, `-EMBEDDING-READINESS.md` | C1, 2026-08-26 | EN-BAP 파이프라인은 architecture 변경 없이 재사용 가능함을 확인 |
| 12 | `resources/theological_sources/baptist/source_candidates.csv` | (더 이전, committed) | ADR-029와 **무관한 별도 트랙**(Baptist 신조/역사 코퍼스) — §13에서 별도로 다룸 |

---

## 4. Worktree / Repository State

```
현재 audit worktree: claude/nae-phase1-candidate-discovery-cb6f51
                      (.claude/worktrees/relaxed-shamir-95cc3d, base: main)
                      → NAE 관련 파일 0개 (main은 dev/dbma-engine과 2026-07-20 이후 미병합)

실제 작업 위치:        /Users/David/DBMA (main worktree, branch: dev/dbma-engine,
                      HEAD 090103c, 2026-08-25 10:52:15 -0500)
```

`dev/dbma-engine` worktree의 `git status --short` (이번 감사 시작 시점, 재확인):

```
 M NAE/smith_activation.py
 M docs/STATE.md
 D test_seal_4qhgiezk/seal_test_pkg/{data,manifest,report}.*
 D test_seal_5z4ickc9/seal_test_pkg/{data,manifest,report}.*
 D test_seal_zlrrtn8n/seal_test_pkg/{data,manifest,report}.*
 M ui/pages/chat.py
?? docs/agents/cue/CUE-ADR029-PHASE1-GATE-INDEPENDENT-REVIEW.md
?? docs/agents/cue/CUE-PHASE1-NEXT-CANDIDATE-EN-BAP-002-READINESS-AUDIT.md
?? docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-INDEPENDENT-VERIFICATION.md
?? docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-REVALIDATION.md
?? docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-INVENTORY.md
?? docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-VALIDATION.md
?? docs/agents/cue/PHASE1-EN-BAP-001-PILOT-ACQUISITION.md
?? docs/agents/cue/PHASE1-ENGLISH-BAP-PIPELINE-AUDIT.md
?? docs/agents/cue/PHASE1-ENGLISH-CANONICAL-EMBEDDING-READINESS.md
?? docs/agents/cue/PHASE1-KOREAN-AUTHORITY-ACQUISITION.md
?? docs/agents/cue/PHASE1-KOREAN-AUTHORITY-RESOLUTION.md
?? docs/agents/cue/PHASE1-SMITH-BASELINE-APPLICATION-GATE.md
?? docs/agents/cue/PHASE1-SMITH-BASELINE-READINESS.md
?? docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md
```

이는 이전 세션(EN-BAP-002 audit) 종료 시점과 **동일**하다 — 이번 감사 전체가
읽기만 수행했고, 다른 세션의 `NAE/smith_activation.py` / `docs/STATE.md` /
`ui/pages/chat.py` 편집이나 `test_seal_*` 삭제에 어떤 개입도 하지 않았다.

---

## 5. ADR-029 PHASE 1 Requirements (원문 직접 추출)

| 항목 | ADR-029 원문 근거 | 값 |
|------|-------------------|-----|
| PHASE 1 목적 | §4.1 | "번역이 아니라: 권위 있는 한국어 신학 용어를 NAE가 일관되게 사용할 수 있도록 하는 것" |
| PHASE 1 scope 표제 | §3 | "Korean Theological Terminology **Corpus**" (Retrieval/Integration 아님 — §4.4의 명시적 layer 분리와 일치) |
| Gate (exit criteria) | §3 | `Gate: canonical term validation PASS` |
| Required schema | §4.4 | `term_id, english_term, korean_term, aliases, definition, source, provenance, confidence` |
| Source priority (evidence 요구사항) | §4.3 | 1. 권위 있는 한국어 신학용어사전 2. 한국어 신학 학술자료의 검증 가능한 용례 3. 영어 원문과 한국어 용어의 cross-reference 4. AI translation — auxiliary only |
| Authority validation 원칙 | §4.2 | "AI가 임의로 번역한 용어를 authoritative terminology로 사용하지 않는다" |
| Layer 분리 요구사항 | §4.4 | "Terminology = authoritative terminology layer" / "Dictionary/Commentary = research evidence layer" — "이 구분을 유지한다" |
| PHASE 0→1 진입 precondition | §3 | `[Gate: 실제 앱 + 실제 질문 테스트 PASS]` (Smith 대상) |
| PHASE 1→2 후속 분리 | §3 | PHASE 2 = "Terminology **retrieval** / Korean↔English **mapping validation**" — retrieval 통합은 별도 phase로 명시적으로 분리됨 |
| Phase transition 절차 | §10 | (1) 독립검증(CUE/C1)이 현재 phase Gate 통과 확인 (2) 사용자(HQ) 검토·승인 (3) 다음 phase acceptance criteria 명시 |
| Discover ≠ Implement 원칙 | §9, §12 | "새로운 아이디어는 기록할 수 있지만 현재 phase를 변경하지 않는다" / "발견된 개선사항은 backlog에 기록하고 현재 Gate를 완료한다" |

**결론**: PHASE 1의 completion criteria는 ADR-029 원문에서 **명시적이고 단일하게**
추출된다 — retrieval 통합, TSU 태깅, embedding, benchmark는 §3 구조상 전부
PHASE 2/3/4 소관으로 이미 분리되어 있다.

---

## 6. PHASE 1 Gate Reconstruction

```text
PHASE 1 — Korean Theological Terminology Corpus
│
├── Required Input A: 권위 있는 한국어 신학용어사전 (§4.3-1)          → REQUIRED (currently: 0 acquired)
├── Required Input B: 한국어 신학 학술자료의 검증 가능한 용례 (§4.3-2)  → REQUIRED (alternate to A; also: 0)
├── Required Input C: 영어 원문 ↔ 한국어 용어 cross-reference (§4.3-3) → OPTIONAL / SUPPORTING
│                     (A 또는 B로 확보된 한국어 후보 term이 이미 있을 때만 의미를 가짐 —
│                      단독으로는 canonical term을 생성하지 못함)
├── AI translation (§4.3-4)                                          → NOT SUFFICIENT ALONE (auxiliary only, §4.2가 명시적 금지)
│
├── Validation A: 레코드가 §4.4 스키마(8개 필드)를 만족               → REQUIRED
├── Validation B: korean_term이 §4.3 priority 순서로 검증된 출처를 가짐 → REQUIRED
├── Validation C: Terminology layer가 Dictionary/Reference layer와 분리 저장됨 → REQUIRED (design constraint, §4.4)
│
├── Required Authority: 최소 1건 이상의 canonical term이 실제로 존재하고 검증됨 → REQUIRED — 현재 0건 (UNMET)
│
├── PHASE 0 precondition (Smith App Gate PASS)                       → DEPENDENCY — 기술적으로 충족(§9), 단 HQ의 명시적 전환 승인 기록은 UNKNOWN(§13)
├── ADR-029 governance approval                                      → DEPENDENCY — RESOLVED (ACCEPTED, 2026-08-25)
│
├── Smith Bible Dictionary (PHASE 0 산출물)                          → NOT REQUIRED for PHASE 1 Gate itself (precondition만 제공, PHASE1 산출물 아님)
├── EN-BAP-001 / EN-BAP-002 acquisition                              → PARALLEL TRACK (§4.3-3 잠재적 supporting material — 현재는 cross-reference할 한국어 후보가 없어 기능적으로 미작동)
├── THEME_KEYWORDS 한국어 확장 / TSU dead field 태깅                  → NOT REQUIRED (PHASE 2+ scope, §3 구조상 명백히 분리됨)
├── BGE-M3 cross-lingual benchmark                                    → NOT REQUIRED (PHASE 4 고유 Gate, §3)
│
└── EXIT CRITERIA: "canonical term validation PASS" (§3)              → NOT MET
```

---

## 7. Korean Terminology Authority Analysis

주장: **"Korean↔English terminology authority 구축이 PHASE 1의 진짜 blocker다."**
이를 사실로 전제하지 않고 원문 대조로 검증한다.

| 질문 | 판정 | 근거 |
|------|------|------|
| ADR-029에 명시되어 있는가? | **PARTIALLY VERIFIED** | §4.3/§4.4가 "Korean 용어 출처"를 요구하지만, "Korean **source acquisition**이 필수"라는 문장 자체는 없다 — Gate("canonical term validation")와 스키마(§4.4)의 논리적 귀결로 도출됨 |
| 명시되어 있다면 mandatory인가? | **VERIFIED (귀결로서)** | §4.2("AI 임의 번역을 authoritative로 사용 금지")가 대체 경로를 봉쇄한다 — 검증된 출처 없이는 어떤 korean_term도 canonical이 될 수 없다 |
| 특정 source acquisition을 요구하는가? | **NOT VERIFIED** | 특정 title(예: "반드시 KR-TH-001을 획득하라")을 지정하지 않는다 — priority-ordered **경로**만 지정한다(§4.3) |
| term_id/korean_term/english_term 구조가 필수인가? | **VERIFIED** | §4.4 원문 그대로 명시 |
| 최소 record count가 정의되어 있는가? | **NOT VERIFIED** | ADR-029는 "몇 건 이상"을 명시하지 않는다. Gate 문구는 "canonical term validation PASS"이며, 이는 **최소 1건 이상 실존 + 검증**을 논리적 최저선으로 삼는다(0건으로는 "validation"이라는 행위 자체가 성립 불가) — 이 최저선 해석은 이번 감사의 판단이며 ADR 원문이 숫자로 못박은 것은 아니다 |
| authority source가 exit criterion과 연결되어 있는가? | **VERIFIED** | §3 Gate("canonical term validation")와 §4.4(스키마) + §4.2(authority 원칙)가 직접 연결됨 |
| 기존 CUE review 해석과 ADR-029 원문이 일치하는가? | **VERIFIED** | `CUE-ADR029-PHASE1-GATE-INDEPENDENT-REVIEW.md`의 §8 A-1 판정("terminology dictionary corpus 자체 부재가 유일한 실질적 PHASE1 blocker")은 이번 감사의 독립 재도출과 **일치한다** |

**결론**: 주장은 **VERIFIED** (스키마·원칙의 논리적 귀결로서). "Korean source
acquisition이 문자 그대로 명령되어 있다"는 더 강한 버전의 주장은 **PARTIALLY
VERIFIED**로 격하한다 — 이 구분을 명확히 유지한다(§14 Evidence Discipline 요구사항).

---

## 8. English Baptist Source Track Analysis

| 분류 | 판정 |
|------|------|
| CORE PHASE 1 REQUIREMENT | **아니다** — ADR-029 §3/§4 어디에도 EN-BAP 획득이 PHASE1 exit criterion으로 명시되지 않음 |
| PIPELINE VALIDATION | **부분적으로 그렇다** — `PHASE1-ENGLISH-BAP-PIPELINE-AUDIT.md`가 Smith 파이프라인의 source-agnostic 재사용성을 실증하는 데는 실제 가치가 있음(§4 Priority-4 기준 정당화 가능) |
| RESEARCH CORPUS EXPANSION | **주된 실질적 성격** — EN-BAP-001/002 pilot은 Smith와 동일하게 canonicalization → embedding → `nae_ref_v1` ingestion 경로를 목표로 한다. 이는 §4.4가 "Dictionary/Commentary = research evidence layer"로 분류한 것과 정확히 일치하며, "Terminology = authoritative terminology layer"가 아니다 |
| PARALLEL WORKSTREAM | **잠재적으로 그렇다, 단 현재는 비기능적** — §4.3-3(영어 원문 cross-reference)의 재료가 될 수 있으나, cross-reference할 한국어 term 후보 자체가 0건이므로 지금은 실제로 아무 Gate에도 기여하지 못한다 |

**English source acquisition이 PHASE 1 exit criterion인지 ADR-029 원문 확인**:
**NOT VERIFIED as exit criterion.** §3 Gate 문구("canonical term validation
PASS")는 "canonical term"(§4.4 스키마)에 대한 것이며, 스키마 필드 어디에도
"English reference corpus size" 또는 "English dictionary count" 항목이 없다.

---

## 9. Smith Baseline Role

| 후보 역할 | 판정 |
|-----------|------|
| PHASE 1 required source | **아니다** |
| Pipeline proof-of-concept | **그렇다 — 주 역할** |
| Ingestion baseline | **그렇다** — `NAE/pipeline/canonical`, `embed/client.py`, `reference/ingest.py`가 Smith로 처음 검증됨 |
| Reference implementation | **그렇다** — EN-BAP-001/002 readiness 판정 전체가 "Smith와 동일 pipeline 재사용 가능"이라는 비교 기준으로 사용됨 |
| Separate pilot | **그렇다** — ADR-029 §3의 `PHASE 0 (CURRENT)`로 PHASE 1과 명시적으로 분리된 별도 단계 |

**증명된 범위**: (1) archive.org 공공영역 소스의 canonicalization 파이프라인 동작,
(2) BGE-M3 English embedding 동작, (3) `nae_ref_v1` Qdrant collection과 실제
retrieval 경로가 라이브로 작동함(`PHASE1-SMITH-BASELINE-APPLICATION-GATE.md`,
7/7 실제 질문 PASS).

**증명하지 못한 범위**: (1) Korean↔English canonical term validation(§4.4)과는
전혀 무관 — Smith는 한국어 자료가 아니며 term_id/korean_term 스키마를 생성하지
않는다. (2) copyrighted source의 legitimate acquisition 절차(Smith는 public
domain이었으므로 EN-BAP류의 purchase/library-access 절차를 검증한 적이 없다).

**결론**: Smith baseline은 PHASE 1의 **필요 조건이 아니라 PHASE 0의 완결된
산출물**이며, PHASE 1 진입의 기술적 precondition(§3 arrow)만 제공한다.

---

## 10. EN-BAP-001 Gate Mapping

```text
EN-BAP-001 (The New Bible Dictionary, 3rd ed.)
→ PHASE 1 Gate ("canonical term validation PASS"): IRRELEVANT
  (레코드가 term_id/korean_term/english_term 스키마를 생성하지 않음 — 전체 텍스트를
   reference corpus로 ingestion하는 경로이지 term-pair 추출 경로가 아님)
→ PHASE 0 (Smith) 후속 reference corpus 확장: BLOCKED (raw source 미획득)
→ 잠재적 §4.3-3 cross-reference 재료: FUNCTIONALLY INERT
  (cross-reference할 한국어 term 후보가 현재 0건이므로 지금은 아무 기능도 하지 못함)
```

## 11. EN-BAP-002 Gate Mapping

```text
EN-BAP-002 (Evangelical Dictionary of Theology, 2nd ed.)
→ PHASE 1 Gate ("canonical term validation PASS"): IRRELEVANT
  (EN-BAP-001과 동일한 이유)
→ PHASE 0 후속 reference corpus 확장: BLOCKED (raw source 미획득;
   archive.org는 CDL borrow-only — corpus 추출 불가, CUE-PHASE1-NEXT-CANDIDATE-
   EN-BAP-002-READINESS-AUDIT.md §7 참고)
→ 잠재적 §4.3-3 cross-reference 재료: FUNCTIONALLY INERT (동일 이유)
```

**두 candidate 모두 PHASE 1 Gate에 대해 IRRELEVANT로 판정한다** — "acquisition이
blocked됐다"는 사실과 "PHASE 1이 blocked됐다"는 사실은 서로 다른 명제이며(§14
Evidence Discipline 요구사항과 일치), 이 두 candidate의 acquisition 여부는 PHASE 1
Gate의 충족/미충족에 어느 방향으로도 영향을 주지 않는다.

---

## 12. Existing CUE Review Reconciliation

| 문서 | 판정 | 이번 감사와의 관계 |
|------|------|---------------------|
| `CUE-PHASE1-TERMINOLOGY-DISCOVERY-INDEPENDENT-VERIFICATION.md` (2026-08-25) | CONDITIONAL | RECONCILED — ADR draft 상태 지적은 이후 ADR 승인으로 해소됨. BGE-M3 scope 오류 지적은 이번 감사와 일치 |
| `CUE-PHASE1-TERMINOLOGY-DISCOVERY-REVALIDATION.md` (2026-08-25) | NOT READY / GOVERNANCE BLOCKED, THEME_KEYWORDS·dead field를 PHASE1 blocker로 포함 | **PARTIALLY SUPERSEDED** — 이 문서 자신도 인정하듯 ADR draft 문제는 해소됨. THEME_KEYWORDS/dead field를 PHASE1 blocker로 분류한 부분은 다음 문서(#3)에 의해 이미 정정되었고, 이번 감사도 독립적으로 같은 정정에 도달한다(§6 Gate Reconstruction에서 이 항목들은 NOT REQUIRED로 판정) |
| `CUE-ADR029-PHASE1-GATE-INDEPENDENT-REVIEW.md` (2026-08-25) | Technical PHASE1 Readiness: CONDITIONAL / Governance Readiness: BLOCKED (당시 ADR DRAFT였음) | **RECONCILED, 갱신됨** — 이 문서의 핵심 결론(terminology dictionary corpus 부재가 유일한 실질 PHASE1 blocker)은 이번 감사가 독립적으로 재확인·채택한다. Governance Readiness는 ADR-029가 이후 ACCEPTED로 전환되어 더 이상 BLOCKED가 아니다(§13에서 갱신) |
| `CUE-PHASE1-NEXT-CANDIDATE-EN-BAP-002-READINESS-AUDIT.md` (2026-08-26, 직전 세션) | EN-BAP-002 = ACQUISITION BLOCKED — PIPELINE READY, §17에서 governance tension 최초 제기(해결하지 않고 flag만) | **FORMALIZED BY THIS REPORT** — 이번 감사는 그 §17의 flag를 공식적인 Gate Reconstruction(§6)과 True Blocker 판정(§15)으로 완성한다 |

**전체적으로**: 이번 감사는 기존 CUE 문서 체인과 **모순되지 않는다**. 오히려
문서 #2(REVALIDATION)의 scope 오류를 문서 #3이 이미 정정했고, 이번 감사는 그
정정된 해석(#3)을 ADR-029 원문에서 처음부터 독립적으로 재도출하여 **삼중으로
확인**한다.

---

## 13. Contradiction Audit

### 13.1 ADR-029 vs 기존 CUE review

**충돌 발견**: 없음 — 위 §12에서 정리한 대로, 시간순으로 REVALIDATION(#2)의
scope 오류를 GATE-INDEPENDENT-REVIEW(#3)가 같은 날 정정했고, 최종 상태는
ADR-029 원문과 일치한다. `ADR-029 governance approval` 상태 자체가 문서 #2/#3
작성 시점(DRAFT)과 현재 파일 상태(ACCEPTED) 사이에 **시점 차이**로 인한 표면적
불일치가 있으나, 이는 실제 모순이 아니라 **문서가 시간에 따라 갱신된 정상적
사례**다. governing hierarchy: 현재 파일 상태(ACCEPTED)가 항상 최신 authority다.

### 13.2 ADR-029 vs Korean Authority reports

충돌 없음. `PHASE1-KOREAN-AUTHORITY-RESOLUTION.md`/`-ACQUISITION.md`는 ADR-029
§4.3 priority-1/2 경로를 정확히 그 순서대로 추구했고, 결과(0건 verified/acquired)를
정직하게 기록했다. ADR-029의 요구사항과 완전히 정합적이다.

### 13.3 ADR-029 vs EN-BAP acquisition sequence

**충돌(라벨링 수준) 발견**: `PHASE1-EN-BAP-001-PILOT-ACQUISITION.md`,
`PHASE1-ENGLISH-BAP-PIPELINE-AUDIT.md`, `PHASE1-ENGLISH-CANONICAL-EMBEDDING-
READINESS.md` 세 문서 모두 제목/본문에서 **"PHASE 1"이라는 라벨을 사용**하여
EN-BAP 작업을 지칭한다. 그러나 §8/§10/§11에서 확인했듯, 이 작업의 실질(reference
corpus ingestion)은 ADR-029 §4.4가 "Dictionary/Commentary = research evidence
layer"로 명시적으로 분리해 둔 영역이며, ADR-029가 정의하는 PHASE 1 산출물
(terminology corpus)이 아니다. **이는 문서 간 사실관계의 모순이 아니라
phase-labeling 관행의 부정확성**이다 — 실제 작업 내용(Smith와 동일한 reference
corpus 확장)과 ADR-029의 PHASE 1 정의가 어긋난다.
→ governing hierarchy: ADR-029(§3/§4)가 authority다. "PHASE 1" 라벨을 붙인
C1의 문서 제목이 ADR-029의 실제 PHASE 정의를 재정의하지 않는다.
→ **HQ decision 필요 여부**: 라벨을 바로잡는 것 자체는 governance 결정이
아니라 documentation 사실 정정이므로 CUE/C1이 문서를 수정할 때 반영 가능하다
(단, 이번 task는 mutation을 금지하므로 여기서는 수정하지 않고 기록만 한다).
다만 "EN-BAP 트랙을 계속 진행할지"는 §13.4/§18에서 별도로 HQ decision 대상으로
분류한다.

### 13.4 ADR-029 vs current source inventory

`resources/theological_sources/baptist/source_candidates.csv`(P0: SLBC1689,
NHBC1833, BFM2000, PBC1742 / P1: TH1612, JS1608, AF1815)는 ADR-029보다 먼저
존재했던 **별개의, ADR-029가 전혀 참조하지 않는 Baptist 신조/역사 코퍼스
확장 트랙**이다. 이는 ADR-029와 직접 충돌하지 않지만(서로 다른 스코프), 결과적으로
NAE에는 현재 **세 개의 병행 source-acquisition 트랙**이 조율 없이 존재한다:
(1) Baptist 신조/역사(source_candidates.csv, committed, ADR-029 밖),
(2) EN-BAP 영어 참고사전(ADR-029 §4.3-3 파생, 실질은 PHASE 0 확장),
(3) Korean terminology authority(ADR-029 §4.3-1/2, 실제 PHASE 1 요구사항).
→ 이는 blocker가 아니라 **로드맵 명료성 문제**로 분류한다(§16 Non-Blockers).
→ **HQ decision 필요**: 세 트랙의 우선순위를 하나의 governing document로
통합할지 여부.

### 13.5 §10 Phase Transition 절차 준수 여부 (신규 발견)

ADR-029 §10은 phase 전환에 "(1) 독립검증 (2) **사용자(HQ) 검토·승인** (3) 다음
phase acceptance criteria 명시" 세 가지를 모두 요구한다. `PHASE1-SMITH-BASELINE-
APPLICATION-GATE.md`(2026-08-26)가 (1)을 기술적으로 충족했음을 보이지만, 이
문서 체인 전체에서 "**HQ가 PHASE 0→1 전환을 검토·승인했다**"는 별도의 명시적
기록은 **발견되지 않았다**(ADR-029 자체의 승인과는 별개의, phase-transition-
specific approval). 이는 §9 원칙("DISCOVER ≠ IMPLEMENT")에 따라 discovery
단계 작업(source inventory 등)은 사전 승인 없이도 허용되므로 실질적 위반은
아니지만, **§10이 요구하는 명시적 HQ 승인 기록의 부재는 절차적 gap으로
기록한다.**
→ 판정: **NOT VERIFIED** (HQ 승인이 없었다는 뜻이 아니라, 그 승인을 기록한
문서를 찾지 못했다는 뜻)
→ HQ decision 필요: 예 — 최소한 확인 요청 필요.

---

## 14. Current Gate Status

| Gate 요소 | 상태 | Evidence 등급 |
|-----------|------|----------------|
| ADR-029 governance approval | RESOLVED | VERIFIED (파일 헤더: ACCEPTED, 2026-08-25, Rev. Bang/HQ) |
| PHASE 0 (Smith) 기술적 Gate | PASSED | VERIFIED (7/7 실제 질문, `PHASE1-SMITH-BASELINE-APPLICATION-GATE.md`) |
| PHASE 0→1 전환의 명시적 HQ 승인 기록 | UNKNOWN | NOT VERIFIED (§13.5) |
| Terminology corpus 존재 (§4.4 스키마 레코드) | 0건 | VERIFIED (repo-wide grep, 이전 CUE review 및 이번 감사 확인) |
| Korean authoritative source 확보 | 0건 | VERIFIED (`PHASE1-KOREAN-AUTHORITY-ACQUISITION.md`) |
| EN-BAP-001/002 acquisition | 0건 (둘 다 BLOCKED) | VERIFIED |
| Pipeline(canonicalization/embedding/Qdrant) 재사용 가능성 | READY | VERIFIED (Smith로 실증) |
| **PHASE 1 exit criterion 충족 여부** | **NOT MET** | VERIFIED |

---

## 15. TRUE BLOCKER

```text
TRUE BLOCKER (ADR-029 §3 + §4.2 + §4.3 + §4.4에 근거):

ADR-029 §4.4 스키마(term_id/english_term/korean_term/aliases/definition/
source/provenance/confidence)를 만족하는 canonical term 레코드가 저장소
어디에도 0건 존재한다. 이 레코드를 정당하게 생성할 수 있는 §4.3 priority-1/2
authoritative Korean source 역시 0건 verified/acquired다
(PHASE1-KOREAN-AUTHORITY-RESOLUTION.md, PHASE1-KOREAN-AUTHORITY-ACQUISITION.md).

이는 "구현이 잘못됐다"는 실패가 아니라 "PHASE 1의 실질적 작업이 아직 착수되지
않았다"는 상태다 — 착수를 막는 기술적 장애물(코드 결함, 아키텍처 충돌)은
발견되지 않았다.
```

이 판정은 evidence 기준(§14 instruction)을 다음과 같이 만족한다:
- ADR-029가 명시적으로 요구 (§4.4 스키마 + §3 Gate 문구) — **VERIFIED**
- 현재 미충족 — **VERIFIED** (repo-wide 0건)
- "있으면 좋은 자료"가 아니라 Gate 문구 자체가 요구하는 산출물 — **VERIFIED**

---

## 16. Non-Blockers

다음은 유용하거나 후속 단계에 필요하지만, ADR-029 원문 기준으로 **PHASE 1
Gate를 막지 않는다**:

| 항목 | 근거 |
|------|------|
| EN-BAP-001 / EN-BAP-002 미획득 | §3/§4.4 — Reference corpus 확장이지 Terminology corpus 산출물이 아님 (§8, §10, §11) |
| `THEME_KEYWORDS` 한국어 미지원 | §3 — PHASE 2("Terminology retrieval") 소관, 이미 REVALIDATION 이후 GATE-INDEPENDENT-REVIEW가 정정함 |
| TSU `themes`/`doctrine_category`/`baptist_theme` dead field | 상동 — retrieval 통합 문제, PHASE 2+ |
| BGE-M3 cross-lingual benchmark | §3 — PHASE 4 고유 Gate |
| `chroma_db`(dbmar_docs collection) empty / embedding cache reconciliation mismatch | `PHASE1-ENGLISH-CANONICAL-EMBEDDING-READINESS.md`가 지적한 파이프라인 위생 문제이나, PHASE 1(Korean terminology corpus)의 스키마·검증과 무관한 별도 인프라 항목 |
| `crosswalk.yaml`을 terminology 구조로 오분류했던 관행 | 이미 이전 CUE 문서에서 문서 식별자 매핑으로 재분류됨(용어 매핑 아님) — 향후 재발 방지용 기록일 뿐 |
| Baptist 신조/역사 코퍼스 트랙(source_candidates.csv) | ADR-029 범위 밖의 별도 트랙 — PHASE1 Gate와 무관 |

---

## 17. Required Dependencies

PHASE 1 Gate가 열리기 위한 최소 의존성 체인:

```
[하나 이상의] §4.3 priority-1 또는 priority-2 Korean authoritative source
  → legitimate acquisition (구매/도서관 접근/기관 협조 등, human-driven)
      ↓
  실제 terminology entry 확인 (제목만으로 커버리지 추정 금지 — 기존 CUE
  Korean Authority Resolution 문서의 원칙 §6 재확인)
      ↓
  §4.4 스키마로 최소 1건 이상의 canonical term 기록
      ↓
  §4.3 우선순위에 따른 출처 검증 ("canonical term validation")
      ↓
  PHASE 1 EXIT CRITERIA 충족
```

EN-BAP 트랙은 이 체인의 필수 노드가 **아니다** — §4.3-3의 optional 보조
경로로만 결합 가능하며, 그마저도 위 체인의 한국어 후보가 먼저 존재해야
의미가 생긴다.

---

## 18. Next Authorized Action

CUE는 정책적 선택을 하지 않는다(§17 governing principle). 아래는 evidence가
가리키는 **선택지**이며, 최종 결정은 HQ의 몫이다.

### 주 권고 (TRUE BLOCKER에 대한 직접 대응)

```
WAIT FOR HUMAN ACQUISITION
```

근거: 자동화 가능한 모든 경로(NLK API, RISS, DBpia, KISS, WorldCat, Google
Scholar, Internet Archive, 출판사 웹사이트 직접 접근)가 이미
`PHASE1-KOREAN-AUTHORITY-ACQUISITION.md`에서 시도되고 전부 실패로 기록되었다.
반복 조사는 새로운 evidence를 만들지 못한다. §4.3 priority-1 authoritative
Korean theological dictionary의 legitimate acquisition은 사람이 개입해야
하는 행위(구매, 도서관 방문, 출판사 직접 문의, 상호대차)다.

### 부차 권고 (§13.3 governance tension에 대한 대응)

```
REQUEST HQ DECISION — EN-BAP 트랙(EN-BAP-001/002 및 향후 후보)을
"PHASE 1 필수 조건"이 아닌 "PHASE 0 연장선의 병행 research-corpus-expansion
트랙"으로 공식 재라벨링할지, 아니면 Korean authority 확보가 완료될 때까지
일시 보류할지.
```

근거: ADR-029는 이를 금지하지도 요구하지도 않는다(§8) — 순수한 우선순위
배분 결정이며 CUE의 권한 밖이다.

### 부차 권고 (§13.5 절차 gap에 대한 대응)

```
REQUEST HQ DECISION — PHASE 0(Smith)→PHASE 1 전환에 대한 §10 명시적 승인
기록이 존재하는지 확인, 없다면 사후 기록.
```

### 명시적으로 배제한 선택지와 그 이유

- `CREATE SEPARATE IMPLEMENTATION TASK` — 아직 아니다. 구현할 대상(어떤
  Korean source를 어떻게 인입할지)이 acquisition 이전에는 정의되지 않는다.
- `CONTINUE SOURCE VALIDATION` — 이미 Korean 측은 3개 문서(Resolution,
  Acquisition, 및 이전 Inventory/Validation)로 충분히 반복됐고 추가 조사가
  새 evidence를 만들 가능성은 낮다(모든 자동화 경로 소진).
- `REVISE GOVERNANCE DOCUMENT` — ADR-029 원문 자체는 이번 감사에서 결함이
  발견되지 않았다(§5). 라벨링 부정확성(§13.3)은 ADR 개정이 아니라 하위
  문서의 표기 정정 수준이다.
- `NO ACTION REQUIRED` — 부적절하다. True blocker가 실존하며 HQ 결정이
  필요한 두 항목이 열려 있다.

---

## 19. Mutation Audit

| Action | Performed? |
|--------|-----------|
| Code modification | NO |
| Architecture modification | NO |
| Corpus mutation | NO |
| Embedding execution | NO |
| Embedding cache mutation | NO |
| Qdrant mutation | NO (읽기 조차 이번 세션에서 재실행하지 않음 — 기존 검증된 보고서의 기록을 인용) |
| Manifest mutation | NO |
| Source acquisition | NO |
| Git add | NO |
| Git commit | NO |

**발견된 문제(§13.3 라벨링 부정확성, §13.5 절차 기록 gap)는 이번 task에서
수정하지 않았다 — 별도 implementation/documentation task 후보로만 기록한다.**

---

## 20. Git Status

이번 감사는 audit worktree(`relaxed-shamir-95cc3d`)에서 시작되어, 문서
연속성을 위해 메인 워크트리(`/Users/David/DBMA`, `dev/dbma-engine`)에 신규
파일 1개만 생성했다.

```bash
$ git status --short   # /Users/David/DBMA, 이 보고서 작성 직전
 M NAE/smith_activation.py
 M docs/STATE.md
 D test_seal_*/... (9 files, 3 세션 이전부터 존재)
 M ui/pages/chat.py
?? docs/agents/cue/{기존 13개 PHASE1/CUE 문서}
```

이번 감사가 추가하는 파일:
```
?? docs/agents/cue/CUE-PHASE1-ADR029-GATE-RECONCILIATION-TRUE-BLOCKER-AUDIT.md
```

기존 uncommitted 변경사항(다른 세션 소유) 중 어느 것도 수정/삭제하지 않았다.
Audit worktree(`relaxed-shamir-95cc3d`) 자체도 변경 없음(애초에 NAE 파일이
존재하지 않음). **Git add/commit: 수행하지 않음.**

---

## 21. Final Decision

```text
NAE PHASE 1 — GATE RECONCILIATION

PHASE 1 STATUS:
OPEN (governance-approved, technically unblocked to begin work, exit
criterion not yet met — this is "not started / in progress", not "blocked
by an unresolved defect")

ADR-029 GATE:
"canonical term validation PASS" — at least one term_id/english_term/
korean_term/aliases/definition/source/provenance/confidence record (§4.4),
sourced per §4.3 priority order (1: Korean authoritative dictionary,
2: Korean academic usage, 3: English cross-reference, 4: AI-assisted —
auxiliary only), with AI-only translation explicitly disallowed as sole
authority (§4.2).

TRUE BLOCKER:
Zero canonical term records exist anywhere in the repository, and zero
verified/acquired §4.3 priority-1/2 authoritative Korean source exists to
create one. (See §15.)

KOREAN AUTHORITY:
REQUIRED (as the logical precondition for any canonical term record to
exist — not literally spelled out as "acquire a Korean source" in ADR-029's
own words, but unavoidable given §4.2 + §4.4; see §7 for the VERIFIED vs
PARTIALLY VERIFIED distinction)

ENGLISH SOURCE ACQUISITION:
PARALLEL (EN-BAP track is legitimate pipeline-validation / research-corpus-
expansion work, structurally a continuation of PHASE 0, not a PHASE 1 exit
criterion; see §8)

EN-BAP-001:
IRRELEVANT to PHASE 1 Gate (see §10) — acquisition status separately
remains ACQUISITION BLOCKED — PIPELINE READY (unchanged from prior report)

EN-BAP-002:
IRRELEVANT to PHASE 1 Gate (see §11) — acquisition status separately
remains ACQUISITION BLOCKED — PIPELINE READY (unchanged from prior report)

NEXT AUTHORIZED ACTION:
WAIT FOR HUMAN ACQUISITION of at least one §4.3 priority-1/2 authoritative
Korean theological terminology source (all automated acquisition routes
already exhausted and failed per PHASE1-KOREAN-AUTHORITY-ACQUISITION.md).
Two secondary items require REQUEST HQ DECISION (EN-BAP track prioritization,
§13.3; PHASE 0→1 transition approval record, §13.5) — see §18.

PRODUCTION MUTATION:
0

CODE MUTATION:
0

GIT COMMIT:
NO
```

---

**Audit Mode**: READ-ONLY RECONCILIATION
**Mutations**: 0
**Git add/commit**: NO
**Report generated**: 2026-08-26
**Report location**: main worktree (`/Users/David/DBMA`), consistent with the
existing PHASE 1 document chain.

---

## 22. Addendum — HQ Decision (2026-08-26, post-report)

The two §18 decision items were put to HQ directly. HQ decided:

| Item | HQ Decision |
|------|-------------|
| §13.3 / §18 — Continue EN-BAP track in parallel, or pause until Korean authority resolved? | **CONTINUE IN PARALLEL**. EN-BAP acquisition/pipeline-validation work is authorized to proceed independently of the Korean authority track — it does not block, and is not blocked by, PHASE 1's actual Gate. |
| §13.3 / §18 — Relabel the mislabeled EN-BAP documents? | **YES, RELABEL**. |

### Action taken on the relabeling decision (this session, read-only-audit
scope lifted only for this specific, HQ-authorized documentation fix)

The three documents identified in §13.3 as carrying an inaccurate "PHASE 1"
label were corrected in place:

| File | Change |
|------|--------|
| `docs/agents/cue/PHASE1-EN-BAP-001-PILOT-ACQUISITION.md` | Title and `**Phase**` field changed from `PHASE 1 —` to `PHASE 0 EXTENSION —`; a RELABEL NOTE added citing this report and the HQ decision |
| `docs/agents/cue/PHASE1-ENGLISH-BAP-PIPELINE-AUDIT.md` | Same |
| `docs/agents/cue/PHASE1-ENGLISH-CANONICAL-EMBEDDING-READINESS.md` | Same |

**Filenames were deliberately left unchanged** — a physical rename would
require also editing filename cross-references in at least 5 other documents
in this shared, actively-used worktree (including files owned by other
sessions), which is a materially larger and riskier change than the "prevent
future confusion about PHASE status" goal requires. The header/title/Phase-
field correction achieves that goal at the point where the mislabeling
actually originates. If HQ specifically wants the physical filenames changed
as well, that is a separate, explicit follow-up action — not performed here.

**Verdicts/findings inside the three documents were not altered** — only the
Phase label and a short explanatory note were added. `ACQUISITION BLOCKED —
PIPELINE READY` stands for both EN-BAP-001 and EN-BAP-002, unchanged.

### Mutation Audit (this addendum only)

| Action | Performed? |
|--------|-----------|
| Code/architecture/corpus/embedding/Qdrant/manifest mutation | NO |
| Source acquisition | NO |
| Documentation correction (3 files, header/label only, HQ-authorized) | YES |
| Git add | NO |
| Git commit | NO |
