# CUE — DAGG INDEX GATE DISCREPANCY / INDEPENDENT FORENSIC VERIFICATION

**작업명**: DAGG-INDEX-GATE-DISCREPANCY — Independent Forensic Verification
**작성자**: CUE (Independent Verification — C1 결과 미채택, 원본 artifact 직접 대조)
**작성일**: 2026-08-26
**Mode**: FORENSIC AUDIT · INDEPENDENT VERIFICATION · READ-ONLY
**Mutation Budget**: Code 0 / Corpus 0 / RAW 0 / Canonical 0 / TSU 0 / Embedding 0 / Qdrant 0 / Manifest 0 / Registry 0 / Cache 0 / Git 0

---

## 1. Executive Summary

C1 감사(`C1-DAGG-VOL1-8-PROCESSING-RESUME-POINT-AUDIT.md`)는 다음을 "치명적 모순"으로 보고했다.

```
Promotion Evidence : dagg_verified = 2,958
Index Report       : gate_pass = 5 / indexed = 5 / gate_block = 3,372
```

독립 검증 결과, **이 수치 차이는 실제 gate 결함이 아니라 STALE ARTIFACT 비교이다.**

| 확인 사항 | 결과 |
|---|---|
| `dagg_verified = 2,958` | **독립 검증됨** — `tsu.json` review_status 집계 + review gate 코드 재실행 + Qdrant 실측이 모두 2,958로 일치 |
| `gate_pass = 5` | **stale** — `index_report.json`은 **2026-08-09 18:32:43** 실행 산출물. 인간 검수(2026-08-09 23:06 ~ 08-11 08:17) *이전* 상태(당시 verified=5, pilot smoke test)를 담고 있음 |
| `gate_block = 3,372` | **stale** — 같은 파일. `3,377 − 5 = 3,372`. 당시 나머지는 전부 `generated`/`rejected` |
| `indexed = 5` | **stale** — 같은 파일. Qdrant 실측 Dagg point = **2,958** (전부 `review_status=verified`) |
| 현재 gate 재실행 | `gate_pass = 2,958` / `gate_block = 419` (397 generated + 22 rejected) |
| TSU ID-level reconciliation | `tsu.json`의 verified 2,958개 ID 집합 == Qdrant Dagg point ID 집합 (차집합 양방향 0) |

> **ROOT CAUSE = C (STALE ARTIFACT).**
> `NAE/corpus/tsu/Dagg_Church_Order/index_report.json`은 pilot 인덱싱 1회(2026-08-09) 이후
> 단 한 번도 재생성되지 않았다. 검수 후 실제 인덱싱은 별도 스크립트
> (`scripts/embed_batch24_36.py`, `scripts/nae_incremental_ingest.py`)로 수행되었고,
> 이 스크립트들은 `index_report.json`을 갱신하지 않는다.
>
> **Dagg 인덱싱은 이미 사실상 완료 상태**(2,958/2,958 verified가 Qdrant `nae_tsu_v1`에 존재).
> gate 로직에는 결함이 없다. 재인덱싱 불필요. 유일한 결함은 stale report 파일 하나이다.

---

## 2. Investigation Scope

**IN SCOPE (모두 직접 수행)**:
- `index_report.json`, `tsu_report.json`, `tsu.json` 원본 직접 파싱
- `NAE/pipeline/tsu/review_gate.py` gate 코드 정독 + 현재 `tsu.json`에 대해 재실행
- `NAE/pipeline/index/indexer.py` code path 정독
- `promotion_batch24_36_evidence.json` + 생성 스크립트(`scripts/generate_promotion_evidence.py`) 정독
- `scripts/embed_batch24_36.py`, `output/embed_batch24_36_report.json`, `output/batch1_23_backlog_embedding_evidence.json` 대조
- Qdrant `nae_tsu_v1` **READ-ONLY** 조회 (collection info / points count / scroll)
- TSU ID-level 집합 reconciliation (tsu.json ↔ Qdrant)
- git log / 파일 mtime lineage 분석

**OUT OF SCOPE (수행 안 함)**: 신규 처리, embedding, Qdrant mutation, 코드/manifest/registry/cache 수정, git add/commit.

---

## 3. C1 Claim Inventory

