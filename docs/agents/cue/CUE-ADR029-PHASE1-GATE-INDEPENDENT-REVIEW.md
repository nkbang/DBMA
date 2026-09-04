# CUE Independent Review — ADR-029 §3 PHASE 1 Gate Interpretation

**검토 대상**: ADR-029 §3 "canonical term validation PASS"의 정확한 의미 및 PHASE 1 Gate 판정
**검토 유형**: READ-ONLY ARCHITECTURE / GOVERNANCE REVIEW (구현 없음)
**검토일**: 2026-08-25
**Governing Authority**: `docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md`
**입력 문서**: `CUE-PHASE1-TERMINOLOGY-DISCOVERY-INDEPENDENT-VERIFICATION.md`,
`CUE-PHASE1-TERMINOLOGY-DISCOVERY-REVALIDATION.md`

---

## 1. Executive Summary

이전 두 문서(CUE 독립검증, CUE 재검증)는 C1의 사실조사를 코드·실행·프로덕션 데이터로
정확히 재확인했으나, **"canonical term validation"이 실제로 요구하는 것이 무엇인지를
ADR-029 §3/§4의 Phase 경계(PHASE 1 vs PHASE 2)에 비추어 명시적으로 판정하지 않은 채**
THEME_KEYWORDS 한국어 미지원·TSU dead field 등 PHASE 2 이후 스코프의 항목들을 PHASE 1
판정에 섞어 "NOT READY / GOVERNANCE BLOCKED"라는 단일 결론으로 병합했다.

이번 검토는 ADR-029 원문을 근거로 이 혼합을 분리한다. 결론:

- **Interpretation B가 정확하다** — PHASE 1은 terminology *dictionary를 실제로 구축·검증*하는
  단계이지만, 그것을 retrieval(THEME_KEYWORDS)·TSU 태깅·Qdrant에 **통합**하는 것은
  ADR-029 §3이 명시적으로 PHASE 2("Terminology retrieval / Korean↔English mapping
  validation")로 분리해둔 별개 단계다.
- 이전 두 문서가 "PHASE 1 blocker"로 지목한 항목(THEME_KEYWORDS EN-only, TSU dead
  field, cross-lingual embedding 부재, BGE-M3 benchmark)은 **전부 PHASE 2~4 스코프이며
  PHASE 1 자체를 막지 않는다.**
- 반면 이전 두 문서가 놓친 진짜 PHASE 1 항목이 있다: **ADR-029 §4.4가 요구하는
  terminology dictionary(term_id/english_term/korean_term/aliases/definition/source/
  provenance/confidence 스키마) 자체가 저장소 어디에도 존재하지 않는다.** 이것이
  "canonical term validation"이 통과할 수 없는 유일하고 정확한 이유다 — 검증할 대상이
  아직 만들어지지 않았다.
- ADR-029는 여전히 `DRAFT`다.

**Technical PHASE 1 Readiness: CONDITIONAL**
**Governance Readiness: BLOCKED**

---

## 2. Review Scope

### 2.1 수행한 작업 (READ-ONLY)
- ADR-029 원문 재확인 (300줄 전체, 이전 검증 이후 변경 없음 확인)
- `CUE-PHASE1-TERMINOLOGY-DISCOVERY-INDEPENDENT-VERIFICATION.md` 전체 재확인
- `CUE-PHASE1-TERMINOLOGY-DISCOVERY-REVALIDATION.md` 전체 재확인
- ADR-029 §3(Fixed Pipeline), §4(PHASE 1 정의), §9(Work Priority Lock), §11(Next Steps) 재분석
- `core/tsu_builder.py`와 `NAE/pipeline/tsu/builder.py` — **두 개의 별개 TSU 빌더**가
  존재함을 확인하고 각각의 스키마 차이를 재확인 (§7.1 참고)
- 저장소 전체에서 `korean_term`/`english_term` 스키마 존재 여부 grep (terminology
  dictionary 실존 여부 확인)
- `NAE/pipeline/registration/state/source_manifest.yaml`에서 한국어 신학용어사전
  raw source 등록 여부 확인
- Qdrant 재조회(read-only GET/scroll) — 현재 `nae_tsu_v1` 접근 가능, 3319 points

### 2.2 수행하지 않은 작업 (금지 사항 준수)
- ADR-029 수정: **미수행**
- 기존 두 CUE 보고서 수정: **미수행**
- source code 수정: **미수행**
- THEME_KEYWORDS/TSU/corpus 수정: **미수행**
- Qdrant mutation: **미수행** (GET/scroll만 수행)
- embedding/benchmark 실행: **미수행**
- git add/commit: **미수행**

---

## 3. ADR-029 Current Status

```
Status: DRAFT — 사용자 승인 필요
Date: 2026-08-25
Deciders: 사용자 (HQ) 승인 필요
git 상태: untracked (??)
```

§11 Next Steps 4개 항목 중 첫 번째("이 ADR을 사용자(HQ)가 검토·승인")가 미완료로
남아있다. 이전 두 문서와 동일하게 재확인됨 — **변경 없음.**

> `ADR-029 is DRAFT and therefore not yet an authoritative approved architectural decision.`

이 사실을 그대로 기록한다. ACCEPTED로 변경하거나 승인을 대행하지 않는다.

---

## 4. PHASE 1 Purpose

ADR-029 §4.1을 원문 그대로 인용한다:

> "번역이 아니라: **권위 있는 한국어 신학 용어를 NAE가 일관되게 사용할 수 있도록 하는
> 것**이다."

이 문장 자체는 최종 목표(outcome)를 기술하지만, §3 Fixed Pipeline이 이 목표를 달성하는
경로를 **두 개의 별도 Phase**로 이미 쪼개놓았다:

```
PHASE 1: Korean Theological Terminology Corpus
    → Gate: canonical term validation PASS
PHASE 2: Terminology retrieval / Korean↔English mapping validation
    → Gate: cross-lingual mapping accuracy PASS
```

PHASE 1의 표제는 "Corpus"이지 "Retrieval"이나 "Integration"이 아니다. PHASE 2의 표제가
별도로 "retrieval / mapping validation"을 명시한다는 사실 자체가, ADR 저자가 **corpus
구축(PHASE 1)과 retrieval 통합·검증(PHASE 2)을 의도적으로 분리**했다는 가장 직접적인
근거다. 만약 PHASE 1이 이미 retrieval 통합까지 포함했다면 PHASE 2는 존재할 이유가 없다.

§4.3(우선순위: 권위있는 사전 → 학술자료 용례 → 영어원문 cross-reference → AI translation
보조)과 §4.4(스키마: term_id/english_term/korean_term/aliases/definition/source/
provenance/confidence, "Terminology = 일반 Corpus와 분리")는 전부 **데이터 큐레이션과
출처 검증**에 관한 것이지, 검색 엔진에 어떻게 연결할지에 관한 것이 아니다.

**PHASE 1의 목적을 한 문장으로 정의**:

> PHASE 1은 terminology *validation*이다 — 권위 있는 출처에서 확보한 한국어-영어
> 신학 용어 쌍을 정의된 스키마로 축적하고, 그 출처의 authoritative 여부를 검증하는
> 단계다. terminology *discovery*(이번 C1/CUE 작업)는 PHASE 1 실행 이전의 scoping
> 단계이며, terminology *implementation*(retrieval 통합, TSU 태깅, embedding)은
> PHASE 2 이후의 별도 engineering task다.

즉 §5의 4가지 선택지 중 **"discovery/validation/implementation이 서로 다른 단계로
분리되어 있다"**가 정답이다 — discovery(현재 이 작업들)는 PHASE 1 착수 전 단계,
validation(canonical term validation)은 PHASE 1 자체, implementation(retrieval
integration)은 PHASE 2다.

---

## 5. Meaning of "Canonical Term Validation PASS"

"canonical term validation"을 구성 요소로 분해한다:

- **canonical term** — §4.4 스키마를 따르는 개별 레코드(term_id, english_term,
  korean_term, aliases, definition, source, provenance, confidence)
- **validation** — §4.3 우선순위에 따라 확보된 term의 출처가 실제로 authoritative한지
  확인하는 행위 (예: "이 한국어 용어가 실제로 권위 있는 신학사전/학술자료에서 왔는가",
  "AI가 임의로 번역한 것이 아닌가" — §4.2: "AI가 임의로 번역한 용어를 authoritative
  terminology로 사용하지 않는다")

따라서 "canonical term validation PASS"는 다음을 의미한다:

> **§4.4 스키마를 따르는 terminology corpus의 각 레코드가 §4.3 우선순위에 따라
> 검증 가능한 authoritative source를 가지고 있음을 확인했다.**

이 Gate 문구 어디에도 "retrieval에서 사용 가능한가", "한국어 query로 검색되는가",
"TSU에 태깅되었는가", "embedding되었는가"라는 조건은 없다. 그런 조건은 PHASE 2 Gate
("cross-lingual mapping **accuracy**")의 영역이다 — "accuracy"라는 단어 자체가
"실제로 작동하는 시스템"을 전제하는 반면, PHASE 1의 "validation"은 "출처의 정당성"을
전제한다. 두 단어의 차이가 두 Phase의 경계와 정확히 일치한다.

---

## 6. Interpretation A vs B

| 항목 | PHASE 1 필수인가? | 근거 |
|---|---|---|
| Canonical terminology 정의(스키마) | **YES** | §4.4가 PHASE 1의 산출물 형태로 명시 |
| 한국어 terminology 목록(실제 항목, 권위 출처 기반) | **YES** | §4.1 목적 + §4.3 우선순위가 실제 데이터 확보를 요구 — 이것이 PHASE 1 산출물 자체 |
| `THEME_KEYWORDS` 한국어 구현 | **NO** | THEME_KEYWORDS는 `core/retrieval.py`의 query-side reranking 컴포넌트 — retrieval 통합은 §3에 의해 PHASE 2("Terminology retrieval") 소관 |
| TSU metadata tagging(`themes`/`doctrine_category`/`baptist_theme` 채우기) | **NO** | 상동. 게다가 §4.4가 "Terminology = 일반 Corpus와 분리"를 원칙으로 명시 — TSU(research evidence layer)에 용어를 태깅하는 것 자체가 PHASE 1이 의도한 산출물 형태와 다르다 |
| terminology dictionary 구축(데이터 축적) | **YES** | PHASE 1의 본질적 산출물 — 현재 **존재하지 않음**(§8) |
| production persistence(기존 Qdrant/TSU에 반영) | **NO** | §4.4가 별도 저장을 명시 — 기존 `nae_tsu_v1` payload에 넣는 것은 PHASE 1 요구사항이 아니며 오히려 원칙 위반. (dictionary 자체를 "어딘가에" 저장하는 것은 필요하지만, 그 저장 형태/위치는 PHASE 1 산출물 정의에 포함되며 기존 TSU/Qdrant 스키마 확장이 아니다) |
| embedding benchmark | **NO** | §3이 명시적으로 PHASE 4 Gate("Korean query → English NAC Top-5/Top-10 PASS")로 배치 |

**판정: Interpretation B가 ADR-029 문맥과 일치한다.**

Interpretation A("THEME_KEYWORDS, TSU tagging, production persistence가 이미
구현되어 있어야 PHASE 1 완료")는 PHASE 2("Terminology retrieval / Korean↔English
mapping validation")의 정의된 스코프를 PHASE 1로 끌어올리는 오류다. 이전
REVALIDATION 문서(§14.2, §15-C)가 "한국어 THEME_KEYWORDS 구현"과 "TSU dead field
태깅"을 PHASE 1을 막는 사유로 나열한 것은 **Interpretation A 방향의 판단이며, ADR
원문과 불일치한다.**

---

## 7. C1/CUE Findings Impact Analysis

| 발견사항 | 분류 | 근거 |
|---|---|---|
| ADR-029 `DRAFT` | **B. Governance Blocking** | governing document 자체가 미승인 |
| 한국어 `THEME_KEYWORDS` 0% | **C. Non-blocking Future Work** (PHASE 2) | §3: retrieval 통합은 PHASE 2 Gate("cross-lingual mapping accuracy") |
| TSU terminology dead field(`themes`/`doctrine_category`/`baptist_theme`) | **C. Non-blocking Future Work** (PHASE 2+) | 상동. 게다가 이 필드들이 채워지는 것 자체가 §4.4 분리 원칙과 맞지 않을 수 있음 — "고칠 대상"인지 자체가 재검토 필요(§10 참고) |
| `crosswalk.yaml` identity mapping(오분류) | **C. Non-blocking, 문서 정정** | 코드 문제가 아니라 이전 두 보고서의 분류 오류 — 이번 보고서로 정정됨(§4 위 두 보고서 §3.1/§4 참고) |
| Korean-derived `claim` embedding | **C. Non-blocking Future Work** (PHASE 3/4) | embedding 언어 설계는 PHASE 3(NAC) 설계 결정 사항 |
| Cross-lingual corpus embedding 부재 | **C. Non-blocking Future Work** (PHASE 3/4) | 상동 |
| BGE-M3 benchmark | **C. Non-blocking for PHASE 1 / PHASE 4 자체 Gate로는 blocking** | §3이 PHASE 4 Gate로 명시 — PHASE 1에는 영향 없음 |
| **(신규) Terminology dictionary corpus 자체 부재** | **A. PHASE 1 Blocking** | §8 참고 — 유일한 실질적 PHASE 1 blocker |

이전 두 문서가 "PHASE 1 blocker"로 지목한 항목은 전부 B 또는 C로 재분류된다. 이번
검토에서 새로 A로 분류한 항목(terminology dictionary corpus 부재)은 이전 두 문서
어디에도 명시적으로 지목되지 않았다 — 둘 다 "주변 인프라의 상태"(THEME_KEYWORDS,
TSU 필드, crosswalk)를 감사했을 뿐, "PHASE 1의 산출물 자체가 존재하는가"라는 가장
직접적인 질문은 검증하지 않았다.

---

## 8. PHASE 1 Blocking Items

### A-1. Terminology dictionary corpus가 저장소에 존재하지 않는다

**검증 방법**: 저장소 전체에서 ADR-029 §4.4 스키마 필드명(`korean_term`,
`english_term`)을 grep — `.py`/`.yaml`/`.json`/`.md` 전체 대상, ADR-029 및 이전 CUE
보고서 자체를 제외하면 **0건.**

**의미**: PHASE 1의 Gate("canonical term validation PASS")는 검증할 대상 corpus가
존재해야 성립한다. 현재 그 corpus는 스키마 정의(ADR-029 §4.4)만 있고 실제 레코드는
0건이다. 이는 "구현이 잘못됐다"는 실패가 아니라 **"PHASE 1의 실질적 작업이 아직
착수되지 않았다"**는 뜻이다.

**추가 확인**: `NAE/pipeline/registration/state/source_manifest.yaml`(raw source
registry)에서 한국어 신학용어사전/사전류 raw source 등록 여부를 확인했다 — 검색된
범위 내에서 등록된 한국어 사전 source 없음. §4.3 우선순위 1번("권위 있는 한국어
신학용어사전")의 원재료 확보 자체도 아직 이루어지지 않은 것으로 보인다(단, 이는
raw source registry만 확인한 결과이며 사용자가 별도로 물리적 사전을 보유하고 있을
가능성은 이 검토의 범위 밖이다).

**이것이 PHASE 1 Gate를 막는가?** — 예, 자명하게 막는다: 검증할 데이터가 없으면
validation을 PASS로 판정할 근거 자체가 없다. 그러나 이는 "blocker를 해소해야 하는"
문제가 아니라 "PHASE 1의 본 작업을 시작해야 하는" 상태다 — §9의 CONDITIONAL 판정
사유가 바로 이것이다.

---

## 9. Governance Blocking Items

### B-1. ADR-029가 DRAFT — 사용자(HQ) 승인 필요

§3에서 재확인. 승인 전까지 이 문서 전체(Phase 순서, Gate 정의)가 공식 governing
roadmap으로 발효되지 않는다. §10(Phase Transition Criteria)도 "독립 검증 + 사용자
승인" 두 가지를 모두 요구하므로, 검증(discovery)이 아무리 정확해도 승인 없이는
Phase transition이 성립하지 않는다.

**이 항목은 code/data 문제가 아니라 순수 governance 결정이다.** 코드 수정으로
해소되지 않는다.

---

## 10. Future Phase Backlog

PHASE 1을 막지 않으며, 각기 다른 후속 Phase에서 처리할 항목:

| 항목 | 설명 | 해당 Phase |
|---|---|---|
| 한국어 `THEME_KEYWORDS` 확장 | 현재 English-only(14 theme × 84 keyword), `BOOK_ID_TO_NAMES`와 동일한 alias-list 패턴으로 확장 가능 | PHASE 2 |
| TSU `themes`/`doctrine_category`/`baptist_theme` dead field 처리 | 채울지, 스키마에서 제거할지 결정 필요 — 단 §4.4 분리 원칙상 이 필드들이 애초에 "terminology 통합 지점"이 맞는지부터 재검토 필요 | PHASE 2 (설계 결정 선행) |
| `crosswalk.yaml` 문서 재분류 | terminology 구조 목록에서 제외, "문서 식별자 crosswalk"로 명확히 라벨링 | 문서 정정(비-blocking) |
| Embedding 언어 설계(한국어 claim vs 영어 source_text) | 현재 corpus는 한국어 `claim`만 embedding. NAC(PHASE 3) 설계 시 재검토 필요 | PHASE 3 |
| BGE-M3 cross-lingual benchmark | §3이 명시한 PHASE 4 고유 Gate("Korean query → English NAC Top-5/Top-10 PASS") | PHASE 4 |
| Taxonomy 구조 | 계층적 분류 필요성 — 현재 어떤 기능도 요구하지 않음 | NOT REQUIRED (재검토 트리거 없는 한 보류) |

---

## 11. Technical PHASE 1 Readiness

# **CONDITIONAL**

**이유**:
- PHASE 1의 실제 Gate 요구사항(§5)은 THEME_KEYWORDS·TSU 태깅·embedding과 무관하다 —
  이 판단 자체는 이전 두 문서의 결론(해당 항목들이 문제)을 정정하는 근거이며, 그
  의미에서는 **PASS 방향**이다.
- 그러나 PHASE 1의 실질적 산출물(terminology dictionary corpus, §4.4 스키마)이
  저장소에 **전혀 존재하지 않는다**(§8) — 검증 대상 자체가 없으므로 "canonical term
  validation PASS"를 선언할 근거가 없다. 이는 **FAIL도 아니고 PASS도 아닌, 착수되지
  않은 상태**다.
- 착수를 막는 기술적 장애물(코드 결함, 아키텍처 충돌, 의존성 문제)은 발견되지
  않았다 — CONDITIONAL이지 FAIL이 아닌 이유다. "조건"은 단순하다: **PHASE 1의 본
  작업(§4.3 우선순위에 따른 실제 term 확보 및 §4.4 스키마로의 기록)을 시작하면 된다.**

---

## 12. Governance Readiness

# **BLOCKED**

**Reason**: ADR-029 remains DRAFT. 사용자(HQ) 승인 없이는 §10(Phase Transition
Criteria)이 요구하는 두 조건("독립 검증 확인" + "사용자 승인") 중 후자가 충족되지
않는다. 독립 검증(discovery 정확도)은 이번 및 이전 두 문서로 충분히 확인됐으나,
승인은 CUE/C1이 대행할 수 없다.

---

## 13. Final Recommendation

1. **사용자(HQ)에게 ADR-029 승인 여부를 확인한다** — Governance Readiness의 유일한
   해소 경로다.
2. **PHASE 1 착수 시 §4.3 우선순위 1번부터 시작한다** — 권위 있는 한국어 신학용어사전
   원천 확보(raw source 등록)가 현재 확인된 범위에서 아직 없다. 이것이 실질적인
   "PHASE 1 시작점"이다.
3. **THEME_KEYWORDS/TSU dead field/embedding 언어 설계는 PHASE 1 완료 조건에서
   제외**하고 backlog(§10)로 명시적으로 재분류한다 — 이전 REVALIDATION 문서의 §14.2/
   §15-C를 그대로 실행 판단 기준으로 삼지 않는다.
4. **BGE-M3 benchmark는 PHASE 4 준비 작업으로만 다룬다** — PHASE 1/2 진행과 병행
   가능하나 PHASE 1 Gate 조건이 아니다.
5. **`crosswalk.yaml`을 terminology 구조 목록에서 제외**하도록 두 이전 보고서의
   해당 서술을 참고 시 이 문서로 정정해서 읽는다(원본 파일은 수정하지 않음).
6. PHASE 1의 실제 corpus 구축이 시작되고 최소 표본이 확보되면, CUE 또는 C1
   Forensic Auditor가 §4.3 출처 기준 충족 여부를 재검증한다.

---

## 14. Evidence / File References

| # | 출처 | 경로 | 확인 방식 |
|---|---|---|---|
| 1 | ADR-029 전문 | `docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md` | 파일 읽기(300줄), 이전 검증 이후 변경 없음 재확인 |
| 2 | CUE 1차 검증 | `docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-INDEPENDENT-VERIFICATION.md` | 전체 재확인 |
| 3 | CUE 재검증 | `docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-REVALIDATION.md` | 전체 재확인 |
| 4 | DBMA-core TSU builder | `core/tsu_builder.py:348-458` | 파일 읽기 — `themes`/`doctrine_category`/`baptist_theme`가 존재하되 항상 `[]` |
| 5 | NAE TSU builder(별개 파이프라인) | `NAE/pipeline/tsu/builder.py:104-125` | 파일 읽기 — 위 세 필드가 record dict에 **아예 없음**(두 빌더는 서로 다른 코드경로) |
| 6 | Qdrant payload whitelist | `NAE/pipeline/index/qdrant_store.py:40-88` | 파일 읽기 |
| 7 | Terminology dictionary 실존 여부 | 저장소 전체 `korean_term`/`english_term` grep | 0건(ADR-029, CUE 보고서 자체 제외) |
| 8 | Raw source 등록 현황 | `NAE/pipeline/registration/state/source_manifest.yaml` | 한국어 신학사전류 키워드 grep — 0건 |
| 9 | Qdrant 접근성 | `curl http://localhost:7333/collections/nae_tsu_v1` | read-only GET, 현재 접근 가능(3319 points) — REVALIDATION 문서 작성 시점과 상태 다를 수 있음, 참고용 기록 |

---

## 15. Files Modified

```text
New file:
  docs/agents/cue/CUE-ADR029-PHASE1-GATE-INDEPENDENT-REVIEW.md (본 문서)

Modified:
  0

Deleted:
  0
```

---

## 16. Git Status

```
$ git status --short
?? docs/agents/cue/CUE-ADR029-PHASE1-GATE-INDEPENDENT-REVIEW.md
?? docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-INDEPENDENT-VERIFICATION.md
?? docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-REVALIDATION.md
?? docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md
 M NAE/smith_activation.py
 M docs/STATE.md
 M ui/pages/chat.py
 D test_seal_4qhgiezk/... (외 test_seal 디렉터리들)

$ git diff --stat -- docs/agents/cue/CUE-ADR029-PHASE1-GATE-INDEPENDENT-REVIEW.md
(신규 파일이므로 diff 없음)
```

이번 작업이 만든 변경은 신규 파일 1개뿐이다. `NAE/smith_activation.py`, `docs/STATE.md`,
`ui/pages/chat.py`의 수정 및 `test_seal_*` 삭제는 이번 세션 이전부터 존재하던 별도
작업(다른 세션)의 uncommitted 변경이며, 이번 검토가 만들거나 건드린 것이 아니다.

**Production mutation: 0. git add/commit: 미수행.**

---

**본 검토는 여기서 종료한다. 구현은 수행하지 않았다.**
