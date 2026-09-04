# C1 DAGG VOL.1–8 PROCESSING RESUME-POINT AUDIT

**작업명**: Dagg Corpus Processing Resume-Point Audit (READ-ONLY)
**작성자**: C1 (Independent Forensic Auditor)
**작성일**: 2026-08-26
**Mode**: READ-ONLY AUDIT — 어떠한 processing도 수행하지 않는다.
**Mutation Budget**: Code 0 / Corpus 0 / TSU 0 / Embedding 0 / Qdrant 0 / Manifest 0 / Registry 0 / Git NO

---

## 1. Executive Summary

이 보고서는 **Dagg 자료의 실제 processing 상태와 과거 중단 지점**을 감사한다.

핵심 발견:

> **"Dagg Vol. 1–8"이라는 개념은 존재하지 않는다.**
>
> 실제 Dagg corpus는 **단일 monograph** `Dagg_Church_Order` (BAP-CHURCH-DAGG-001)이며,
> Dagg-002(Treatise on Church Discipline)는 Dagg-001에 통합되었다.
>
> 이 단일 corpus는 **acquisition → canonicalization → TSU → embedding까지 완료**되었으나,
> **Qdrant 인덱싱에서 심각한 gate_block 문제**(3,372/3,377 차단)로 인해
> **실제 인덱스에는 단 5개 record만 등록**된 상태이다.

---

## 2. Investigation Scope

**IN SCOPE**:
- Dagg corpus의 filesystem artifact 전역 조사
- 각 pipeline stage별 존재 여부 및 상태 확인
- Git history를 통한 processing timeline 복원
- Human review checkpoint 및 promotion evidence 분석
- Index/Qdrant 상태 확인

**OUT OF SCOPE**(수행하지 않음):
- 신규 acquisition
- 신규 processing 실행
- 기존 artifact 수정
- git add/commit
- ADR-029 Phase 1 상태 변경

---

## 3. Dagg Corpus Identity

### 3.1 실제 corpus 구성

| source_id | title | author | status | notes |
|-----------|-------|--------|--------|-------|
| BAP-CHURCH-DAGG-001 | Manual of Church Order | John L. Dagg | ACQUIRED | 단일 monograph |
| BAP-CHURCH-DAGG-002 | Treatise on Church Discipline | John Dagg | ACQUIRED_CONSOLIDATED_WITH_DAGG-001 | Dagg-001에 통합 |

### 3.2 "Vol. 1–8" 개념에 대한 사실 확인

**결론: Dagg Vol. 1–8은 존재하지 않는다.**

- manifest(`resources/theological_sources/manifest/pilot/dagg/`)에서 Dagg는 단일 monograph로 정의됨
- volume_id = null (monograph이므로 volume 개념 없음)
- filesystem 상에도 `Dagg_Church_Order` 단일 corpus directory만 존재
- Dagg의 원저작물(Church Order)은 single-volume 책(314페이지)

### 3.3 Metadata

```json
{
  "title": "Church Order",
  "creator": "John L. Dagg",
  "publisher": "Bible and Publication Society",
  "publication_place": "Philadelphia",
  "edition": "1871",
  "year": 1871,
  "source_id": "BAP-CHURCH-DAGG-001",
  "work_id": "WORK-DAGG-CHURCH-ORDER-001",
  "edition_id": "WORK-DAGG-CHURCH-ORDER-001-1871",
  "author_id": "dagg_john_l"
}
```

---

## 4. Acquisition Status

### 4.1 Acquisition: COMPLETE

**Evidence**:

| 파일 | 크기 | 생성일 |
|------|------|--------|
| `original.pdf` | 16,265,071 bytes (15.5 MB) | 2026-08-07 |
| `hocr.html` | 17,179,317 bytes (16.4 MB) | 2026-08-07 |
| `ocr.txt` | 698,234 bytes (682 KB) | 2026-08-07 |
| `metadata.json` | 345 bytes | 2026-08-07 |

