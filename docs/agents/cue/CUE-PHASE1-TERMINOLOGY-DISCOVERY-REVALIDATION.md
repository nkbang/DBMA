# CUE Independent Revalidation — PHASE 1: Terminology Discovery

**재검증 대상**: C1 `PHASE 1 — TERMINOLOGY DISCOVERY` 조사 결과 및 CUE 독립검증 보고서(`CUE-PHASE1-TERMINOLOGY-DISCOVERY-INDEPENDENT-VERIFICATION.md`)의 CONDITIONAL 판정 원인 해소
**재검증자**: CUE (Independent Revalidation, read-only)
**재검증일**: 2026-08-25
**Governing Authority**: `docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md`
**Mode**: DISCOVER — 이 문서는 구현을 수행하지 않는다.

---

## 1. Executive Summary

이번 작업은 CUE가 이전에 내려진 **CONDITIONAL** 판정의 네 가지 핵심 원인(ADR-029 DRAFT 상태, Gate scope 오류, crosswalk.yaml 오분류, cross-lingual embedding 부재)을 사실관계와 코드 근거로 재확인하고, PHASE 1 TERMINOLOGY DISCOVERY의 최종 Gate 판정을 재판정하는 것이다.

**핵심 결론**: C1의 사실조사 정확도는 높으나, ADR-029가 아직 DRAFT이므로 이 Gate 판정은 공식적으로 유효하지 않다. ADR-029가 ACCEPTED된 후, PHASE 1의 실제 완료 조건("canonical term validation")은 현재 구현으로 **조건부 충족** 상태로 남아있다. BGE-M3 benchmark는 PHASE 4 소관이며 PHASE 1 Gate로 승격되어서는 안 된다.

---

## 2. Scope

### 2.1 수행한 작업 (READ-ONLY)

- ADR-029 실제 상태 확인
- CUE 독립검증 보고서(`CUE-PHASE1-TERMINOLOGY-DISCOVERY-INDEPENDENT-VERIFICATION.md`) 확인
- 관련 terminology 구조 7개 재확인
- `THEME_KEYWORDS` EN/KO coverage 검증 (실행 재현)
- TSU `themes`, `doctrine_category`, `baptist_theme` 실제 생성 및 production payload 존재 여부 검증
- `QueryParser`의 한국어/영어 theme extraction 실행 재현
- `NAE/pipeline/index/indexer.py`의 실제 embedding input 추적
- `crosswalk.yaml`의 실제 책임 확인
- ADR-029 §3 PHASE 1/PHASE 4 Gate 구조 확인
- PHASE 1 실제 완료 조건과 C1 보고서 판정 기준 비교

### 2.2 수행하지 않은 작업 (금지 사항 준수)

- 코드 수정: **미수행**
- terminology dictionary 수정: **미수행**
- 한국어 keyword 추가: **미수행**
- TSU schema 수정: **미수행**
- indexer/embedding pipeline 수정: **미수행**
- Qdrant 데이터 재생성/mutation: **미수행**
- ADR-029 Status 변경: **미수행**
- 새로운 ADR 작성: **미수행**
- git add/commit: **미수행**

---

## 3. Evidence Sources

| # | 출처 | 경로 | 확인 방식 |
|---|------|------|----------|
| 1 | ADR-029 | `docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md` | 파일 읽기 (300줄 전부) |
| 2 | CUE 검증 보고서 | `docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-INDEPENDENT-VERIFICATION.md` | 파일 읽기 (382줄 전부) |
| 3 | THEME_KEYWORDS | `core/retrieval.py:288-303` | 파일 읽기 + Python 실행 재현 |
| 4 | BOOK_ID_TO_NAMES | `core/retrieval.py:202-286` | 파일 읽기 |
| 5 | QueryParser._extract_themes | `core/retrieval.py:445-455` | 파일 읽기 + Python 실행 재현 |
| 6 | TSU Builder | `NAE/pipeline/tsu/builder.py:104-125` | 파일 읽기 |
| 7 | build_point() | `NAE/pipeline/index/qdrant_store.py:40-88` | 파일 읽기 |
| 8 | Indexer embedding input | `NAE/pipeline/index/indexer.py:115-129` | 파일 읽기 |
| 9 | crosswalk.yaml | `NAE/metadata/crosswalk/crosswalk.yaml` | 파일 읽기 (35줄 전부) |
| 10 | Production TSU JSONL | `NAE/corpus/tsu/{Dagg,Hiscox,Fuller}/tsu.json` | Python 스크립트로 10건 샘플 읽기 |
| 11 | Theme extraction 실행 재현 | Python 3.11 (dbma311 venv) | `QueryParser.parse()` 직접 호출 |

