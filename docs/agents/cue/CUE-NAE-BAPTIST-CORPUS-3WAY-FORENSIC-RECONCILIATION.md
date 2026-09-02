# CUE — NAE Baptist Corpus 3-Way Forensic Reconciliation

**작업명**: NAE-BAPTIST-CORPUS — C1 Audit ↔ CUE Verification ↔ 실제 상태 Independent Cross-Verification
**작성자**: CUE (Independent Forensic Verification — 기존 보고서 2건을 evidence로만 취급, 실측 우선)
**작성일**: 2026-08-27
**Mode**: FORENSIC · READ-ONLY · FIND → MEASURE → RECONCILE → REPORT
**Mutation Budget**: Code 0 / Corpus 0 / RAW 0 / Canonical 0 / TSU 0 / Review 0 / Embedding 0 / Qdrant 0 / Manifest 0 / Registry 0 / Cache 0 / Git add·commit 0

---

> **STATUS: FINAL — HQ-approved as ADR-030 v2.1 Baseline (2026-08-29).**
> Cited by `docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md` header ("Baseline").
> The body below is the 2026-08-27 forensic reconciliation, unchanged. Approved for commit;
> commit pending separate HQ authorization. Independent re-verification on 2026-08-29
> (WS-B / WS-C audit) reproduced its core findings — 3,319 CLEAN production baseline
> (Dagg 2,958 + Hiscox 361), manifest triad M1/M2/M3, and the SLBC1689 / PBC1742 /
> 19-CLAIM-ONLY backlog — with no contradiction.

---

**검증 대상 (evidence로만 취급, 결론 미채택)**
1. `docs/agents/cue/C1-NAE-BAPTIST-CORPUS-DOWNLOADED-SOURCE-INVENTORY-AUDIT.md` (C1, 2026-08-26)
2. `docs/agents/cue/CUE-DAGG-INDEX-GATE-DISCREPANCY-INDEPENDENT-VERIFICATION.md` (CUE, 2026-08-26)

**교차 참조**: `C1-DAGG-VOL1-8-PROCESSING-RESUME-POINT-AUDIT.md`, `C1-NAE-BAPTIST-CORPUS-SOURCE-MANIFEST-RECONCILIATION.md`, `CUE-NAE-BAPTIST-CORPUS-001-26-RECORD-INDEPENDENT-VERIFICATION.md`, `CUE-NAE-BAPTIST-CORPUS-001-FINAL-GOVERNANCE-RECONCILIATION.md`

---

## 0. 한 줄 결론

**현재 production data(Qdrant `nae_tsu_v1`의 Dagg 2,958 + Hiscox 361 = 3,319 point)는 5중 독립 대조로 완전 정합하며 재처리 불필요하다.** C1의 DOWNLOADED audit이 보고한 "checksum mismatch 2건 / 임베딩 0 / 인간검수 0 / 5 indexed / NOT PRODUCTION READY"는 **네 가지 측정 방법 오류**(hocr.html을 pdf로 대조, hash-cache를 source_id로 조회, 검수 파일을 파일명으로 조회, stale `index_report.json` 인용, Qdrant를 잘못된 포트로 접속)에서 비롯한 것으로, 실측으로 **CONTRADICTED**된다. CUE의 DAGG-INDEX-GATE verification은 수치·근거 전부 **독립 재현되어 CONFIRMED**다. 단, corpus 전체(Fuller Vol02–08 TSU, CLAIM-ONLY 19건, SLBC1689/PBC1742 provenance)의 **backlog는 실재**하며 이는 "정상 인덱싱된 데이터의 결함"이 아니라 "아직 처리 안 한 범위"다 — 두 개념을 분리한다.

---

## 1. 독립 측정 환경

| 항목 | 값 |
|---|---|
| 측정 일시 | 2026-08-27 |
| 측정 위치 | main checkout `/Users/David/DBMA` (공유 production data), 읽기 전용 |
| Python | `/Users/David/envs/dbma311/bin/python` 3.11.15 (공식 venv) |
| Qdrant | 컨테이너 `nae_qdrant` (`qdrant/qdrant:latest`, up 47h), 호스트 포트 **7333**→6333, GET/count/scroll만 사용 |
| Git | main checkout `dev/dbma-engine` @ `090103c`. `git add`/`commit`/`reset`/`checkout` 미수행 |
| Mutation | 0 (아래 §18) — 산출물은 본 보고서 1건 |

---

## 2. 검증 A — Manifest ↔ Filesystem

### 2.1 발견: manifest는 **3개** 존재한다 (C1 audit은 1개만 조사)

| # | Manifest 파일 | schema | record 수 | 대상 | 최종 커밋 |
|---|---|---|---|---|---|
| M1 | `NAE/authority/source_manifest.yaml` | `1.2` | **10** | Dagg, Hiscox, Fuller VOL01–08 | `b111293` 2026-08-18 |
| M2 | `NAE/pipeline/registration/state/source_manifest.yaml` | (present) | **14** | M1의 10건 + Smith VOL01–04 (`BAP-REF-SMITH-VOL0x`) | (state 파일) |
| M3 | `NAE/manifest/NAE_SOURCE_MANIFEST_v1.csv` | CSV+header | **25 data rows** (26 lines) | "NAE-BAPTIST-CORPUS-001" 광의 wishlist | `a7b894c` 2026-08-01 |

- C1의 DOWNLOADED audit(§3)과 이번 task order가 지칭하는 것은 **M1 (10 records, schema 1.2)** — 직접 파싱으로 **CONFIRMED**.
- C1의 *별건* manifest-reconciliation 보고서는 M3를 "26 records"로 주장했으나, 직접 `csv.reader` 파싱 = **25 data rows**. 생성 커밋 `a7b894c` 메시지 자체가 *"25 planned Baptist theological sources"*. → C1의 "26" **CONTRADICTED**, CUE의 "25" **CONFIRMED**.

### 2.2 Raw filesystem 실측 (`NAE/corpus/raw/archive_org/`)

```
church_order/  Dagg_Church_Order/         (original.pdf hocr.html ocr.txt metadata.json)
church_order/  Hiscox_Standard_Manual/    (original.pdf hocr.html ocr.txt metadata.json)
missions/      Fuller_Complete_Works_Vol01..08/  (각 original.pdf ocr.txt metadata.json)
reference/     Smith_Bible_Dictionary_HackettAbbot_Vol1..4/  (각 original.pdf djvu.xml ocr.txt metadata.json)
AF1815/ PBC1742/ TH1612/   → 빈 디렉터리 (0 파일)
```

- **raw PDF = 정확히 14개** (`find NAE/corpus/raw -name '*.pdf' | wc -l` = 14). C1 본문 "14" CONFIRMED. C1 §12 evidence-command 출력의 "15"는 오기(quarantine PDF 1건을 합산). Quarantine 포함 시 NAE 트리 전체 PDF = 15.
- **manifest-orphan PDF = 0**: 디스크 14개 = M1(10) + Smith 4(M2 등록). manifest에 있는데 raw 없는 항목: M1 기준 0.

### 2.3 Source별 matrix (현재 실측)

