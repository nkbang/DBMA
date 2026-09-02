---
title: "ADR-029: NAE Research Corpus Expansion Pipeline Lock"
category: governance
based_on:
  - docs/architecture/ADR-028-NAE-Smith-Reference-Layer.md
  - docs/NAE_SMITH_BIBLE_DICTIONARY_REGISTRATION_001.md
  - docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md
  - docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md
created: 2026-08-25
scope_modified: — (governance document, no code changes)
---

# ADR-029: NAE Research Corpus Expansion Pipeline Lock

| | |
|---|---|
| **Status** | **ACCEPTED** |
| **Date** | 2026-08-25 |
| **Approved** | 2026-08-25 |
| **Approver** | Rev. Bang / HQ |
| **Deciders** | 사용자 (HQ) |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 1. Purpose

이 문서의 목적은 NAE의 연구자료 확장 방향을 고정하여, 개발 중 새로운
자료·기능·아키텍처로 임의 이탈하지 않도록 하는 것이다.

Smith Bible Dictionary 완료 이후 다음을 고정한다:

1. **최우선 작업 순서** — Smith completion → Korean Theological Terminology → NAC → Source Control
2. **Phase Gate** — 각 phase의 검증 통과 전 다음 phase 시작 금지
3. **Terminology Corpus 분리** — 일반 RAG 자료와 authoritative terminology layer 분리
4. **NAC Pilot 우선** — 전체 임베딩 전 1권 pilot + 검증 필수
5. **Cross-lingual retrieval 검증** — BGE-M3 capability만으로 production readiness 가정 금지
6. **Library Source Control 시기** — 실제 질문·연구 workflow 관찰 후 설계

**이 순서는 별도 승인 없이 변경하지 않는다.**

---

## 2. Current Priority — PHASE 0: Smith Bible Dictionary

### 2.1 현재 상태 (2026-08-29 — CLOSED)

| 항목 | 상태 | 근거 |
|---|---|---|
| Raw source registration | **완료** (100%) | `NAE_SMITH_BIBLE_DICTIONARY_REGISTRATION_001.md` |
| 4권 PDF + djvu.xml 다운로드 | **완료** | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol{1..4}/` |
| Source manifest 등록 | **완료** | `NAE/pipeline/registration/state/source_manifest.yaml` |
| TSU Builder / Chunking / Embedding | **보류** | ADR-021 범위 밖, 후속 단계 |
| Reference 임베딩 경로 설계 | **보류** | 별도 세션 과제로 미룸 |

### 2.2 Phase 0 Closure Evidence (2026-08-29)

```text
Commit: 76308d07d0802e97b88cccde90a4a634e98107ec

Smith Activation: 14/14 PASS
Smith Retrieval: 5/5 PASS
E2E: ALL PASS
Fault Isolation: PASS
TSU Regression: 40/40 PASS

Qdrant nae_ref_v1: 34,948 points, GREEN
Production TSU: 3,319 UNCHANGED
```

**Phase 0: OPEN → CLOSED (2026-08-29)**

### 2.3 Smith activation policy (ADR-028 요약)

```text
Smith activation (conditional heuristic)
    → CUE independent verification
    → Korean activation HIGH finding recovery
    → 관련 regression
    → ADR-028 readiness
    → 실제 앱 실행
    → 실제 질문 테스트
```

**Smith가 완료되기 전에는 다음 단계의 corpus ingestion/embedding을 시작하지 않는다.**

### 2.3 Smith activation policy (ADR-028 요약)

- **권한 계층:** Scripture(1순위) > TSU theological corpus(2순위) > Smith reference(3순위, background knowledge)
- **UI 노출 금지:** Smith 결과를 별도 citation badge/card로 표시하지 않음
---

## 3. Fixed Pipeline — Smith 이후 순서

```text
PHASE 0 (CLOSED)
Smith Bible Dictionary
        ↓ [Gate: 실제 앱 + 실제 질문 테스트 PASS — 2026-08-29 CLOSED]
PHASE 1 (NEXT)
Korean Theological Terminology Corpus
        ↓ [Gate: canonical term validation PASS]
PHASE 2
Terminology retrieval / Korean↔English mapping validation
        ↓ [Gate: cross-lingual mapping accuracy PASS]
PHASE 3
NAC English Commentary — Pilot 1 volume
        ↓ [Gate: file/metadata/TSU quality audit PASS]
PHASE 4
Cross-lingual Korean→English retrieval benchmark
        ↓ [Gate: Korean query → English NAC Top-5/Top-10 PASS]
PHASE 5
NAC full set ingestion/embedding
        ↓ [Gate: full corpus regression PASS]
PHASE 6
Library Source Control / Research Scope
        ↓ [Gate: user workflow observation + design PASS]
PHASE 7
Additional commentary / theological corpus
```

**이 순서는 별도 승인 없이 변경하지 않는다.**

---

## 4. PHASE 1 — Korean Theological Terminology

### 4.1 목적

번역이 아니라:

> **권위 있는 한국어 신학 용어를 NAE가 일관되게 사용할 수 있도록 하는 것**

이다.

### 4.2 원칙

```text
English theological concept
    → Authoritative Korean terminology source
    → Canonical Korean term
    → Definition / provenance