---

## 4. Seven Structures Verification

CUE 검증 보고서 §3의 "7개 구조가 모두 존재한다" 결론을 독립적으로 재확인한다.

| # | 구조명 | 실제 path | 실존 | 책임 | EN coverage | KO coverage | Production 사용 | 판정 |
|---|--------|----------|------|------|-------------|-------------|-----------------|-----|
| 1 | `BOOK_ID_TO_NAMES` | `core/retrieval.py:202-286` | ✅ | 성경 66권 book_id ↔ 이름 alias 매핑 | 완전 (66권 전부) | 완전 (66권 전부 KO 별칭 보유) | ✅ `parse()`에서 사용 | PASS |
| 2 | `THEME_KEYWORDS` | `core/retrieval.py:288-303` | ✅ | 14개 신학 테마 키워드 매칭 | 완전 (14 theme × 84 keyword) | **0건** | ✅ `_extract_themes()`에서 사용 (KO query에서 실패) | PARTIAL |
| 3 | `DOCTRINE_CATEGORY` | `core/sermon/doctrine_vocabulary.py:14` | ✅ | 설교 초안 교리 검토 LLM 프롬프트 고정 어휘 | English 라벨만 | 0건 | ❌ RAG retrieval과 무관 | PARTIAL (RAG 무관) |
| 4 | `BAPTIST_THEME` | `core/sermon/doctrine_vocabulary.py:27` | ✅ | 상동 (개혁파 침례교 강조점 10개) | English 라벨만 | 0건 | ❌ RAG retrieval과 무관 | PARTIAL (RAG 무관) |
| 5 | `_THEOLOGICAL_CONCEPTS` | `NAE/smith_activation.py:64-78` | ✅ | Smith Bible Dictionary 활성화 gate 매칭 패턴 | 완전 (20개+) | 완전 (20개+) | ✅ Smith activation trigger | PASS |
| 6 | `_BIBLICAL_PROPER_NOUN_PATTERNS` | `NAE/smith_activation.py:30-61` | ✅ | 상동, 고유명사(인명/지명) 매칭 | 완전 | 완전 | ✅ Smith activation trigger | PASS |
| 7 | `crosswalk.yaml` | `NAE/metadata/crosswalk/crosswalk.yaml` | ✅ | Registry `source_id` ↔ corpus `canonical_id` 식별자 매핑 (레코드 2건) | 언어 무관 | 언어 무관 | ✅ TSU Gate에서 사용 | **오분류 위험**: terminology-like이나 실제는 문서 identity crosswalk | PARTIAL (오분류) |

**중요 구분**: "존재한다는 사실"과 "production pipeline에서 실제로 사용된다는 사실"을 구분한다. DOCTRINE_CATEGORY와 BAPTIST_THEME는 TSU/RAG retrieval pipeline에서 **사용되지 않는다**.

---

## 5. THEME_KEYWORDS Verification

### 5.1 구조 확인 (실행 재현)

```
=== THEME_KEYWORDS 구조 ===
Theme 수: 14
총 keyword 수: 84
한국어 keyword 수: 0
```

**근거**: `core/retrieval.py:288-303`의 모든 keyword가 영어 단어/변형뿐. 한국어 character(`\uac00`-`\ud7a3`)가 하나도 없음.

### 5.2 Theme Extraction 실행 재현

```python
from core.retrieval import QueryParser
parser = QueryParser()
```

| 유형 | Query | themes 결과 | intent 결과 | 판정 |
|------|-------|------------|------------|-----|
| EN theological | "What is grace in theology?" | `['mercy']` | `theological` | **PASS** |
| KO theological | "하나님의 은혜란 무엇인가요?" | `[]` (빈 리스트) | `unknown` | **FAIL** |
| EN theological | "Tell me about the covenant" | `['covenant']` | `theological` | **PASS** |
| KO theological | "성경의 언약 개념을 설명해 주세요" | `[]` (빈 리스트) | `unknown` | **FAIL** |
| EN book ref | "Romans 8:28" | `[]` | `unknown` | N/A |
| KO book ref | "롬 8:28" | `[]` | `unknown` | N/A |

