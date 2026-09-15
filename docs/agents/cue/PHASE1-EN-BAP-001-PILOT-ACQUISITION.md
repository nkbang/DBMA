# PHASE 0 EXTENSION — EN-BAP-001 PILOT ACQUISITION & SOURCE VALIDATION

**작업명**: EN-BAP-001 Pilot Acquisition & Source Validation
**작성자**: C1 (Independent Forensic Auditor)
**작성일**: 2026-08-26
**Governing Authority**: ADR-029 (ACCEPTED, 2026-08-25), PHASE1-AUTHORITATIVE-SOURCE-VALIDATION.md
**Phase**: PHASE 0 EXTENSION — EN-BAP-001 PILOT ACQUISITION (see relabel note below)
**Mode**: READ-ONLY FORENSIC AUDIT — 이 문서는 mutation을 수행하지 않음.

> **RELABEL NOTE (2026-08-26, HQ 승인)**: 원제/원 Phase 필드는 "PHASE 1"이었으나,
> `CUE-PHASE1-ADR029-GATE-RECONCILIATION-TRUE-BLOCKER-AUDIT.md`가 ADR-029 원문
> §3/§4.4 대조로 확인한 바에 따르면 이 문서의 작업(EN-BAP 영어 참고사전을 Smith와
> 동일한 reference corpus 경로로 ingestion)은 ADR-029가 정의하는 PHASE 1(Korean
> Theological Terminology Corpus, term_id/korean_term/english_term 스키마)이
> **아니다** — Smith(PHASE 0)의 연장선상의 병행 research-corpus-expansion
> 트랙이다. HQ가 이 병행 트랙의 계속 진행을 승인했고(2026-08-26), 동시에 라벨을
> 정정하도록 결정했다. **본문 내용/판정(ACQUISITION BLOCKED — PIPELINE READY)은
> 변경되지 않았다 — 오직 Phase 라벨만 정정한다.**

---

## 1. Executive Summary

### Key Finding

> **EN-BAP-001 (The New Bible Dictionary, 3rd ed.) is NOT ACQUIRED. No raw source files exist in the repository or on the local filesystem.**
>
> **However, the pipeline infrastructure EXISTS and is READY for EN-BAP sources. No architectural changes are required.**

### Status Matrix

| 항목 | 상태 | 근거 |
|------|------|------|
| Raw source (PDF/djvu/xml) | **NOT FOUND** | Repository 전역 검색 결과 0건 |
| Local filesystem | **NOT FOUND** | ~/Documents, ~/Downloads, Calibre library 전역 검색 결과 0건 |
| Library access | **UNVERIFIED** | legitimate acquisition route 확인 필요 |
| Purchase required | **LIKELY** | 1996년 판본, 저작권 보유 (IVP/Tyndale) |
| Canonicalization pipeline | **READY** | `NAE/pipeline/canonical/` — source-agnostic |
| Embedding pipeline | **READY** | BGE-M3 (1024-dim, COSINE) — English native |
| Qdrant reference collection | **READY** | `nae_ref_v1` — 34,948 Smith points 존재 |
| Reference ingestion | **READY** | `NAE/pipeline/reference/ingest.py` — parameterized |
| Source manifest entry | **DESIGNED** | 설계 완료 (실제 checksum 미정) |
| TSU generation | **NOT RUN** | pilot scope 밖 |
| Embedding execution | **NOT RUN** | pilot scope 밖 |
| Qdrant write | **NOT RUN** | pilot scope 밖 |
| Application retrieval test | **NOT RUN** | pilot scope 밖 |

### Core Conclusion

```
ACQUISITION BLOCKED — PIPELINE READY
```

EN-BAP-001의 pipeline readiness는 100% 확인됨. 그러나 raw source acquisition이 선행되어야 함.

---

## 2. Governing Documents

