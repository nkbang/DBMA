# PHASE 0 EXTENSION \u2014 ENGLISH BAP PIPELINE IMPLEMENTATION AUDIT

**작업명**: English Bible Academic Pipeline (EN-BAP) Implementation State Audit
**작성자**: C1 (Independent Forensic Auditor)
**작성일**: 2026-08-26
**Governing Authority**: ADR-029 (ACCEPTED, 2026-08-25), PHASE1-AUTHORITATIVE-SOURCE-VALIDATION.md
**Phase**: PHASE 0 EXTENSION \u2014 EN-BAP PIPELINE AUDIT (see relabel note below)
**Mode**: READ-ONLY FORENSIC AUDIT \u2014 이 문서는 mutation을 수행하지 않음.

> **RELABEL NOTE (2026-08-26, HQ 승인)**: 원제/원 Phase 필드는 "PHASE 1"이었으나,
> `CUE-PHASE1-ADR029-GATE-RECONCILIATION-TRUE-BLOCKER-AUDIT.md`가 ADR-029 원문
> §3/§4.4 대조로 확인한 바에 따르면 이 문서의 작업은 ADR-029가 정의하는 PHASE 1
> (Korean Theological Terminology Corpus)이 **아니다** \u2014 Smith(PHASE 0)의
> 연장선상의 병행 research-corpus-expansion 트랙이다. HQ가 이 병행 트랙의 계속
> 진행을 승인했고(2026-08-26), 동시에 라벨을 정정하도록 결정했다. **본문
> 내용/판정은 변경되지 않았다 \u2014 오직 Phase 라벨만 정정한다.**

---

## 1. Executive Summary

### Key Finding

> **The 9 English canonical sources (EN-BAP-001~010) are SELECTED but NOT ACQUIRED. The pipeline infrastructure EXISTS and WORKS for Smith Bible Dictionary, but is NOT YET CONFIGURED for EN-BAP sources.**

Smith Bible Dictionary has PASSED the Application Gate (7/7 real queries verified). The same pipeline infrastructure CAN BE REUSED for EN-BAP sources because:
- Canonicalization pipeline is source-agnostic (`NAE/pipeline/canonical/pipeline.py`)
- Embedding pipeline is language-agnostic (BGE-M3, 1024-dim)
- Reference corpus ingestion is parameterized (`NAE/pipeline/reference/ingest.py`)
- Source isolation exists via separate Qdrant collection (`nae_ref_v1`)

However, the following are NOT YET implemented for EN-BAP:
1. **Acquisition mechanism** \u2014 No code to download/acquire external sources
2. **Source validation** \u2014 No checksum/provenance verification for new sources
3. **Registration entries** \u2014 EN-BAP source IDs not in `source_manifest.yaml` or `registration_state.json`
4. **TSU compatibility** \u2014 TSU builder is Korean-script-specific; English sources use reference corpus pipeline instead (correct design)

### Overall Determination

```
CONDITIONAL \u2014 PIPELINE GAP
```

The pipeline infrastructure exists and works for Smith. The same code CAN handle EN-BAP sources IF:
1. Raw sources are acquired (external download)
2. Source entries are added to `source_manifest.yaml`
3. Canonicalization is run on English sources (same pipeline as Smith)
4. Reference corpus ingestion is called with new identifiers

**No architectural changes are required.** The gap is operational, not architectural.

---

## 2. Governing Documents