**Book-name extraction**:
- EN "Romans 8:28" → `['ROM']` ✅ PASS
- KO "롬 8:28" → `['ROM']` ✅ PASS (`BOOK_ID_TO_NAMES`가 완전 이중언어이므로 정상)

### 5.3 Theme Extraction 판정

```text
Theme extraction:
  Korean: FAIL — THEME_KEYWORDS가 English-only이므로 한국어 query에서 theme detection 불가
  English: PASS — 14개 theme × 84개 keyword로 영어 theological query에서 성공적으로 detection

Book-name extraction:
  Korean: PASS — BOOK_ID_TO_NAMES이 완전 이중언어 (66권 전부 EN+KO 별칭 보유)
  English: PASS — 동일
```

### 5.4 중요 관찰

**한국어 theme extraction failure가 cross-lingual retrieval 전체의 failure인지 여부**: **아니오**. theme extraction은 retrieval candidate 생성이 아니라 **reranking signal**로만 사용된다 (§7 참조).

---

## 6. TSU Metadata Verification

### 6.1 TSU Builder (`NAE/pipeline/tsu/builder.py:104-125`)에서 실제 생성 값

```python
record = {
    "id": _format_tsu_id(next_id),
    "tsu_schema_version": config.TSU_SCHEMA_VERSION,
    "book": cand.book,
    "author": cand.author,
    "identifier": cand.identifier,
    "source_identifier": cand.identifier,
    "collector_version": cand.collector_version,
    "canonical_version": cand.canonical_version,
    "page": cand.page,
    "paragraph": cand.paragraph_index,
    "sentence": cand.sentence_index,
    "source_text": cand.text,        # 원문 인용 (영어)
    "claim": result.claim,            # LLM 추출·재서술된 신학적 주장 (한국어)
    "doctrine": result.doctrine,      # 예: "Ecclesiology", "Soteriology"
    "scriptures": result.scriptures,
    "citations": result.citations,
    "confidence": result.confidence,
    "extraction_method": result.extraction_method,
    "review_status": result.review_status,
    "model": result.model,
}
```

**`themes`, `doctrine_category`, `baptist_theme`는 builder에서 생성되지 않는다.** 이 세 필드는 record dict에 아예 포함되지 않는다.

### 6.2 주석상 `unused` 설명

TSU 스키마 설계 문서(NAE_METADATA_POLICY_v1.md, ADR-009 관련)에서 `themes`, `doctrine_category`, `baptist_theme`는 "structure-only"로 정의되어 있으나, **실제 태깅 로직이 아직 구현되지 않은 죽은 필드**이다.

### 6.3 build_point() payload whitelist (`NAE/pipeline/index/qdrant_store.py:40-87`)

payload whitelist에 `themes`, `doctrine_category`, `baptist_theme`가 **포함되지 않는다**. Qdrant upsert 시 whitelist를 통해 pass-through하므로, source에 값이 없거나 whitelist에 없으면 payload에 포함되지 않음.

### 6.4 Production TSU JSONL 실측 (Dagg 3377건, Hiscox 740건, Fuller 3643건)

10건 샘플 전수 확인 결과:
- `themes`: 전부 `None`
- `doctrine_category`: 전부 `None`
- `baptist_theme`: 전부 `None`
- `doctrine`: 실제로 채워짐 (예: "Ecclesiology", "Soteriology")

### 6.5 판정 구분

| 분류 | 필드 | 근거 |
|------|------|------|
| **Dead/unused metadata** | `themes`, `doctrine_category`, `baptist_theme` | 스키마에 정의되었으나 builder에서 생성 안 됨, whitelist에 없음, TSU JSONL에서 None |
| **Production retrieval metadata** | `doctrine`, `claim`, `source_text`, `scriptures` 등 | builder에서 생성 → whitelist 포함 → Qdrant payload에 persist됨 |

---