| Source | raw PDF | M1(authority) | M2(registration) | M3(CSV) | canonical | TSU | review | Qdrant |
|---|---|---|---|---|---|---|---|---|
| Dagg_Church_Order | ✅ | ✅ `BAP-CHURCH-DAGG-001` | ✅ | ✅ `-001`/`-002` | ✅ ok (source=hocr, 314p) | ✅ 3,377 | ✅ 2,958 verified | ✅ 2,958 (`nae_tsu_v1`) |
| Hiscox_Standard_Manual | ✅ | ✅ `BAP-CHURCH-HISCOX` | ✅ | ✅ | ✅ ok (source=hocr, 192p) | ✅ 740 | ✅ 361 verified | ✅ 361 (`nae_tsu_v1`) |
| Fuller Vol01 | ✅ | ✅ `BAP-MISS-FULLER-VOL01` | ✅ | ✅(1 rec 대표) | ✅ ok | ✅ 3,643 (all generated) | ❌ | ❌ |
| Fuller Vol02–08 | ✅ (7) | ✅ (7) | ✅ (7) | ✅(동일 1 rec) | ✅ ok (7건, 1890–2769 para) | ❌ | ❌ | ❌ |
| Smith Vol1–4 | ✅ (4) | ❌ | ✅ `BAP-REF-SMITH-VOL0x` | ❌ | ✅ ok (4건) | ❌ (설계상) | ❌ (설계상) | ✅ 34,948 (`nae_ref_v1`) |
| PBC1765 | ✅ (quarantine) | ❌ | ❌ | ❌ | ✅ ok (114p) | ❌ (HQ HOLD) | ❌ | ❌ |
| AF1815 / PBC1742 / TH1612 | ❌ (빈 dir) | ❌ | ❌ | PBC1742만 M3 | PBC1742=failed | ❌ | ❌ | ❌ |

---

## 3. 검증 B — Checksum / Provenance

### 3.1 SHA256 실측 (14개 raw PDF 전부 직접 계산)

| # | Source | M1/M2 `raw_checksum` | disk `original.pdf` | disk `hocr.html` | 판정 |
|---|---|---|---|---|---|
| 1 | Dagg | `f515bb48…c3493b` | `2c553042…2d42b` ✗ | **`f515bb48…c3493b` ✅** | **MATCH** (field는 hocr.html 지칭) |
| 2 | Hiscox | `83ee4096…d1471` | `14f4554f…16174` ✗ | **`83ee4096…d1471` ✅** | **MATCH** (field는 hocr.html 지칭) |
| 3–10 | Fuller Vol01–08 | (8개 값) | 8개 전부 일치 ✅ | (해당 없음) | **MATCH** ×8 |
| 11–14 | Smith Vol1–4 | M2 + ledger에 등록 | 4개 전부 일치 ✅ | (해당 없음) | **MATCH** ×4 (M1/M3엔 없음) |

### 3.2 "Dagg / Hiscox checksum mismatch"의 정체 — 확정

C1은 M1의 `raw_checksum`을 **모든 source에 대해 `original.pdf`와만** 대조했다. 그러나:

1. **`raw_checksum_ledger.jsonl` 직접 확인** — Dagg/Hiscox의 `raw_path`가 명시적으로 **`hocr.html`**로 기록되어 있다. Fuller/Smith의 `raw_path`는 `original.pdf`.
   ```
   {"source_id":"BAP-CHURCH-DAGG-001","raw_path":".../Dagg_Church_Order/hocr.html","checksum":"f515bb48…","event":"preserve"}
   {"source_id":"BAP-CHURCH-HISCOX","raw_path":".../Hiscox_Standard_Manual/hocr.html","checksum":"83ee4096…","event":"preserve"}
   ```
2. **canonical `normalize_report.json` 확인** — Dagg/Hiscox 둘 다 `"source": "hocr"` (hOCR에서 canonical 생성됨, PDF 아님). Fuller Vol02–08은 djvu.xml, Smith도 djvu.xml.
3. **`shasum -a 256 hocr.html` 실행** — Dagg `hocr.html` = `f515bb48…c3493b` (M1 값과 **완전 일치**), Hiscox `hocr.html` = `83ee4096…d1471` (M1 값과 **완전 일치**).
4. **`original.pdf`(2c553042…)의 정통성** — `NAE/metadata/crosswalk/crosswalk.yaml`이 인간 검수 기록으로 명시: *"original.pdf (sha256=2c553042…, recovered from ~/NAE_CORPUS_RAW/raw/, checksum-verified against pre-cleanup backup)… OCR title page text… independently corroborate the same work/edition."*

> **∴ Dagg/Hiscox의 `raw_checksum`은 실측과 MATCH이다** — 대조 대상이 `hocr.html`일 뿐. hocr-sourced ingest에서는 `raw_checksum`이 `hocr.html`의 해시를, pdf/djvu-sourced ingest에서는 `original.pdf`의 해시를 담는다. **provenance identity failure 아님.** 잔존 이슈는 M1(`NAE/authority/source_manifest.yaml`)에 `raw_path` 필드가 없어 `raw_checksum`의 대상이 모호하다는 **manifest 위생 결함**(hygiene) 하나뿐이다.

### 3.3 Fuller / Smith

- Fuller Vol01–08: 8건 전부 `original.pdf` 해시 = manifest 값. **MATCH ×8** (C1과 일치).
- Smith Vol1–4: `original.pdf` 해시 = M2 + `raw_checksum_ledger.jsonl` 값 (2026-08-25 preserve/reverify). **MATCH ×4**. M1/M3에는 미등록.

---

## 4. 검증 C — TSU 실제 상태 (현재 `tsu.json` 직접 파싱)

| Source | 파일 mtime | total | verified | generated | rejected | `tsu_verified.json` |
|---|---|---:|---:|---:|---:|---|
| Dagg_Church_Order | 2026-08-11 08:13 | **3,377** | **2,958** | 397 | 22 | 없음 |
| Hiscox_Standard_Manual | 2026-08-11 00:59 | **740** | **361** | 379 | 0 | 없음 |
| Fuller_Complete_Works_Vol01 | 2026-08-16 06:44 | **3,643** | **0** | 3,643 | 0 | 없음 |
| Fuller Vol02–08 | — | TSU 디렉터리 자체 없음 | | | | |
| Smith Vol1–4 | — | TSU 디렉터리 자체 없음 (reference-chunk 트랙, 설계상 TSU 미생성) | | | | |

- Dagg `review_decision` 교차: `approved 2958 / rejected 22 / None 397` — `review_status`와 모순 0.
- Dagg `review_date` 분포: `08-08:2, 08-09:93, 08-10:1524, 08-11:1361, <none>:397`. → 2026-08-09 18:32(인덱스 실행 시각)에는 verified ≈ pilot 5건.
- Hiscox `review_date` 분포: `08-08:3, 08-09:2, 08-11:356, <none>:379`.
- Dagg/Hiscox: `duplicate_of` 설정 0, empty claim 0, unique id = total.

**보고서 표현 대조**
- C1 DOWNLOADED audit "Review status: all `generated`" / "none promoted to verified" → **CONTRADICTED**.
- C1 DAGG-VOL1-8 audit §5.3 표 "verified 2,958 / generated 397 / rejected 22" → **CONFIRMED** (동일 C1이 나흘 뒤 DOWNLOADED audit에서 회귀).
- CUE DAGG-INDEX-GATE §5 표 (2,958 / 397 / 22, review_date 분포) → **CONFIRMED** (분포까지 재현).
- Fuller Vol01 "3,643 claims, all generated, no index" → **CONFIRMED**.

---

## 5. 검증 D — Human Review

### 5.1 `NAE/review/human/decisions/` 실측 (40개 파일)