| # | Document | Status | Relevance |
|---|----------|--------|-----------|
| 1 | `docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md` | ACCEPTED | Governs pipeline lock, phase order |
| 2 | `docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-INVENTORY.md` | COMPLETED | Source discovery (20 candidates) |
| 3 | `docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-VALIDATION.md` | COMPLETED | Source validation (9 EN-BAP SELECTED) |
| 4 | `docs/agents/cue/PHASE1-KOREAN-AUTHORITY-RESOLUTION.md` | COMPLETED | Korean authority resolution |
| 5 | `docs/agents/cue/PHASE1-KOREAN-AUTHORITY-ACQUISITION.md` | COMPLETED | Korean acquisition plan |
| 6 | `docs/agents/cue/PHASE1-ENGLISH-CANONICAL-EMBEDDING-READINESS.md` | AUDIT | English embedding readiness |
| 7 | `docs/agents/cue/PHASE1-SMITH-BASELINE-READINESS.md` | VERIFIED | Smith baseline recovery |
| 8 | `docs/agents/cue/PHASE1-SMITH-BASELINE-APPLICATION-GATE.md` | PASS | Smith application gate (7/7) |

---

## 3. Source Identity Mapping

### 3.1 EN-BAP Sources (from PHASE1-AUTHORITATIVE-SOURCE-VALIDATION.md)

| # | Source ID | Title | Editor/Author | Publisher | Year | Status |
|---|-----------|-------|---------------|-----------|------|--------|
| 1 | EN-BAP-001 | The New Bible Dictionary (3rd ed.) | J.D. Douglas et al. | IVP/Tyndale | 1996 | SELECTED, NOT ACQUIRED |
| 2 | EN-BAP-002 | Evangelical Dictionary of Theology | Walter A. Elwell | Baker Academic | 2001 | SELECTED, NOT ACQUIRED |
| 3 | EN-BAP-003 | Dictionary of the Later New Testament | J.D. Douglas / Ralph P. Martin | IVP/Tyndale | 1987 | SELECTED, NOT ACQUIRED |
| 4 | EN-BAP-004 | Baptist Standard Bible Dictionary | Various | Broadman \u0026 Holman | 1996 | SELECTED, NOT ACQUIRED |
| 5 | EN-BAP-005 | BDAG Greek-English Lexicon (4th ed.) | Bauer, Danker, Arndt, Gingrich | U. Chicago Press | 2000 | SELECTED, NOT ACQUIRED |
| 6 | EN-BAP-007 | Nelson's Illustrated Bible Dictionary | Coleman Barron et al. | Tyndale House | 2003 | SELECTED, NOT ACQUIRED |
| 7 | EN-BAP-008 | Holman Bible Dictionary | Walter A. Elwell / Victor P. Hamilton | Broadman \u0026 Holman | 1996 | SELECTED, NOT ACQUIRED |
| 8 | EN-BAP-009 | Anchor Bible Dictionary | David Noel Freedman (ed.) | Doubleday | 1992 | SELECTED, NOT ACQUIRED |
| 9 | EN-BAP-010 | International Standard Bible Encyclopedia | Geoffrey W. Bromiley (ed.) | Eerdmans | 1979-1988 | SELECTED, NOT ACQUIRED |

### 3.2 Repository Evidence

**Raw source directory** (`NAE/corpus/raw/archive_org/reference/`):
```
Smith_Bible_Dictionary_HackettAbbot_Vol1/   \u2190 EXISTS (4 subdirs)
Smith_Bible_Dictionary_HackettAbbot_Vol2/   \u2190 EXISTS (3 subdirs)
Smith_Bible_Dictionary_HackettAbbot_Vol3/   \u2190 EXISTS (3 subdirs)
Smith_Bible_Dictionary_HackettAbbot_Vol4/   \u2190 EXISTS (3 subdirs)
EN-BAP-001/                                  \u2190 DOES NOT EXIST
EN-BAP-002/                                  \u2190 DOES NOT EXIST
... (all EN-BAP sources: NOT FOUND)
```