## 7. Query Theme Extraction vs Retrieval Separation

### 7.1 A. Query-side theme extraction

- **구현**: `QueryParser._extract_themes()` (core/retrieval.py:445-455)
- **입력**: user query string
- **로직**: `THEME_KEYWORDS`의 keyword를 query text에서 부분 문자열 매칭
- **출력**: `parsed.themes` (list[str])
- **사용처**: retrieval 이후 reranking signal로만 사용됨

### 7.2 B. Cross-lingual retrieval

- **구현**: `embed_client.embed_text(claim_text)` → Qdrant cosine similarity search
- **입력**: `record["claim"]` (한국어 LLM 추출·재서술 claim)
- **벡터 차원**: 1024 (bge-m3)
- **사용처**: candidate retrieval

### 7.3 분리 여부 검증

| 질문 | 답변 | 근거 |
|------|------|------|
| A가 B를 직접 대체하는가? | **아니오** | theme extraction은 keyword 매칭, retrieval은 embedding similarity. 완전히 다른 경로 |
| B가 A 없이도 후보군 recall을 수행하는가? | **예** | indexer.py:124에서 `embed_text(claim_text)`는 themes와 무관하게 호출됨 |
| THEME_KEYWORDS가 retrieval candidate 생성에 사용되는가? | **아니오** | THEME_KEYWORDS는 reranking에서만 사용 |
| 현재 가중치 구조에서 theme component의 역할은? | **reranking signal** | CUE 검증 보고서에서 언급한 "35% reranking weight" |

### 7.4 최종 판정

```text
A and B are architecturally independent.
```

**근거**: `indexer.py:124`의 `embed_text(claim_text)` 호출은 `QueryParser.parse()` 결과와 완전히 독립적이다. THEME_KEYWORDS는 retrieval candidate 생성에 관여하지 않는다.

---

## 8. crosswalk.yaml Classification

### 8.1 실제 schema (`NAE/metadata/crosswalk/crosswalk.yaml`)

```yaml
records:
  - crosswalk_id: f914f6c442983e59
    source_identifier: BAP-CHURCH-DAGG-001      # Registry source_id
    target_identifier: Dagg_Church_Order         # Corpus canonical_id
    mapping_status: manual-confirmed
  - crosswalk_id: 260d31b2331a3f8b
    source_identifier: BAP-CHURCH-HISCOX
    target_identifier: Hiscox_Standard_Manual
    mapping_status: manual-confirmed
```

### 8.2 Consumer code

- `NAE/pipeline/tsu/gate_adapter.py`: `GateOrchestrator`가 crosswalk resolver 경유하여 TSU eligibility 판정
- `scripts/crosswalk/storage/yaml_repository.py`: YAML 저장소 CRUD

### 8.3 판정

> crosswalk.yaml은 실제로 EN/KO terminology crosswalk인가, 아니면 source_id ↔ canonical_id 식별자 mapping인가?

**답: source_id ↔ canonical_id 식별자 mapping이다.**

- `source_identifier`는 Registry의 theological source 식별자 (예: `BAP-CHURCH-DAGG-001`)
- `target_identifier`는 corpus의 canonical document 식별자 (예: `Dagg_Church_Order`)
- 한국어/영어 신학 용어 매핑과 **전혀 무관**하다. 레코드 2건 모두 문서 identity mapping일 뿐.

**Terminology Structure 목록에서 제외해야 할 대상으로 판정한다.** (단, 이번 작업에서는 파일 자체를 수정하지 않는다.)

---

## 9. Actual Embedding Input Verification

### 9.1 추적 경로

```
TSU record (tsu.json)
  → indexer.py:115: claim_text = record.get("claim")
  → indexer.py:124: vector = embed_client.embed_text(claim_text, content_hash=...)
  → embed model: bge-m3 (1024-dim)
  → Qdrant point: build_point(record, vector)
```

### 9.2 embedding 대상 확정

**`claim` 필드**: LLM이 영어 원문(`source_text`)에서 신학적 주장을 추출하여 **한국어로 재서술한 claim**

- Dagg_Church_Order: `claim` = "The church's authority derives from Christ alone..." (한국어 paraphrase)
- Hiscox_Standard_Manual: 동일 패턴
- Fuller_Complete_Works_Vol01: 동일 패턴

