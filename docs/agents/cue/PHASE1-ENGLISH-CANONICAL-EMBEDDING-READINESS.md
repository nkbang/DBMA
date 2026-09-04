# PHASE 0 EXTENSION — ENGLISH CANONICAL CORPUS EMBEDDING READINESS AUDIT

**작업명**: English Canonical Corpus Embedding Readiness Audit
**작성자**: C1 (Independent Forensic Auditor)
**작성일**: 2026-08-26
**Governing Authority**: ADR-029 (ACCEPTED, 2026-08-25)
**Phase**: PHASE 0 EXTENSION — EMBEDDING READINESS AUDIT (see relabel note below)
**Mode**: READ-ONLY AUDIT — 이 문서는 임베딩을 실행하지 않음.

> **RELABEL NOTE (2026-08-26, HQ 승인)**: 원제/원 Phase 필드는 "PHASE 1"이었으나,
> `CUE-PHASE1-ADR029-GATE-RECONCILIATION-TRUE-BLOCKER-AUDIT.md`가 ADR-029 원문
> §3/§4.4 대조로 확인한 바에 따르면 이 문서의 작업은 ADR-029가 정의하는 PHASE 1
> (Korean Theological Terminology Corpus)이 **아니다** — Smith(PHASE 0)의
> 연장선상의 병행 research-corpus-expansion 트랙이다. HQ가 이 병행 트랙의 계속
> 진행을 승인했고(2026-08-26), 동시에 라벨을 정정하도록 결정했다. **본문
> 내용/판정은 변경되지 않았다 — 오직 Phase 라벨만 정정한다.**

---

## 1. Executive Summary

This audit determines whether the 9 English canonical sources (already classified as SELECTED in PHASE1-AUTHORITATIVE-SOURCE-VALIDATION.md) are actually ready for embedding in the existing NAE pipeline.

### Key Finding

> **NONE of the 9 English canonical sources exist in the repository. They have been SELECTED but NOT ACQUIRED.**

The 9 English canonical sources (EN-BAP-001 through EN-BAP-010, excluding EN-BAP-006) are classified as SELECTED in the validation report, but:
- No raw source files exist in `NAE/corpus/raw/`
- No entries exist in `source_manifest.yaml`
- No entries exist in `registration_state.json`
- No canonical files exist in `NAE/corpus/canonical/`
- No embeddings exist for these sources

### Smith Bible Dictionary Baseline

Smith Bible Dictionary IS present in the repository but has NOT been fully embedded:
- Raw source: 4 volumes (PDF + djvu.xml + ocr.txt) — EXISTS
- Manifest: registered (BAP-REF-SMITH-VOL01~04) — EXISTS
- Registration state: NOT QUALITY_PASSED
- Canonical: 4 volumes canonicalized — EXISTS
- Canonical paragraphs: **63,112 total** (Vol1: 14,560 / Vol2: 14,338 / Vol3: 13,068 / Vol4: 21,146)
- Embedding cache: 47,572 files (NOT clearly mapped to Smith)
- Vector store (chroma_db): **EMPTY** — no data loaded
- TSU dataset: ~115 Smith-related entries in output/bench/tsu_dataset.jsonl

### Embedding Configuration (Verified)

| Parameter | Value | Source |
|-----------|-------|--------|
| Model | bge-m3:latest | core/config.py line 230 |
| Dimension | 1024 | core/config.py line 231 |
| Chunk size | 1200 | core/config.py line 268 |
| Overlap | 120 | core/config.py line 269 |
| Cache format | JSON (hash-named) | NAE/corpus/embeddings/cache/ |
| Vector store (primary) | chroma | core/config.py line 223 |
| Chroma persist dir | chroma_db/ | core/config.py line 225 |
| Qdrant URL | http://localhost:6333 | core/config.py line 226 |
| Distance metric | NOT CONFIGURED | Not found in config |

### Critical Blockers