| # | C1 주장 | CUE 판정 |
|---|---|---|
| C1-1 | "Dagg Vol.1–8 개념 없음, 단일 monograph" | **동의** (본 작업 범위 밖, 재확인만) |
| C1-2 | Acquisition → Canonical → TSU → Embedding 완료 | **동의** |
| C1-3 | "인덱싱에서 3,372/3,377 gate_block, 인덱스에 단 5개만 등록" | **반박** — stale `index_report.json` 인용. 실제 Qdrant Dagg point = 2,958 |
| C1-4 | "Promotion Evidence(2,958) vs Index Report(5) 모순, 원인 조사 필요" | **원인 확정**: STALE ARTIFACT (§15) |
| C1-5 | "SAFE TO RESUME: NO / HOLD — gate_block 해소 후 재인덱싱 필요" | **반박** — 재인덱싱 불필요. stale report 파일 교체만 필요 (§16–17) |
| C1-6 | gate_block 원인은 "검증하지 않음(AUDIT ONLY)" | 본 작업이 그 검증을 완료함 |

---

## 4. Promotion Evidence Verification

**파일**: `NAE/review/human/evidence/promotion_batch24_36_evidence.json`
- `generated_at`: `2026-08-11T14:43:22.392494+00:00`
- `generated_by`: `"CUE (independent — no C1 findings referenced)"`

**§B production_accounting** (직접 대조):
```
dagg_verified = 2958   dagg_generated = 397   dagg_rejected = 22
matches_expected = true
```
→ 현재 `tsu.json` review_status 집계와 **정확히 일치**.

**§F indexing_evidence** (핵심 — 여기서 C1의 "2,958 indexed" 수치가 나옴):
```json
"indexing_evidence": {
  "final_indexed": 3319,
  "identifiers_nonzero": [
    {"identifier": "Hiscox_Standard_Manual", "indexed": 361},
    {"identifier": "Dagg_Church_Order",      "indexed": 2958}
  ]
}
```

**생성 코드 확인** (`scripts/generate_promotion_evidence.py` §F):
```python
from NAE.pipeline.index import indexer
idx_summary = indexer.index_all(dry_run=True)      # ← DRY RUN
identifiers_nonzero = [i for i in idx_summary["identifiers"] if i["indexed"] > 0]
```
`indexer.index_all(dry_run=True)`는 Qdrant를 건드리지 않는다. `index_all()`이
per-identifier `would_index`(gate 통과 + claim 존재 + non-duplicate 개수)를
`"indexed"` 키로 remap 해서 담는다(`indexer.py:135`).

> **∴ Promotion Evidence의 "Dagg indexed: 2958"은 실제 Qdrant write count가 아니라
> "지금 인덱서를 돌리면 몇 건이 gate를 통과하는가"의 dry-run projection이다.**
> 값 2,958 자체는 현재 corpus 상태에 대해 정확하다.

---

## 5. Verified TSU Reconciliation

**파일**: `NAE/corpus/tsu/Dagg_Church_Order/tsu.json` (6,006,046 bytes, mtime `2026-08-11 08:13:43`)

| 항목 | 값 | 방법 |
|---|---|---|
| record 총수 | 3,377 | `len(json)` |
| unique `id` | 3,377 / 3,377 | `set(id)` |
| `review_status == verified` | **2,958** | `Counter` |
| `review_status == generated` | 397 | `Counter` |
| `review_status == rejected` | 22 | `Counter` |
| `review_metadata` 보유 | 2,980 (= 2,958 + 22) | — |
| `review_decision` 분포 | `approved: 2958`, `rejected: 22`, `None: 397` | — |
| status × decision 교차 | `(verified, approved): 2958` / `(rejected, rejected): 22` / `(generated, None): 397` | 모순 없음 |

**`review_date` 분포 (핵심 — 검수가 언제 일어났는가)**:
```
2026-08-08 :     2
2026-08-09 :    93
2026-08-10 : 1,524
2026-08-11 :    90  +  1,271 (ISO timestamp 형식, batch 24-36)
None       :   397  (generated — 미검수)
```
→ **2026-08-09 18:32(인덱스 실행 시각)에는 verified가 약 5건뿐이었다.**
"2026-08-09" 검수 93건조차 대부분 그날 밤 23:06 이후(batch 1 first reviews)에 이뤄졌다.

**`scriptures` 필드**: 전 레코드 `[]` (0건). Dagg canonical의 `scripture_references_found = 0`과 일관 — gate와 무관.

---

## 6. Index Report Verification

**파일**: `NAE/corpus/tsu/Dagg_Church_Order/index_report.json` (259 bytes)

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