**Canonical directory** (`NAE/corpus/canonical/`):
```
Smith_Bible_Dictionary_HackettAbbot_Vol{1-4}/  \u2190 EXISTS
Dagg_Church_Order/                               \u2190 EXISTS
Fuller_Complete_Works_Vol{01-08}/                \u2190 EXISTS (8 dirs)
Hiscox_Standard_Manual/                          \u2190 EXISTS
PBC1742/                                         \u2190 EXISTS
PBC1765/                                         \u2190 EXISTS
SLBC1689/                                        \u2190 EXISTS
EN-BAP-001/                                      \u2190 DOES NOT EXIST
... (all EN-BAP sources: NOT FOUND)
```

**source_manifest.yaml** (`NAE/pipeline/registration/state/source_manifest.yaml`):
- 18 entries total (Dagg, Hiscox, Fuller x8, Smith x4)
- **EN-BAP entries: NONE**

**registration_state.json** (`NAE/pipeline/registration/state/registration_state.json`):
- 10 entries total (all QUALITY_PASSED)
- **EN-BAP entries: NONE**

### 3.3 Verification Method

```bash
# Raw source check
find NAE/corpus/raw/archive_org/reference/ -maxdepth 1 -type d | grep "EN-BAP"
# Result: NO MATCH (0 files)

# Canonical check
find NAE/corpus/canonical/ -maxdepth 1 -type d | grep "EN-BAP"
# Result: NO MATCH (0 files)

# Manifest check
grep "EN-BAP" NAE/pipeline/registration/state/source_manifest.yaml
# Result: NO MATCH (0 entries)

# Registration state check
grep "EN-BAP" NAE/pipeline/registration/state/registration_state.json
# Result: NO MATCH (0 entries)

# Code check
grep -r "EN-BAP-001\|EN-BAP-002\|EN-BAP-003\|EN-BAP-004\|EN-BAP-005\|EN-BAP-007\|EN-BAP-008\|EN-BAP-009\|EN-BAP-010" NAE/pipeline/
# Result: NO MATCH (0 references in code)
```

---

## 4. Pipeline Architecture

### 4.1 Current Pipeline (Smith Bible Dictionary \u2014 PASSED)

```
Raw source (PDF + djvu.xml + ocr.txt)
    \u2193 [NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol{1-4}/]
Source manifest registration
    \u2193 [source_manifest.yaml: BAP-REF-SMITH-VOL01~04]
Canonicalization
    \u2193 [NAE/pipeline/canonical/pipeline.py::normalize_item()]
    \u2192 extract (OCR/djvu) \u2192 normalize \u2192 structure \u2192 reflow \u2192 annotate
    \u2192 canonical.json + canonical.txt per volume
    \u2192 63,112 total paragraphs
Registration / Provenance
    \u2193 [source_manifest.yaml + registration_state.json]
    \u2192 Smith: NOT QUALITY_PASSED (only Fuller/Dagg/Hiscox in state)
TSU Build
    \u2193 [core/tsu_builder.py::build_tsu_records()]
    \u2192 Smith: ~115 entries in output/bench/tsu_dataset.jsonl
    \u2192 NOTE: TSU is scripture-focused; Smith uses reference corpus instead
Embedding
    \u2193 [NAE/pipeline/embed/client.py + core/embedder.py]
    \u2192 BGE-M3, 1024-dim, COSINE
    \u2192 47,572 cache files (unknown origin)
Vector Store
    \u2193 [Qdrant nae_ref_v1 collection]
    \u2192 34,948 points (Smith Bible Dictionary)
    \u2192 Separate from TSU collection
Application Retrieval
    \u2193 [NAE/smith_activation.py + NAE/reference_retrieval_adapter.py]
    \u2192 should_activate_smith() \u2192 search_reference() \u2192 Qdrant nae_ref_v1
    \u2192 Deterministic schema: text, source_id, volume, page_start, page_end, heading_context, chunk_index, content_type
Real Query Test
    \u2193 [PHASE1-SMITH-BASELINE-APPLICATION-GATE.md]
    \u2192 7/7 queries PASS (5 Smith-activated, 2 correctly skipped)
```

### 4.2 EN-BAP Pipeline (Target State)