| 항목 | 값 |
|---|---|
| decision 파일 | 40 (batch_0001–0036 + batch_0002 remediation ×2 + pilot_001 + pilot_001_remediation) |
| 검수된 unique tsu_id | **3,341** |
| 최종 APPROVED (unique) | **3,319** |
| REJECTED | 22 (전부 Dagg) |
| CONDITIONAL | 5 |
| reviewer_id | `David` |
| 검수 기간 | 2026-08-09 ~ 2026-08-11 (git commit `3f6d56d`…`a330642`) |

### 5.2 APPROVED ↔ verified 집합 대조 (ID-level, CUE 직접 실행)

```
APPROVED ∩ Dagg-verified   = 2,958   (Dagg verified 전량)
APPROVED ∩ Hiscox-verified = 361     (Hiscox verified 전량)
APPROVED 중 어느 verified 집합에도 없는 것 = 0
Dagg-verified 중 APPROVED 집합에 없는 것   = 0
```

### 5.3 `promotion_batch24_36_evidence.json` (mtime 2026-08-11 09:43)

```
production_accounting: dagg_verified 2958 / dagg_generated 397 / dagg_rejected 22
                       hiscox_verified 361 / hiscox_generated 379 / matches_expected: true
indexing_evidence:     final_indexed 3319, Dagg 2958, Hiscox 361,
                       only_dagg_hiscox_nonzero: true, PASS: true
```

**질문별 답**
1. C1 DOWNLOADED audit 작성 시점 Baptist human review = 0? → **아니오.** 작성(2026-08-26) 3주 전(08-09~11)에 3,319건 승격 완료. C1이 `NAE/review/human/`을 파일명으로 조회해 `batch_NNNN_decisions.json`(소스명 아님)을 놓친 것으로 보임.
2. Dagg verified 2,958이 실제 human review 결과? → **예.** §5.2 ID 완전 일치.
3. 언제 생성? → 2026-08-09 23:06 ~ 2026-08-11 08:17 (배치 1–36).
4. C1 report ↔ 현재 상태 시간적 transition 존재? → **예.** stale `index_report.json`(08-09 18:32) 이후 검수 이벤트 전부 발생. C1은 검수 *이전* 스냅샷을 현재로 오인.
5. 다른 Baptist source에도 verified? → **예, Hiscox 361.** Fuller/Smith/PBC1765는 0.

→ C1 DOWNLOADED audit "Human review state: none" **CONTRADICTED**. Snapshot discrepancy 확정.

---

## 6. 검증 E — Embedding Evidence

| 확인 항목 | 실측 |
|---|---|
| `NAE/corpus/embeddings/cache/` 파일 수 | **47,579** (`find -type f`) — hash-key(`<64hex>.json`) 공유 캐시, source_id/document_type 필드 없음 (설계상) |
| Dagg+Hiscox verified TSU에 매칭되는 캐시 | **3,319** (`batch1_23_backlog_embedding_evidence.json` `embedding_cache_file_count: 3319`) |
| `embed_batch24_36_report.json` | `newly_indexed 1271, errors []` |
| `batch1_23_backlog_embedding_evidence.json` `verified_recompute` | dagg 2958 + hiscox 361 = 3319, `matches_qdrant_points: true` |
| **물리적 벡터** | Qdrant `nae_tsu_v1`에 **3,319 벡터 (size 1024, Cosine) resident** |

- C1 "Baptist corpus-specific embedding = 0" 주장: C1은 *"캐시 파일이 Baptist source_id를 들고 있는가"*를 셌다. 캐시는 구조상 hash-key만 가지므로 그 지표는 **항상 0** — measurement artifact다. 실제 embedding 증거(hash-매칭 캐시 3,319 + Qdrant 벡터 3,319 + errors 0)는 존재한다. → **CONTRADICTED**.
- Dagg 2,958: embedding dimension **1024**, model space = `nae_tsu_v1` (Cosine), Qdrant point count **2,958**.

---

## 7. 검증 F — Qdrant (READ-ONLY, 포트 7333)

### 7.1 접속 정정

- `docker ps`: `nae_qdrant … 0.0.0.0:7333->6333/tcp` (up 47h). `config.yaml`은 `url: "http://localhost:6333"` — **stale**.
- `curl :6333/collections` → 무응답. `curl :7333/collections` → `{"collections":[{"name":"nae_ref_v1"},{"name":"nae_tsu_v1"}]}`.
- → C1의 "Qdrant not reachable → OUT OF SCOPE"는 **methodology gap**이다. 서비스는 처음부터 7333에서 도달 가능했다. CUE DAGG-INDEX-GATE는 7333을 사용해 정상 조회했다.

### 7.2 `nae_tsu_v1` 실측

| 지표 | 값 |
|---|---|
| `points_count` | **3,319** |
| vector size / distance | 1024 / Cosine |
| `indexed_vectors_count` | 0 (HNSW `indexing_threshold: 10000` 미도달 — payload/vector는 저장, ANN 그래프 미구축. 정상) |
| identifier = Dagg_Church_Order | **2,958** (review_status=verified: 2,958) |
| identifier = Hiscox_Standard_Manual | **361** (review_status=verified: 361) |
| review_status ≠ verified (컬렉션 전체) | **0** |
| identifier 매칭 Fuller* | **0** |
| 3,319 = 2,958 + 361 | ✅ 정확 |

### 7.3 `nae_ref_v1` 실측 (Smith 트랙)

| 지표 | 값 |
|---|---|
| `points_count` | **34,948** (`indexed_vectors_count` 38,692) |
| payload | `source_id: BAP-REF-SMITH-VOL0x`, `content_type: reference_dictionary`, chunk 기반 (chunk_index/text/page_start·end) — **TSU claim 아님** |
| Vol1 / Vol2 / Vol3 / Vol4 | 8,841 / 8,391 / 8,184 / 9,532 (합 34,948) |

---

## 8. 검증 G — Dagg 2,958 3-Way(+2) Reconciliation ★핵심

CUE가 직접 생성한 5개 집합 (모두 현재 상태 기준):

| 집합 | 정의 | |A| |
|---|---|---:|
| **A** | `tsu.json` `review_status == verified` (source=Dagg) | **2,958** |
| **B** | `review_gate.filter_embedding_eligible(현재 tsu.json)` `pass_count` (repo 코드 직접 실행) | **2,958** |
| **C** | Qdrant `nae_tsu_v1` `identifier=Dagg_Church_Order` point ID 집합 (scroll 전수) | **2,958** |
| **D** | human review decision 파일 40개의 APPROVED tsu_id ∩ Dagg | **2,958** |
| **E'** | `indexer.index_all(dry_run=True)` would-index (repo 코드 직접 실행) | **2,958** |

차집합 (A ↔ C, ID를 `TSU-\d+` → int 매핑 후):

```
A − C = 0        C − A = 0        A == C : True
Qdrant ∩ generated = 0            Qdrant ∩ rejected = 0
Qdrant point payload review_status 분포 : {verified: 2958}   (비검증 누수 0)
```

> **A = B = C = D = E' = 2,958. 완전 일치. 차집합 전부 공집합. 비검증(generated/rejected) 누수 0.**
> Dagg 인덱싱은 **사실상 완료 상태**이며 재인덱싱 시 `embed_batch24_36.py` 로직상 `target − existing = 0`.

---

## 9. 검증 H — Hiscox 361 Reconciliation

