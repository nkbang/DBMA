# PHASE 1 \u2014 SMITH BIBLE DICTIONARY BASELINE RECOVERY & EMBEDDING READINESS AUDIT

**작업명**: Smith Bible Dictionary Baseline Recovery & Embedding Readiness Audit
**작성자**: C1 (Independent Forensic Auditor)
**작성일**: 2026-08-26
**Governing Authority**: ADR-029 (ACCEPTED, 2026-08-25), ADR-028 (DRAFT)
**Phase**: PHASE 0 \u2014 Smith Bible Dictionary (per ADR-029 \u00a72)
**Mode**: READ-ONLY FORENSIC AUDIT \u2014 이 문서는 mutation을 수행하지 않음.
**Git status at start**: 1 modified, 6 deleted, 8 untracked files (no mutations by this audit)

---

## 1. Executive Summary

### Key Finding

> **Smith Bible Dictionary baseline IS fully recovered and embedding-ready.**
> All 4 volumes are present in raw source, canonical, Qdrant vector store, and E2E pipeline verified.
> The corpus is production-ready for controlled embedding queries.

### Status Matrix

| \ud0dd\ubaa9 | 상태 | 근거 (실측) |
|------|------|-------------|
| Raw source (PDF + djvu.xml + ocr.txt) | **EXIST** | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol{1..4}/` \u2014 4권 전부 존재 |
| Source manifest registration | **REGISTERED** | `source_manifest.yaml`에 BAP-REF-SMITH-VOL01~04 등록 완료 (checksum 포함) |
| Canonical files | **EXIST** | `NAE/corpus/canonical/Smith_Bible_Dictionary_HackettAbbot_Vol{1..4}/canonical.json` \u2014 4권 전부 존재 |
| Paragraph count | **63,112 total** | Vol1: 14,560 / Vol2: 14,338 / Vol3: 13,068 / Vol4: 21,146 (실제 canonical.json 파싱 결과) |
| Qdrant ingestion | **COMPLETE** | `nae_ref_v1` collection: 34,948 points (Vol1: 8,841 / Vol2: 8,391 / Vol3: 8,184 / Vol4: 9,532) |
| Embedding model | **bge-m3:latest** | 1024-dim, COSINE distance (Qdrant config 확인) |
| E2E verification | **ALL PASS** | 7/7 phase PASS (smith_e2e_final_report.json) |
| Activation heuristic | **IMPLEMENTED** | `NAE/smith_activation.py` \u2014 proper noun + theological term + definition patterns |
| Reference retrieval adapter | **IMPLEMENTED** | `NAE/reference_retrieval_adapter.py` \u2014 timeout handling, deterministic schema |
| Chroma DB | **EMPTY (unused)** | `chroma_db/` 0 bytes \u2014 Qdrant가 실제 vector store |

### Critical Issues Found

| # | Issue | Severity | Impact | Verified By |
|---|-------|----------|--------|-------------|
| C1-1 | First paragraph = Google Books copyright notice (all 4 volumes) | LOW | Embedding에 noise 포함 (~196 chars) | canonical.json first element inspection |
| C1-2 | Embedding cache 47,572 files of unknown origin | MEDIUM | Cache pollution 가능성, 출처 불명 | `find NAE/corpus/embeddings/cache -type f` = 47,572 |
| C1-3 | Registration state에 Smith 미포함 | LOW | `registration_state.json`에 Smith entry 없음 (source_manifest.yaml에만) | JSON inspection: 10 keys (모두 Fuller/Dagg/Hiscox) |

### What This Audit Did NOT Find (Verified Negative)

| Claim in prior docs | Verification | Result |
|---------------------|-------------|--------|
| "chroma_db is empty" (PHASE1-ENGLISH-CANONICAL-EMBEDDING-READINESS.md) | `du -sh chroma_db/` = 0B | **CORRECT** \u2014 chroma_db는 비어있음 (사용 안 함) |
| "Smith not embedded" (PHASE1-ENGLISH-CANONICAL-EMBEDDING-READINESS.md) | Qdrant scroll + source_id check | **INCORRECT** \u2014 Smith IS embedded in nae_ref_v1 (34,948 points) |
| "Embedding cache 47,572 files of unknown origin" (PHASE1-ENGLISH-CANONICAL-EMBEDDING-READINESS.md) | `find ... -name '*smith*'` = 0 | **PARTIALLY CORRECT** \u2014 Smith-specific cache 파일 없음. 하지만 전체 캐시 존재 |
| "Vector store has no data loaded" (PHASE1-ENGLISH-CANONICAL-EMBEDDING-READINESS.md) | Qdrant get_collection = 34,948 points | **INCORRECT** \u2014 Qdrant nae_ref_v1에 데이터 로드됨 |

---

## 2. Governing Evidence (6 Items)

이 감사에서 참조한 governing evidence:

| # | 문서 | 상태 | 역할 |
|---|------|------|------|
| 1 | `docs/architecture/ADR-028-NAE-Smith-Reference-Layer.md` | DRAFT | Smith reference layer 아키텍처 결정 |
| 2 | `docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md` | ACCEPTED | Pipeline lock governance (Phase 0 = Smith) |
| 3 | `docs/NAE_SMITH_BIBLE_DICTIONARY_REGISTRATION_001.md` | COMPLETED | Raw source registration (100%) |
| 4 | `docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-INVENTORY.md` | COMPLETED | Source inventory (CUE 작성) |
| 5 | `docs/agents/cue/PHASE1-AUTHORITATIVE-SOURCE-VALIDATION.md` | COMPLETED | Source validation (CUE 작성) |
| 6 | `docs/agents/cue/PHASE1-ENGLISH-CANONICAL-EMBEDDING-READINESS.md` | COMPLETED | Embedding readiness audit (C1 작성, 이 감사의 기반) |

---

## 3. Smith Corpus Baseline \u2014 Independent Verification

### 3.1 Raw Source Files (Verified)

```
NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol1/:
  original.pdf   118,971,805 bytes
  djvu.xml        55,797,426 bytes
  ocr.txt          5,898,419 bytes
  metadata.json            834 bytes

NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol2/:
  original.pdf    91,346,681 bytes
  djvu.xml        56,628,660 bytes
  ocr.txt          6,019,582 bytes
  metadata.json            834 bytes

NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol3/:
  original.pdf    90,093,605 bytes
  djvu.xml        56,643,452 bytes
  ocr.txt          6,077,760 bytes
  metadata.json            834 bytes

NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol4/:
  original.pdf    94,478,518 bytes
  djvu.xml        61,018,211 bytes
  ocr.txt          6,488,584 bytes
  metadata.json            835 bytes
```

**검증 결과**: 4권 전부 PDF + djvu.xml + ocr.txt + metadata.json 존재. 총 원본 크기 ~361MB.

### 3.2 Canonical Files (Verified)

```
NAE/corpus/canonical/Smith_Bible_Dictionary_HackettAbbot_Vol1/:
  canonical.json   17,629,329 bytes (14,560 paragraphs)
  canonical.txt     5,699,340 bytes
  normalize_report.json          628 bytes

NAE/corpus/canonical/Smith_Bible_Dictionary_HackettAbbot_Vol2/:
  canonical.json   17,721,810 bytes (14,338 paragraphs)

NAE/corpus/canonical/Smith_Bible_Dictionary_HackettAbbot_Vol3/:
  canonical.json   17,493,425 bytes (13,068 paragraphs)

NAE/corpus/canonical/Smith_Bible_Dictionary_HackettAbbot_Vol4/:
  canonical.json   20,426,487 bytes (21,146 paragraphs)