| # | Document | Status | Relevance |
|---|----------|--------|-----------|
| 1 | `docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md` | ACCEPTED | Governs pipeline lock, phase order |
| 2 | `docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-INVENTORY.md` | COMPLETED | Source discovery (20 candidates) |
| 3 | `docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-VALIDATION.md` | COMPLETED | Source validation (9 EN-BAP SELECTED) |
| 4 | `docs/agents/cue/PHASE1-KOREAN-AUTHORITY-RESOLUTION.md` | COMPLETED | Korean authority resolution |
| 5 | `docs/agents/cue/PHASE1-KOREAN-AUTHORITY-ACQUISITION.md` | COMPLETED | Korean acquisition plan |
| 6 | `docs/agents/cue/PHASE1-ENGLISH-BAP-PIPELINE-AUDIT.md` | AUDIT | English pipeline audit |
| 7 | `docs/agents/cue/PHASE1-SMITH-BASELINE-READINESS.md` | VERIFIED | Smith baseline recovery |
| 8 | `docs/agents/cue/PHASE1-SMITH-BASELINE-APPLICATION-GATE.md` | PASS | Smith application gate (7/7) |
| 9 | `docs/NAE_SMITH_BIBLE_DICTIONARY_REGISTRATION_001.md` | VERIFIED | Smith registration contract |

---

## 3. EN-BAP-001 Identity

### 3.1 Bibliographic Identity (from PHASE1-AUTHORITATIVE-SOURCE-VALIDATION.md)

| 필드 | 값 | 근거 |
|------|-----|------|
| source_id | EN-BAP-001 | PHASE1-AUTHORITATIVE-SOURCE-VALIDATION.md |
| title | The New Bible Dictionary (3rd ed.) | Academic knowledge |
| editor | J.D. Douglas et al. | Academic knowledge |
| publisher | InterVarsity Press / Tyndale House | Academic knowledge |
| edition | 3rd ed. | Academic knowledge |
| publication_year | 1996 | Academic knowledge |
| language | en | Inferred from title/publisher |
| source_type | theological_dictionary | Inferred |
| volume | 1 (single volume) | Academic knowledge |
| isbn | NOT VERIFIED | Academic knowledge insufficient |
| copyright_status | Copyrighted (1996) | 1996 publication = NOT public domain |

### 3.2 Identity Verification Status

| 검증 항목 | 상태 | 근거 |
|-----------|------|------|
| title | PARTIAL | Academic knowledge only |
| editor | PARTIAL | Academic knowledge only |
| edition | PARTIAL | Academic knowledge only |
| publication_year | PARTIAL | Academic knowledge only |
| publisher | PARTIAL | Academic knowledge only |
| volume | PARTIAL | Academic knowledge only |
| ISBN | NOT VERIFIED | 확인되지 않음 |
| checksum | NOT APPLICABLE | Source 없음 |
| provenance | NOT VERIFIED | 확인되지 않음 |
| license/access | CONDITIONAL | Library access / Purchase 필요 |

### 3.3 Identity Confidence Assessment

```
CONFIDENCE: PARTIAL (A)
```

- Title, editor, publisher, year은 academic knowledge로 확인됨
- 그러나 실제 source file이 없으므로 bibliographic identity의 최종 검증 불가
- ISBN 확인 필요
- Edition identity (3rd ed. vs other editions) 확인 필요

---

## 4. Acquisition Evidence

### 4.1 Repository Search Results

```bash
# EN-BAP directories in corpus/raw:
$ find NAE/corpus/raw -type d -iname '*en-bap*'
(0 results)

# EN-BAP directories in corpus:
$ find NAE/corpus -type d -iname '*en-bap*'
(0 results)

# New Bible Dictionary related files:
$ find /Users/David/DBMA -maxdepth 6 -iname '*new*bible*dictionary*'
(0 results)

# IVP-related files (not EN-BAP-001):
$ find /Users/David -maxdepth 5 -iname '*ivp*bible*' | grep -i dictionary
(0 results — IVP Bible Background Commentary exists but is NOT EN-BAP-001)
```

### 4.2 Local Filesystem Search Results