| 집합 | |값| |
|---|---:|
| A `tsu.json` verified | 361 |
| B `review_gate` pass_count | 361 |
| C Qdrant `identifier=Hiscox_Standard_Manual` | 361 |
| D human APPROVED ∩ Hiscox | 361 |
| E' `index_all(dry_run=True)` | 361 |

```
A − C = 0    C − A = 0    A == C : True
Qdrant ∩ generated = 0    Qdrant point payload : {verified: 361}
```

**C1의 "740 claims / indexed 5" ↔ CUE의 "361 Qdrant points" 차이 설명**:
- **740** = Hiscox TSU 총 claim 수 (`tsu_report.json` `claims_extracted: 740`). **CONFIRMED**, 변화 없음.
- **5** = stale `Hiscox_Standard_Manual/index_report.json` (`generated_at: 2026-08-09T18:32:42Z`, `gate_pass=5, gate_block=735, indexed=5`; `740 − 5 = 735`). 2026-08-09 pilot smoke test 스냅샷. git commit `3a2da21` 이후 불변.
- **361** = 인간 검수(2026-08-11, `review_date` 356건 + 08-08/09 5건) 후 `review_status=verified`가 된 subset. 이 361개가 `nae_incremental_ingest.py`로 `nae_tsu_v1`에 upsert됨.
- → **361은 stale artifact도 다른 processing subset도 아니다. verified subset 그 자체**이며 ID-level로 Qdrant와 완전 일치(양방향 차집합 0). **판정: REAL (verified subset).**

---

## 10. 검증 I — Fuller Vol01–08

| Vol | raw PDF | checksum | canonical | TSU | review | embedding | Qdrant | registration_state |
|---|---|---|---|---|---|---|---|---|
| 01 | ✅ | **MATCH** | ✅ ok | ✅ 3,643 (all generated) | ❌ | ❌ | ❌ | QUALITY_PASSED |
| 02 | ✅ | **MATCH** | ✅ ok (2,040 para) | ❌ | ❌ | ❌ | ❌ | QUALITY_PASSED |
| 03 | ✅ | **MATCH** | ✅ ok (2,526) | ❌ | ❌ | ❌ | ❌ | QUALITY_PASSED |
| 04 | ✅ | **MATCH** | ✅ ok (2,268) | ❌ | ❌ | ❌ | ❌ | QUALITY_PASSED |
| 05 | ✅ | **MATCH** | ✅ ok (1,890) | ❌ | ❌ | ❌ | ❌ | QUALITY_PASSED |
| 06 | ✅ | **MATCH** | ✅ ok (2,756) | ❌ | ❌ | ❌ | ❌ | QUALITY_PASSED |
| 07 | ✅ | **MATCH** | ✅ ok (2,103) | ❌ | ❌ | ❌ | ❌ | QUALITY_PASSED |
| 08 | ✅ | **MATCH** | ✅ ok (2,769) | ❌ | ❌ | ❌ | ❌ | QUALITY_PASSED |

- Vol01 TSU = 3,643 claims (`tsu_report.json` `generated_at 2026-08-16T11:44`, elapsed 57,726s). **C1의 "3,643" CONFIRMED.** review/index 상태: 전량 `generated`, gate pass = 0. **C1의 "no index_report" CONFIRMED.**
- Vol02–08: TSU 디렉터리 부재 **CONFIRMED**. 단 raw+checksum+canonical(status ok)+registration(QUALITY_PASSED)은 **완료** — "unprocessed"는 과소 표현. 정확히는 **canonicalized·registered / TSU-pending**.
- 8권 전부 source identity 분리됨 (`work_id`/`edition_id`가 Vol별로 고유, checksum 8종 상이).
- **재처리 안 함.**

---

## 11. 검증 J — Smith Bible Dictionary / PBC1765

### 11.1 Smith Bible Dictionary Vol1–4

| 항목 | 실측 |
|---|---|
| raw PDF | ✅ 4권 (`reference/Smith_Bible_Dictionary_HackettAbbot_Vol1..4/`) |
| checksum 기대값 | ✅ `NAE/pipeline/registration/state/source_manifest.yaml` (M2) + `raw_checksum_ledger.jsonl` (2026-08-25 preserve/reverify) — **4권 전부 disk와 MATCH** |
| M1 (authority YAML) 등록 | ❌ |
| M3 (CSV) 등록 | ❌ |
| 등록 문서 | ✅ `docs/NAE_SMITH_BIBLE_DICTIONARY_REGISTRATION_001.md` (2026-08-25), ADR-021 파이프라인, 4권 `QUALITY_PASSED` |
| canonical | ✅ 4권 status ok |
| TSU | ❌ (설계상 — "TSU Builder … ADR-021 범위 밖, 후속 단계") |
| embedding / Qdrant | ✅ **`nae_ref_v1`에 34,948 chunk** (`BAP-REF-SMITH-VOL0x`, reference-dictionary 트랙) |

→ C1 DOWNLOADED audit "Smith … no manifest entries and no TSU processing — undocumented sources":
- "M1/M3에 없음" → **CONFIRMED**
- "no TSU" → **CONFIRMED** (설계상)
- "undocumented" → **CONTRADICTED**. M2 등록 + checksum ledger MATCH + 등록 문서 + ADR-021 QUALITY_PASSED + `nae_ref_v1` 34,948 point. **C1이 조사하지 않은 별도 registry/collection에서 문서화·부분 production 상태.**
- 참고: memory note "Smith 임베딩 보류"(2026-08-25 기준)는 이후 `nae_ref_v1` 적재로 **stale**.

### 11.2 PBC1765

| 항목 | 실측 |
|---|---|
| 위치 | `NAE/corpus/quarantine/PBC1765/` (raw: `confeo00phil.pdf` 8.2MB + `_djvu.txt` + `_scandata.xml`) + `NAE/corpus/canonical/PBC1765/` (canonical ok, 114p) |
| M1 / M2 / M3 등록 | ❌ (3개 manifest 전부 부재 — 25/14/10 id 목록에 없음) |
| processing 상태 | canonical만 (`status: ok`), TSU/embedding/Qdrant 없음 |
| production corpus 포함 | ❌ |
| governance | `docs/agents/cue/HQ-ADVISORY-PBC1765-CANONICAL-DECISION.md` (2026-08-01) — **명시적 HQ HOLD**: *"canonical_admission을 raw→canonical 1차 통과로만 인정, TSU 생성/embedding/Qdrant indexing으로 자동 진행하지 말 것"* (근거: 앞 60개 단락 중 ~62% OCR noise, chapter heading 다수 미인식, `scripture_references_found: 0`) |
| 내용 identity | OCR grep으로 검증됨 (Philadelphia Baptist Confession, "Ant. Armbruster … 1765", chapter 구조) |

→ C1 DOWNLOADED audit "PBC1765 unregistered in quarantine → **HIGH** blocking issue":
- "3개 manifest에 미등록 + quarantine 존재" → **CONFIRMED (사실)**
- 심각도 프레이밍 → **재조정**. 이는 관리되지 않는 무결성 gap이 아니라 **HQ가 품질을 이유로 의도적으로 격리한 상태**(quality-hold)다. provenance는 추적 가능. "블로킹 이슈"가 아니라 "결정 완료된 보류".

---

## 12. Snapshot / Temporal Analysis