```
Raw source (PDF + djvu.xml + ocr.txt) \u2190 NOT ACQUIRED
    \u2193 [NAE/corpus/raw/archive_org/reference/EN-BAP-XXX/]
Source manifest registration \u2190 NOT DONE
    \u2193 [source_manifest.yaml: EN-BAP-001~010 entries]
Canonicalization \u2190 SAME PIPELINE as Smith
    \u2193 [NAE/pipeline/canonical/pipeline.py::normalize_item()]
    \u2192 Works for any OCR/djvu source (source-agnostic)
Registration / Provenance \u2190 NEEDS MANIFEST ENTRIES
    \u2193 [source_manifest.yaml + registration_state.json]
TSU Build \u2190 NOT APPLICABLE (reference corpus, not scripture)
    \u2193 N/A \u2014 English dictionaries use reference corpus pipeline
Embedding \u2190 SAME PIPELINE as Smith
    \u2193 [NAE/pipeline/embed/client.py + core/embedder.py]
    \u2192 BGE-M3 handles English natively
Vector Store \u2190 SAME COLLECTION (nae_ref_v1)
    \u2193 [Qdrant nae_ref_v1 collection]
    \u2192 source_id field provides isolation
Application Retrieval \u2190 NEEDS IDENTIFIER REGISTRATION
    \u2193 [NAE/reference_retrieval_adapter.py]
    \u2192 search_reference() queries nae_ref_v1 with source_id filter
Real Query Test \u2190 NOT YET TESTED (no data loaded)
```

---

## 5. Acquisition

### Status: NOT_IMPLEMENTED

**Evidence**:
- No acquisition code exists in `core/` or `NAE/pipeline/`
- No `acquire_source`, `download_source`, or similar functions found
- No external source download mechanism in any pipeline module
- Smith Bible Dictionary was manually placed (archive.org download)

**Existing infrastructure**:
- `source_manifest.yaml` has `archive_source: archive_org` field for provenance
- Raw source directory structure exists (`NAE/corpus/raw/archive_org/reference/`)
- But no automated acquisition mechanism

**Gap**: EN-BAP sources must be acquired externally (purchase, library access, or archive.org). No code exists to automate this.

---

## 6. Validation

### Status: PARTIALLY_IMPLEMENTED

**Evidence**:
- `source_manifest.yaml` has `raw_checksum` field for each source
- `registration_state.json` tracks QUALITY_PASSED state
- `NAE/pipeline/ingest/state.py` has ProcessingState enum with validation states
- `NAE/pipeline/ingest/content_hash.py` has content hash classification

**What exists**:
- Checksum verification infrastructure (SHA-256 in manifest)
- Incremental state tracking (DISCOVERED \u2192 IDENTIFIED \u2192 INGESTED \u2192 ...)
- Content hash change detection (NEW/CHANGED/UNCHANGED)

**What's missing for EN-BAP**:
- No checksum entries for EN-BAP sources in `source_manifest.yaml`
- No provenance verification for external sources
- No license verification automation

---

## 7. Canonicalization

### Status: IMPLEMENTED (source-agnostic)

**Evidence**:
- `NAE/pipeline/canonical/pipeline.py::normalize_item()` is the orchestrator
- Pipeline stages: extract \u2192 normalize \u2192 structure \u2192 reflow \u2192 annotate
- All stages are source-format agnostic (works on OCR/djvu text)
- Tests exist: `tests/test_nae_canonical_pipeline.py`, `test_nae_canonical_normalize.py`, etc.

**Smith evidence**:
- 4 volumes canonicalized successfully
- 63,112 total paragraphs
- Output: `canonical.json` + `canonical.txt` + `normalize_report.json` per volume

**EN-BAP compatibility**:
- Same pipeline works for any OCR/djvu source
- No Smith-specific logic in canonicalization code
- **READY for EN-BAP sources once raw files are acquired**

---

## 8. Registration / Provenance