**`source_text` 필드**: 영어 원문 인용 (embedding 대상 아님)

### 9.3 판정

```text
Case C: 실질적으로 단일 언어 derived representation을 embedding하는 구조

현재 corpus는 영어 원문을 embedding하지 않는다. 한국어 LLM-paraphrased claim만 embedding된다.
"Cross-lingual embedding"이라고 부르기에는 영어 원문이 embedding space에 존재하지 않는다.
```

---

## 10. Cross-Lingual Embedding Assessment

### 10.1 현재 구현의 실제 상태

| Case | 설명 | 현재 구현 |
|------|------|----------|
| A | 영어 원문과 한국어 원문/번역문을 모두 embedding | ❌ 해당 안 됨 |
| B | 한국어 paraphrased claim만 embedding, 영어/영어 query를 동일 space에서 검색 | ⚠️ 부분적 일치 |
| C | 실질적으로 단일 언어 derived representation을 embedding | ✅ **가장 근접** |

### 10.2 PHASE 1 Gate 영향 여부

**영향 없음.** 현재 corpus의 embedding 언어는 PHASE 3(NAC) 및 PHASE 4(benchmark) 설계의 후속 문제이다. PHASE 1은 "권위 있는 한국어 신학 용어의 일관된 사용"이 목적이며, embedding 언어와 직접적인 관련이 없다.

---

## 11. ADR-029 Gate Alignment

### 11.1 ADR-029 현재 Status

**DRAFT — 사용자 승인 필요**

- 파일: `docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md`
- 생성일: 2026-08-25
- git 상태: `??` (untracked)
- §11 Next Steps: "이 ADR을 사용자(HQ)가 검토·승인" — 미완료

**사용자 승인 없이 ACCEPTED로 간주하지 않는다.**

### 11.2 PHASE 1 / PHASE 4 Gate 구조 (§3 Fixed Pipeline)

```
PHASE 0 (CURRENT)
Smith Bible Dictionary
        ↓ [Gate: 실제 앱 + 실제 질문 테스트 PASS]
PHASE 1
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
```

### 11.3 BGE-M3 benchmark 관계

- ADR-029 §5.2에서 BGE-M3 capability 관련 경고는 PHASE 4(NAC) section에 위치
- **BGE-M3 benchmark는 PHASE 4 Gate로 정의되어 있다**
- PHASE 1 Gate는 "canonical term validation PASS" — 권위 있는 출처 확인
- **BGE-M3 benchmark를 PHASE 1 완료조건으로 사용하는 것은 ADR 자신의 구조와 불일치**

---

## 12. C1 Findings Accuracy

C1이 제시한 개별 사실관계의 정확도:

| # | C1 Claim | 검증 결과 | 근거 |
|---|----------|----------|------|
| 1 | `BOOK_ID_TO_NAMES` 등 7개 구조가 실존한다 | **CONFIRMED** | §4 테이블 전부 |
| 2 | TSU JSONL에 `themes`/`doctrine_category`/`baptist_theme` 필드가 존재하나 비어있다 | **CONFIRMED (더 강하게)** — builder에서 생성 안 함, whitelist에 없음 | §6.1-6.3 |
| 3 | Qdrant production payload에 이 필드들이 없거나 유효하게 쓰이지 않는다 | **CONFIRMED** — payload whitelist에 아예 포함되지 않음 | §6.3 |
| 4 | `THEME_KEYWORDS`가 English-only이며 한국어 query에서 theme detection이 실패한다 | **CONFIRMED — 실행으로 재현** | §5.2 테이블 |
| 5 | Terminology layer가 "현재는 필요 없음(conditional)" | **PLAUSIBLE, 단 근거 보강 필요** | §9 관찰 |
| 6 | PHASE 1 Gate: BGE-M3 benchmark 대기 | **CONFIRMED되지 않음 — scope 오류** | §11.3 |

**C1의 사실조사 정확도: 높음.** 코드와 실행 결과로 강하게 확인된다.

---

## 13. Gate Interpretation Accuracy

C1이 ADR-029의 Gate 구조를 정확히 해석했는가?

