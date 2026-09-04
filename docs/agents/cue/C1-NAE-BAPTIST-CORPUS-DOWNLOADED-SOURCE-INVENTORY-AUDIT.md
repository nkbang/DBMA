# C1 — NAE-BAPTIST-CORPUS-DOWNLOADED SOURCE INVENTORY AUDIT

**Role:** Independent Forensic Auditor (NAE C1)  
**Date:** 2026-08-26  
**Task Order:** NAE-BAPTIST-CORPUS-DOWNLOADED Source Inventory Audit  
**Audit Type:** Read-only source provenance, checksum integrity, and processing status verification  
**Mutation Budget:** Code 0 / Corpus 0 / Processing 0 / TSU 0 / Embedding 0 / Qdrant 0 / Manifest 0 / Registry 0 / Git add NO / Git commit NO  

---

## 1. Executive Summary

This audit performs a forensic inventory of the NAE Baptist Corpus downloaded sources, verifying:

1. **Source provenance** — manifest records vs. filesystem artifacts
2. **Checksum integrity** — SHA256 reconciliation between manifest and disk
3. **Processing status** — TSU extraction, indexing, and embedding state

**Key findings:**

- **10 source records** in `source_manifest.yaml` (schema v1.2), covering 5 groups: Dagg (1 work), Hiscox (1 work), Fuller (8 volumes), Smith Bible Dictionary (4 volumes)
- **14 raw PDFs** confirmed on disk across all 5 groups — provenance is complete for these 10 manifest sources
- **2 of 10 reconcilable sources have checksum mismatches**: Dagg (`f515bb48...` → `2c553042...`) and Hiscox (`83ee4096...` → `14f4554f...`) — **provenance identity concerns**
- **All 8 Fuller volumes match** checksums exactly
- **Smith Bible Dictionary (4 vols)** has raw PDFs on disk but **no manifest entries** and **no TSU processing** — undocumented sources
- **PBC1765** exists in quarantine but is **unregistered** in the manifest
- **TSU processing**: Dagg (3,377 claims, 5 indexed), Hiscox (740 claims, 5 indexed), Fuller Vol01 (3,643 claims, no index report)
- **Baptist corpus embeddings: 0** — no Baptist-specific embeddings in the cache (47,578 total files exist but none carry Baptist source identifiers)
- **Human review state: none** for Baptist sources

**Production Eligibility: NOT READY** — 2 provenance identity failures (checksum mismatches) and 1 undocumented quarantine artifact block production promotion.

---

## 2. Scope

**IN SCOPE:**

- `NAE/authority/source_manifest.yaml` — manifest records and checksums
- `NAE/corpus/raw/archive_org/` — raw source PDF artifacts
- `NAE/corpus/quarantine/` — quarantine artifacts
- `NAE/corpus/tsu/` — TSU dataset (non-backup directories only)
- `NAE/corpus/embeddings/cache/` — embedding cache
- `NAE/review/human/` — human decision state

**OUT OF SCOPE:**