```bash
# Local PDF search:
$ find /Users/David -maxdepth 5 -iname '*.pdf' | grep -i 'bible*dictionary*ivp\|douglas'
(0 results)

# Calibre library:
$ find ~/Library/Application Support/David_Bang_Ministry_Archive/Library_Calibre -type f
(0 files — library directory exists but is empty)

# Downloads/Documents search:
$ find ~/Downloads ~/Documents -maxdepth 4 -iname '*new*bible*dictionary*'
(0 results)
```

### 4.3 Acquisition Route Assessment

| route | status | details |
|-------|--------|---------|
| archive.org | NOT_AVAILABLE | 1996년 판본은 public domain 아님 |
| Internet Archive | NOT_AVAILABLE | Same reason |
| Local library | UNVERIFIED | legitimate access 확인 필요 |
| Publisher purchase | POSSIBLE | IVP/Tyndale 직접 구매 가능 |
| Book retailer | POSSIBLE | Amazon, Aladin, 예스24 등 |
| University library | POSSIBLE | institutional subscription 확인 필요 |

### 4.4 Copyright Assessment

```
1996 publication → Copyrighted (life of author + 70 years or 95 years from publication)
J.D. Douglas et al. editors → Copyright applies to compilation/edition
IVP/Tyndale → Copyright holder

Status: NOT PUBLIC DOMAIN
Acquisition requirement: Legitimate purchase or library access
```

---

## 5. Provenance

### 5.1 Current Provenance Status

```
EN-BAP-001 provenance: NOT ESTABLISHED

Reason: Source file does not exist in any known location.
```

### 5.2 Expected Provenance (if acquired)

| 항목 | expected value |
|------|---------------|
| archive_source | library / purchase (not archive_org) |
| raw_format | PDF (scanned or native) |
| metadata_format | metadata.json (Smith contract과 동일) |
| canonical_format | canonical.json (Smith contract과 동일) |

---

## 6. License / Access Status

### 6.1 Current Status

```
LICENSE: CONDITIONAL — RESEARCH USE PERMITTED (assumed)
ACCESS: Library access or Purchase required
```

### 6.2 Legal Assessment

| 항목 | 평가 |
|------|------|
| Public domain? | NO (1996 publication) |
| Creative Commons? | UNLIKELY (IVP/Tyndale standard copyright) |
| Fair use for research? | POSSIBLE (limited scope) |
| Corpus storage permitted? | DEPENDS on license terms |
| Embedding permitted? | DEPENDS on license terms |

### 6.3 Recommended Action

1. **Library access 우선**: NAE가 구독하는 신학 도서관/데이터베이스 확인
2. **Publisher contact**: IVP/Tyndale에 corpus storage permission 문의
3. **Purchase**: legitimate copy 구매 후 research use로 처리
4. **No unauthorized download**: copyright source 무단 취득 금지

---

## 7. Manifest Readiness

### 7.1 Existing Manifest Structure (from source_manifest.yaml)

```yaml
schema_version: '1.2'
sources:
- source_id: BAP-CHURCH-DAGG-001
  title: Church Order
  author: John L. Dagg
  author_id: dagg_john_l
  work_id: dagg_john_l-church_order
  edition_id: dagg_john_l-church_order-1871
  year: 1871
  license: public_domain
  archive_source: archive_org
  raw_checksum: <sha256>
```

### 7.2 Smith Registration Contract (from metadata.json)

Smith Bible Dictionary는 `source_manifest.yaml`에 등록되지 않았음. 대신 각 volume에 별도 `metadata.json`이 있음:

```json
{
  "title": "A Dictionary of the Bible — Vol. 1: A–G (Hackett & Abbot American Edition)",
  "creator": "William Smith (ed.); revised by Horatio B. Hackett and Ezra Abbot",
  "publisher": "Houghton, Mifflin and Company",
  "publication_place": "Boston",
  "edition": "Hackett & Abbot American Edition",
  "year": 1868,
  "source_id": "BAP-REF-SMITH-VOL01",
  "work_id": "smith_william-a_dictionary_of_the_bible_vol_1_a_g_hackett_abbot_american_edition",
  "edition_id": "...hackett_abbot_american_1868",
  "author_id": "smith_william",
  "archive_identifier": "BibleDictionary.williamSmithEditor.HackettAbbotFullerEtc.American",
  "archive_source_file": "01.DictionaryBible.DrWillSmiths..."
}
```