- **파일 mtime**: `2026-08-09 13:32:43` (CDT) = `18:32:43 UTC` — `generated_at`과 동일 실행.
- **git**: commit `3a2da21` (2026-08-09 18:36:14, *"NAE Pilot 001 human review gate → promotion → remediation → embedding → retrieval benchmark"*) 이후 **변경 없음** (`git diff HEAD` empty).
- **트리 전체 `index_report.json` 스캔**: 6개 파일 모두 `generated_at`이 `2026-08-09T18:32:42~43` 클러스터. **단일 `index_all()` 실행 산출물.**
  - `Hiscox_Standard_Manual/index_report.json`: `gate_pass=5, gate_block=735, indexed=5` — Dagg와 동일하게 "5" (pilot 10건 중 Hiscox 몫 5건).
  - backup 디렉터리 4개: 전부 `records_total_raw=0`.

> `index_report.json`은 **2026-08-09 pilot smoke test 1회의 동결 스냅샷**이다.
> 검수 완료(2026-08-11) 이후 이 파일을 재생성한 실행은 존재하지 않는다.

---

## 7. Gate-Pass / Gate-Block Analysis

### 7.1 Gate 코드 (`NAE/pipeline/tsu/review_gate.py`)

```python
EMBEDDING_ELIGIBLE_STATUSES = frozenset({VERIFIED})   # "verified" 만 통과
```
`check_tsu_review_status()` — `review_status != "verified"` → `REVIEW_GATE_BLOCK`, 사유 문자열 기록.
`filter_embedding_eligible()` — 배치 집계 (`pass_count`, `block_count`, `block_details`).
순수 판정 모듈: embedding 호출 없음, Qdrant 접근 없음, 파일 쓰기 없음 (docstring + 코드 확인).

`NAE/pipeline/index/indexer.py :: load_records_with_gate_summary()`가 이 gate를 호출하고,
`index_identifier()`가 그 결과를 `index_report.json`에 기록.

### 7.2 현재 `tsu.json`에 대한 gate 재실행 (CUE 직접 실행, READ-ONLY)

```
filter_embedding_eligible(load("Dagg_Church_Order/tsu.json")):
  total      : 3,377
  gate_pass  : 2,958
  gate_block :   419
    397  review_status='generated' not eligible for embedding (requires 'verified')
     22  review_status='rejected'  not eligible for embedding (requires 'verified')
  pass 레코드 중 empty claim: 0 / duplicate_of 설정: 0
```

### 7.3 2026-08-09 stale 값 재구성

| 시점 | verified | gate_pass | gate_block | 근거 |
|---|---|---|---|---|
| 2026-08-09 18:32 (index_report.json) | 5 | **5** | **3,372** | `3,377 − 5`. 당시 나머지 3,372건 = generated/rejected |
| 2026-08-26 (현재 tsu.json, gate 재실행) | 2,958 | **2,958** | **419** | §7.2 |

> gate_block 사유는 100% `review_status != verified` (검수 전 상태). schema mismatch / metadata 요구 /
> ID 규칙 / namespace / source 불일치 **아님**. gate 로직 결함 **아님**.

---

## 8. Promotion Gate vs Index Gate

| 항목 | Promotion Gate (인간 검수 → verified 승격) | Index Gate (`review_gate.py`) |
|---|---|---|
| Input dataset | `NAE/review/human/decisions/batch_*_decisions.json` + `tsu.json` | `tsu_verified.json`(있으면) 또는 `tsu.json` |
| Required field | `tsu_id`, reviewer decision | `id`, `review_status`, `claim` |
| Verification rule | 인간이 `approved` → `review_status='verified'` 기록 | `review_status == "verified"` 인가? |
| Eligibility rule | 승인된 candidate만 승격 | `verified` 만 embedding 통과 |
| Filter | `HUMAN_REVIEW_REQUIRED`, `Hiscox 284`, 미해결 blocking exception 제외 | `duplicate_of` 있으면 skip, `claim` 비면 skip (indexer 단계) |
| ID rule | `TSU-\d+` | `TSU-(\d+)` → Qdrant point id (int) |
| Source rule | corpus별 decisions 파일 | `identifier` 디렉터리 |
| Expected count | batch 24-36 = 1,271 approved | (동적) |
| Actual count | 2,958 verified (전 batch 누적) | 2,958 gate_pass (현재) / 5 (2026-08-09 stale) |

**동일 corpus/TSU 집합을 대상으로 하는가?** → **예.** 둘 다 `Dagg_Church_Order/tsu.json`의
동일 3,377 레코드를 대상으로 한다. 두 gate는 **직렬**이다: Promotion Gate가 `verified` 도장을
찍으면 → Index Gate가 그 도장을 확인해서 통과시킨다.