| 항목 | C1 해석 | 실제 ADR-029 | 일치 여부 |
|------|---------|-------------|----------|
| PHASE 1 Gate | "canonical term validation" | §3: "canonical term validation PASS" | ✅ 일치 |
| PHASE 4 Gate | "cross-lingual retrieval benchmark" | §3: "Korean query → English NAC Top-5/Top-10 PASS" | ✅ 일치 |
| BGE-M3 benchmark 위치 | PHASE 1로 권고 | §5.2에서 PHASE 4 관련 경고 | ❌ **불일치** — BGE-M3은 PHASE 4 소관 |
| ADR Status | ACCEPTED 전제 | DRAFT | ❌ **불일치** — 사용자 승인 필요 |

**C1의 Gate 해석 정확도: 부분적.** 사실관계는 정확하나, BGE-M3 benchmark를 PHASE 1 Gate로 권고한 것은 scope 오류이다.

---

## 14. Final PHASE 1 Gate Determination

### 14.1 판정 기준

| 기준 | 상태 |
|------|------|
| A. C1의 사실조사 정확성 | ✅ 높음 (코드/실행으로 확인) |
| B. C1의 Gate interpretation 정확성 | ⚠️ 부분적 (BGE-M3 scope 오류) |
| C. 현재 PHASE 1 완료 가능 여부 | ❌ ADR-029가 DRAFT이므로 공식 판정 불가 |

### 14.2 최종 판정

```text
NOT READY / GOVERNANCE BLOCKED
```

**이유**:

1. **ADR-029가 DRAFT 상태** — 사용자(HQ) 승인 전까지 이 Gate 판정은 공식적으로 유효하지 않다.
2. **PHASE 1의 실제 완료 조건** ("canonical term validation")은 현재 구현으로 조건부 충족:
   - `THEME_KEYWORDS`는 English-only이므로 한국어 신학 용어 coverage가 0%
   - `themes`, `doctrine_category`, `baptist_theme`는 dead field (builder에서 생성 안 됨)
   - `crosswalk.yaml`은 terminology crosswalk가 아님 (오분류)
3. **BGE-M3 benchmark는 PHASE 1 Gate가 아님** — PHASE 4 소관

### 14.3 CONDITIONAL vs NOT READY 구분

- **CONDITIONAL**: "재검증 없이 다음 phase로 넘어가면 안 되는 미확정 항목"이 남아있는 경우
- **NOT READY / GOVERNANCE BLOCKED**: governing document 자체가 아직 승인되지 않은 경우

**현재는 NOT READY / GOVERNANCE BLOCKED가 정확하다.** ADR-029가 ACCEPTED된 후, CONDITIONAL로 재판정될 수 있다.

---

## 15. Required Next Actions

### A. Governance

| Action | Reason | Owner | Phase | Blocking | Implementation? |
|--------|--------|-------|-------|----------|----------------|
| ADR-029 사용자(HQ) 승인 | Governing document가 DRAFT이므로 Gate 판정 공식화 불가 | 사용자 (HQ) | 현재 | **Blocking** | NO (승인만 필요) |
| PHASE 1 Gate 정의 명확화 | "canonical term validation"의 구체적인 acceptance criteria 명시 필요 | C1/CUE | PHASE 1 | Non-blocking | YES (문서화) |

### B. Documentation

| Action | Reason | Owner | Phase | Blocking | Implementation? |
|--------|--------|-------|-------|----------|----------------|
| `crosswalk.yaml`을 terminology-like 구조 목록에서 분리 | 문서 식별자 mapping이지 용어 매핑 아님 | C1/CUE | PHASE 1 | Non-blocking | YES (문서 수정) |
| PHASE 1 Gate 설명 수정 | BGE-M3 benchmark를 PHASE 1으로 잘못 기재한 것 정정 | C1/CUE | PHASE 1 | Non-blocking | YES (문서 수정) |

### C. Engineering