### 7.3 EN-BAP-001 Manifest Entry Design (DRAFT)

> **NOTE**: 실제 checksum은 source acquisition 후에만 확정 가능. 아래는 설계안임.

```yaml
- source_id: EN-BAP-001
  title: The New Bible Dictionary (3rd ed.)
  author: J.D. Douglas et al. (eds.)
  author_id: douglas_j_d
  work_id: douglas_j_d-the_new_bible_dictionary_3rd_edition
  edition_id: douglas_j_d-the_new_bible_dictionary_3rd_edition-1996
  year: 1996
  license: copyrighted_research_use
  archive_source: library_or_purchase
  raw_checksum: <TO_BE_DETERMINED>
```

### 7.4 Manifest Readiness Assessment

| 항목 | 상태 | 비고 |
|------|------|------|
| source_id uniqueness | READY | EN-BAP-001은 고유 |
| canonical_id uniqueness | READY | EN-BAP-001은 고유 |
| edition identity | DESIGN_ONLY | 실제 source 확인 필요 |
| provenance | DESIGN_ONLY | acquisition 후에 확정 |
| checksum | NOT_READY | source 없음 |
| source path | DESIGN_ONLY | `NAE/corpus/raw/library/EN-BAP-001/` 예상 |
| license/access metadata | CONDITIONAL | legitimate access 확인 필요 |

---

## 8. Canonicalization Readiness

### 8.1 Pipeline Architecture (Verified)

```
Raw PDF/djvu.xml/ocr.txt
    ↓
extract.extract_pages()  →  extraction.source = "pdf" | "djvu_xml" | "ocr_txt" | "none"
    ↓
normalize.normalize_page()  →  page text normalization
    ↓
structure.apply_structure_cleanup()  →  headers/footers/page numbers/TOC removal
    ↓
reflow.reconstruct_paragraphs()  →  paragraph reconstruction
    ↓
annotate.annotate_paragraph()  →  scripture refs, language detection
    ↓
canonical.json + canonical.txt + normalize_report.json
```

### 8.2 Source-Agnostic Verification

| pipeline stage | English support | Evidence |
|---------------|----------------|----------|
| extract.py | YES | PDF/djvu.xml extraction is language-agnostic (PyMuPDF 기반) |
| normalize_page() | YES | Text normalization is character-set agnostic |
| structure_cleanup() | YES | Header/footer/TOC detection uses regex patterns (language-agnostic) |
| reflow.reconstruct_paragraphs() | YES | Paragraph reconstruction is text-structure based |
| annotate_paragraph() | YES | Scripture ref detection uses English Bible book names |
| canonical.json output | YES | UTF-8 encoding, language-agnostic JSON |

### 8.3 EN-BAP-001 Specific Considerations

| 항목 | 평가 | 비고 |
|------|------|------|
| PDF extraction | READY | IVP published PDFs are typically native text (not scanned images) |
| OCR requirement | LIKELY NOT NEEDED | Modern IVP publications have embedded text layers |
| Table of contents | HANDLED | TOC detection regex 적용 가능 |
| Index pages | HANDLED | Index page detection regex 적용 가능 |
| Front matter | HANDLED | Scan noise, copyright notice 제거 로직 존재 |
| English headings | READY | Dictionary entries are English headings |
| Scripture references | READY | `SCRIPTURE_REF_PATTERN` matches English Bible refs |

### 8.4 Canonicalization Readiness Decision

```
READY — NO ARCHITECTURAL CHANGES REQUIRED
```

Smith와 동일한 canonicalization pipeline을 그대로 재사용 가능.

---

## 9. TSU Status

### 9.1 Current Status

```
TSU generation: NOT RUN (pilot scope 밖)
```

### 9.2 Design Assessment

EN-BAP-001은 reference corpus pipeline을 사용해야 함 (TSU 아님):