**2,958 → 5 감소의 정체**: 감소가 아니다. **5는 Promotion Gate가 도장을 찍기 *전*의 Index Gate 결과**이고,
**2,958은 도장을 찍은 *후*의 Index Gate 결과**다. 두 숫자는 서로 다른 시점의 같은 gate이다.

---

## 9. TSU ID-Level Reconciliation

CUE 직접 실행 (tsu.json 파싱 + Qdrant scroll, READ-ONLY):

```
tsu.json  verified  : 2,958 ID
tsu.json  generated :   397 ID
tsu.json  rejected  :    22 ID
Qdrant nae_tsu_v1, identifier=Dagg_Church_Order : 2,958 point ID

verified − Qdrant     = 0   (verified인데 인덱스에 없는 것: 없음)
Qdrant   − verified   = 0   (인덱스에 있는데 verified 아닌 것: 없음)
Qdrant ∩ generated    = 0
Qdrant ∩ rejected     = 0
verified 집합 == Qdrant 집합 : True   (완전 일치)
```

**lineage 보존 확인**:

| 단계 | count | identity |
|---|---|---|
| Total TSU | 3,377 | `TSU-0000006` … (unique) |
| verified TSU | 2,958 | ↓ 보존 |
| promotion evidence (`dagg_verified`) | 2,958 | ↓ 보존 |
| index candidate (gate_pass, 현재) | 2,958 | ↓ 보존 |
| Qdrant indexed (실측) | 2,958 | 집합 완전 일치 |

차집합 전부 공집합 → **verified ↔ promotion ↔ index candidate ↔ indexed 사이에 누수/오염 없음.**

---

## 10. Embedding Cache Reconciliation

- `NAE/corpus/embeddings/cache/` 실제 파일 수: **47,578** (`find -type f | wc -l`)
- 파일명 = content hash (`<64hex>.json`). `hashing.tsu_hash(schema_version, claim, book, page, scriptures)` 기반.
- **NAE corpus 전체 공유 캐시** — Dagg 전용 구분 없음. 2026-08-25 Smith's Bible Dictionary 통합(commit `001e022`)으로 수만 건 추가됨. C1이 인용한 "47,580"과 근사(캐시는 시간에 따라 증감).
- `output/batch1_23_backlog_embedding_evidence.json`의 `"embedding_cache_file_count": 3319`는
  **Dagg+Hiscox verified TSU hash에 매칭되는 캐시만 필터한 수**(전체 디렉터리 수가 아님).
- **2,958 verified Dagg TSU와의 관계**: 2,958건 각각의 claim에 대한 embedding 벡터가 hash-key로
  이 공유 캐시에 존재하며, `embed_batch24_36.py` / `nae_incremental_ingest.py`가 그 벡터를 읽어
  Qdrant에 upsert함. 캐시 47,578은 Dagg만의 수가 아니므로 gate discrepancy와 무관.

---

## 11. Qdrant Read-Only Verification

컨테이너 `nae_qdrant` (qdrant/qdrant:latest, `0.0.0.0:7333->6333`), 46시간 up.
**GET/POST count·scroll 만 사용. insert/delete/update 0.**

```
GET /collections                      → nae_ref_v1, nae_tsu_v1
GET /collections/nae_tsu_v1           → status=green, points_count=3319,
                                        vector size=1024, distance=Cosine
POST /points/count identifier=Dagg_Church_Order              → 2958
POST /points/count identifier=Dagg_Church_Order & verified   → 2958
POST /points/count identifier=Hiscox_Standard_Manual         → 361
scroll Dagg sample → id:6 TSU-0000006 review_status=verified,
                     id:7 TSU-0000007 verified, id:8 TSU-0000008 verified
```

| 지표 | index_report.json (stale) | Qdrant 실측 (현재) |
|---|---|---|
| Dagg indexed | 5 | **2,958** |
| collection 총 points | (해당 없음) | **3,319** = Dagg 2,958 + Hiscox 361 |

> `promotion_batch24_36_evidence.json`의 `final_indexed: 3319`, `batch1_23_backlog_embedding_evidence.json`의
> `qdrant_total_points: 3319` 와 **Qdrant 실측이 정확히 일치**. `index_report.json` 의 `indexed: 5` 만 어긋남.

`indexed_vectors_count: 0`은 HNSW 인덱싱 임계치(`indexing_threshold: 10000`) 미도달로 payload/vector는
저장되었으나 ANN 그래프 미구축 상태를 의미 — points_count(3,319)가 실제 저장 건수이며 정상.