### Status: PARTIALLY_IMPLEMENTED

**Evidence**:
- `source_manifest.yaml` (schema_version 1.2) \u2014 authoritative source registry
- `registration_state.json` \u2014 quality state tracking
- `NAE/pipeline/ingest/manifest.py::build_production_manifest()` \u2014 production manifest builder
- `NAE/pipeline/ingest/state.py::IncrementalStateStore` \u2014 incremental processing state

**Smith evidence**:
- 4 entries in `source_manifest.yaml` (BAP-REF-SMITH-VOL01~04)
- Checksums present for all 4 volumes
- **NOT in `registration_state.json`** (only Fuller/Dagg/Hiscox have QUALITY_PASSED)

**EN-BAP gap**:
- No EN-BAP entries in `source_manifest.yaml`
- No EN-BAP entries in `registration_state.json`
- Manifest schema supports arbitrary sources (no Smith-specific constraints)

---

## 9. TSU

### Status: NOT_APPLICABLE for EN-BAP

**Evidence**:
- `core/tsu_builder.py::build_tsu_records()` is designed for scripture documents
- Book ID resolution (`_resolve_book_id()`) uses Korean filename patterns
- TSU schema includes `book_id`, `verse_mapping`, `themes` \u2014 scripture-specific fields
- Smith Bible Dictionary does NOT use TSU pipeline; it uses reference corpus pipeline

**Correct design**: English dictionaries should use the **reference corpus pipeline**, not TSU. This is by design:
- TSU = scripture evidence layer (verse-level claims)
- Reference corpus = dictionary/encyclopedia background knowledge

**No gap here** \u2014 EN-BAP sources correctly target reference corpus, not TSU.

---

## 10. Embedding

### Status: IMPLEMENTED (language-agnostic)

**Evidence**:
- `core/embedder.py::_OllamaEmbedder` \u2014 Ollama-based embedding
- Model: BGE-M3 (multilingual, 1024-dim)
- `NAE/pipeline/reference/ingest.py` \u2014 reference corpus ingestion with embedding
- Chunk size: 1200, overlap: 200

**Smith evidence**:
- 34,948 points embedded in Qdrant nae_ref_v1
- Embedding cache: 47,572 files (unknown origin)

**EN-BAP compatibility**:
- BGE-M3 handles English natively (confirmed by multilingual training)
- Same embedding pipeline works for any text source
- **READY for EN-BAP sources**

---

## 11. Vector Store

### Status: IMPLEMENTED (with source isolation)

**Evidence**:
- `NAE/pipeline/reference/config.py::REFERENCE_COLLECTION_NAME = "nae_ref_v1"`
- Separate from TSU collection (`index_config.COLLECTION_NAME`)
- Point ID scheme: `uuid5(NAMESPACE, f"{identifier}:{chunk_index}")` \u2014 deterministic, collision-free
- Payload includes `source_id`, `volume`, `identifier` for isolation

**Smith evidence**:
- 34,948 points in nae_ref_v1
- All Smith entries have `source_id: BAP-REF-SMITH-VOL01~04`

**EN-BAP compatibility**:
- Same collection (nae_ref_v1) \u2014 sources isolated by `source_id` field
- No source_id collision risk (different prefix pattern: EN-BAP-XXX vs BAP-REF-SMITH-VOLxx)
- **READY for EN-BAP sources**

---

## 12. Application Retrieval

### Status: IMPLEMENTED (Smith-specific activation, generic retrieval)

**Evidence**:
- `NAE/smith_activation.py::should_activate_smith()` \u2014 Smith-specific activation heuristic
- `NAE/reference_retrieval_adapter.py::search_reference()` \u2014 generic reference corpus search
- Activation: proper noun + theological term + definition patterns
- Retrieval: embed query \u2192 Qdrant nae_ref_v1 \u2192 filter by source_id