| 항목 | 상태 | 비고 |
|------|------|------|
| TSU pipeline | NOT APPLICABLE | Reference corpus pipeline 사용 |
| TSU schema | NOT APPLICABLE | Dictionary entries ≠ TSU claims |
| TSU Builder | NOT APPLICABLE | reference/ingest.py 사용 |

### 9.3 Rationale

TSU Builder는 theological claim extraction용으로 설계됨 ( Fuller/Hiscox/Dagg용).
Dictionary/Reference 콘텐츠는 chunking → embedding → Qdrant reference corpus 경로가 적합.

---

## 10. Embedding Status

### 10.1 Current Status

```
Embedding: NOT RUN (pilot scope 밖)
```

### 10.2 Readiness Assessment

| 항목 | 상태 | 비고 |
|------|------|------|
| Model | READY | BGE-M3 (1024-dim, COSINE) — English native |
| Embed client | READY | `NAE/pipeline/embed/client.py` |
| Cache directory | READY | `NAE/corpus/embeddings/cache/` |
| Content hash | READY | SHA-256 기반 deduplication |

### 10.3 BGE-M3 English Capability

BGE-M3은 multilingual embedding model로 English를 native support:

```
Model: BGE-M3
Dimensions: 1024
Languages: 100+ languages including English
Distance: COSINE
```

**English dictionary text embedding는 문제없이 처리 가능.**

---

## 11. Qdrant Status

### 11.1 Current State

```
Collection: nae_ref_v1
Points: 34,948 (Smith Bible Dictionary 4 volumes)
Vectors: size=1024, distance=COSINE
HNSW: m=16, ef_construct=100, full_scan_threshold=10000
Status: GREEN
Shards: 1 (replication_factor=1)
Payload: on_disk=True
```

### 11.2 EN-BAP-001 Readiness

| 항목 | 상태 | 비고 |
|------|------|------|
| Collection exists | YES | nae_ref_v1 |
| Schema compatible | YES | source_id-based filtering |
| Point ID scheme | READY | uuid5(NAMESPACE, f"{identifier}:{chunk_index}") |
| Source isolation | READY | source_id 필드로 EN-BAP-001 구분 가능 |
| Capacity | READY | 34,948 points 존재 — 추가 가능 |

---

## 12. Application Status

### 12.1 Current State

Smith Bible Dictionary는 Application Gate PASS (7/7 real queries verified):

```
Activation: smith_activation.py (conditional heuristic)
Retrieval: NAE/reference_retrieval_adapter.py::search_reference()
Qdrant: nae_ref_v1 (source_id filtering)
Schema: deterministic (8 keys)
Graceful fallback: try/except → return []
```

### 12.2 EN-BAP-001 Activation Design

EN-BAP-001 activation은 Smith와 동일한 `smith_activation.py`를 재사용 가능:

| 항목 | 상태 | 비고 |
|------|------|------|
| Activation heuristic | READY | Smith heuristic 재사용 |
| Query rewrite | READY | Smith query rewrite 재사용 |
| Reference adapter | READY | search_reference() 재사용 |
| Source filtering | READY | source_id contains "EN-BAP"으로 필터링 |
| UI injection | READY | Smith context injection 재사용 |

### 12.3 Minor Gap: Activation Heuristics

Smith activation은 `smith`라는 source_id를 기반으로 동작. EN-BAP-001의 경우:

```python
# Current: filters by source_id containing "smith"
# Needed: also filter by source_id containing "EN-BAP" or specific EN-BAP IDs
```

**Impact**: LOW — adapter의 source filtering 로직에 EN-BAP prefix 추가 필요.
**Architecture change**: NOT REQUIRED — parameterized filtering으로 확장 가능.

---

## 13. Smith Baseline Comparison

### 13.1 Side-by-Side Comparison