---

## 12. Code Path Verification

**실제 인덱싱 경로 (검수 후)**:

1. `scripts/embed_batch24_36.py` (commit `74b28d6`, 2026-08-11 11:24)
   - `output/final_human_review_candidate.json`에서 1,271 tsu_id 로드
   - `qdrant_store.get_client()` → 기존 point scroll → `target − existing` 만 embed
   - `qdrant_store.upsert_points(client, points)` **직접 호출**
   - 보고서: `output/embed_batch24_36_report.json` (`newly_indexed: 1271, errors: []`)
   - **`index_report.json` 을 쓰지 않음**
2. `scripts/nae_incremental_ingest.py --apply` (Batch 1–23 backlog 2,038건: Dagg 1,682 + Hiscox 356)
   - `output/batch1_23_backlog_embedding_evidence.json` 이 명시: *"이번 backlog embedding은
     `scripts/nae_incremental_ingest.py --apply` 만 사용했다"*, `index_all() 코드 무변경`
   - **`index_report.json` 을 쓰지 않음**

**`index_report.json` 을 쓰는 유일한 코드**: `NAE/pipeline/index/indexer.py:147`
(`index_identifier()` non-dry-run). repo 전체 grep 확인 — 다른 writer 없음.

**downstream 소비자**: `.automation/night-shift/dashboard/backend/collector.py:263` 및
`pipeline_stages.py`가 `index_report.json` 을 파이프라인 단계 상태의 SSOT로 **읽는다.**
→ stale 파일이 Ops Dashboard / 상태 보고에 계속 `indexed=5, gate_block=3372`로 노출되는 이유.

> gate/indexer 코드 자체는 정상. config·filter·namespace·status field·verification field 모두
> 설계대로 동작. **버그 없음.** stale 원인은 "검수 후 인덱싱이 indexer.py를 우회했다"는 운영 경로 문제.

---

## 13. Artifact Timestamp / Lineage Analysis

```
2026-08-07 05:10  canonical.json / normalize_report.json                  (Canonicalization)
2026-08-08 02:37  tsu_report.json  (claims_extracted=3377, 44,918s)       (TSU extraction)
2026-08-09 18:32  index_report.json  ★ gate_pass=5 / indexed=5  ← pilot smoke test (verified=5)
2026-08-09 18:36  commit 3a2da21  (index_report.json 커밋, 이후 불변)
2026-08-09 23:06  commit 3f6d56d  batch 1 first 38 reviews          ┐
2026-08-10 …      commit 6fe70c3…c722a65  batch 2–15                 │ 인간 검수
2026-08-11 01:33  commit c7e10f0  batch 16–23                        │ (2,958 verified 생성)
2026-08-11 08:17  commit a330642  batch 24–36 final (1,271)          ┘
2026-08-11 08:13  tsu.json mtime  (검수 결과 반영된 최종본)
2026-08-11 11:24  commit 74b28d6  embed_batch24_36.py → Qdrant upsert 1,271
2026-08-11 14:43  promotion_batch24_36_evidence.json  (dagg_verified=2958, dry-run indexed=2958)
2026-08-11 21:00~ nae_incremental_ingest.py → Qdrant upsert backlog 2,038
2026-08-12 02:24  batch1_23_backlog_embedding_evidence.json  (Qdrant points=3319)
2026-08-25 09:35  commit 001e022  Smith Bible Dict 통합 (공유 캐시 증가)
```

**핵심**: `index_report.json`(08-09 18:32)은 그 아래 모든 검수·인덱싱 이벤트보다 **먼저** 생성되었고
이후 갱신되지 않았다. `promotion_evidence`(08-11)와 `index_report`(08-09)는
**서로 다른 execution lineage의 산출물**을 비교한 것.

---

## 14. Stale Artifact Analysis

| 질문 | 답 |
|---|---|
| `index_report.json`이 최신 execution 상태와 일치하는가? | **아니오** |
| 서로 다른 실행 시점의 artifact를 비교했는가? | **예** — index_report(08-09 pilot) vs promotion evidence(08-11 post-review) |
| 서로 다른 dataset인가? | 아니오 — 동일 `Dagg_Church_Order/tsu.json`, 다른 *시점* |
| 파일 존재 = 동일 lineage 라고 가정했는가(C1)? | 예 — C1이 두 파일을 동일 실행 결과로 취급 |
| stale 파일이 downstream에 영향을 주는가? | 예 — night-shift dashboard collector가 SSOT로 소비 (§12) |