**Smith evidence**:
- 7/7 real queries PASS
- Activation correct for biblical proper nouns, theological terms, Korean queries
- Source provenance preserved (BAP-REF-SMITH-VOL01~04)

**EN-BAP gap**:
- `smith_activation.py` is Smith-specific (hardcoded patterns)
- `nae_reference_ingest.py::_REFERENCE_CANONICALS` only has Smith identifiers
- **Need**: EN-BAP activation heuristics or generic reference corpus activation
- **Note**: This is a minor gap \u2014 retrieval adapter already supports any source_id

---

## 13. Real Query Test Readiness

### Status: NOT_READY (no EN-BAP data in vector store)

**Evidence**:
- Qdrant nae_ref_v1 contains only Smith Bible Dictionary data
- No EN-BAP entries in any collection
- No EN-BAP activation heuristics implemented

**To enable real query test for EN-BAP**:
1. Acquire raw sources (external)
2. Run canonicalization (same pipeline as Smith)
3. Add manifest entries (source_manifest.yaml)
4. Run reference corpus ingestion (nae_reference_ingest.py with new identifiers)
5. Test with real queries

---

## 14. Source Isolation

### Status: IMPLEMENTED (verified)

**Evidence**:
- Qdrant payload includes `source_id`, `volume`, `identifier` fields
- Point ID scheme: `uuid5(NAMESPACE, f"{identifier}:{chunk_index}")` \u2014 deterministic per source
- Smith entries have `source_id: BAP-REF-SMITH-VOL01~04`
- EN-BAP entries would have `source_id: EN-BAP-001~010` (no collision possible)

**Path verification**:
```
Raw source: NAE/corpus/raw/archive_org/reference/EN-BAP-XXX/
  \u2192 identifier: "EN-BAP-XXX"
Canonical: NAE/corpus/canonical/EN-BAP-XXX/
  \u2192 identifier: "EN-BAP-XXX" (in canonical.json)
Embedding: cache hash of content
  \u2192 source_id passed through payload
Qdrant: nae_ref_v1
  \u2192 source_id: "EN-BAP-001" (example)
Retrieval: search_reference() filters by source_id
  \u2192 source provenance preserved
Citation: source_id in result schema
  \u2192 deterministic citation
```

**No collision risk**: Smith uses `BAP-REF-SMITH-VOLxx` prefix; EN-BAP would use `EN-BAP-xxx` prefix. Different namespaces, no overlap.

---

## 15. Smith Baseline Comparison

| Pipeline Stage | Smith | EN-BAP | Gap |
|---------------|-------|--------|-----|
| Acquisition | COMPLETED (manual) | NOT ACQUIRED | **BLOCKER** \u2014 external download needed |
| Validation | CHECKSUM VERIFIED | NOT APPLICABLE (no source) | Resolved by acquisition |
| Canonicalization | 63,112 paragraphs | SAME PIPELINE | **NONE** \u2014 ready to use |
| Registration | MANIFEST + STATE | NEEDS MANIFEST ENTRIES | **OPERATIONAL** \u2014 add entries |
| TSU | ~115 entries (scripture) | NOT APPLICABLE | **NONE** \u2014 reference corpus used |
| Embedding | 34,948 points (Smith) | SAME PIPELINE | **NONE** \u2014 BGE-M3 handles English |
| Vector Store | nae_ref_v1 (34,948 pts) | SAME COLLECTION | **NONE** \u2014 source_id isolation works |
| Retrieval | smith_activation.py | NEEDS EN-BAP HEURISTICS | **MINOR** \u2014 adapter is generic |
| Application Test | 7/7 PASS | NOT TESTED (no data) | Resolved by ingestion |

### Smith Reusability Assessment

**Can Smith's pipeline be reused for EN-BAP?** YES, with the following caveats:

1. **Canonicalization**: Direct reuse \u2014 same `normalize_item()` works for any OCR/djvu source
2. **Embedding**: Direct reuse \u2014 BGE-M3 handles English natively
3. **Reference ingestion**: Direct reuse \u2014 `ingest()` is parameterized by identifier/source_id
4. **Registration**: Manual step \u2014 add entries to `source_manifest.yaml`
5. **Activation**: Minor gap \u2014 need EN-BAP-specific or generic reference activation

**No architectural changes required.** The pipeline was designed for extensibility.

---

## 16. EN-BAP Readiness Matrix

| # | Source ID | Title | Raw Source | Manifest | Canonical | Embedding | Qdrant | Ready? |
|---|-----------|-------|------------|----------|-----------|-----------|--------|--------|
| 1 | EN-BAP-001 | New Bible Dictionary (3rd ed.) | NOT FOUND | NO | NO | NO | NO | NO |
| 2 | EN-BAP-002 | EDT | NOT FOUND | NO | NO | NO | NO | NO |
| 3 | EN-BAP-003 | DLNT | NOT FOUND | NO | NO | NO | NO | NO |
| 4 | EN-BAP-004 | BSBD | NOT FOUND | NO | NO | NO | NO | NO |
| 5 | EN-BAP-005 | BDAG | NOT FOUND | NO | NO | NO | NO | NO |
| 6 | EN-BAP-007 | Nelson's | NOT FOUND | NO | NO | NO | NO | NO |
| 7 | EN-BAP-008 | Holman | NOT FOUND | NO | NO | NO | NO | NO |
| 8 | EN-BAP-009 | Anchor Bible | NOT FOUND | NO | NO | NO | NO | NO |
| 9 | EN-BAP-010 | ISBE | NOT FOUND | NO | NO | NO | NO | NO |

---

## 17. Gaps

### Gap 1: Acquisition (BLOCKER)
- **Severity**: BLOCKING
- **Description**: No code exists to acquire external sources
- **Impact**: Cannot proceed without raw source files
- **Resolution**: Manual acquisition required (purchase, library access, archive.org)

### Gap 2: Manifest Registration (OPERATIONAL)
- **Severity**: NON-BLOCKING
- **Description**: EN-BAP entries not in `source_manifest.yaml` or `registration_state.json`
- **Impact**: Pipeline won't recognize EN-BAP sources until entries are added
- **Resolution**: Add entries to `source_manifest.yaml` (schema supports arbitrary sources)

### Gap 3: Activation Heuristics (MINOR)
- **Severity**: NON-BLOCKING
- **Description**: `smith_activation.py` is Smith-specific; no EN-BAP activation
- **Impact**: EN-BAP retrieval won't be triggered automatically
- **Resolution**: Add EN-BAP-specific patterns or generic reference corpus activation

### Gap 4: Reference Canonical Registry (MINOR)
- **Severity**: NON-BLOCKING
- **Description**: `nae_reference_ingest.py::_REFERENCE_CANONICALS` only has Smith identifiers
- **Impact**: CLI won't recognize EN-BAP identifiers without `--canonical-path` override
- **Resolution**: Add EN-BAP entries to `_REFERENCE_CANONICALS` dict or use `--canonical-path`

---

## 18. Blockers

### BLOCKER: Raw Source Acquisition
- None of the 9 EN-BAP sources exist in the repository
- No acquisition mechanism exists in code
- External action required (purchase, library access, archive.org)

### NON-BLOCKER: Pipeline Configuration
- All pipeline stages are ready to handle EN-BAP sources
- No architectural changes needed
- Only operational steps remain (manifest entries, ingestion)

---

## 19. Recommended Next Step