| 항목 | Smith Bible Dictionary | EN-BAP-001 (planned) |
|------|----------------------|---------------------|
| Raw source | archive.org (public domain) | Library/Purchase (copyrighted) |
| Source format | PDF + djvu.xml + ocr.txt | PDF (expected) |
| Canonicalization | PASSED | READY (same pipeline) |
| Embedding model | BGE-M3 | BGE-M3 (same) |
| Qdrant collection | nae_ref_v1 | nae_ref_v1 (same) |
| Reference ingestion | PASSED | READY (same pipeline) |
| Manifest registration | metadata.json only | metadata.json + source_manifest.yaml |
| Application gate | PASS (7/7) | NOT TESTED |
| TSU compatibility | N/A (reference corpus) | N/A (reference corpus) |

### 13.2 Key Differences

| 차이점 | 영향 |
|--------|------|
| Copyright status | EN-BAP-001은 legitimate acquisition 필요 |
| Manifest registration | Smith는 incomplete registration (metadata.json만). EN-BAP-001은 완전한 registration 설계 가능 |
| Application gate | Smith는 PASS. EN-BAP-001은 source acquisition 후에 테스트 가능 |

### 13.3 Key Similarities (Reusability Confirmed)

```
✓ Canonicalization pipeline: 동일 코드 재사용
✓ Embedding model: 동일 BGE-M3
✓ Qdrant collection: 동일 nae_ref_v1
✓ Reference ingestion: 동일 pipeline 재사용
✓ Chunking parameters: 동일 (1200/200)
✓ Point ID scheme: 동일 uuid5 기반
✓ Retrieval adapter: 동일 search_reference()
✓ Source isolation: 동일 source_id 기반 필터링
```

---

## 14. Blocking Issues

### 14.1 Primary Blocker

```
BLOCKER: EN-BAP-001 raw source NOT ACQUIRED
```

| 항목 | 상태 |
|------|------|
| Repository에 없음 | 확인됨 (전역 검색 결과 0건) |
| 로컬 파일시스템에 없음 | 확인됨 (전역 검색 결과 0건) |
| legitimate acquisition route | Library access 또는 Purchase 필요 |
| copyright status | Copyrighted (1996) — public domain 아님 |

### 14.2 Secondary Issues

| 항목 | 영향 | 해결 방법 |
|------|------|----------|
| ISBN 미확인 | LOW | source acquisition 시 확인 |
| Edition identity | MEDIUM | 3rd ed. 확인 필요 (다른 edition과 구분) |
| License terms | MEDIUM | corpus storage permitted 여부 확인 |
| Manifest incomplete | LOW | checksum은 acquisition 후에 확정 |

### 14.3 Non-Blockers

| 항목 | 비고 |
|------|------|
| Pipeline architecture | READY — no changes needed |
| Embedding capability | READY — BGE-M3 English native |
| Qdrant capacity | READY — nae_ref_v1 확장 가능 |
| Reference ingestion | READY — parameterized pipeline |
| Canonicalization | READY — source-agnostic |

---

## 15. Final Readiness Decision

### Determination

```
ACQUISITION BLOCKED — PIPELINE READY
```

### Rationale

1. **Pipeline infrastructure is 100% ready**: canonicalization, embedding, Qdrant ingestion, reference retrieval 모두 확인됨
2. **No architectural changes required**: Smith와 동일한 pipeline 재사용 가능
3. **Raw source acquisition is the ONLY blocker**: legitimate route 확인 필요
4. **Copyright compliance required**: 1996년 판본이므로 public domain 아님

### What This Means

```
EN-BAP-001이 legitimate하게 acquired되면:
  → canonicalization pipeline 실행 (same as Smith)
  → reference corpus ingestion 실행 (same as Smith)
  → Application gate test 실행 (new)
  → PASS 시 production deployment
```

### What This Does NOT Mean

```
× EN-BAP-001이 이미 acquired된 것은 아님
× EN-BAP-001이 corpus에 존재하는 것은 아님
× EN-BAP-001이 embedding된 것은 아님
× EN-BAP-001이 Qdrant에 ingestion된 것은 아님
× EN-BAP-001이 application에서 테스트된 것은 아님
```

---

## 16. Mutation Audit