```
2026-08-07 05:10   canonical (Dagg/Hiscox/Fuller) — normalize_report source=hocr
2026-08-08 02:37   Dagg tsu_report (claims_extracted 3,377, elapsed 44,918s)
2026-08-09 18:32   ★ index_report.json ×2 (Dagg gate_pass=5 / Hiscox gate_pass=5) — pilot smoke test. 당시 verified ≈ 5
2026-08-09 18:36   commit 3a2da21  (index_report.json 커밋; git diff HEAD empty — 이후 불변)
2026-08-09 23:06   commit 3f6d56d  human review batch 1 first 38
2026-08-10 00:09 → 2026-08-11 08:17   commit 10505ae … a330642  batch 1–36 (Dagg 2,958 + Hiscox 361 → verified)
2026-08-11 00:59 / 08:13   Hiscox / Dagg tsu.json 최종 mtime
2026-08-11 ~11:24  embed_batch24_36.py → Qdrant upsert 1,271
2026-08-11 14:43   promotion_batch24_36_evidence.json (dagg_verified=2958, dry-run indexed=2958)
2026-08-11 21:00+  nae_incremental_ingest.py --apply → Qdrant upsert backlog 2,038 (Dagg 1,682 + Hiscox 356)
2026-08-12 02:24   batch1_23_backlog_embedding_evidence.json (qdrant_total_points=3319)
2026-08-15 07:31   raw_checksum_ledger reverify (Dagg/Hiscox = hocr.html) / registration_state QUALITY_PASSED ×10
2026-08-16 06:44   Fuller Vol01 tsu.json / tsu_report (3,643, all generated)
2026-08-18 23:55   commit b111293 — NAE/authority/source_manifest.yaml (M1, 10 records) 커밋
2026-08-25         Smith 등록 + nae_ref_v1 embedding (34,948 chunk)
2026-08-26         C1 DAGG-VOL1-8 audit · CUE DAGG-INDEX-GATE verification · C1 DOWNLOADED-SOURCE-INVENTORY audit
2026-08-27         ← 본 3-way forensic reconciliation
```

**`index_report.json indexed=5` ↔ `Qdrant Dagg=2,958` 동시 존재의 이유** (writer/execution history):
- `index_report.json`의 유일한 writer는 `NAE/pipeline/index/indexer.py`의 non-dry-run `index_identifier()` (repo grep은 CUE가 수행; 본 검증은 **git 불변성 + Qdrant 실체**를 독립 확인).
- 검수 후 실제 인덱싱은 `scripts/embed_batch24_36.py` + `scripts/nae_incremental_ingest.py --apply`가 `qdrant_store.upsert_points()`를 **직접 호출**해 수행 — 두 스크립트 모두 `index_report.json`을 갱신하지 않는다.
- ∴ `index_report.json`은 2026-08-09 pilot에서 **동결**, Qdrant는 2026-08-11에 **2,958/361까지 채워짐**. 서로 다른 execution lineage.
- downstream 소비자(`.automation/night-shift/dashboard/backend/collector.py`)가 이 stale 파일을 SSOT로 읽어 Ops Dashboard에 `indexed=5`로 노출 (CUE §12 지적, 본 검증에서 파일 불변성 재확인).

---

## 13. C1 DOWNLOADED Audit — claim별 판정

| # | C1 주장 | 독립 실측 | 판정 |
|---|---|---|---|
| C1-a | M1 = 10 records, schema 1.2 | 직접 파싱 일치 | **CONFIRMED** |
| C1-b | raw PDF 14개 on disk | `find … | wc -l` = 14 (evidence-cmd "15"는 오기) | **CONFIRMED** (본문) |
| C1-c | Dagg checksum MISMATCH (f515bb48 ≠ 2c553042) → CRITICAL | f515bb48 = Dagg `hocr.html` SHA256 (ledger가 raw_path=hocr.html 명시). raw_checksum은 그 대상과 **MATCH** | **CONTRADICTED** (결함 아님; manifest에 `raw_path` 부재라는 hygiene 이슈만 유효) |
| C1-d | Hiscox checksum MISMATCH → CRITICAL | 83ee4096 = Hiscox `hocr.html` SHA256. **MATCH** | **CONTRADICTED** (동상) |
| C1-e | Fuller Vol01–08 all MATCH | 8건 재계산 일치 | **CONFIRMED** |
| C1-f | Smith ×4 raw 있음 / manifest 없음 / TSU 없음 / "undocumented" | M1·M3 없음·TSU 없음 = 사실. M2+ledger 등록·등록문서·QUALITY_PASSED·`nae_ref_v1` 34,948 = 문서화됨 | **PARTIALLY CONFIRMED** ("undocumented" 부분 CONTRADICTED) |
| C1-g | PBC1765 quarantine 미등록 → HIGH 블로킹 | 3개 manifest 전부 미등록·quarantine 존재 = 사실. HQ Advisory에 의한 **의도적 quality-hold** | **CONFIRMED (사실) / 심각도 재조정** (STALE 아님, 관리된 보류) |
| C1-h | TSU claim 수 Dagg 3,377 / Hiscox 740 / Fuller01 3,643 | 파싱 일치 | **CONFIRMED** |
| C1-i | Dagg·Hiscox "indexed: 5" | stale `index_report.json` (2026-08-09, git 불변). 실측 Qdrant 2,958 / 361 | **CONTRADICTED (STALE ARTIFACT)** |
| C1-j | "Review status: all generated / none verified" | 현재 tsu.json: Dagg 2,958 verified, Hiscox 361 verified | **CONTRADICTED** |
| C1-k | "Baptist corpus embeddings: 0" | 3,319 벡터(1024-dim) Qdrant resident + hash-매칭 캐시 3,319 + errors 0 | **CONTRADICTED** (measurement artifact) |
| C1-l | "Human review state: none" | decision 파일 40개, APPROVED 3,319, reviewer David, ID 완전 일치 | **CONTRADICTED** |
| C1-m | Fuller Vol01 not indexed / no index_report | 실측 일치 (gate pass 0) | **CONFIRMED** |
| C1-n | Fuller Vol02–08 unprocessed | TSU/review/embed 없음 = 사실. raw+checksum MATCH+canonical ok+QUALITY_PASSED | **PARTIALLY CONFIRMED** ("unprocessed"→"TSU-pending"으로 정정) |
| C1-o | Qdrant not reachable (localhost:6333) → OUT OF SCOPE | 컨테이너 `nae_qdrant` up 47h, 호스트 포트 **7333**. config.yaml만 6333 (stale) | **CONTRADICTED (methodology gap)** — 서비스는 도달 가능했음 |
| C1-p | Production Eligibility: NOT READY (6 blocking) | 인덱싱된 3,319 point는 5중 정합·누수 0 → 재처리 불요. 나머지는 backlog | **CONTRADICTED (indexed slice) / SUSTAINED (corpus-wide backlog)** |
| C1-q | 선행 "Cathcart provenance complete" REJECTED | Cathcart/Smith-as-Cathcart artifact 없음 재확인 | **CONFIRMED** |

---

## 14. CUE DAGG-INDEX-GATE Verification — 재현 결과