**Source**: Internet Archive (`archive_org/church_order/Dagg_Church_Order/`)


---

## 5. Volume Status (Single Corpus: Dagg_Church_Order)

### 5.1 Raw Stage: COMPLETE

- **파일 수**: 4개 (PDF, HOcr, OCR text, metadata)
- **페이지 수**: 314페이지
- **OCR 상태**: complete
- **HOcr 상태**: complete

### 5.2 Canonicalization Stage: COMPLETE

**Evidence**:

| 파일 | 크기 | 생성일 |
|------|------|--------|
| `canonical.json` | 2,005,666 bytes (1.9 MB) | 2026-08-07 |
| `canonical.txt` | 680,106 bytes (664 KB) | 2026-08-07 |
| `normalize_report.json` | 592 bytes | 2026-08-07 |

**Normalize Report**:

```json
{
  "identifier": "Dagg_Church_Order",
  "status": "ok",
  "pipeline_version": "2.0.0",
  "generated_at": "2026-08-07T05:10:03.212552+00:00",
  "source": "hocr",
  "page_count": 314,
  "characters_before": 678195,
  "characters_after": 674793,
  "paragraph_count": 1572,
  "verse_paragraph_count": 14,
  "heading_count": 112,
  "quote_count": 12,
  "sentence_count": 5012,
  "language_blocks_detected": 0,
  "headers_footers_removed": 45,
  "page_numbers_removed": 47,
  "footnotes_extracted": 19,
  "scripture_references_found": 0
}
```

**판정**: canonicalization **완료**. 1,572개 paragraph, 112개 heading 추출.

### 5.3 TSU Stage: COMPLETE (with critical gate issue)

**Evidence**:

| 파일 | 크기 | 생성일 |
|------|------|--------|
| `tsu.json` | 6,006,046 bytes (5.7 MB) | 2026-08-11 |
| `tsu_report.json` | 887 bytes | 2026-08-07 |
| `index_report.json` | 259 bytes | 2026-08-09 |

**TSU Report**:

```json
{
  "identifier": "Dagg_Church_Order",
  "builder_version": "3.0.0",
  "generated_at": "2026-08-08T02:37:38.955060+00:00",
  "model": "my-theology-bot-v2:latest",
  "candidates_evaluated": 4569,
  "candidates_total": 4569,
  "claims_extracted": 3377,
  "llm_errors": 1,
  "doctrine_breakdown": {
    "Ecclesiology": 1759,
    "Scripture / Authority": 102,
    "Lord's Supper": 206,
    "Soteriology": 153,
    "Baptism": 719,
    "Church Discipline": 33,
    "Sanctification": 119,
    "Trinity": 13,
    "Eschatology": 35,
    "Providence": 22,
    "Other": 27,
    "Confession": 4,
    "Justification": 24,
    "Election": 54,
    "Church Covenant": 5
  },
  "elapsed_seconds": 44918.17,
  "partial": false
}
```

**TSU review_status 분포**:

| status | count | percentage |
|--------|-------|------------|
| verified | 2,958 | 87.6% |
| generated | 397 | 11.8% |
| rejected | 22 | 0.6% |
| **total** | **3,377** | **100%** |

**인덱싱 결과**(index_report.json):

```json
{
  "identifier": "Dagg_Church_Order",
  "generated_at": "2026-08-09T18:32:43.493617+00:00",
  "collection": "nae_tsu_v1",
  "records_total_raw": 3377,
  "gate_pass": 5,
  "gate_block": 3372,
  "indexed": 5,
  "skipped_duplicate": 0,
  "embedding_errors": 0
}
```

**중요 발견**: 3,377개 claims 중 **3,372개(99.8%)가 gate에서 차단**됨. 인덱스에는 단 5개만 등록.

### 5.4 Embedding Stage: COMPLETE (cache exists)