```
STEP 1: Acquire raw source files for EN-BAP-001 (New Bible Dictionary)
        \u2192 Place in NAE/corpus/raw/archive_org/reference/EN-BAP-001/

STEP 2: Add manifest entry to source_manifest.yaml
        \u2192 source_id: EN-BAP-001, title, author, checksum, etc.

STEP 3: Run canonicalization
        \u2192 python -c "from NAE.pipeline.canonical import pipeline; ... normalize_item(...)"

STEP 4: Run reference corpus ingestion
        \u2192 python scripts/nae_reference_ingest.py --identifier EN-BAP-001 --apply

STEP 5: Verify in Qdrant
        \u2192 Check nae_ref_v1 for new source_id entries

STEP 6: Test with real queries
        \u2192 Use search_reference() with EN-BAP content
```

**Pilot approach**: Process EN-BAP-001 first (single volume), verify all stages, then proceed to remaining sources.

---

## 20. Mutation Audit

| Action | Performed? | Evidence |
|--------|-----------|----------|
| Source download | NO | No acquisition code exists |
| External acquisition | NO | No external requests made |
| Source modification | NO | No files modified |
| Canonicalization execution | NO | No pipeline runs executed |
| TSU generation | NO | Not applicable (reference corpus) |
| Embedding execution | NO | No embedding runs executed |
| Qdrant write | NO | Qdrant not running; no writes attempted |
| Chroma write | NO | chroma_db/ is empty |
| Registration mutation | NO | No manifest/state changes |
| Cache mutation | NO | No cache changes |
| Code modification | NO | No code changes |
| Git add | NO | git status unchanged |
| Git commit | NO | No commits made |

**Production mutation: 0**
**Corpus mutation: 0**
**TSU mutation: 0**
**Qdrant mutation: 0**
**Embedding execution: 0**
**Cache mutation: 0**
**Code changes: 0**

---

## 21. Git Status

```
Modified files: 2 (NAE/smith_activation.py, docs/STATE.md, ui/pages/chat.py)
Deleted files: 6 (test_seal_* directories)
Untracked files: 8 (PHASE1 documents from prior sessions)
Total status entries: 23
```

**This audit**: No changes to git status. All investigation was read-only.

---

## 22. Final Decision

### Determination: CONDITIONAL \u2014 PIPELINE GAP

**Rationale**:

1. **Pipeline infrastructure EXISTS and WORKS** for Smith Bible Dictionary (Application Gate PASS)
2. **Same pipeline CAN HANDLE EN-BAP sources** \u2014 no architectural changes needed
3. **9 EN-BAP sources are NOT ACQUIRED** \u2014 this is the primary blocker
4. **Registration entries MISSING** \u2014 operational gap, not architectural
5. **Activation heuristics MINOR GAP** \u2014 adapter is generic; only trigger patterns need updating

### Why NOT READY_FOR_EN_BAP_001:

- Raw source files do not exist in repository
- No acquisition mechanism exists in code
- Without raw sources, no pipeline stage can execute
- This is a data availability issue, not a code issue

### Why NOT BLOCKED \u2014 ARCHITECTURAL ISSUE:

- All pipeline stages are designed for extensibility
- Canonicalization is source-agnostic
- Embedding handles English natively (BGE-M3)
- Reference corpus ingestion is parameterized
- Source isolation via source_id works for any prefix pattern

### Why NOT NOT_READY \u2014 REQUIRED SOURCE INFRASTRUCTURE MISSING:

- The infrastructure EXISTS (canonicalization, embedding, reference ingestion, Qdrant)
- Only the data (raw sources) and registration entries are missing
- These are operational gaps, not infrastructure gaps

### Recommended Path Forward:

```
EN-BAP-001 pilot acquisition \u2192 canonicalization \u2192 ingestion \u2192 verification
    \u2193 [All stages use existing Smith pipeline]
    \u2193
If PASS: Proceed to remaining EN-BAP sources
If FAIL: Identify specific stage failure and fix
```

**One Pipeline. One Config. One Retrieval Engine. One Execution State.**

---

**Audit Mode**: READ-ONLY FORENSIC AUDIT
**Mutations**: 0
**Git add/commit**: NO
**Report generated**: 2026-08-26