| CUE 주장 | CUE 근거 | CUE 재현(본 검증) | 판정 |
|---|---|---|---|
| `dagg_verified = 2,958` (3-way 일치) | tsu.json + gate + Qdrant | tsu.json 2,958 + gate 2,958 + Qdrant 2,958 + human APPROVED 2,958 + dry-run 2,958 (**5-way**) | **CONFIRMED (강화)** |
| `gate_pass = 5` = stale | index_report.json 2026-08-09 | git commit `3a2da21` 이후 불변, `git diff HEAD` empty, `3377−5=3372` | **CONFIRMED** |
| 현재 gate 재실행 = `pass 2,958 / block 419` | `filter_embedding_eligible` | 동일 코드 재실행: `pass_count=2958 block_count=419` | **CONFIRMED (동일 수치)** |
| Qdrant Dagg = 2,958 (전부 verified), 총 3,319 (+Hiscox 361) | Qdrant scroll | `points_count 3319`, Dagg 2958 (verified 2958), Hiscox 361, 비검증 0 | **CONFIRMED** |
| verified ID 집합 == Qdrant ID 집합 (양방향 차집합 0) | ID reconciliation | `A−C=0, C−A=0, A==C True`, Qdrant∩generated=0, ∩rejected=0 | **CONFIRMED** |
| ROOT CAUSE = C (STALE ARTIFACT) | 6개 증거 | git 불변성 + writer 경로 + Qdrant 실체 재확인 | **CONFIRMED** |
| PRODUCTION ELIGIBLE = YES / 재인덱싱 불필요 | 누수 0 | 컬렉션 전체 비검증 0, Fuller 누수 0 | **CONFIRMED** |
| `index_report.json` stale 동안 Ops Dashboard 신뢰 불가 | collector.py 소비 | 파일 불변 확인 (downstream 코드 경로는 CUE 판단 채택) | **CONFIRMED** |

**+ C1 DAGG-VOL1-8 audit 대조**: review_status 표(2,958/397/22)는 **CONFIRMED**. 그러나 그 보고서의 결론 "SAFE TO RESUME: NO / HOLD — gate_block 3,372 해소 후 재인덱싱 필요"는 stale `index_report.json` 인용에 기반 → **CONTRADICTED** (2,958은 이미 인덱싱됨).

---

## 15. 최종 Cross-Verification Matrix

| 검증 항목 | C1 DOWNLOADED Audit 주장 | 기존 CUE 주장 (DAGG-INDEX-GATE / 26-REC / FINAL-GOV) | 독립 실측 (2026-08-27) | 판정 |
|---|---|---|---|---|
| Manifest 식별 | M1 10 records, schema 1.2 | — | M1 10 / M2 14 / M3 25 (3개 존재) | **C1 CONFIRMED** (M1 한정), 범위 보강 |
| Manifest 레코드 수 (CSV) | (별건 C1) 26 | 25 | M3 = 25 data rows (커밋 msg "25 planned") | **CUE CONFIRMED / C1 CONTRADICTED** |
| Raw files | 14 on disk | 14 (church_order+missions+reference) | 14 (+ quarantine 1) | **양측 CONFIRMED** |
| Dagg checksum | MISMATCH → CRITICAL | (범위 밖) | `raw_checksum` = `hocr.html` SHA256, **MATCH** | **C1 CONTRADICTED** (hygiene 이슈만 유효) |
| Hiscox checksum | MISMATCH → CRITICAL | (범위 밖) | `raw_checksum` = `hocr.html` SHA256, **MATCH** | **C1 CONTRADICTED** |
| Fuller 01–08 checksum | MATCH ×8 | — | MATCH ×8 (재계산) | **CONFIRMED** |
| Smith ×4 checksum | (기대값 없음) | (manifest 밖) | M2+ledger 값과 **MATCH ×4** | **REAL / M2 등록됨** |
| Dagg TSU total | 3,377 | 3,377 | 3,377 | **CONFIRMED** |
| Dagg verified | 0 ("all generated") | 2,958 | **2,958** | **CUE CONFIRMED / C1 CONTRADICTED** |
| Dagg gate_pass (현재) | (5, stale) | 2,958 | 2,958 (`filter_embedding_eligible` 재실행) | **CUE CONFIRMED** |
| Dagg Qdrant | (unreachable) | 2,958 | **2,958** (ID 집합 == verified 집합) | **CUE CONFIRMED** |
| Hiscox TSU total | 740 | 740 | 740 | **CONFIRMED** |
| Hiscox verified | 0 ("generated") | 361 | **361** | **CUE CONFIRMED / C1 CONTRADICTED** |
| Hiscox Qdrant | (5, stale index_report) | 361 | **361** (ID 집합 == verified 집합) | **CUE CONFIRMED** — 361 = verified subset (REAL) |
| Fuller Vol01 | 3,643 claims, generated, no index | (TSU만 존재) | 3,643, all generated, gate pass 0 | **CONFIRMED** |
| Fuller Vol02–08 | unprocessed | PARTIAL (Vol01만) | raw+checksum+canonical(ok)+QUALITY_PASSED / TSU·review·embed 없음 | **PARTIALLY CONFIRMED** ("TSU-pending"으로 정정) |
| Smith Dictionary | undocumented, no TSU | manifest linkage 없음 (별도 트랙) | M2+ledger 등록, 등록문서, `nae_ref_v1` 34,948 chunk | **PARTIALLY CONFIRMED** ("undocumented" CONTRADICTED) |
| PBC1765 | quarantine 미등록 → HIGH 블로킹 | provenance COMPLETE, quality-hold | 3개 manifest 미등록, HQ Advisory 의한 의도적 quality-hold | **CONFIRMED (사실) / 심각도 재조정** |
| Baptist embeddings | 0 | 공유 hash 캐시 (Dagg 벡터 존재) | Qdrant 3,319 벡터 resident + hash-매칭 캐시 3,319 | **CUE CONFIRMED / C1 CONTRADICTED** |
| Human review | none | 2,958 verified (batch 1–36) | decision 40파일, APPROVED 3,319, ID 완전 일치 | **CUE CONFIRMED / C1 CONTRADICTED** |
| `index_report.json` | indexed=5 (그대로 인용) | STALE ARTIFACT (2026-08-09 pilot) | git 불변, generated_at 08-09 18:32, 검수 前 스냅샷 | **CUE CONFIRMED (STALE ARTIFACT)** |
| Qdrant 도달성 | not reachable (6333) → OUT OF SCOPE | 7333에서 조회함 | 컨테이너 up 47h, 호스트 포트 7333 (config.yaml만 6333) | **CUE CONFIRMED / C1 methodology gap** |
| Production eligibility (indexed slice) | NOT READY | ELIGIBLE (누수 0) | 3,319 point 5중 정합, 비검증 누수 0 | **CUE CONFIRMED / C1 CONTRADICTED** |
| Production readiness (corpus-wide) | NOT READY | HOLD (Fuller TSU / CLAIM-ONLY / provenance) | Fuller Vol02–08 TSU 미착수, M3 19건 CLAIM-ONLY, SLBC1689/PBC1742 broken | **양측 방향 일치 (backlog 실재)** |

판정 범례: **CONFIRMED** · **PARTIALLY CONFIRMED** · **CONTRADICTED** · **STALE ARTIFACT** · **REAL** · **methodology gap**

---

## 16. 3-Way 분리 결론 (task order §15 — 절대 혼합 금지)

### A. 현재 Production Data Integrity — **정상 (CLEAN)**

- Qdrant `nae_tsu_v1` = 3,319 point = Dagg 2,958 + Hiscox 361, **전량 `review_status=verified`**.
- Dagg 2,958: `tsu.json verified` = `review_gate pass` = `indexer dry-run` = `human APPROVED` = `Qdrant point ID` — **5개 집합 완전 일치, 차집합 0, 비검증 누수 0**.
- Hiscox 361: 동일하게 5중 일치.
- embedding: 3,319 벡터(1024-dim, Cosine) 물리적 resident, errors 0.
- **재인덱싱·재임베딩 불필요.** ADR-029 Phase 1, Dagg upstream: UNCHANGED.
- 유일한 관측 결함: `Dagg/Hiscox/index_report.json`이 2026-08-09 pilot 스냅샷에 동결(stale) → Ops Dashboard/파이프라인 상태 표기가 `indexed=5 / gate_block=3,372`로 오탐. **데이터 결함 아님, 리포트 파일 정정 사안.**