- **embedding cache 디렉터리**: `NAE/corpus/embeddings/cache/`
- **캐시 파일 수**: 47,580개 (전체 corpus 공유 캐시)
- **Dagg 전용 캐시 파일**: 별도 구분 없음 (hash 기반 공유 캐시)
- **캐시 생성일**: 2026-08-11 ~ 2026-08-25

### 5.5 Qdrant/Index Stage: PARTIAL (critical gap)

**Evidence**:

| 지표 | 값 |
|------|-----|
| total_raw claims | 3,377 |
| gate_pass | **5** |
| gate_block | **3,372** |
| indexed | **5** |
| skipped_duplicate | 0 |
| embedding_errors | 0 |

**Promotion Evidence**(batch24_36):

```
dagg_verified: 2,958
dagg_generated: 397
dagg_rejected: 22
final_indexed: 3,319 (전체 corpus 기준)
Dagg_Church_Order indexed: 2,958
Hiscox_Standard_Manual indexed: 361
```

**모순 분석**:
- promotion evidence는 `dagg_verified=2,958`를 보고
- 그러나 index_report는 `gate_pass=5, indexed=5`를 보고
- **이 discrepancy가 핵심 문제**

---

## 6. Historical Processing Timeline

### 6.1 Git History (Dagg 관련 commit)

| 날짜 | Commit | 내용 |
|------|--------|------|
| 2026-08-07 05:10 | — | canonicalization 완료 (normalize_report 생성) |
| 2026-08-08 02:37 | — | TSU extraction 완료 (tsu_report 생성, 44,918초 소요) |
| 2026-08-09 18:32 | — | index 생성 완료 (index_report 생성) |
| 2026-08-09 18:36 | `3a2da21` | Pilot 001 human review gate → promotion → remediation → embedding |
| 2026-08-09 23:06 | `3f6d56d` | Batch 1 first 38 reviews (28 verified, 10 rejected) |
| 2026-08-09 23:25 | `b9f4342` | Batch 1 reviews 39-68 (30 verified) |
| 2026-08-09 23:48 | `45301e3` | Batch 1 reviews 69-78 (9 verified, 1 rejected) |
| 2026-08-10 00:09 | `10505ae` | Batch 1 complete (85 verified, 15 rejected) |
| 2026-08-10 10:38 | `6fe70c3` | Batch 2 (112 verified, 22 rejected) |
| 2026-08-10 14:46 | `1287732` | Batch 2 exception resolution + Batch 3 (95 verified, 22 exceptions) |
| 2026-08-10 20:47 | `c722a65` | Batch 4-15 complete (1,327 verified, 22 rejected, 190 exception) |
| 2026-08-11 01:33 | `c7e10f0` | Batch 16-23 promotion |
| 2026-08-11 08:17 | `a330642` | **Batch 24-36 final promotion** (1,271 candidates) |

### 6.2 Processing Duration

- **canonicalization**: 2026-08-07 (약 1일)
- **TSU extraction**: 2026-08-07 ~ 2026-08-08 (44,918초 ≈ 12.5시간)
- **Human review**: 2026-08-09 ~ 2026-08-11 (약 2일)
- **Embedding**: 2026-08-11 ~ 2026-08-25 (캐시 파일 기준)
- **인덱싱**: 2026-08-09 (index_report 생성일)

---

## 7. Artifact Inventory

### 7.1 Production Artifacts

| Stage | Path | 존재 | 크기 |
|-------|------|------|------|
| Raw PDF | `NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/original.pdf` | YES | 16.2 MB |
| Raw HOcr | `.../hocr.html` | YES | 17.2 MB |
| Raw OCR | `.../ocr.txt` | YES | 698 KB |
| Raw Metadata | `.../metadata.json` | YES | 345 B |
| Canonical JSON | `NAE/corpus/canonical/Dagg_Church_Order/canonical.json` | YES | 2.0 MB |
| Canonical TXT | `.../canonical.txt` | YES | 680 KB |
| Normalize Report | `.../normalize_report.json` | YES | 592 B |
| TSU JSON | `NAE/corpus/tsu/Dagg_Church_Order/tsu.json` | YES | 6.0 MB |
| TSU Report | `.../tsu_report.json` | YES | 887 B |
| Index Report | `.../index_report.json` | YES | 259 B |