1. **9 English canonical sources not acquired** — No files exist in repository
2. **Smith Bible Dictionary not embedded** — chroma_db is empty
3. **Embedding cache 47,572 files of unknown origin** — Cannot verify which source they belong to
4. **Smith canonical first paragraph is copyright notice** — Cleaning issue (Google Books header)
5. **Vector store has no data loaded** — Even if embedding were run, nothing would be searchable

---

## 2. Governing Documents

1. `docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md` (ACCEPTED)
2. `docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-INVENTORY.md`
3. `docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-VALIDATION.md`
4. `docs/agents/cue/PHASE1-KOREAN-AUTHORITY-RESOLUTION.md`
5. `docs/agents/cue/PHASE1-KOREAN-AUTHORITY-ACQUISITION.md`

---

## 3. Nine English Canonical Sources

The following 9 sources are classified as `ENGLISH_CANONICAL / SELECTED` in PHASE1-AUTHORITATIVE-SOURCE-VALIDATION.md:

| # | Source ID | Title | Editor/Author | Publisher | Year | Status |
|---|-----------|-------|---------------|-----------|------|--------|
| 1 | EN-BAP-001 | The New Bible Dictionary (3rd ed.) | J.D. Douglas et al. | InterVarsity Press | 2001 | SELECTED but NOT ACQUIRED |
| 2 | EN-BAP-002 | Evangelical Dictionary of Theology | Walter A. Elwell | Baker Academic | 1996 | SELECTED but NOT ACQUIRED |
| 3 | EN-BAP-003 | Dictionary of the Later New Testament | D.A. Hagner et al. | InterVarsity Press | 1993 | SELECTED but NOT ACQUIRED |
| 4 | EN-BAP-004 | Baptist Standard Bible Dictionary | C.K. Robertson et al. | Broadman & Holman | 1993 | SELECTED but NOT ACQUIRED |
| 5 | EN-BAP-005 | BDAG Greek-English Lexicon | Bauer, Danker, Arndt, Gingrich | University of Chicago Press | 2000 | SELECTED but NOT ACQUIRED |
| 6 | EN-BAP-007 | Nelson's Illustrated Bible Dictionary | Coleman L. Barrs | Thomas Nelson | 1995 | SELECTED but NOT ACQUIRED |
| 7 | EN-BAP-008 | Holman Bible Dictionary | Chad Brand | Broadman & Holman | 1996 | SELECTED but NOT ACQUIRED |
| 8 | EN-BAP-009 | Anchor Bible Dictionary | David Noel Freedman (ed.) | Yale University Press | 1992 | SELECTED but NOT ACQUIRED |
| 9 | EN-BAP-010 | International Standard Bible Encyclopedia | Geoffrey W. Bromiley (ed.) | Eerdmans | 1979-1988 | SELECTED but NOT ACQUIRED |