### B. Corpus Governance Readiness — **부분적, 정리 필요 (다만 대부분 이미 해소)**

- **checksum "mismatch"**: 실제로는 `NAE/authority/source_manifest.yaml`(M1)에 `raw_path` 필드가 없어 `raw_checksum`이 `hocr.html`(Dagg/Hiscox)인지 `original.pdf`(Fuller/Smith)인지 문서상 모호. `raw_checksum_ledger.jsonl`에는 정확히 기록되어 있음. → **M1에 `raw_path`/`checksum_target` 명시 권고** (경미).
- **manifest 3원화**: M1(10)/M2(14)/M3(25)의 관계·권위 순서가 단일 문서로 정리되어 있지 않음. Smith가 M2에만, PBC1765가 어디에도 없음.
- **PBC1765**: HQ Advisory에 의한 의도적 quarantine — governance 상 정상 처리됨(미등록이 곧 결함 아님).
- **M3의 19건 CLAIM-ONLY, SLBC1689/PBC1742 provenance BROKEN**: `CUE-NAE-BAPTIST-CORPUS-001-FINAL-GOVERNANCE-RECONCILIATION.md`에서 이미 확정됨 — 본 검증도 동일. HQ decision 대기.

### C. Future Processing Backlog — **실재 (아직 처리 안 한 범위)**

- Fuller Vol02–08: TSU 미생성 (raw+canonical+registration은 완료).
- Fuller Vol01: TSU 3,643건 생성됨, human review 미착수 → verified 0 → 인덱싱 대상 0.
- Smith Vol1–4: `nae_ref_v1`(reference-chunk) 트랙으로는 인덱싱 완료(34,948), TSU-claim 트랙은 설계상 미대상.
- M3의 CLAIM-ONLY 19건: raw acquisition 자체 미완료.

> **A(정상)가 B/C의 미완료를 자동 의미하지 않고, B/C의 backlog가 A의 재처리를 요구하지도 않는다.**
> "이미 정상 인덱싱된 Dagg 2,958 / Hiscox 361"과 "아직 처리 안 한 Fuller Vol02–08 등"은 별개 사안이다.

---

## 17. 모든 Discrepancy — STALE / REAL / UNVERIFIED 판정

| discrepancy | 판정 | 근거 |
|---|---|---|
| `index_report.json indexed=5` vs Qdrant 2,958 (Dagg) | **STALE** | generated_at 2026-08-09T18:32, git 불변, 모든 검수 commit보다 앞섬 |
| `index_report.json indexed=5` vs Qdrant 361 (Hiscox) | **STALE** | 동일 파일군, `740−5=735` |
| C1 "checksum mismatch" (Dagg/Hiscox) | **REAL이나 defect 아님** | manifest 값 = `hocr.html` SHA256 (실측 MATCH); `raw_path` 미기재라는 hygiene 이슈만 REAL |
| C1 "review status all generated" | **STALE (snapshot)** | 검수 이전 상태를 현재로 인용 |
| C1 "human review none" | **STALE (snapshot)** | decision 40파일 실재, ID 일치 |
| C1 "Baptist embeddings 0" | **measurement artifact** | hash-cache를 source_id로 조회 (구조상 항상 0) |
| C1 "Qdrant not reachable" | **REAL 관측이나 결론 오류** | 포트 6333 시도(config.yaml stale). 실제 7333 up |
| C1 "5 blocking issues → NOT READY" | 인덱싱된 slice에 대해 **CONTRADICTED** / corpus 전체에 대해 **REAL backlog** | §16 |
| Smith "undocumented" | **CONTRADICTED** | M2+ledger 등록, `nae_ref_v1` 34,948 |
| Fuller Vol02–08 "unprocessed" | **PARTIALLY REAL** | TSU 없음은 REAL, canonical/registration은 완료 |
| M3 record count 26 (C1 별건) | **REAL error** | `csv.reader` = 25 |
| Fuller Vol01 verified 0 / no index | **REAL** | review 미착수 |
| SLBC1689 / PBC1742 provenance BROKEN | **REAL** | FINAL-GOVERNANCE-RECONCILIATION과 동일 |
| M3 CLAIM-ONLY 19건 raw 부재 | **REAL** | 디렉터리 부재 재확인 |
| memory "Smith 임베딩 보류" | **STALE** | `nae_ref_v1` 34,948 point 실재 (2026-08-27) |
| `config.yaml` qdrant url = 6333 | **REAL (stale config)** | 컨테이너는 7333→6333 매핑 |

**UNVERIFIED로 남는 것**:
- Dagg/Hiscox `original.pdf`(`2c553042…`/`14f4554f…`)와 archive.org 원본의 대조 — 외부 네트워크 미사용. 단 `crosswalk.yaml`이 "pre-cleanup backup과 checksum 대조 + OCR title page 일치"를 인간 검수로 기록 → provenance는 내부 evidence로 corroborated.
- `index_report.json`을 우회한 스크립트 2종(`embed_batch24_36.py` / `nae_incremental_ingest.py`)의 코드 grep — CUE가 §12에서 수행, 본 검증은 git 불변성 + Qdrant 실체 + `index_all(dry_run=True)` 재현으로 결론 지지 (코드 재-grep 미수행).

---

## 18. Mutation Audit

| 항목 | mutation | 비고 |
|---|---|---|
| CODE | 0 | 읽기만 (`review_gate` / `indexer` 는 import 후 dry-run·순수함수 호출) |
| CORPUS / RAW / CANONICAL / TSU | 0 | `json.load` 파싱만 |
| REVIEW | 0 | decision 파일 파싱만 |
| EMBEDDING / CACHE | 0 | `find | wc -l`, 파일 열람 없음 |
| QDRANT | 0 | GET `/collections`, POST `/points/count`, POST `/points/scroll` 만 (upsert·delete·update 0) |
| MANIFEST / REGISTRY | 0 | 파싱만 |
| GIT | 0 | `log` / `diff HEAD` / `rev-parse` / `status --porcelain` 만. add·commit·reset·checkout 0 |
| 산출물 | 본 보고서 1건 (`docs/agents/cue/CUE-NAE-BAPTIST-CORPUS-3WAY-FORENSIC-RECONCILIATION.md`, untracked) | task order §16 허용 범위 |

`NAE/corpus/tsu/` `git status --porcelain` = clean (다른 세션 변경분 미개입).

---

## 19. 종료 조건 체크리스트

- [x] Manifest ↔ filesystem reconciliation (M1/M2/M3 3개 전부, source별 matrix §2.3)
- [x] checksum 독립 검증 (14개 PDF SHA256 재계산 + hocr.html + ledger 대조 §3)
- [x] source별 TSU count 독립 검증 (§4)
- [x] source별 review status 독립 검증 (decision 40파일 집계 + ID 대조 §5)
- [x] embedding evidence 독립 검증 (cache + evidence JSON + Qdrant 벡터 §6)
- [x] Qdrant source/ID reconciliation (§7–9)
- [x] Dagg 2,958 3-way(+2) reconciliation — A=B=C=D=E'=2,958, 차집합 0 (§8)
- [x] Hiscox 361 reconciliation — 5중 일치, 740/5/361 차이 설명 (§9)
- [x] Fuller Vol01–08 상태 확인 (§10)
- [x] Smith Dictionary / PBC1765 governance 상태 확인 (§11)
- [x] C1 ↔ CUE ↔ 실제 상태 cross-verification matrix (§15)
- [x] 모든 discrepancy STALE / REAL / UNVERIFIED 판정 (§17)
- [x] Production data integrity / Governance readiness / Future backlog 분리 (§16)
- [x] Mutation 0 / Processing 0 / Embedding 0 / Qdrant mutation 0 / Git commit NO (§18)