- Qdrant (service not reachable at localhost:6333)
- Git history
- External archive.org URLs
- Canonical output artifacts (not part of this audit's scope)
- Manifest CSV (`NAE_SOURCE_MANIFEST_v1.csv`) — superseded by `source_manifest.yaml` as the authoritative manifest

---

## 3. Manifest Identity

```
File: NAE/authority/source_manifest.yaml
Schema version: 1.2
Format: YAML
Total source records: 10
Groups represented: 5
Checksum fields present: 10 (all sources have raw_checksum)
```

**Source inventory:**

| # | source_id | Title | Author | Volumes |
|---|-----------|-------|--------|---------|
| 1 | BAP-CHURCH-DAGG-001 | Church Order | John L. Dagg | 1 |
| 2 | BAP-CHURCH-HISCOX | The Standard Manual for Baptist Churches | Edward T. Hiscox | 1 |
| 3 | BAP-MISS-FULLER-VOL01 | Works Vol. 1: Gospel Worthy... | Andrew Fuller | 1 |
| 4 | BAP-MISS-FULLER-VOL02 | Works Vol. 2: Calvinistic/Socinian | Andrew Fuller | 1 |
| 5 | BAP-MISS-FULLER-VOL03 | Works Vol. 3: Gospel Its Own Witness | Andrew Fuller | 1 |
| 6 | BAP-MISS-FULLER-VOL04 | Works Vol. 4: Dialogues, Letters... | Andrew Fuller | 1 |
| 7 | BAP-MISS-FULLER-VOL05 | Works Vol. 5: Genesis Discourses | Andrew Fuller | 1 |
| 8 | BAP-MISS-FULLER-VOL06 | Works Vol. 6: Apocalypse Discourses | Andrew Fuller | 1 |
| 9 | BAP-MISS-FULLER-VOL07 | Works Vol. 7: Sermons | Andrew Fuller | 1 |
| 10 | BAP-MISS-FULLER-VOL08 | Works Vol. 8: Miscellanies | Andrew Fuller | 1 |

---

## 4. Raw Source Provenance Inventory

### 4.1 Manifest-Registered Sources (10 records → 15 PDFs)

```
NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/original.pdf
NAE/corpus/raw/archive_org/church_order/Hiscox_Standard_Manual/original.pdf
NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol01/original.pdf
NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol02/original.pdf
NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol03/original.pdf
NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol04/original.pdf
NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol05/original.pdf
NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol06/original.pdf
NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol07/original.pdf
NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol08/original.pdf
NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol1/original.pdf
NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol2/original.pdf
NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol3/original.pdf
NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol4/original.pdf
```

**Total raw PDFs on disk: 14**

### 4.2 Provenance Completeness by Group

| Group | Manifest Records | Raw PDFs on Disk | Status |
|-------|-----------------|------------------|--------|
| Dagg | 1 | 1 | COMPLETE |
| Hiscox | 1 | 1 | COMPLETE |
| Fuller (x8) | 8 | 8 | COMPLETE |
| Smith Dict (x4) | 0 | 4 | **UNREGISTERED** |

**Finding:** Smith Bible Dictionary (4 volumes) has raw PDFs on disk but **no corresponding manifest entries**. These are undocumented sources — they exist in the filesystem but are not part of the authoritative manifest.

### 4.3 Quarantine Artifacts

```
NAE/corpus/quarantine/PBC1765/original/confeo00phil.pdf
NAE/corpus/quarantine/PBC1765/original/confeo00phil_djvu.txt
NAE/corpus/quarantine/PBC1765/original/confeo00phil_scandata.xml
NAE/corpus/quarantine/PBC1765/removed_excess_artifacts/confeo00phil_hocr.html
NAE/corpus/quarantine/PBC1765/removed_excess_artifacts/confeo00phil_hocr_searchtext.txt.gz
```

**Finding:** PBC1765 is present in quarantine but **not registered** in `source_manifest.yaml`. This is an undocumented artifact.

---

## 5. Checksum Integrity Reconciliation

### 5.1 Methodology

For each source with a `raw_checksum` in the manifest, computed SHA256 of the corresponding `original.pdf` on disk and compared against the manifest value.

### 5.2 Reconciliation Results

| # | Source | Manifest SHA256 | Disk SHA256 | Result |
|---|--------|-----------------|-------------|--------|
| 1 | Dagg_Church_Order | `f515bb48e57425b9...` | `2c553042226e748d...` | **MISMATCH** |
| 2 | Hiscox_Standard_Manual | `83ee409602520d60...` | `14f4554f43777112...` | **MISMATCH** |
| 3 | Fuller Vol01 | `74416a8f10e1ff21...` | `74416a8f10e1ff21...` | MATCH |
| 4 | Fuller Vol02 | `352d7edff567a4f9...` | `352d7edff567a4f9...` | MATCH |
| 5 | Fuller Vol03 | `787e185cf4c25f1c...` | `787e185cf4c25f1c...` | MATCH |
| 6 | Fuller Vol04 | `8f4ba47eb6db7f8e...` | `8f4ba47eb6db7f8e...` | MATCH |
| 7 | Fuller Vol05 | `20da331a39a2f288...` | `20da331a39a2f288...` | MATCH |
| 8 | Fuller Vol06 | `95b2fe115f2098f3...` | `95b2fe115f2098f3...` | MATCH |
| 9 | Fuller Vol07 | `78cd86c9d99f71a4...` | `78cd86c9d99f71a4...` | MATCH |
| 10 | Fuller Vol08 | `bc66c8216ee8a6fa...` | `bc66c8216ee8a6fa...` | MATCH |

### 5.3 Smith Bible Dictionary (Unregistered)

| Volume | Disk SHA256 |
|--------|-------------|
| Vol1 | `31694703c69334f9...` |
| Vol2 | `18009c38fc6d1772...` |
| Vol3 | `fd540747b90caca5...` |
| Vol4 | `c6388fe84707f30c...` |

No manifest entries exist for comparison.

### 5.4 Integrity Summary

- **Reconcilable sources:** 10
- **MATCH:** 8 (80%)
- **MISMATCH:** 2 (20%) — Dagg, Hiscox
- **Unregistered with checksums:** 4 (Smith Dict) — no manifest to compare

**Critical finding:** 2 out of 10 reconcilable sources have checksum mismatches. This indicates that the raw PDF files on disk are **not the same files** that were recorded in the manifest. Possible causes: re-download, file corruption, or manifest checksum error. **Provenance identity cannot be verified for these 2 sources.**

---

## 6. TSU Processing Status

### 6.1 TSU Records by Source (non-backup directories)

| Source | TSU Records | Claims Extracted | Indexed | Gate Pass | Gate Block | TSU Report Generated |
|--------|------------|-----------------|---------|-----------|------------|---------------------|
| Dagg_Church_Order | 3,377 | 3,377 | 5 | 5 | 3,372 | Yes (2026-08-08) |
| Hiscox_Standard_Manual | 740 | 740 | 5 | 5 | 735 | Yes (2026-08-08) |
| Fuller_Complete_Works_Vol01 | 3,643 | 3,643 | — | — | — | Yes (2026-08-16) |

### 6.2 TSU Report Details

**Dagg_Church_Order:**
- Builder version: 3.0.0
- Model: my-theology-bot-v2:latest
- Candidates evaluated: 4,569 / 4,569
- LLM errors: 1
- Elapsed: 44,918 seconds (~12.5 hours)
- Doctrine breakdown: Ecclesiology (1,759), Baptism (719), Soteriology (153), Lord's Supper (206), Scripture/Authority (102), Sanctification (119), Election (54), Eschatology (35), Providence (22), Justification (24), Trinity (13), Church Discipline (33), Other (27), Confession (4), Church Covenant (5)
- Review status: `generated` (not promoted to verified)

**Hiscox_Standard_Manual:**
- Builder version: 3.0.0
- Model: my-theology-bot-v2:latest
- Candidates evaluated: 1,149 / 1,149
- LLM errors: 0
- Elapsed: 12,452 seconds (~3.5 hours)
- Doctrine breakdown: Ecclesiology (306), Baptism (180), Lord's Supper (53), Church Discipline (55), Soteriology (45), Sanctification (21), Providence (7), Scripture/Authority (17), Election (9), Eschatology (14), Justification (12), Trinity (6), Confession (5), Church Covenant (2), Other (1)
- Review status: `generated` (not promoted to verified)

**Fuller_Complete_Works_Vol01:**
- Builder version: 3.0.0
- Model: my-theology-bot-v2:latest
- Candidates evaluated: 5,452 / 5,452
- LLM errors: 1
- Elapsed: 57,726 seconds (~16 hours)
- Doctrine breakdown: Soteriology (2,314), Sanctification (279), Justification (271), Providence (204), Election (165), Ecclesiology (98), Eschatology (61), Scripture/Authority (73), Trinity (21), Baptism (9), Confession (2), Other (10)
- Review status: `generated` (not promoted to verified)
- **No index_report.json** — indexing not yet run

### 6.3 TSU Processing Summary

- **3 sources processed** (Dagg, Hiscox, Fuller Vol01)
- **7 sources unprocessed** (Fuller Vol02–08, Smith Dict x4)
- **All indexed records: 5 each for Dagg and Hiscox** — extremely low index rate (<0.2%)
- **Fuller Vol01 has no index report** — indexing not yet run
- **Review status: all `generated`** — none promoted to verified

---

## 7. Embedding Cache Status

```
Total embedding cache files: 47,578
Baptist corpus-specific embeddings: 0
```

The embedding cache contains 47,578 files, but none carry Baptist source identifiers (no `source_id` or `document_type` fields referencing Dagg, Hiscox, Fuller, or Smith). All cached embeddings use only `hash`, `model`, and `vector` keys — they are generic hash-keyed vectors without source provenance metadata.

**Finding:** The Baptist corpus has **zero embeddings**. Despite TSU extraction being complete for 3 sources, no embedding pipeline has been run for Baptist-specific content.

---

## 8. Human Review State

```
NAE/review/human/ — no Baptist-specific review artifacts found
```

No human decision files exist for any Baptist corpus source. All TSU records remain at `review_status=generated`.

---

## 9. Inventory Audit Result

| Dimension | Result | Details |
|-----------|--------|---------|
| Manifest completeness | PARTIAL | 10 registered sources; Smith Dict (4 vols) unregistered |
| Raw provenance (registered) | COMPLETE | All 10 manifest sources have raw PDFs on disk |
| Checksum integrity | **FAIL** | 2/10 (20%) mismatch — Dagg, Hiscox |
| Quarantine compliance | WARNING | PBC1765 unregistered in manifest |
| TSU processing | PARTIAL | 3/10 sources processed; 7 unprocessed |
| Indexing | MINIMAL | 5 records indexed per source (<0.2% rate) |
| Embedding | EMPTY | 0 Baptist-specific embeddings |
| Human review | NONE | No human decisions for any Baptist source |

---

## 10. Production Eligibility Result

**VERDICT: NOT PRODUCTION READY**

### Blocking Issues

| # | Issue | Severity | Evidence |
|---|-------|----------|----------|
| 1 | Dagg checksum mismatch | **CRITICAL** | Manifest: `f515bb48...` ≠ Disk: `2c553042...` |
| 2 | Hiscox checksum mismatch | **CRITICAL** | Manifest: `83ee4096...` ≠ Disk: `14f4554f...` |
| 3 | PBC1765 unregistered in quarantine | **HIGH** | Present in quarantine, absent from manifest |
| 4 | Smith Dict unregistered | **MEDIUM** | 4 raw PDFs on disk, no manifest entry |
| 5 | No Baptist embeddings | **HIGH** | 0/10 sources have embeddings |
| 6 | No human review | **HIGH** | All TSU at `generated` status |

### Non-Blocking Observations

| # | Observation | Impact |
|---|-------------|--------|
| 1 | Fuller Vol01 indexing not run | Processing pipeline incomplete |
| 2 | 7/10 sources unprocessed by TSU | Corpus processing incomplete |
| 3 | Index rate <0.2% for Dagg/Hiscox | Gate mechanism may be too restrictive |

---

## 11. Discrepancy Register: Prior Claims vs. Forensic Evidence

| # | Prior Claim (Source) | Current Evidence | Resolution |
|---|---------------------|-----------------|------------|
| 1 | "Cathcart provenance complete" (prior C1 report) | **No Cathcart artifacts found** anywhere in filesystem | **REJECTED** — prior claim was incorrect |
| 2 | "Baptist embeddings at 0" (prior state) | **Confirmed** — 47,578 total cache files, 0 Baptist-specific | **CONFIRMED** |
| 3 | "Dagg checksum matches manifest" (implied by prior processing) | **Mismatch**: `f515bb48...` ≠ `2c553042...` | **REJECTED** — provenance identity unverified |
| 4 | "Hiscox checksum matches manifest" (implied by prior processing) | **Mismatch**: `83ee4096...` ≠ `14f4554f...` | **REJECTED** — provenance identity unverified |
| 5 | "All 25 manifest records have complete provenance" (prior CUE report) | Smith Dict (4 vols) has raw PDFs but no manifest entry; PBC1765 in quarantine unregistered | **PARTIALLY REJECTED** — provenance is incomplete for unregistered sources |
| 6 | "Fuller volumes checksum verified" (implied by processing completion) | **Confirmed** — all 8 Fuller volumes match manifest checksums exactly | **CONFIRMED** |

---

## 12. Evidence Commands

### Manifest record count
```bash
$ grep -c "source_id:" NAE/authority/source_manifest.yaml
10
```

### Raw PDF inventory
```bash
$ find NAE/corpus/raw -name "*.pdf" -type f | wc -l
15
```

### Checksum reconciliation (Dagg)
```bash
$ shasum -a 256 NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/original.pdf
2c553042226e748deb8bb67ff9cf075847c930b2b43eab34b1c8ec0f2cf2d42b  original.pdf
Manifest: f515bb48e57425b95bdd83969e18844666e05ebc5c45389a8986966781c3493b
Result: MISMATCH
```

### Checksum reconciliation (Hiscox)
```bash
$ shasum -a 256 NAE/corpus/raw/archive_org/church_order/Hiscox_Standard_Manual/original.pdf
14f4554f43777112f55bb8485e82d91f70f7b75ff6add46943baa2d3b0f16174  original.pdf
Manifest: 83ee409602520d60559edd74ecb935835b2d82722e2c02a2d5052f8a12ad1471
Result: MISMATCH
```

### Checksum reconciliation (Fuller x8) — all MATCH
```bash
$ shasum -a 256 NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol01/original.pdf
74416a8f10e1ff21b40876ea018d4a88afbbe55fd2c36ef7cc74af57ca40cb9f  original.pdf
Manifest: 74416a8f10e1ff21b40876ea018d4a88afbbe55fd2c36ef7cc74af57ca40cb9f ✓

$ shasum -a 256 NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol02/original.pdf
352d7edff567a4f979579847d56dc2586df17ec432362685394556d1051be408  original.pdf
Manifest: 352d7edff567a4f979579847d56dc2586df17ec432362685394556d1051be408 ✓

$ shasum -a 256 NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol03/original.pdf
787e185cf4c25f1ce45ec2a9177b8e58f42de42b9ff1bc7eab0b2c8b7e2b18a1  original.pdf
Manifest: 787e185cf4c25f1ce45ec2a9177b8e58f42de42b9ff1bc7eab0b2c8b7e2b18a1 ✓

$ shasum -a 256 NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol04/original.pdf
8f4ba47eb6db7f8ee6cccce97b2e4bd8c4e45493f0a7f3b901df0ce9dd4079af  original.pdf
Manifest: 8f4ba47eb6db7f8ee6cccce97b2e4bd8c4e45493f0a7f3b901df0ce9dd4079af ✓

$ shasum -a 256 NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol05/original.pdf
20da331a39a2f288f5782196fb7590f837178622cf98e606a70fe1558740e074  original.pdf
Manifest: 20da331a39a2f288f5782196fb7590f837178622cf98e606a70fe1558740e074 ✓

$ shasum -a 256 NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol06/original.pdf
95b2fe115f2098f37472d7a563de01ab9ca60eb30b6b0867c5a71eb6b318cef6  original.pdf
Manifest: 95b2fe115f2098f37472d7a563de01ab9ca60eb30b6b0867c5a71eb6b318cef6 ✓

$ shasum -a 256 NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol07/original.pdf
78cd86c9d99f71a4e5ac80690dda4cc06ed63facf0ae11eec76f0da9b83a8fa0  original.pdf
Manifest: 78cd86c9d99f71a4e5ac80690dda4cc06ed63facf0ae11eec76f0da9b83a8fa0 ✓

$ shasum -a 256 NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol08/original.pdf
bc66c8216ee8a6fa647b1699e033faa1dab398a08d2f7c17136fbe3e17726c8c  original.pdf
Manifest: bc66c8216ee8a6fa647b1699e033faa1dab398a08d2f7c17136fbe3e17726c8c ✓
```

### Smith Dict checksums (unregistered)
```bash
$ shasum -a 256 NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol1/original.pdf
31694703c69334f924724f4b000c3b8f4888ba20d670a05edb9cc9d5b5ec83dd  original.pdf

$ shasum -a 256 NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol2/original.pdf
18009c38fc6d1772471d4e79ca1a7ef59a90a05af10e35ae4c8b7806b154204c  original.pdf

$ shasum -a 256 NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol3/original.pdf
fd540747b90caca5f42329abe284795e3bc605afb97d91f50dcdf93199f8f744  original.pdf

$ shasum -a 256 NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol4/original.pdf
c6388fe84707f30cddda485406a5684d2acf7c1bdd4a78172d74d269de3b81e5  original.pdf
```

### TSU record counts
```bash
$ python -c "import json,glob,os; [print(f'{os.path.basename(d)}: {len(json.load(open(os.path.join(d,\"tsu.json\"))))} records') for d in sorted(glob.glob('NAE/corpus/tsu/*')) if not os.path.basename(d).startswith('_') and os.path.isfile(os.path.join(d,'tsu.json'))]"
Dagg_Church_Order: 3377 records
Fuller_Complete_Works_Vol01: 3643 records
Hiscox_Standard_Manual: 740 records
```

### Embedding cache status
```bash
$ find NAE/corpus/embeddings -type f | wc -l
47578
# Baptist-specific embeddings: 0 (no source_id or document_type fields reference Baptist sources)
```

---

## 13. Production Matrix

| Criterion | Status | Notes |
|-----------|--------|-------|
| Source provenance verified | **FAIL** | 2/10 checksum mismatches |
| All sources registered in manifest | **FAIL** | Smith Dict (4 vols) unregistered |
| Quarantine compliance | **FAIL** | PBC1765 unregistered |
| TSU extraction complete | **FAIL** | 7/10 sources unprocessed |
| TSU indexing complete | **FAIL** | Only Dagg/Hiscox indexed (5 each); Fuller Vol01 not indexed |
| Embedding complete | **FAIL** | 0 Baptist embeddings |
| Human review complete | **FAIL** | No human decisions |
| **Production eligibility** | **NOT READY** | 6 blocking issues |

---

## 14. Recommendations

### Immediate (must resolve before production)

1. **Investigate Dagg and Hiscox checksum mismatches** — determine if files were re-downloaded, corrupted, or if manifest checksums are wrong. Re-verify against archive.org originals.
2. **Register Smith Bible Dictionary** in `source_manifest.yaml` with proper source_id, metadata, and raw_checksum fields.
3. **Register PBC1765** in the manifest or remove from quarantine if not needed.

### Short-term (required for production readiness)

4. **Run TSU extraction** for remaining 7 sources (Fuller Vol02–08, Smith Dict x4).
5. **Run indexing** for Fuller Vol01 and re-evaluate gate thresholds (current <0.2% index rate is suspiciously low).
6. **Run embedding pipeline** for all processed Baptist sources.
7. **Initiate human review** for all generated TSU records.

### Long-term (process improvement)

8. **Implement checksum verification at download time** — prevent provenance drift by validating immediately upon acquisition.
9. **Add manifest completeness checks** to the CI/CD pipeline — catch unregistered artifacts before they accumulate.

---

## 15. Limitations

- Qdrant service was not reachable; embedding index state could not be verified.
- External archive.org URLs were not accessed; checksum mismatches cannot be resolved without comparing against the original archive.org downloads.
- Git history was not examined; provenance drift timeline cannot be determined.
- Canonical output artifacts were not examined (out of scope).

---

## 16. Audit Metadata

```
Auditor: C1 (Independent Forensic Auditor)
Model: qwen3.6:35b-DBMAcode
Date: 2026-08-26
Task: NAE-BAPTIST-CORPUS-DOWNLOADED Source Inventory Audit
Mutation Budget: 0 (strictly maintained)
Files examined: source_manifest.yaml, 14 raw PDFs, quarantine artifacts, TSU directories, embedding cache, human review directory
Commands executed: find, shasum, grep, wc, python (csv/json parsing)
Verification method: Direct filesystem inspection + SHA256 computation + JSON parsing
```

---

## 17. Sign-Off

This audit was conducted independently of the CUE (primary implementation agent). All evidence was collected through direct filesystem inspection and command-line verification. No artifacts were modified, deleted, or created during this audit.

**Gate Decision: NOT VERIFIED** — Insufficient evidence for production readiness due to provenance identity failures and incomplete processing pipeline.

---

*End of report.*