```

AI가 임의로 번역한 용어를 authoritative terminology로 사용하지 않는다.

### 4.3 우선순위

1. 권위 있는 한국어 신학용어사전
2. 한국어 신학 학술자료의 검증 가능한 용례
3. 영어 원문과 한국어 용어의 cross-reference
4. AI translation — auxiliary only

### 4.4 Terminology Corpus = 일반 Corpus와 분리

Terminology는 일반 RAG 자료와 동일한 pool로 취급하지 않는다.

최소한 다음 개념을 유지한다:

```
term_id
english_term
korean_term
aliases
definition
source
provenance
confidence
```

**Terminology = authoritative terminology layer**
**Dictionary/Commentary = research evidence layer**

이 구분을 유지한다.

---

## 5. PHASE 3 — NAC (New American Commentary)

### 5.1 NAC는 즉시 전체 임베딩하지 않는다

NAC는 반드시 다음 순서로 진행한다:

```text
NAC acquisition
    → 1 volume pilot
    → file extraction audit
    → structure / metadata audit
    → TSU conversion
    → sample quality audit
    → Korean → English retrieval test
    → PASS
    → full NAC acquisition
    → full embedding
```

**한 권의 pilot이 통과하기 전에는 NAC 전체 세트를 구매·임베딩·indexing하지 않는다.**

### 5.2 Cross-Lingual Retrieval Gate

NAC English corpus의 핵심 검증 항목:

> **한국어 질문으로 영어 NAC를 얼마나 정확하게 찾는가?**

최소 benchmark:

- 한국어 theological concept query
- 한국어 Scripture-based query
- 한국어 exegetical query
- 영어 원문 relevance
- Top-5 / Top-10 retrieval
- citation accuracy

**BGE-M3가 가능하다는 이유만으로 production readiness를 가정하지 않는다.**

---

## 6. Translation Corpus Status

검증되지 않은 한국어 NAC 번역본이 존재하더라도:

```text
NAC English Original = AUTHORITATIVE
Korean Translation  = SECONDARY / UNVERIFIED
```

번역본은 향후 검색 보조 또는 비교 자료로 사용할 수 있으나, **영어 원문을 대체하지 않는다.**

AI 자체 번역은 authoritative corpus로 승격시키지 않는다.

---

## 7. Library Source Control — 시기

사용자가 자료별 ON/OFF를 제어하는 기능은 **지금 구현하지 않는다.**

먼저:

```text
Smith → 실제 앱 → 실제 질문 → 실제 연구 workflow 관찰
```

을 수행한다. 그 후 실제 사용 패턴을 근거로 **Library Source Control / Research Scope**를 설계한다.

목표:

> **무엇을 알고 있는가가 아니라, 이번 연구에서 무엇을 근거로 삼을 것인가를 목회자가 통제한다.**

---

## 8. Governance Rules — 절대 변경 금지

다음 사항은 pipeline 진행 중 임의 변경 금지:

| # | 규칙 |
|---|---|
| 1 | Architecture Freeze |
| 2 | 기존 ADR 우회 금지 |
| 3 | 새로운 vector DB 추가 금지 |
| 4 | 기존 retrieval authority 우회 금지 |
| 5 | production corpus와 experimental corpus 혼합 금지 |
| 6 | unverified translation을 authoritative source로 승격 금지 |
| 7 | 전체 corpus를 pilot 없이 일괄 embedding하지 않음 |
| 8 | 새로운 기능을 발견했다고 현재 phase를 중단하지 않음 |
| 9 | ingestion/embedding/cache/indexing을 필요 이상으로 재실행하지 않음 |
| 10 | 각 phase의 Gate를 통과하기 전에 다음 phase로 이동하지 않음 |

---

## 9. Work Priority Lock

C1과 CUE 모두 다음 우선순위를 따른다:

```text
CURRENT:
Smith completion
    → CUE verification
    → HIGH finding resolution
    → Regression
    → APP RUN
    → REAL USER QUERIES
    → [ONLY THEN]
Terminology Corpus
    → NAC Pilot
    → NAC Full
    → Source Control
```

**새로운 아이디어는 기록할 수 있지만 현재 phase를 변경하지 않는다.**

즉:

> **DISCOVER ≠ IMPLEMENT**

발견된 개선사항은 backlog에 기록하고 현재 Gate를 완료한다.

---

## 10. Phase Transition Criteria

각 phase에서 다음 phase로 이동하려면:

1. **현재 phase의 모든 Gate를 통과했음을 독립 검증(CUE 또는 C1 Forensic Auditor)이 확인**
2. **사용자(HQ)가 결과를 검토하고 승인**
3. **다음 phase의 구체적인 acceptance criteria를 명시**

---

## 11. Next Steps (승인 후)

- [ ] 이 ADR을 사용자(HQ)가 검토·승인
- [ ] 승인 시 Status를 `ACCEPTED`로 변경
- [ ] Smith Bible Dictionary Phase 완료 전까지 이 문서의 priority lock 유지
- [ ] 각 phase 완료 시 STATE.md에 진행 상황 기록

---

## 12. C1/CUE 지시 사항

> **"이 문서를 NAE의 Research Corpus Expansion Pipeline의 governing roadmap으로 취급하라. 현재 Smith phase를 완료하기 전에는 다음 phase의 implementation을 시작하지 말라. 새로운 아이디어나 발견사항은 pipeline을 변경하지 말고 backlog/decision log에 기록하라. Phase transition은 각 Gate의 검증과 사용자 승인 후에만 수행한다."**