### 7.2 Backup Artifacts

| 유형 | 수 | 최신일 |
|------|-----|--------|
| TSU promotion backup | 36개 (_batch0001~0036) | 2026-08-11 |
| TSU remediation backup | 2개 | 2026-08-10 |
| TSU migration backup | 1개 | 2026-08-08 |
| TSU general backup | 1개 | 2026-08-07 |

### 7.3 Human Review Artifacts

| Path | 존재 |
|------|------|
| `NAE/review/human/checkpoints/batch24_36_green_checkpoint/` | YES |
| `.../screening_state.json` (2,047 TSU IDs) | YES |
| `.../decisions/pilot_001_decisions.json` (2 Dagg items) | YES |
| `.../decisions/pilot_001_remediation_decisions.json` (2 Dagg items) | YES |
| `.../exception_queue.json` | YES |
| `NAE/review/human/evidence/promotion_batch24_36_evidence.json` | YES |

---

## 8. Stage-by-Stage Status Matrix

| Volume | Acquisition | Raw | Extraction | Canonical | TSU | Embedding | Qdrant | Overall |
|--------|-------------|-----|------------|-----------|-----|-----------|--------|---------|
| Dagg_Church_Order (BAP-CHURCH-DAGG-001) | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE | COMPLETE | PARTIAL | PARTIAL |

**Overall 판정**: **PARTIAL** — 인덱싱에서 심각한 gate_block 발생

---

## 9. Interruption / Failure Analysis

### 9.1 중단 지점

**과거 processing은 중단되지 않았다.** 모든 stage가 완료되었음.

**그러나 인덱싱 단계에서 치명적 문제가 발견됨**:

- **3,377개 claims 중 3,372개(99.8%)가 gate에서 차단**
- 인덱스에 등록된 것은 단 5개 record
- embedding은 완료되었으나, indexed record가 극히 제한적

### 9.2 gate_block 원인 분석 (추측, 미검증)

index_report의 `gate_pass=5`는 다음 중 하나일 수 있음:
1. gate 규칙이 매우 엄격하게 적용됨
2. Dagg corpus의 TSU가 특정 조건을 만족하지 못함
3. indexing pipeline의 버그 또는 설정 문제

**이 원인은 본 감사에서 검증하지 않음**(AUDIT ONLY).

### 9.3 Promotion Evidence vs Index Report 모순

| 지표 | Promotion Evidence | Index Report |
|------|-------------------|--------------|
| verified TSU | 2,958 | — |
| indexed | — | 5 |
| gate_pass | — | 5 |

**이 discrepancy는 반드시 해소되어야 함**.

---

## 10. Duplicate Processing Risk

### 10.1 각 stage별 판정

| Stage | Existing Artifact | Reuse Safe | Re-process Safe |
|-------|------------------|------------|-----------------|
| Acquisition | COMPLETE (raw files) | SAFE TO REUSE | NOT NEEDED |
| Raw | COMPLETE | SAFE TO REUSE | NOT NEEDED |
| Canonicalization | COMPLETE (canonical.json, canonical.txt) | SAFE TO REUSE | NOT NEEDED |
| TSU | COMPLETE (tsu.json, 3,377 claims) | SAFE TO REUSE | NOT NEEDED |
| Embedding | COMPLETE (47,580 cache files) | SAFE TO REUSE | NOT NEEDED |
| Qdrant/Index | PARTIAL (5 indexed) | **REVIEW REQUIRED** | POTENTIAL ISSUE |

### 10.2 중복 처리 위험도: **MEDIUM**