**증거 요약**: `index_report.json.generated_at = 2026-08-09T18:32:43` < 모든 batch review commit
(최초 `3f6d56d` = 2026-08-09T23:06) < `tsu.json` mtime (2026-08-11T08:13) < Qdrant 실측(2,958).
gate 코드를 현재 `tsu.json`에 재실행하면 `gate_pass=2958` — stale 파일의 `5`가 아님.

---

## 15. Root Cause Determination

```
ROOT CAUSE : C — STALE ARTIFACT
```

**확정 근거 (evidence)**:

1. `NAE/corpus/tsu/Dagg_Church_Order/index_report.json` 의 `generated_at` =
   `2026-08-09T18:32:43.493617+00:00`, git commit `3a2da21` 이후 **불변**(`git diff HEAD` empty),
   파일 mtime `2026-08-09 13:32:43 CDT` 동일.
2. 이 시각은 **모든** 인간 검수 batch commit(최초 `3f6d56d` 2026-08-09 23:06:55)보다 **앞선다.**
   `tsu.json` 의 `review_date` 분포상 08-09 18:32 시점 verified ≈ 5 (pilot).
   `3,377 − 5 = 3,372` = 보고된 `gate_block`.
3. 동일 `review_gate.filter_embedding_eligible()` 를 **현재** `tsu.json` 에 재실행 →
   `gate_pass = 2,958`, `gate_block = 419` (397 generated + 22 rejected). stale 파일의 5/3,372 아님.
4. 검수 후 실제 인덱싱은 `scripts/embed_batch24_36.py` + `scripts/nae_incremental_ingest.py --apply`
   가 `qdrant_store.upsert_points()` 를 직접 호출하여 수행. 두 스크립트 모두 `index_report.json`
   미갱신 (코드 grep 확인). `index_report.json` writer는 `indexer.py:147` 하나뿐.
5. Qdrant `nae_tsu_v1` **실측**: Dagg point = 2,958 (전부 `verified`), 총 3,319 (+Hiscox 361).
   `tsu.json` verified ID 집합과 Qdrant Dagg point ID 집합 **완전 일치**(양방향 차집합 0).
6. `promotion_batch24_36_evidence.json` + `batch1_23_backlog_embedding_evidence.json` 의
   `3319` / `2958` 수치가 Qdrant 실측과 일치. **오직 `index_report.json` 만 어긋남.**

**배제된 가설**:
- A (EXPECTED — 2,958 중 5만 index-eligible): 배제. 현재 gate 재실행 = 2,958 통과.
- B (DATA/STATE MISMATCH): 배제. ID-level 완전 일치, protected-field 위반 0(promotion evidence §D).
- D (REPORTING ERROR — gate 실행됐으나 report만 틀림): 부분적으로만 해당. `index_report.json`은
  *자기 실행 시점 기준으로는 정확*했고, 그 후 갱신되지 않아 stale가 됨 → 본질은 C.
- E (IMPLEMENTATION BUG): 배제. gate/indexer 코드 정상, 검수 후 인덱싱 경로가 indexer.py를
  우회한 운영상의 문제일 뿐 코드 결함 아님.
- F (UNRESOLVED): 배제. 6개 독립 증거로 확정.

---

## 16. Production Eligibility

| 항목 | 판정 | 근거 |
|---|---|---|
| Dagg verified TSU가 Qdrant에 존재하는가 | **YES — 2,958/2,958** | Qdrant 실측 + ID 완전 일치 |
| 인덱스에 비검증(generated/rejected) 누수 | **없음 (0)** | Qdrant ∩ generated = 0, ∩ rejected = 0 |
| payload 무결성 | 정상 | scroll 샘플 `review_status=verified`, tsu_id/doctrine/page 정상 |
| production 파일 mutation (검수 후) | 없음 | backlog evidence: Dagg/Hiscox/exception_queue hash 무변경 |
| **PRODUCTION ELIGIBLE** | **YES** | Dagg 인덱싱은 사실상 완료 상태 |

단, `index_report.json` 이 stale인 채로 남아 있으면 **Ops Dashboard / 파이프라인 상태 보고가
계속 "indexed=5 / gate_block=3,372"로 오탐**하므로, 그 파일 교체 전까지 상태 표기는 신뢰 불가.

---

## 17. Resume Decision

```
SAFE TO REINDEX : HOLD  (재인덱싱은 불필요하며, 원인 확정 전 금지였던 조건은 이제 해소됨)
```