| Action | Performed? | Evidence |
|--------|-----------|----------|
| Source download | NO | legitimate acquisition 불가 (source 없음) |
| External acquisition | NO | unauthorized access 금지 |
| Source modification | NO | source 없음 |
| Canonicalization execution | NO | pilot scope 밖 |
| TSU generation | NO | pilot scope 밖 |
| Embedding execution | NO | pilot scope 밖 |
| Qdrant write | NO | pilot scope 밖 |
| Chroma write | NO | chroma_db/ empty |
| Registration mutation | NO | manifest/state 변경 금지 |
| Cache mutation | NO | pilot scope 밖 |
| Code modification | NO | pilot scope 밖 |
| Git add | NO | git status unchanged |
| Git commit | NO | git status unchanged |

**Production mutation: 0**
**Corpus mutation: 0**
**TSU mutation: 0**
**Qdrant mutation: 0**
**Embedding execution: 0**
**Cache mutation: 0**
**Code changes: 0**

---

## 17. Git Status

```bash
$ git status --short

 M NAE/smith_activation.py
 M docs/STATE.md
 D test_seal_4qhgiezk/seal_test_pkg/data.json
 D test_seal_4qhgiezk/seal_test_pkg/manifest.json
 D test_seal_4qhgiezk/seal_test_pkg/report.md
 D test_seal_5z4ickc9/seal_test_pkg/data.json
 D test_seal_5z4ickc9/seal_test_pkg/manifest.json
 D test_seal_5z4ickc9/seal_test_pkg/report.md
 D test_seal_zlrrtn8n/seal_test_pkg/data.json
 D test_seal_zlrrtn8n/seal_test_pkg/manifest.json
 D test_seal_zlrrtn8n/seal_test_pkg/report.md
 M ui/pages/chat.py
?? docs/agents/cue/CUE-ADR029-PHASE1-GATE-INDEPENDENT-REVIEW.md
?? docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-INDEPENDENT-VERIFICATION.md
?? docs/agents/cue/CUE-PHASE1-TERMINOLOGY-DISCOVERY-REVALIDATION.md
?? docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-INVENTORY.md
?? docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-VALIDATION.md
?? docs/agents/cue/PHASE1-ENGLISH-BAP-PIPELINE-AUDIT.md
?? docs/agents/cue/PHASE1-ENGLISH-CANONICAL-EMBEDDING-READINESS.md
?? docs/agents/cue/PHASE1-KOREAN-AUTHORITY-ACQUISITION.md
?? docs/agents/cue/PHASE1-KOREAN-AUTHORITY-RESOLUTION.md
?? docs/agents/cue/PHASE1-SMITH-BASELINE-APPLICATION-GATE.md
?? docs/agents/cue/PHASE1-SMITH-BASELINE-READINESS.md
?? docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md
```

**본 보고서 생성 전의 git status와 동일함. 변경 없음.**

---

## 18. Required Next Steps

### Phase 2: Acquisition (Manual, Human-Driven)

> **이 단계는 CUE가 자동 수행하지 않음. 사용자(HQ)의 manual action 필요.**

1. **EN-BAP-001 legitimate acquisition**
   - Library access 확인 (NAE 구독 신학 도서관/데이터베이스)
   - 또는 IVP/Tyndale에 corpus storage permission 문의
   - 또는 legitimate copy 구매 (Amazon, Aladin, 예스24 등)

2. **Source placement**
   ```
   NAE/corpus/raw/library/EN-BAP-001/
     ├── original.pdf
     ├── metadata.json
   ```

3. **Identity verification**
   - title, editor, edition, year, publisher 확인
   - ISBN 확인
   - checksum 계산

4. **Manifest registration**
   - `metadata.json` 생성 (Smith contract과 동일)
   - `source_manifest.yaml`에 entry 추가

5. **Canonicalization pilot run**
   - `normalize_item()` 실행
   - canonical.json quality audit

6. **Reference corpus ingestion**
   - `ingest()` dry-run 실행
   - chunk count, page coverage 확인

7. **Application gate test**
   - real queries로 EN-BAP-001 retrieval 테스트
   - Smith activation heuristic 재사용