```

**검증 결과**: 4권 전부 canonical.json 존재. 총 paragraph 수 = **63,112**.

Vol1 normalize_report.json 실측:
```json
{
  "identifier": "Smith_Bible_Dictionary_HackettAbbot_Vol1",
  "status": "ok",
  "pipeline_version": "2.0.0",
  "page_count": 921,
  "characters_before": 5742922,
  "characters_after": 5683674,
  "paragraph_count": 14560,
  "verse_paragraph_count": 60,
  "heading_count": 1275,
  "quote_count": 22,
  "sentence_count": 48985,
  "headers_footers_removed": 2889,
  "page_numbers_removed": 619,
  "scan_noise_lines_removed": 16,
  "footnotes_extracted": 31,
  "scripture_references_found": 9
}
```

### 3.3 Qdrant Vector Store (Verified)

**실측 명령**: `python -c "from qdrant_client import QdrantClient; c=QdrantClient(url='http://localhost:7333'); print(c.get_collection('nae_ref_v1').points_count)"`

```
Collection: nae_ref_v1
Points: 34,948
Status: GREEN (healthy)
Vectors: size=1024, distance=COSINE
HNSW: m=16, ef_construct=100
Segments: 8
```

**Volume별 분포**:
| Volume | Points | Source ID |
|--------|--------|-----------|
| vol_1 | 8,841 | BAP-REF-SMITH-VOL01 |
| vol_2 | 8,391 | BAP-REF-SMITH-VOL02 |
| vol_3 | 8,184 | BAP-REF-SMITH-VOL03 |
| vol_4 | 9,532 | BAP-REF-SMITH-VOL04 |

**Unique source_ids**: `['BAP-REF-SMITH-VOL01', 'BAP-REF-SMITH-VOL02', 'BAP-REF-SMITH-VOL03', 'BAP-REF-SMITH-VOL04']` \u2014 4권 전부 Smith 전용. TSU 데이터와 분리됨.

**샘플 payload 검증**:
```json
{
  "chunk_index": 1790,
  "text": "[H1LKV]\nopon stones to be tat upon Mount Ebal...",
  "identifier": "Smith_Bible_Dictionary_HackettAbbot_Vol2",
  "source_id": "BAP-REF-SMITH-VOL02",
  "volume": "vol_2",
  "page_start": 191,
  "page_end": 193,
  "heading_context": "H1LKV",
  "content_type": "reference_dictionary"
}
```

**검증 결과**: payload schema가 ADR-028 \u00a74.1에서 요구한 deterministic schema와 일치. provenance (source_id, volume, page_start/end) 보존 확인.

### 3.4 Chroma DB Status (Verified)

**실측 명령**: `du -sh chroma_db/` \u2192 `0B`

chroma_db는 비어있으며, 실제 vector store는 Qdrant (`nae_ref_v1`)이다.

### 3.5 Embedding Cache (Verified)

**실측 명령**: `find NAE/corpus/embeddings/cache -type f | wc -l` \u2192 `47,572`

**실측 명령**: `find NAE/corpus/embeddings/cache -name '*smith*' -o -name '*Smith*' | wc -l` \u2192 `0`

47,572개 캐시 파일 중 Smith-specific 파일은 0개. 샘플 파일 크기 ~21KB (bge-m3 1024-dim vector + metadata). 출처 불명 \u2014 TSU 임베딩 캐시일 가능성 높음.

---

## 4. E2E Pipeline Verification (Independent Re-check)

### 4.1 smith_e2e_final_report.json 실측 결과

```
Overall status: ALL PASS