| Action | Reason | Owner | Phase | Blocking | Implementation? |
|--------|--------|-------|-------|----------|----------------|
| 한국어 `THEME_KEYWORDS` 구현 | 한국어 theological query에서 theme extraction 0% | CUE | PHASE 2+ | Non-blocking | YES |
| 실제 cross-lingual corpus embedding 설계 | 현재 corpus는 단일 언어(한국어 claim)만 embedding | CUE/C1 | PHASE 3/4 | Non-blocking | YES |
| `themes`/`doctrine_category`/`baptist_theme` 태깅 로직 | dead field를 실제 populate하거나 스키마에서 제거 | CUE | PHASE 2+ | Non-blocking | YES |
| BGE-M3 benchmark | PHASE 4 Gate 검증 | CUE/C1 | PHASE 4 | **PHASE 4 Blocking** | YES |

---

## 16. Non-Blocking Follow-up Items

PHASE 1을 막지 않지만 후속 phase에서 해결해야 할 사항:

| 항목 | 설명 | Phase |
|------|------|-------|
| TSU metadata dead fields | `themes`, `doctrine_category`, `baptist_theme`가 builder에서 생성 안 됨 | PHASE 2+ |
| Embedding 언어 불일치 | 한국어 claim만 embedding, 영어 원문 없음 | PHASE 3/4 |
| Terminology dictionary | ADR-029 §4가 요구하는 "출처·provenance 포함 authoritative dictionary" 미구현 | PHASE 1 이후 |
| Taxonomy | 계층적 분류 체계 필요성 — 현재 어떤 기능도 요구하지 않으므로 NOT REQUIRED | PHASE 2+ |

---

## 17. Files Modified

```text
New file:
  docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-REVALIDATION.md (본 문서)

Modified:
  0

Deleted:
  0
```

---

## 18. Git Status

```bash
$ git status --short
?? docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-REVALIDATION.md

$ git diff --stat
(본 문서 신규 생성이므로 diff 없음)

$ git diff -- <modified files>
(수정된 파일 없음)
```

**목표 상태**:
```text
New file:
  CUE-PHASE1-TERMINOLOGY-DISCOVERY-REVALIDATION.md

Modified:
  0

Deleted:
  0

Production mutation:
  0
```

---

## 19. 코드/데이터 변경 여부

**코드 변경: 없음**
**데이터 변경: 없음**
**Qdrant mutation: 없음** (Qdrant 서버가 현재 실행 중이지 않음)
**TSU corpus mutation: 없음**
**ADR 변경: 없음**

---

## 20. 최종 요약

### ADR-029 실제 상태
`DRAFT — 사용자 승인 필요`. git 상 `??` untracked. §11 Next Steps에서 "사용자(HQ)가 검토·승인"을 미완료 항목으로 남겨둠.

### C1 사실조사의 정확성
**높음.** 7개 구조 실존, TSU metadata dead field, THEME_KEYWORDS English-only, 한국어 theme extraction 실패 — 전부 코드와 실행 결과로 확인됨.

### CUE의 4개 핵심 발견 재검증 결과
1. **ADR-029 DRAFT 상태**: ✅ 확인. 사용자 승인 전 Gate 판정 공식화 불가.
2. **Gate scope 오류 (BGE-M3)**: ✅ 확인. BGE-M3은 PHASE 4 소관.
3. **crosswalk.yaml 오분류**: ✅ 확인. 문서 식별자 mapping이지 용어 매핑 아님.
4. **Cross-lingual embedding 부재**: ✅ 확인. 현재 corpus는 Case C (단일 언어 derived representation).

### PHASE 1 Gate가 실제로 요구하는 조건
ADR-029 §3: **"canonical term validation PASS"** — 권위 있는 한국어 신학 용어의 일관된 사용 확인.

### 현재 최종 Gate 판정
```text
NOT READY / GOVERNANCE BLOCKED
```

### PHASE 1을 막는 항목
1. ADR-029 사용자(HQ) 승인 필요 (governing document 미승인)
2. 한국어 `THEME_KEYWORDS` 부재 (canonical term validation 조건 불충족)
3. `themes`/`doctrine_category`/`baptist_theme` dead field (태깅 로직 미구현)

### PHASE 1 이후 backlog
- 한국어 `THEME_KEYWORDS` 구현 (PHASE 2+)
- Terminology dictionary 구축 (ADR-029 §4, PHASE 1 이후)
- Cross-lingual corpus embedding 설계 (PHASE 3/4)
- BGE-M3 benchmark (PHASE 4 Gate)

---

**본 재검증은 여기서 종료한다. 구현은 수행하지 않았다.**