- **재인덱싱 불필요**: 2,958 verified TSU가 이미 Qdrant `nae_tsu_v1` 에 전부 존재.
  재실행해도 `embed_batch24_36.py` 로직상 `target − existing` = 0 (이미 `already_embedded`).
- **필요한 것은 stale report 교체뿐** (§18 REQUIRED FIX). 이는 corpus/embedding/Qdrant mutation이
  아니라 관측 artifact 정정이므로 HQ 승인 후 별도 처리.
- Dagg upstream(acquisition→embedding)은 **UNCHANGED**. ADR-029 Phase 1 **UNCHANGED**.

---

## 18. Mutation Audit

| 항목 | mutation | 비고 |
|---|---|---|
| CODE | 0 | 읽기만 |
| CORPUS / RAW / CANONICAL / TSU | 0 | 파싱만 |
| EMBEDDING | 0 | — |
| QDRANT | 0 | GET / count / scroll 만 (insert·delete·update 없음) |
| MANIFEST / REGISTRY / CACHE | 0 | — |
| GIT | 0 | add·commit·reset·checkout 없음 |
| 산출물 | 본 보고서 1개 (`docs/agents/cue/CUE-DAGG-INDEX-GATE-DISCREPANCY-INDEPENDENT-VERIFICATION.md`) | task order §15 허용 범위 |

**PROCESSING = 0 · EMBEDDING = 0 · QDRANT MUTATION = 0.**

---

## 19. Git Status

- 작업 전/후 `git add` / `git commit` / `git reset` / `git checkout` **미수행**.
- 다른 session의 변경사항 미수정.
- 조사는 main checkout(`/Users/David/DBMA`, branch `dev/dbma-engine`)의 파일을 **읽기만** 함.
- worktree(`claude/dagg-index-gate-discrepancy-54e189`)는 2026-08-24 스냅샷이라 Dagg/NAE context 부재 →
  본 보고서는 peer CUE 보고서와 동일 위치인 main checkout `docs/agents/cue/` 에 배치(커밋하지 않음, 현재 `??` 상태).

---

## 20. Final Decision

```
DAGG INDEX GATE DISCREPANCY

PROMOTION VERIFIED:
YES — dagg_verified = 2,958 (tsu.json review_status 집계 + review_gate 코드 재실행 +
      Qdrant 실측, 3-way 일치)

VERIFIED TSU:
2,958   (generated 397 / rejected 22 / total 3,377)

INDEX CANDIDATE:
2,958   (review_gate.filter_embedding_eligible() 를 현재 tsu.json 에 재실행한 gate_pass)

GATE PASS:
2,958   (현재)   ←→   5 (2026-08-09 18:32 stale index_report.json)

GATE BLOCK:
419     (현재; 397 generated + 22 rejected)   ←→   3,372 (stale; = 3,377 − 5)

INDEXED:
2,958   (Qdrant nae_tsu_v1, identifier=Dagg_Church_Order, 전부 review_status=verified;
         tsu.json verified ID 집합과 완전 일치)
         ←→ 5 (stale index_report.json)
         Qdrant 총 points = 3,319 (Dagg 2,958 + Hiscox 361)

ROOT CAUSE:
C — STALE ARTIFACT

ROOT CAUSE EVIDENCE:
1) index_report.json.generated_at = 2026-08-09T18:32:43, git commit 3a2da21 이후 불변.
   이 시각은 모든 인간 검수 batch(최초 commit 3f6d56d = 2026-08-09 23:06)보다 앞섬.
   당시 verified ≈ 5 (pilot) → 3,377 − 5 = 3,372 = 보고된 gate_block.
2) 동일 review_gate 코드를 현재 tsu.json 에 재실행 → gate_pass = 2,958 / gate_block = 419.
3) 검수 후 실제 인덱싱은 scripts/embed_batch24_36.py + scripts/nae_incremental_ingest.py --apply
   (qdrant_store.upsert_points 직접 호출)로 수행. 둘 다 index_report.json 미갱신.
   index_report.json 의 유일한 writer 는 indexer.py:147 (non-dry-run index_identifier).
4) Qdrant 실측 Dagg point = 2,958 (전부 verified), tsu.json verified ID 집합과 양방향 차집합 0.
5) promotion_batch24_36_evidence.json / batch1_23_backlog_embedding_evidence.json 의
   3319 / 2958 수치가 Qdrant 실측과 일치. 오직 index_report.json 만 어긋남.
6) promotion evidence 의 "indexed: 2958" 은 indexer.index_all(dry_run=True) 의 would_index
   projection (Qdrant write 아님) — 값 자체는 현재 corpus 에 대해 정확.

PRODUCTION ELIGIBLE:
YES — 2,958 verified TSU 가 이미 Qdrant nae_tsu_v1 에 정상 인덱싱됨. 비검증 누수 0.
      (단, index_report.json 이 stale 인 동안 Ops Dashboard 상태 표기는 신뢰 불가.)

SAFE TO REINDEX:
HOLD — 재인덱싱 불필요 (2,958 전부 이미 존재; embed_batch24_36 재실행 시 to_embed=0).
       필요한 것은 stale index_report.json 정정뿐.

REQUIRED FIX:
1) NAE/corpus/tsu/Dagg_Church_Order/index_report.json 을 현재 실측 기준으로 재생성 또는
   supersede 표기: gate_pass=2958, gate_block=419, indexed=2958 (Qdrant 실측),
   generated_at 갱신. (Hiscox_Standard_Manual/index_report.json 도 동일 — indexed 5 → 361.)
   → 방법 A(권장): READ-ONLY 재생성 스크립트가 Qdrant 실측 + gate 재실행 결과를 써넣음.
   → 방법 B: indexer.index_identifier(dry_run=False) 재실행. 이미 존재하는 point 는
     upsert(멱등)이므로 corpus 변경 없음. 단 embedding 캐시 재조회 발생 → HQ 승인 필요.
2) (후속, 별건) 검수 후 인덱싱 경로(embed_batch24_36 / nae_incremental_ingest)가
   완료 시 index_report.json 을 갱신하도록 배선 통일 — 재발 방지.
3) C1 보고서(C1-DAGG-VOL1-8-...RESUME-POINT-AUDIT.md)의 "gate_block 3,372 / SAFE TO RESUME: NO"
   결론을 본 검증 결과로 정정.

DAGG UPSTREAM PROCESSING:
UNCHANGED

ADR-029 PHASE 1:
UNCHANGED

CODE MUTATION:
0

CORPUS MUTATION:
0

EMBEDDING:
0

QDRANT MUTATION:
0

GIT COMMIT:
NO
```