- canonical/TSU/embedding artifact는 모두 존재하므로 재처리 불필요
- 인덱싱만 재시도 필요하지만, gate_block 문제 해소 전 재시도는 무의미

---

## 11. Resume Point

### 11.1 현재 상태

Dagg corpus는 **모든 stage를 완료**했으나, **인덱싱에서 실패**(gate_block 3,372/3,377).

### 11.2 Resume Point

```
RESUME POINT:
Dagg_Church_Order / STAGE: Qdrant Index (gate_block 해소 후 재시도)
```

**그러나**:
- gate_block 원인을 먼저 조사해야 함
- artifact 재생성이 아닌 **기존 artifact 활용**이 우선
- 2,958개 verified TSU는 이미 존재 — 인덱싱만 재시도하면 됨 (gate 해소 시)

---

## 12. Safe-to-Resume Assessment

| 항목 | 판정 | 근거 |
|------|------|------|
| Acquisition | SAFE TO REUSE | raw files 존재 |
| Canonicalization | SAFE TO REUSE | canonical.json 존재 |
| TSU | SAFE TO REUSE | tsu.json (3,377 claims) 존재 |
| Embedding | SAFE TO REUSE | cache 47,580개 파일 존재 |
| Qdrant Index | **HOLD** | gate_block 3,372/3,372 — 원인 조사 필요 |

### 12.1 Safe to Resume: **NO **(HOLD)

**이유**: 인덱싱의 gate_block 문제(99.8% 차단)가 해소되지 않은 상태에서는 resume할 수 없음.
기존 artifact는 모두 존재하므로, **gate_block 원인 조사 → 해소 → 재인덱싱** 순서 필요.

---

## 13. Relationship to Current NAE Governance

| 항목 | 관계 |
|------|------|
| Dagg processing recovery | 이 감사의 대상 |
| Baptist Corpus governance reconciliation | 별개 작업 |
| ADR-029 Korean terminology gate | **변경 없음** |

**Dagg의 processing 상태가 ADR-029 Phase 1에 영향을 주지 않음**.

---

## 14. Mutation Audit

| 항목 | mutation |
|------|----------|
| CODE | 0 |
| CORPUS | 0 |
| RAW | 0 |
| CANONICAL | 0 |
| TSU | 0 |
| EMBEDDING | 0 |
| QDRANT | 0 |
| MANIFEST | 0 |
| REGISTRY | 0 |
| CACHE | 0 |

---

## 15. Git Status

- **git add**: 수행하지 않음
- **git commit**: 수행하지 않음
- **git reset/checkout**: 수행하지 않음
- **기타 session의 변경사항 수정**: 수행하지 않음

---

## 16. Final Decision

```
DAGG CORPUS PROCESSING RECOVERY AUDIT

ACQUISITION:
COMPLETE — BAP-CHURCH-DAGG-001 (Dagg_Church_Order) raw files present
BAP-CHURCH-DAGG-002 consolidated into DAGG-001

NOTE: "Dagg Vol. 1–8" does not exist. Dagg is a single monograph corpus.

VOL.1 (Dagg_Church_Order):
Acquisition = COMPLETE
Raw = COMPLETE (314 pages, PDF+HOcr+OCR+metadata)
Canonicalization = COMPLETE (1,572 paragraphs, 112 headings)
TSU = COMPLETE (3,377 claims extracted, 2,958 verified)
Embedding = COMPLETE (cache exists, 47,580 files)
Qdrant/Index = PARTIAL (gate_block: 3,372/3,377 blocked, only 5 indexed)

OVERALL STATUS: PARTIAL — critical gate_block issue in indexing

HISTORICAL INTERRUPTION POINT:
Processing was NOT interrupted. All stages completed.
However, Qdrant indexing had a critical gate_block (99.8% of claims blocked).

CURRENT RESUME POINT:
Dagg_Church_Order / STAGE: Qdrant Index (after gate_block resolution)

DUPLICATE PROCESSING RISK:
MEDIUM — existing artifacts are all present; only index re-ingestion needed
but gate_block must be resolved first.

SAFE TO RESUME:
NO / HOLD — gate_block 원인 조사 및 해소 필요

REQUIRED NEXT ACTION:
1. Investigate gate_block cause (index_report.json: gate_pass=5, gate_block=3,372)
2. Resolve gate_block issue
3. Re-ingest 2,958 verified TSUs to Qdrant (artifact already exists)

ADR-029 PHASE 1:
UNCHANGED

CODE MUTATION:
0

CORPUS MUTATION:
0

PROCESSING:
0

EMBEDDING:
0

QDRANT:
0

GIT COMMIT:
NO
```