---

## 20. Final Decision

```
NAE-BAPTIST-CORPUS — 3-WAY FORENSIC RECONCILIATION

PRODUCTION DATA INTEGRITY (현재 인덱싱된 것):
CLEAN — nae_tsu_v1 = 3,319 point (Dagg 2,958 + Hiscox 361), 전량 verified.
        Dagg 2,958: tsu.json = review_gate = indexer dry-run = human APPROVED
        = Qdrant point ID, 5개 집합 완전 일치, 차집합 0, 비검증 누수 0.
        Hiscox 361: 동일 5중 일치.
        재인덱싱·재임베딩 불필요.

DAGG 2,958 3-WAY:
A(tsu.json verified) = B(gate pass) = C(Qdrant ID) = D(human APPROVED)
= E'(indexer dry-run) = 2,958.  A−B = B−C = C−A = A−C = A−D = 0.

HISCOX 361:
A = B = C = D = E' = 361.  차집합 0.  740(총 claim) − 5(stale) 무관, 361 = verified subset (REAL).

CHECKSUM:
Dagg/Hiscox "mismatch" = CONTRADICTED. manifest raw_checksum = hocr.html SHA256
(raw_checksum_ledger.jsonl이 raw_path=hocr.html 명시, 실측 MATCH).
Fuller 01–08 MATCH ×8. Smith 01–04 MATCH ×4 (M2+ledger).
잔존: M1(authority yaml)에 raw_path 필드 부재 = manifest hygiene 이슈 (경미).

INDEX_REPORT.JSON:
STALE ARTIFACT — Dagg/Hiscox 공히 generated_at 2026-08-09T18:32, git commit 3a2da21
이후 불변, 모든 human-review batch commit보다 앞섬. gate_pass=5는 pilot smoke test 값.
현재 gate 재실행 = Dagg 2,958 / Hiscox 361.

C1 DOWNLOADED AUDIT:
PARTIALLY CONFIRMED —
  CONFIRMED: M1 10 records, raw 14, Fuller checksum ×8, TSU claim 수, Fuller Vol01 미인덱싱,
             Cathcart artifact 부재.
  CONTRADICTED: Dagg/Hiscox checksum "mismatch"(→ hocr.html MATCH), "review all generated"
             (→ 2,958/361 verified), "embeddings 0"(→ 3,319 벡터 resident), "human review none"
             (→ decision 40파일 3,319 APPROVED), "indexed 5"(→ Qdrant 2,958/361, STALE),
             "Qdrant not reachable"(→ 포트 7333 up, config.yaml만 stale),
             "NOT PRODUCTION READY"(→ indexed slice는 정합, 재처리 불요).
  재조정: Smith "undocumented"(→ M2+nae_ref_v1 34,948), PBC1765 "HIGH blocking"
             (→ 의도적 quality-hold), Fuller Vol02–08 "unprocessed"(→ TSU-pending).

CUE DAGG-INDEX-GATE VERIFICATION:
CONFIRMED — 모든 수치(2,958 / 361 / 3,319 / gate 2,958·419 / stale 5 / ID 집합 일치 /
ROOT CAUSE = C STALE ARTIFACT / PRODUCTION ELIGIBLE = YES)를 독립 재현. 5-way로 강화됨.
+ C1 DAGG-VOL1-8 audit: review_status 표(2,958/397/22) CONFIRMED, 그러나 "SAFE TO RESUME: NO,
재인덱싱 필요" 결론은 CONTRADICTED (2,958 이미 인덱싱됨).

CORPUS GOVERNANCE:
manifest 3원화(M1 10 / M2 14 / M3 25) 정리 필요. M1에 raw_path 명시 권고.
PBC1765 = HQ Advisory quarantine (정상). SLBC1689/PBC1742 = provenance BROKEN
(FINAL-GOVERNANCE-RECONCILIATION 유지). M3 19건 CLAIM-ONLY.

FUTURE BACKLOG (실재, A와 분리):
Fuller Vol02–08 TSU 미착수. Fuller Vol01 human review 미착수. M3 CLAIM-ONLY 19건 raw 미확보.

REQUIRED FIX (실행 안 함 — 정보 제공):
1) NAE/corpus/tsu/{Dagg,Hiscox}_*/index_report.json 을 실측 기준으로 재생성 또는 supersede 표기
   (Dagg gate_pass/indexed = 2,958·gate_block 419; Hiscox = 361·379). Qdrant/corpus mutation 아님.
2) 검수 후 인덱싱 경로(embed_batch24_36 / nae_incremental_ingest)가 index_report.json 을
   갱신하도록 배선 통일 (재발 방지).
3) config.yaml qdrant url 6333 → 7333 정정 (또는 컨테이너 매핑 정합).
4) NAE/authority/source_manifest.yaml 에 raw_path/checksum_target 필드 추가.
5) manifest 3원화(M1/M2/M3) 권위·범위를 단일 문서로 정리.
6) C1-NAE-BAPTIST-CORPUS-DOWNLOADED-SOURCE-INVENTORY-AUDIT.md 의
   checksum/embedding/human-review/indexed/Qdrant 결론을 본 검증으로 정정.

CODE MUTATION: 0    CORPUS MUTATION: 0    EMBEDDING: 0    QDRANT MUTATION: 0
MANIFEST MUTATION: 0    GIT COMMIT: NO
```

---

## Final Principle

> **이번 작업의 목적은 고치는 것이 아니라 확인하는 것이다.**
> FIND → MEASURE → RECONCILE → REPORT 까지만 수행했다.
>
> 두 보고서 모두 evidence로만 취급했고, 실측을 우선했다.
> - C1이 "정상"이라고 한 부분(Fuller checksum, TSU claim 수)은 실측으로 정상이었다.
> - C1이 "결함"이라고 한 부분(checksum mismatch, embedding 0, review none, indexed 5)은
>   전부 **측정 방법의 산물**이었다 — hocr.html을 pdf로, hash-cache를 source_id로,
>   batch 파일을 파일명으로, pilot 스냅샷을 현재로, 포트 6333을 7333 대신.
> - CUE의 DAGG-INDEX-GATE verification은 수치·근거가 전부 독립 재현되었다.
>
> **현재 production data(Dagg 2,958 / Hiscox 361)는 정상이다.** 그러나 그것이
> corpus 전체의 readiness를 의미하지 않으며(Fuller Vol02–08 등 backlog 실재),
> 반대로 backlog의 존재가 이미 정상인 3,319 point의 재처리를 요구하지도 않는다.
>
> 검증 중 발견한 문제는 직접 수정하지 않았다. §20 REQUIRED FIX는 HQ 결정 대기.

---

**Verification Mode**: FORENSIC · READ-ONLY · INDEPENDENT
**Mutations**: 0
**Git add/commit**: NO
**Report generated**: 2026-08-27