---

## 21. 종료 조건 체크리스트

- [x] `dagg_verified = 2,958` 독립 검증 — tsu.json 집계 + gate 재실행 + Qdrant 3-way 일치
- [x] `gate_pass = 5` 독립 검증 — 2026-08-09 pilot stale 값으로 확정 (`3,377 − 5 = 3,372`)
- [x] `gate_block = 3,372` 독립 검증 — 동일 stale 파일, 검수 전 상태
- [x] `indexed = 5` 독립 검증 — stale. Qdrant 실측 2,958
- [x] 두 gate 기준 비교 — §8 (직렬 관계, 동일 corpus·다른 시점)
- [x] TSU ID-level reconciliation — verified 집합 == Qdrant 집합 (§9)
- [x] embedding cache 관계 확인 — 공유 hash 캐시 47,578, Dagg 전용 아님 (§10)
- [x] Qdrant read-only 확인 — points_count 3,319 / Dagg 2,958 (§11)
- [x] 실제 gate code path 확인 — review_gate.py + indexer.py + 우회 스크립트 2종 (§12)
- [x] artifact timestamp/lineage 확인 — §13
- [x] stale artifact 여부 확인 — §14 확정
- [x] discrepancy root cause 판정 — C (STALE ARTIFACT), 6개 증거 (§15)
- [x] production eligibility 판정 — YES (§16)
- [x] safe-to-reindex 판정 — HOLD / 불필요 (§17)
- [x] required fix 제시 — §20 REQUIRED FIX
- [x] mutation = 0 / processing = 0 / embedding = 0 / Qdrant mutation = 0 / Git commit = NO

---

**CUE Independent Verification Complete. HQ 승인 없이 C1에게 수정·재인덱싱 지시하지 않음.**

**한 줄 결론**: "왜 2,958이 5가 되었는가?" → **되지 않았다.** `index_report.json`이
인간 검수 *이전*(2026-08-09) pilot 실행에서 멈춰 있을 뿐이고, 검수 후 인덱싱은 `indexer.py`를
우회한 스크립트로 수행되어 그 파일을 갱신하지 않았다. 실제 Qdrant에는 2,958개 verified Dagg TSU가
이미 전부 인덱싱되어 있으며 gate 로직은 정상이다.