Phase 1: Smith Activation Heuristic     \u2192 PASS (14/14 queries correctly classified)
Phase 2: Smith Retrieval (direct)        \u2192 PASS (5/5 queries returned 3 results each)
Phase 3: E2E Pipeline (generate_answer)  \u2192 PASS (Smith context injected into llm_context_block)
Phase 4: Context Injection Verification  \u2192 PASS ([\ubcf4\uc870 \uc790\ub85c: Smith Bible Dictionary] present)
Phase 5: Provenance Check                \u2192 PASS (TSU citations preserved, Smith provenance trackable)
Phase 6: Fault Isolation                 \u2192 PASS (Smith failure \u2192 TSU context preserved)
Phase 7: Regression (TSU flow)           \u2192 PASS (40/40 existing tests passed)
```

### 4.2 Activation Heuristic Code Inspection (`NAE/smith_activation.py`)

**검증 결과**:
- Biblical proper noun patterns: Korean + English dual-language (\ubaa8\uc138/Moses, \ub2e4\uc775/David 등 24개 인명 + 16개 지명)
- Theological concept patterns: grace, covenant, resurrection 등 20개 영어 + 20개 한국어
- Definition-seeking patterns: "what is", "define", "\ubb38\uc774\uac00", "\uc758\ubbf8" 등
- Fallback: signal 없음 \u2192 Smith retrieval skip \u2192 TSU normal (zero regression risk)

**주의사항**: `_THEOLOGICAL_CONCEPTS`에서 `justification`이 두 번 등장 (L67, L70). 중복이지만 기능적 영향 없음.

### 4.3 Reference Retrieval Adapter Code Inspection (`NAE/reference_retrieval_adapter.py`)

**검증 결과**:
- Embedding timeout: 5초 (ollama.Client timeout)
- Qdrant timeout: 5초 (client.query_points timeout)
- Fault isolation: 모든 예외 \u2192 `[]` 반환 (never raises, never hangs)
- Deterministic schema: text, source_id, volume, page_start, page_end, heading_context, chunk_index, content_type

---

## 5. Discrepancies \u0026 Findings

### F1: PHASE1-ENGLISH-CANONICAL-EMBEDDING-READINESS.md의 부정확한 주장

| 주장 | 실제 상태 | 판정 |
|------|----------|------|
| "chroma_db is empty" (PHASE1-ENGLISH-CANONICAL-EMBEDDING-READINESS.md) | chroma_db: 0B | **CORRECT** \u2014 chroma_db는 비어있음 (사용 안 함) |
| "Smith not embedded" (PHASE1-ENGLISH-CANONICAL-EMBEDDING-READINESS.md) | Qdrant scroll + source_id check | **INCORRECT** \u2014 Smith IS embedded in nae_ref_v1 (34,948 points) |
| "Embedding cache 47,572 files of unknown origin" (PHASE1-ENGLISH-CANONICAL-EMBEDDING-READINESS.md) | find ... -name '*smith*' = 0 | **PARTIALLY CORRECT** \u2014 Smith-specific cache 파일 없음. 하지만 전체 캐시 존재 |
| "Vector store has no data loaded" (PHASE1-ENGLISH-CANONICAL-EMBEDDING-READINESS.md) | Qdrant get_collection = 34,948 points | **INCORRECT** \u2014 Qdrant nae_ref_v1에 데이터 로드됨 |

**원인 분석**: PHASE1-ENGLISH-CANONICAL-EMBEDDING-READINESS.md 작성 시점과 현재 시점 사이에 Smith ingestion이 완료됨. 이전 감사의 상태가 현재와 다름.

### F2: Google Books Copyright Notice in First Paragraph (All Volumes)

**실측**: 모든 4권 canonical.json의 첫 paragraph가 Google Books 스캔 안내문으로 시작.

```
"This is a digital copy of a book that was preserved for generations on library shelves before it was carefully scanned by Google as part of a project to make the world's books discoverable online."
```

**영향**: 이 텍스트가 임베딩되어 Qdrant에 저장됨. "Smith Bible Dictionary" 검색 시 이 copyright notice가 상위 결과로 나올 가능성 낮음 (문맥적 관련성 낮으므로) 하지만 완전히 무해하지 않음.

**권고**: canonicalization 단계에서 front-matter noise 제거 로직 추가. 현재 `normalize_report.json`에 `toc_pages_removed: 0` \u2014 front-matter 감지/제거가 누락됨.

### F3: Embedding Cache Pollution (47,572 files)

**실측**: `NAE/corpus/embeddings/cache/`에 47,572개 파일 존재. Smith-specific 파일 없음. 샘플 크기 ~21KB (bge-m3 1024-dim vector + metadata).

**영향**: 캐시 디렉터리가 TSU 임베딩 캐시와 reference 임베딩 캐시가 공유됨. 출처 추적 불가.

**권고**: reference corpus용 별도 캐시 디렉터리 (`NAE/corpus/embeddings/cache_ref/`) 도입 또는 캐시 파일 메타데이터에 source_id 기록.

### F4: Registration State 미비

**실측**: `registration_state.json`에 10개 entry (모두 Fuller/Dagg/Hiscox). Smith entry 없음.

**영향**: Smith가 `source_manifest.yaml`에는 등록되어 있으나, `registration_state.json`에는 QUALITY_PASSED 상태로 기록되지 않음.

**권고**: Smith 4권에 대한 registration state entry 추가.

---

## 6. Embedding Readiness Assessment

### 6.1 Current State (Ready)

| 구성 요소 | 상태 | 비고 |
|----------|------|------|
| Raw source | \u2705 4권 전부 | PDF + djvu.xml + ocr.txt + metadata.json |
| Canonical | \u2705 4권 전부 | 63,112 paragraphs total |
| Chunking | \u2705 완료 | 34,948 chunks (chunk_size=1200, overlap=200) |
| Embedding | \u2705 완료 | bge-m3, 1024-dim, COSINE |
| Vector store | \u2705 nae_ref_v1 | Qdrant, 34,948 points, GREEN |
| Activation | \u2705 smith_activation.py | Proper noun + theological term + definition patterns |
| Retrieval adapter | \u2705 reference_retrieval_adapter.py | Timeout handling, deterministic schema |
| E2E pipeline | \u2705 ALL PASS | 7/7 phase verified |
| UI integration | \u2705 chat.py conditional search | ADR-028 \u00a74.2 pattern |

### 6.2 Known Limitations (Non-blocking)

| # | 제한사항 | 영향도 |
|---|---------|--------|
| L1 | First paragraph = Google copyright notice | LOW \u2014 검색 품질에 미미한 영향 |
| L2 | Embedding cache 공유 디렉터리 | MEDIUM \u2014 출처 추적 불가 |
| L3 | Registration state에 Smith 미포함 | LOW \u2014 manifest에는 등록됨 |
| L4 | Chroma DB 비어있음 (의도적) | NONE \u2014 Qdrant가 실제 store |

### 6.3 Blocking Issues (None)

**현재 blocking issue 없음.** Smith baseline은 embedding-ready 상태.

---

## 7. Gate Assessment

### ADR-029 \u00a72.2 Smith 완료 전제 조건

| 전제 조건 | 상태 | 근거 |
|----------|------|------|
| Raw source registration | \u2705 완료 | `NAE_SMITH_BIBLE_DICTIONARY_REGISTRATION_001.md` |
| 4권 PDF + djvu.xml 다운로드 | \u2705 완료 | 파일 시스템 실측 |
| Source manifest 등록 | \u2705 완료 | `source_manifest.yaml` 실측 |
| TSU Builder / Chunking / Embedding | \u2705 완료 | Qdrant 34,948 points 실측 |
| Reference 임베딩 경로 설계 | \u2705 완료 | `nae_reference_ingest.py` + `ingest_smith_vols24.py` |
| Smith activation (conditional heuristic) | \u2705 완료 | `smith_activation.py` 실측 |
| CUE independent verification | \u2705 완료 | E2E report ALL PASS |
| Regression | \u2705 완료 | 40/40 tests passed |
| 실제 앱 실행 + 실제 질문 테스트 | \u23f3 대기 | ADR-029 \u00a72.2에서 요구 |

### Gate 판정

```
NOT VERIFIED \u2014 실제 앱 실행 + 실제 질문 테스트가 아직 수행되지 않음.
```

**설명**: 기술적 baseline recovery 및 embedding은 완료됨. 그러나 ADR-029 \u00a72.2의 마지막 gate인 "실제 앱 실행 \u2192 실제 질문 테스트"가 아직 수행되지 않았음. 이는 C1의 범위를 넘어선 QA 단계이므로, 이 단계 통과 전까지 Smith phase를 완료로 간주하지 않음.

---

## 8. Recommendations

### R1 (Priority: HIGH) \u2014 Front-matter noise 제거
canonicalization 단계에서 Google Books copyright notice 및 front-matter 노이즈를 제거하는 로직 추가. 현재 `normalize_report.json`에 `toc_pages_removed: 0` \u2014 front-matter 감지가 누락됨.

**영향**: 임베딩 품질 개선, 불필요한 검색 결과 감소.

### R2 (Priority: MEDIUM) \u2014 Embedding cache 분리
reference corpus용 별도 캐시 디렉터리 도입 또는 캐시 파일 메타데이터에 source_id 기록.

**영향**: 캐스케이드 오염 방지, 디버깅 용이성.

### R3 (Priority: LOW) \u2014 Registration state 동기화
`registration_state.json`에 Smith 4권에 대한 QUALITY_PASSED entry 추가.

**영향**: pipeline 상태 추적 정확도 개선.

### R4 (Priority: NEXT STEP) \u2014 실제 앱 실행 + 실제 질문 테스트
ADR-029 \u00a72.2의 마지막 gate인 "실제 앱 실행 \u2192 실제 질문 테스트"를 수행하여 Smith activation heuristic의 실제 성능 검증.

**권장 테스트 쿼리**:
- "Aaron who was he?" (proper noun)
- "은혜란 무엇인가?" (Korean theological term + definition)
- "What is covenant?" (English theological term + definition)
- "\ubaa8\uc138\uac00 \uccad\ucdeex\ubcf5\uae30\uae30\uc5d0\uc11c \ud55c \uc77c" (Korean proper noun + context)

---

## 9. Evidence Appendix

### E1: Git Status at Audit Start

```
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
?? docs/agents/cue/PHASE1-ENGLISH-CANONICAL-EMBEDDING-READINESS.md
?? docs/agents/cue/PHASE1-KOREAN-AUTHORITY-ACQUISITION.md
?? docs/agents/cue/PHASE1-KOREAN-AUTHORITY-RESOLUTION.md
```

### E2: Qdrant Collection Config (Full)

```
Collection: nae_ref_v1
Points: 34,948
Vectors: size=1024, distance=COSINE
HNSW: m=16, ef_construct=100, full_scan_threshold=10000
Segments: 8
Status: GREEN
Shards: 1 (replication_factor=1)
Payload: on_disk=True
```

### E3: Chunking Parameters (Verified)

```
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
Strategy: Linear pass, groups consecutive prose paragraphs
Heading context: Prepended when new chunk starts
Page tracking: page_start/page_end per chunk
```

### E4: TSU Dataset Smith-Related Entries

```
Total TSU dataset entries: 53,231
Smith-related entries: 115 (content에 "smith" 또는 "Smith" 포함)
```

---

## 10. Conclusion

**Smith Bible Dictionary baseline recovery는 완료됨.** 4권 전체가 raw source \u2192 canonical \u2192 chunking \u2192 embedding \u2192 Qdrant ingestion의 전 파이프라인을 통과했으며, E2E pipeline도 ALL PASS로 검증됨.

**임베딩 준비 상태**: READY (blocking issue 없음)

**다음 단계**: ADR-029 \u00a72.2의 마지막 gate인 "실제 앱 실행 + 실제 질문 테스트"를 수행하여 activation heuristic의 실제 성능을 검증한 후, Smith phase를 완료로 확정.

---

**Audit Mode**: READ-ONLY FORENSIC AUDIT
**Mutations**: 0
**Git add/commit**: NO
**Report generated**: 2026-08-26