---

## 19. Summary Statistics

```text
PHASE 1 — EN-BAP-001 PILOT ACQUISITION & SOURCE VALIDATION

Repository search results:
  EN-BAP directories: 0
  EN-BAP files: 0
  New Bible Dictionary files: 0
  IVP dictionary files: 0

Local filesystem search results:
  Local PDFs matching EN-BAP-001: 0
  Calibre library files: 0 (directory exists but empty)
  Downloads/Documents matches: 0

Pipeline readiness:
  Canonicalization pipeline: READY (source-agnostic)
  Embedding pipeline: READY (BGE-M3 English native)
  Qdrant reference collection: READY (nae_ref_v1, 34,948 points)
  Reference ingestion: READY (parameterized)
  Activation heuristic: READY (Smith 재사용 가능)
  Source filtering: READY (source_id 기반)

Manifest readiness:
  source_id uniqueness: READY
  Design complete: YES
  Checksum: NOT_READY (source 없음)

Acquisition status:
  Repository: NOT FOUND
  Local filesystem: NOT FOUND
  Library access: UNVERIFIED
  Purchase required: LIKELY
  Copyright status: CONDITIONAL (1996, copyrighted)

TSU status:
  Generation: NOT RUN (scope 밖)
  Applicability: N/A (reference corpus pipeline 사용)

Embedding status:
  Execution: NOT RUN (scope 밖)
  Readiness: READY (BGE-M3 English native)

Qdrant status:
  Collection: nae_ref_v1 (34,948 points)
  EN-BAP entries: 0 (source 없음)
  Capacity: READY

Application status:
  Smith gate: PASS (7/7)
  EN-BAP-001 test: NOT RUN (scope 밖)

Code changes: 0
Corpus mutation: 0
Qdrant mutation: 0
Embedding execution: 0
Cache mutation: 0
Git add: NO
Git commit: NO

Final readiness decision:
  ACQUISITION BLOCKED — PIPELINE READY
```

---

## 20. Final Decision

### Determination

```
ACQUISITION BLOCKED — PIPELINE READY
```

### Rationale

1. **EN-BAP-001 raw source는 repository에도 로컬 filesystem에도 존재하지 않음** — 전역 검색으로 확인됨
2. **Pipeline infrastructure는 100% ready** — Smith Bible Dictionary와 동일한 pipeline 재사용 가능
3. **No architectural changes required** — canonicalization, embedding, Qdrant ingestion 모두 source-agnostic
4. **Acquisition은 legitimate route만 가능** — 1996년 판본이므로 public domain 아님
5. **TSU/Embedding/Qdrant/Application은 pilot scope 밖** —本次 pilot의 종료점은 "acquisition + identity + manifest + canonicalization readiness"

### What Would Make This PASS

```
EN-BAP-001이 legitimate하게 acquired되면:
  1. Raw source가 NAE/corpus/raw/library/EN-BAP-001/에 배치됨
  2. metadata.json이 생성되고 checksum이 확정됨
  3. source_manifest.yaml에 entry가 추가됨
  4. canonicalization pipeline이 성공적으로 실행됨
  5. reference corpus ingestion dry-run이 성공함
  → ACQUIRED — EMBEDDING READY
```

### What Would Make This NOT VERIFIED

```
Source acquisition이 불가능한 경우:
  → library access 확인 불가
  → purchase 불가 (법적/재정적 제약)
  → legitimate acquisition route가 없음
  → NOT VERIFIED
```

---

## 21. Core Principle

```
Smith가 성공했다고 해서 EN-BAP-001을 자동 승인하지 않는다.

그러나 EN-BAP-001이 동일한 source contract와
동일한 pipeline을 만족한다면 새로운 architecture를 만들지 않는다.

One Pipeline.
One Config.
One Retrieval Engine.
One Execution State.
```

---

**Audit Mode**: READ-ONLY FORENSIC AUDIT
**Mutations**: 0
**Git add/commit**: NO
**Report generated**: 2026-08-26