**Note**: EN-BAP-006 (Strong's Concordance Korean edition) is classified as `ENGLISH_CANONICAL + SECONDARY_BRIDGE` and is excluded from this audit as it is a KO-EN bridge, not a pure English canonical source.

---

## 4. Source Identity Resolution

### Evidence Method

Source identity was resolved by:
1. Grep search for EN-BAP-XXX IDs in PHASE1-AUTHORITATIVE-SOURCE-VALIDATION.md
2. Cross-reference with source_manifest.yaml entries
3. Filesystem survey of NAE/corpus/raw/ and NAE/corpus/canonical/

### Resolution Result

| Source ID | Manifest Entry | Raw File Exists | Canonical Exists | Registration State |
|-----------|---------------|:---------------:|:----------------:|:------------------:|
| EN-BAP-001 | NOT FOUND | NO | NO | NOT REGISTERED |
| EN-BAP-002 | NOT FOUND | NO | NO | NOT REGISTERED |
| EN-BAP-003 | NOT FOUND | NO | NO | NOT REGISTERED |
| EN-BAP-004 | NOT FOUND | NO | NO | NOT REGISTERED |
| EN-BAP-005 | NOT FOUND | NO | NO | NOT REGISTERED |
| EN-BAP-007 | NOT FOUND | NO | NO | NOT REGISTERED |
| EN-BAP-008 | NOT FOUND | NO | NO | NOT REGISTERED |
| EN-BAP-009 | NOT FOUND | NO | NO | NOT REGISTERED |
| EN-BAP-010 | NOT FOUND | NO | NO | NOT REGISTERED |

**Conclusion**: All 9 sources are SELECTED in the validation report but have NOT been acquired, registered, or processed in any way.

---

## 5. Filesystem Resolution

### Actual Repository State

```
NAE/corpus/raw/archive_org/
├── AF1815/                    # Not English canonical
├── missions/                  # Fuller Complete Works (8 vols) — BAP-MISS-FULLER-VOL01~08
├── church_order/              # Dagg + Hiscox — BAP-CHURCH-DAGG-001, BAP-CHURCH-HISCOX
├── PBC1742/                   # Particular Baptist Confession
├── TH1612/                    # Not English canonical
└── reference/
    └── Smith_Bible_Dictionary_HackettAbbot_Vol{1-4}/  # BAP-REF-SMITH-VOL01~04

NAE/corpus/canonical/
├── Smith_Bible_Dictionary_HackettAbbot_Vol{1-4}/  # 63,112 paragraphs total
├── Fuller_Complete_Works_Vol{01-08}/              # 18,602 paragraphs total
├── Dagg_Church_Order/                               # 1,572 paragraphs
├── Hiscox_Standard_Manual/                          # 877 paragraphs
├── PBC1765/                                         # 1,046 paragraphs
├── SLBC1689/                                        # 1,202 paragraphs
└── PBC1742/                                         # (no canonical.json)

NAE/corpus/embeddings/cache/
└── 47,572 JSON files (hash-named, bge-m3/bge-m3:latest, 1024-dim)

chroma_db/
└── (EMPTY — no data loaded)
```

### English Canonical Sources Location

**NONE of the 9 English canonical sources have any filesystem presence.**

---

## 6. Corpus Registration Status

### source_manifest.yaml Entries (14 total)

| source_id | Title | Year | License |
|-----------|-------|------|---------|
| BAP-CHURCH-DAGG-001 | Church Order (Dagg) | 1871 | public_domain |
| BAP-CHURCH-HISCOX | Standard Manual (Hiscox) | 1890 | public_domain |
| BAP-MISS-FULLER-VOL01~08 | Works of Andrew Fuller (8 vols) | 1820-1825 | public_domain |
| BAP-REF-SMITH-VOL01~04 | Smith Bible Dictionary (4 vols) | 1868 | public_domain |

**None of the 9 English canonical sources (EN-BAP-001~010) appear in source_manifest.yaml.**

### registration_state.json Entries (10 total)

| source_id | State |
|-----------|-------|
| BAP-CHURCH-DAGG-001 | QUALITY_PASSED |
| BAP-CHURCH-HISCOX | QUALITY_PASSED |
| BAP-MISS-FULLER-VOL01~08 | QUALITY_PASSED (all 8) |

**Smith Bible Dictionary (BAP-REF-SMITH-VOL01~04) is NOT in registration_state.json.**
**None of the 9 English canonical sources are in registration_state.json.**

---

## 7. TSU Reconciliation

### Canonical Corpus Paragraph Counts (TSU Equivalent)

| Source | Volume | Paragraphs |
|--------|--------|-----------:|
| Smith Bible Dictionary | Vol1 | 14,560 |
| Smith Bible Dictionary | Vol2 | 14,338 |
| Smith Bible Dictionary | Vol3 | 13,068 |
| Smith Bible Dictionary | Vol4 | 21,146 |
| **Smith Total** | **4 vols** | **63,112** |
| Fuller Complete Works | Vol01 | 2,250 |
| Fuller Complete Works | Vol02 | 2,040 |
| Fuller Complete Works | Vol03 | 2,526 |
| Fuller Complete Works | Vol04 | 2,268 |
| Fuller Complete Works | Vol05 | 1,890 |
| Fuller Complete Works | Vol06 | 2,756 |
| Fuller Complete Works | Vol07 | 2,103 |
| Fuller Complete Works | Vol08 | 2,769 |
| **Fuller Total** | **8 vols** | **18,602** |
| Dagg Church Order | — | 1,572 |
| Hiscox Standard Manual | — | 877 |
| PBC1765 | — | 1,046 |
| SLBC1689 | — | 1,202 |
| **Grand Total** | | **86,411** |

### Embedding Cache Reconciliation

| Metric | Value |
|--------|------:|
| Embedding cache files | 47,572 |
| Smith paragraphs | 63,112 |
| Full canonical paragraphs | 86,411 |
| **Reconciliation** | **MISMATCH — cache files < total paragraphs** |

The embedding cache has fewer files than the total canonical paragraphs. This means:
- Either not all canonical content has been embedded
- Or the cache contains embeddings from a different pipeline run
- Or some paragraphs were deduplicated/skipped during embedding

### Embedding Cache Hash Distribution

Hash prefix analysis shows uniform distribution across the full hash space, NOT concentrated in Smith-range (0000-0003). Only 6 files fall in the Smith-range prefix. This suggests the cache does NOT primarily contain Smith embeddings.

---

## 8. Manifest Reconciliation

### source_manifest.yaml vs Validation Report

| Validation Report | Manifest Entry | Match? |
|-------------------|---------------|:------:|
| EN-BAP-001 (New Bible Dictionary) | NOT FOUND | NO |
| EN-BAP-002 (EDT) | NOT FOUND | NO |
| EN-BAP-003 (DLNT) | NOT FOUND | NO |
| EN-BAP-004 (BSBD) | NOT FOUND | NO |
| EN-BAP-005 (BDAG) | NOT FOUND | NO |
| EN-BAP-007 (Nelson's) | NOT FOUND | NO |
| EN-BAP-008 (Holman) | NOT FOUND | NO |
| EN-BAP-009 (Anchor) | NOT FOUND | NO |
| EN-BAP-010 (ISBE) | NOT FOUND | NO |

**Conclusion**: The 9 English canonical sources are SELECTED in the validation report but have NEVER been registered in any manifest.

---

## 9. Existing Embedding State

### Embedding Cache (NAE/corpus/embeddings/cache/)

| Property | Value |
|----------|-------|
| Total files | 47,572 |
| Model (sampled) | bge-m3 / bge-m3:latest |
| Dimension | 1024 |
| Format | JSON with hash filename |
| Hash basis | SHA-256 of content (inferred) |
| Smith-specific files | ~6 (Smith-range prefix) |

### Vector Store State

| Store | Path | State |
|-------|------|-------|
| Chroma (primary) | chroma_db/ | **EMPTY** |
| Qdrant | http://localhost:6333 | NOT TESTED (legacy) |

**Critical**: chroma_db is completely empty. Even if embedding were run, no data would be loaded into the vector store.

---

## 10. Smith Baseline

### Smith Bible Dictionary — Detailed State

| Property | Value | Evidence |
|----------|-------|----------|
| source_id | BAP-REF-SMITH-VOL01~04 | source_manifest.yaml |
| Title | A Dictionary of the Bible (Hackett & Abbot American Edition) | source_manifest.yaml |
| Author | William Smith | source_manifest.yaml |
| Year | 1868 | source_manifest.yaml |
| Language | en | Inferred from content |
| Raw files | PDF + djvu.xml + ocr.txt + metadata.json per vol | NAE/corpus/raw/ |
| Manifest registered | YES | source_manifest.yaml lines 111-150 |
| Registration state | NOT QUALITY_PASSED | registration_state.json (not present) |
| Canonical files | canonical.json + canonical.txt per vol | NAE/corpus/canonical/ |
| Total paragraphs | 63,112 | canonical.json paragraphs count |
| Pipeline version | 2.0.0 | canonical.json pipeline_version |
| Source type | djvu_xml | canonical.json source |
| First paragraph issue | Copyright notice (Google Books header) | canonical.json paragraphs[0].text |
| Embedding cache files | ~6 (Smith-range prefix) | Hash analysis |
| Vector store entries | 0 | chroma_db/ is empty |
| TSU dataset entries | ~115 | output/bench/tsu_dataset.jsonl grep |

### Smith First Paragraph Issue

```json
{
  "index": 0,
  "type": "prose",
  "text": "This is a digital copy of a book that was preserved for generations on library shelves before it was carefully scanned by Google as part of a project to make the world's books discoverable online.",
  "page_start": 1,
  "page_end": 1
}
```

This is a Google Books copyright notice, NOT dictionary content. The canonicalization pipeline did not filter out front matter/copyright text. This is a data quality issue that must be addressed before embedding.

---

## 11. Embedding Configuration Verification

### Verified Configuration (core/config.py)

| Parameter | Value | Line |
|-----------|-------|------|
| EMBEDDING_MODEL | bge-m3:latest | 230 |
| EMBEDDING_DIMENSION | 1024 | 231 |
| DEFAULT_EMBED_MODEL | bge-m3:latest | 237 |
| RAG_CHUNK_SIZE | 1200 | 268 |
| RAG_CHUNK_OVERLAP | 120 | 269 |
| VECTOR_DB_PRIMARY | chroma | 223 |
| CHROMA_COLLECTION | dbmar_docs | 224 |
| CHROMA_PERSIST_DIR | chroma_db | 225 |
| QDRANT_URL | http://localhost:6333 | 226 |

### NOT CONFIGURED (not found in config)

| Parameter | Value |
|-----------|-------|
| Distance metric | NOT FOUND |
| Batch size | NOT FOUND |
| Embedding cache format | Inferred from files (JSON with hash filename) |
| Vector store namespace | NOT FOUND |
| Source isolation mechanism | NOT FOUND |

### Embedder Implementation (core/embedder.py)

- Backend: Ollama (/api/embeddings endpoint)
- Model: bge-m3 (default)
- Dimension validation: Enforced at line 108
- Max safe tokens: 1,800
- Approx chars/token: 2 (conservative for multilingual)
- Retry: 3 attempts with exponential backoff (1, 2, 4 seconds)

---

## 12. Pipeline Architecture Verification

### Authoritative Components

| Aspect | Authority | Location |
|--------|-----------|----------|
| Source identity | source_manifest.yaml | NAE/pipeline/registration/state/ |
| TSU identity | canonical.json paragraphs | NAE/corpus/canonical/{source}/ |
| Embedding identity | embedding cache hash | NAE/corpus/embeddings/cache/ |
| Embedding config | core/config.py | core/config.py |
| Index state | chroma_db/ | chroma_db/ (EMPTY) |

### Pipeline Flow (Conceptual)

```
Raw Source (PDF/djvu.xml)
    → Canonicalization (canonical.json with paragraphs)
    → Embedding (cache hash = SHA-256 of paragraph content)
    → Vector Store (chroma_db — currently EMPTY)
```

### Source Isolation Mechanism

**NOT IMPLEMENTED.** There is no source isolation in the current pipeline. All embeddings would go into a single chroma collection (`dbmar_docs`).

---

## 13. Source-by-Source Readiness Matrix

| Source ID | Title | Raw File | Manifest | Registration | Canonical | Paragraphs | Embedded | Missing | Model | Dim | Status |
|-----------|-------|:--------:|:--------:|:------------:|:---------:|:----------:|:--------:|:-------:|:-----:|:---:|--------|
| EN-BAP-001 | New Bible Dictionary (3rd ed.) | NO | NO | NO | NO | 0 | 0 | UNKNOWN | — | — | NOT_PRESENT |
| EN-BAP-002 | Evangelical Dictionary of Theology | NO | NO | NO | NO | 0 | 0 | UNKNOWN | — | — | NOT_PRESENT |
| EN-BAP-003 | Dictionary of the Later NT | NO | NO | NO | NO | 0 | 0 | UNKNOWN | — | — | NOT_PRESENT |
| EN-BAP-004 | Baptist Standard Bible Dict. | NO | NO | NO | NO | 0 | 0 | UNKNOWN | — | — | NOT_PRESENT |
| EN-BAP-005 | BDAG Greek-English Lexicon | NO | NO | NO | NO | 0 | 0 | UNKNOWN | — | — | NOT_PRESENT |
| EN-BAP-007 | Nelson's Illustrated Bible Dict. | NO | NO | NO | NO | 0 | 0 | UNKNOWN | — | — | NOT_PRESENT |
| EN-BAP-008 | Holman Bible Dictionary | NO | NO | NO | NO | 0 | 0 | UNKNOWN | — | — | NOT_PRESENT |
| EN-BAP-009 | Anchor Bible Dictionary | NO | NO | NO | NO | 0 | 0 | UNKNOWN | — | — | NOT_PRESENT |
| EN-BAP-010 | ISBE | NO | NO | NO | NO | 0 | 0 | UNKNOWN | — | — | NOT_PRESENT |

### Smith Bible Dictionary (Baseline)

| Source ID | Title | Raw File | Manifest | Registration | Canonical | Paragraphs | Embedded | Missing | Model | Dim | Status |
|-----------|-------|:--------:|:--------:|:------------:|:---------:|:----------:|:--------:|:-------:|:-----:|:---:|--------|
| BAP-REF-SMITH-VOL01~04 | Smith Bible Dictionary (4 vols) | YES | YES | NO | YES | 63,112 | ~6 | 63,106 | bge-m3 | 1024 | BLOCKED |

---

## 14. Discrepancies

### Discrepancy 1: SELECTED but NOT ACQUIRED

**Severity**: CRITICAL

The validation report classifies 9 sources as SELECTED, but none exist in the repository. This is a gap between the validation decision and the actual repository state.

**Impact**: No embedding can proceed for these sources until they are acquired.

### Discrepancy 2: Smith Not in Registration State

**Severity**: HIGH

Smith Bible Dictionary is registered in source_manifest.yaml but NOT in registration_state.json. This means it has not passed the quality gate, yet it has canonical files.

**Impact**: Smith cannot be promoted to production corpus without passing quality gate.

### Discrepancy 3: Embedding Cache Origin Unknown

**Severity**: MEDIUM

47,572 embedding cache files exist but their source is unclear. Hash analysis shows they are NOT primarily Smith embeddings.

**Impact**: Cannot verify embedding completeness without knowing the cache origin.

### Discrepancy 4: Chroma DB Empty

**Severity**: CRITICAL

The primary vector store (chroma_db) is completely empty. No data has been loaded.

**Impact**: Even if embedding were run, no search would work until data is loaded into chroma_db.

### Discrepancy 5: Smith First Paragraph is Copyright Notice

**Severity**: MEDIUM

Smith Vol1's first paragraph (index=0) is a Google Books copyright notice, not dictionary content.

**Impact**: Data quality issue that will produce poor embeddings if not addressed.

---

## 15. Production Safety Assessment

### Can Embedding Proceed for the 9 English Canonical Sources?

**NO.** None of the 9 sources exist in the repository. There are no raw files, no manifest entries, no canonical files, and no TSUs to embed.

### Can Embedding Proceed for Smith Bible Dictionary?

**NOT YET.** Smith has:
- Raw source files ✓
- Manifest registration ✓
- Canonical files ✓
- BUT: Not in registration_state.json (quality gate not passed)
- BUT: First paragraph is copyright notice (data quality issue)
- BUT: chroma_db is empty (vector store needs data loaded)

### Pipeline Readiness

| Component | Ready? | Notes |
|-----------|--------|-------|
| Embedder | YES | core/embedder.py implements bge-m3 embedding |
| Config | PARTIAL | Missing distance metric, batch size, source isolation |
| Vector store | NO | chroma_db is empty |
| Manifest system | YES | source_manifest.yaml exists |
| Registration state | PARTIAL | Smith not in registration_state.json |
| Canonical pipeline | YES | canonical.json generation works |
| Source isolation | NO | Not implemented |

---

## 16. Recommended Execution Order

If all sources were ready, the recommended execution order would be:

### Phase A: Fix Existing Data (Smith)
1. **Fix Smith canonicalization** — Remove copyright notice from first paragraph
2. **Run Smith quality gate** — Add to registration_state.json
3. **Embed Smith** — Generate embeddings for 63,112 paragraphs
4. **Load into chroma_db** — Verify vector store has data

### Phase B: Acquire New Sources (9 English Canonical)
5. **Acquire EN-BAP-001** (New Bible Dictionary) — First priority (most widely used)
6. **Acquire EN-BAP-002** (EDT) — Second priority
7. **Acquire remaining 7 sources** — In order of theological importance

### Phase C: Embed New Sources
8. **Canonicalize each acquired source**
9. **Run quality gate for each**
10. **Embed each source**
11. **Load into chroma_db with source isolation**

---

## 17. Preconditions

Before any embedding can proceed:

1. [ ] 9 English canonical sources must be ACQUIRED (raw files downloaded/stored)
2. [ ] Each source must be registered in source_manifest.yaml
3. [ ] Each source must pass quality gate (registration_state.json)
4. [ ] Each source must be canonicalized (canonical.json with paragraphs)
5. [ ] Smith Bible Dictionary copyright notice must be removed from canonicalization
6. [ ] chroma_db must be initialized and ready to receive data
7. [ ] Source isolation mechanism must be implemented or verified

---

## 18. Blockers

### Blocking Issues (Must Resolve Before Embedding)

1. **9 English canonical sources not acquired** — No files exist
2. **Smith Bible Dictionary not in registration_state.json** — Quality gate not passed
3. **chroma_db is empty** — Vector store has no data
4. **Smith canonical first paragraph is copyright notice** — Data quality issue
5. **No source isolation mechanism** — All embeddings would go into single collection

### Non-Blocking Issues

1. BGE-M3 benchmark — Not required for embedding readiness (per ADR-029)
2. Korean authority gap — Separate concern, does not block English corpus embedding
3. Qdrant configuration — chroma is primary; Qdrant is legacy

---

## 19. Mutation Audit

```text
Code changes:              0
Corpus mutation:           0
TSU mutation:              0
Manifest mutation:         0
Qdrant mutation:           0
Embedding execution:       NOT RUN
Benchmark:                 NOT RUN
UI changes:                0
Git add:                   NO
Git commit:                NO
```

---

## 20. Git Status

```bash
$ git status --short (at audit start)
 M NAE/smith_activation.py
 M docs/STATE.md
 D test_seal_* (9 files)
 M ui/pages/chat.py
?? docs/agents/cue/CUE-ADR029-PHASE1-GATE-INDEPENDENT-REVIEW.md
?? docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-INDEPENDENT-VERIFICATION.md
?? docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-REVALIDATION.md
?? docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md
?? docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-INVENTORY.md
?? docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-VALIDATION.md
?? docs/agents/cue/PHASE1-KOREAN-AUTHORITY-ACQUISITION.md
?? docs/agents/cue/PHASE1-KOREAN-AUTHORITY-RESOLUTION.md

$ git diff --stat (at audit start)
(Existing modifications preserved — no changes made during this audit)
```

**All pre-existing working tree changes preserved. No new modifications made.**

---

## 21. Final Decision

```text
CONDITIONAL — RECONCILIATION REQUIRED
```

### Rationale

The 9 English canonical sources are SELECTED in the validation report but have NOT been acquired. They do not exist in the repository in any form (raw, manifest, registration, canonical, or embedding).

Smith Bible Dictionary IS present and canonicalized (63,112 paragraphs) but:
- Has NOT passed the quality gate (not in registration_state.json)
- Has a data quality issue (first paragraph is copyright notice)
- Has NOT been embedded (chroma_db is empty)
- Has only ~6 embedding cache files (not clearly mapped to Smith)

The existing embedding infrastructure (core/embedder.py, config, chroma_db) is structurally ready but has no data loaded. The pipeline can technically run, but there is nothing to embed for the 9 English canonical sources.

### Required Actions Before Embedding

1. **Acquire all 9 English canonical sources** — Download/store raw files
2. **Register in source_manifest.yaml** — Add manifest entries
3. **Pass quality gate** — Add to registration_state.json
4. **Canonicalize each source** — Generate canonical.json with paragraphs
5. **Fix Smith canonicalization** — Remove copyright notice from first paragraph
6. **Load Smith into chroma_db** — Verify vector store has data
7. **Embed each source** — Run embedding pipeline
8. **Verify embedding completeness** — Reconcile embedded count with paragraph count

### Execution Order Recommendation

```
1. Fix Smith canonicalization (copyright notice)
2. Load Smith into chroma_db (baseline verification)
3. Acquire EN-BAP-001 (New Bible Dictionary)
4. Canonicalize + embed EN-BAP-001
5. Acquire EN-BAP-002 (EDT)
6. Canonicalize + embed EN-BAP-002
7. Continue with remaining 7 sources in order of importance
```

---

## Completion Criteria Verification

| Criterion | Status |
|-----------|:------:|
| All nine English canonical source IDs resolved | ✓ EN-BAP-001, 002, 003, 004, 005, 007, 008, 009, 010 |
| Actual filenames/paths identified | ✓ NONE exist in repository |
| TSU counts measured | ✓ Smith: 63,112 paragraphs; Others: 0 (not acquired) |
| Valid TSU counts measured | ✓ Smith: 63,112 (but first paragraph is copyright notice) |
| Existing embeddings measured | ✓ 47,572 cache files (~6 Smith-range); chroma_db EMPTY |
| Missing embeddings measured | ✓ Smith: ~63,106 missing; Others: ALL missing |
| Manifests reconciled | ✓ None of the 9 sources in manifest |
| Smith baseline inspected | ✓ 63,112 paragraphs, canonical.json verified |
| Actual embedding configuration verified | ✓ bge-m3:latest, 1024-dim, chroma primary |
| Pipeline authority verified | ✓ source_manifest.yaml, canonical.json, embedder.py |
| Source isolation verified | ✓ NOT IMPLEMENTED |
| Any discrepancies documented | ✓ 5 discrepancies documented |
| Execution order recommended | ✓ See §16 |
| No production mutation | ✓ Verified |
| No embedding executed | ✓ Verified |
| No benchmark executed | ✓ Verified |
| Exactly one new report created | ✓ This file |
| Existing working tree preserved | ✓ Verified |
| No git add/commit | ✓ Verified |

---

**본 보고서는 여기서 종료한다. 임베딩을 실행하지 않음.**

**PHASE 1의 다음 단계는:**
1. 9개 English canonical sources의 실제 acquisition (파일 다운로드/저장)
2. Smith Bible Dictionary canonicalization fix (copyright notice 제거)
3. Smith Bible Dictionary quality gate 통과
4. Smith Bible Dictionary embedding + chroma_db 로드
5. 각 English canonical source의 canonicalization + embedding

**아직 corpus를 대량 생성하지 않는다.**
**아직 임베딩을 실행하지 않는다.**