---

## 17. Resume Decision Matrix

| Volume | Current Stage | Existing Artifact | Reuse Safe | Resume Stage | Decision |
|--------|--------------|-------------------|------------|--------------|----------|
| Dagg_Church_Order | Qdrant Index (blocked) | All stages complete except indexed records | YES (all except index) | Qdrant Index (post-gate-fix) | HOLD |

---

## 18. Critical Findings Summary

### 18.1 핵심 발견 1: "Vol. 1–8" 개념 오류

> Dagg는 **단일 monograph**이다. Vol. 1–8이라는 구분은 존재하지 않는다.
> manifest에서도 `volume_id: null`로 명시됨.

### 18.2 핵심 발견 2: 인덱싱 gate_block 치명적 문제

> 3,377 claims 중 **3,372개(99.8%)가 gate에서 차단**.
> 인덱스에 등록된 것은 단 5개 record.
> 이는 **production readiness에 치명적**인 상태.

### 18.3 핵심 발견 3: Promotion Evidence vs Index Report 모순

> promotion evidence는 `dagg_verified=2,958`를 보고하나,
> index_report는 `indexed=5`를 보고함.
> 이 discrepancy의 원인을 반드시 조사해야 함.

### 18.4 핵심 발견 4: 모든 artifact는 존재함

> acquisition → canonicalization → TSU → embedding까지 **모든 stage 완료**.
> 재처리 불필요 — 기존 artifact 활용 가능.
> 인덱싱만 gate_block 해소 후 재시도 필요.

---

## 19. Evidence Commands

본 보고서의 모든 주장은 다음 명령으로 재현 가능:

```bash
# Dagg corpus identity
find /Users/David/DBMA -type f -iname '*dagg*' | grep -v '.venv' | grep -v '__pycache__'

# Acquisition status
ls -la /Users/David/DBMA/NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/

# Canonicalization status
cat /Users/David/DBMA/NAE/corpus/canonical/Dagg_Church_Order/normalize_report.json

# TSU status
cat /Users/David/DBMA/NAE/corpus/tsu/Dagg_Church_Order/tsu_report.json
cat /Users/David/DBMA/NAE/corpus/tsu/Dagg_Church_Order/index_report.json

# Promotion evidence
cat /Users/David/DBMA/NAE/review/human/evidence/promotion_batch24_36_evidence.json | grep dagg

# Git history
git log --format='%h %ai %s' --all -- 'NAE/corpus/tsu/Dagg_Church_Order/*'
```

---

## 20. Limitations

- gate_block 원인은 본 감사에서 **검증하지 않음** (AUDIT ONLY)
- Qdrant 인덱스 직접 조회는 수행하지 않음
- embedding cache의 Dagg-specific content는 별도 구분되지 않음 (hash 기반 공유 캐시)

---

## 21. Conclusion

Dagg corpus는 **acquisition부터 embedding까지 모든 stage를 완료**했으나,
**Qdrant 인덱싱에서 99.8% gate_block**이라는 치명적 문제를 안고 있다.

기존 artifact는 모두 존재하므로 재처리 불필요.
**gate_block 원인 조사 → 해소 → 재인덱싱**이 다음 단계.

---

**C1 Audit Complete. HQ Approval Required Before Any Action.**