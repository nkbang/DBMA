# Preflight Report — Fuller Vol.01–08 (C1 Independent Verification, RE-RUN)

git status --porcelain:
?? docs/NAE_FULLER_PREFLIGHT_REPORT_C1_001.md

git rev-parse HEAD: 561de4940e95dfa5d2d45da1bb8c9853d29f576d
git remote -v: nas http://100.94.139.122:3000/David/DBMA.git (fetch/push), origin https://github.com/nkbang/DBMA.git (fetch/push)
git rev-parse --show-toplevel: /Users/David/DBMA

STATUS: PASS (all T1–T6 verified, drift=0, checksums=8/8 match, Qdrant reachable, Fuller vectors=0)

Changed Files:
?? docs/NAE_FULLER_PREFLIGHT_REPORT_C1_001.md
?? docs/NAE_FULLER_PREFLIGHT_REPORT_C1_002.md

---

## T1 Baseline 무결성

**명령**: `python scripts/nae_corpus_reconcile.py --json`
**Exit code**: 0
**Drift**: core=[], governance=[] → **drift 없음**

```json
{
  "authorities": {
    "m2_sources": 14,
    "indexed_ids_count": 3319,
    "verified_ids_count": 3319,
    "qdrant_status": "reachable",
    "qdrant_ids_count": 3319
  },
  "invariants": [
    {
      "id": "INV-1",
      "ok": true,
      "detail": "verified_ids == indexed_ids"
    },
    {
      "id": "INV-2",
      "ok": true,
      "detail": "qdrant_ids == verified_ids"
    },
    {
      "id": "INV-3",
      "ok": true,
      "detail": "No embedded non-verified/rejected/other TSU"
    }
  ],
  "governance": [
    {
      "id": "GC-1",
      "ok": true,
      "detail": "All admission source_ids exist in M2"
    },
    {
      "id": "GC-2",
      "ok": true,
      "detail": "All sources with verified TSUs have admissions"
    }
  ],
  "qdrant": "reachable",
  "drift": {
    "core": [],
    "governance": []
  }
}
```

**판정**: PASS — exit 0, drift 없음. 즉시 중단 조건 불만족.

---

## T2 Fuller RAW 3-way 체크섬 (8/8)

| Vol | 원본 PDF 경로 | shasum(실측) | manifest.yaml | ledger.jsonl | 일치 |
|-----|--------------|-------------|---------------|--------------|------|
| 01 | NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol01/original.pdf | 74416a8f...cb9f | 74416a8f...cb9f | 74416a8f...cb9f | ✓ |
| 02 | NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol02/original.pdf | 352d7edf...e408 | 352d7edf...e408 | 352d7edf...e408 | ✓ |
| 03 | NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol03/original.pdf | 787e185c...18a1 | 787e185c...18a1 | 787e185c...18a1 | ✓ |
| 04 | NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol04/original.pdf | 8f4ba47e...79af | 8f4ba47e...79af | 8f4ba47e...79af | ✓ |
| 05 | NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol05/original.pdf | 20da331a...e074 | 20da331a...e074 | 20da331a...e074 | ✓ |
| 06 | NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol06/original.pdf | 95b2fe11...cef6 | 95b2fe11...cef6 | 95b2fe11...cef6 | ✓ |
| 07 | NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol07/original.pdf | 78cd86c9...8fa0 | 78cd86c9...8fa0 | 78cd86c9...8fa0 | ✓ |
| 08 | NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol08/original.pdf | bc66c821...6c8c | bc66c821...6c8c | bc66c821...6c8c | ✓ |

**판정**: PASS — 8/8 3-way 일치.

---

## T3 Canonical 준비도 (8/8)

| Vol | canonical.json 파싱 | normalize_report status | fatal/error | canonical.txt bytes | canonical.json paragraphs |
|-----|---------------------|------------------------|-------------|--------------------|--------------------------|
| 01 | OK | ok | 없음 | 954,514 | 2,250 |
| 02 | OK | ok | 없음 | 858,772 | 2,040 |
| 03 | OK | ok | 없음 | 1,029,275 | 2,526 |
| 04 | OK | ok | 없음 | 945,300 | 2,268 |
| 05 | OK | ok | 없음 | 768,064 | 1,890 |
| 06 | OK | ok | 없음 | 843,002 | 2,756 |
| 07 | OK | ok | 없음 | 949,732 | 2,103 |
| 08 | OK | ok | 없음 | 1,085,983 | 2,769 |

**normalize_report.json 전량 인용 (status 필드만)**:
- Vol01: `"status": "ok"` — pipeline_version=2.0.0, source=ocr, characters_after=953307, paragraph_count=2250, heading_count=137
- Vol02: `"status": "ok"` — pipeline_version=2.0.0, source=ocr, characters_after=857805, paragraph_count=2040, heading_count=144
- Vol03: `"status": "ok"` — pipeline_version=2.0.0, source=ocr, characters_after=1028129, paragraph_count=2526, heading_count=184
- Vol04: `"status": "ok"` — pipeline_version=2.0.0, source=ocr, characters_after=944284, paragraph_count=2268, heading_count=395
- Vol05: `"status": "ok"` — pipeline_version=2.0.0, source=ocr, characters_after=767156, paragraph_count=1890, heading_count=284
- Vol06: `"status": "ok"` — pipeline_version=2.0.0, source=ocr, characters_after=841580, paragraph_count=2756, heading_count=359
- Vol07: `"status": "ok"` — pipeline_version=2.0.0, source=ocr, characters_after=949051, paragraph_count=2103, heading_count=77
- Vol08: `"status": "ok"` — pipeline_version=2.0.0, source=ocr, characters_after=1084597, paragraph_count=2769, heading_count=163

**판정**: PASS — 8/8 canonical.json 파싱 성공, normalize_report status="ok", fatal/error 필드 없음.

---

## T4 Vol.01 TSU 인벤토리

**명령**: Python 스크립트 (tsu.json 직접 읽기 + incremental_state.json 교집합 확인)

```
Total records: 3643
id range: TSU-0004123 ~ TSU-0007765
duplicate ids: 0
review_status distribution: {"generated": 3643}
Intersection with incremental_state (Fuller source_ids): 0
```

**판정**: PASS — 총 3,643개 레코드, id 중복 0, review_status 전량 `generated`, incremental_state 교집합 0.

---

## T5 Vol.02–08 TSU 규모 추정

**추정 방법**: Vol.01 (canonical characters_after → TSU 수) 비율 적용

```
Vol01: 953307 chars / 3643 TSU = 261.6819 chars/TSU
Ratio (TSU per char): 0.003821

Vol1: 953307 chars -> ~3643 TSU (ratio=0.003821)
Vol2: 857805 chars -> ~3278 TSU (ratio=0.003821)
Vol3: 1028129 chars -> ~3929 TSU (ratio=0.003821)
Vol4: 944284 chars -> ~3609 TSU (ratio=0.003821)
Vol5: 767156 chars -> ~2932 TSU (ratio=0.003821)
Vol6: 841580 chars -> ~3216 TSU (ratio=0.003821)
Vol7: 949051 chars -> ~3627 TSU (ratio=0.003821)
Vol8: 1084597 chars -> ~4145 TSU (ratio=0.003821)

8-volume total estimated TSU: 28379
```

**HQ Decision Request §4 갱신용**: Fuller Vol.01–08 전체 예상 검수 TSU 수 ≈ **28,379개** (Vol.01 실측 비율 기반 추정치)

---

## T6 Qdrant 내 Fuller 벡터 부재 확인

**Qdrant 상태**: reachable (localhost:7333)

**작업 전 컬렉션 상태**:
```
Collection: nae_ref_v1, points: 34948
Collection: nae_tsu_v1, points: 3319
```

**nae_tsu_v1 Fuller source_identifier 필터 count**: 0

**작업 후 컬렉션 상태**:
```
Collection: nae_ref_v1, points: 34948
Collection: nae_tsu_v1, points: 3319
```

**판정**: PASS — Fuller 벡터 0개 (미인용 상태 예상), 작업 전후 컬렉션 상태 동일 (nae_ref_v1=34948 / nae_tsu_v1=3319).

---

## Mutation Budget 증명

본 preflight 작업(읽기 전용 수집)으로 인한 신규 파일 생성은 `docs/NAE_FULLER_PREFLIGHT_REPORT_C1_002.md` 1개뿐. Mutation Budget = 0 (Code 0 / Corpus 0 / RAW 0 / Canonical 0 / TSU 0 / Embedding 0 / Qdrant 0 / Registration-state 0 / Manifest 0 / Config 0 / git commit(data) 0).

---

## Next

- HOLD 해제 결정 = HQ (이 preflight은 근거 수집만 수행)
- 실행 Task Order(TSU 생성·검수·임베딩·색인) = CUE, HQ 승인 후 별도 발급
- estimated TSU ≈ 28,379개는 HQ Decision Request §4에 반영 가능

---

*Report generated: 2026-09-08 by C1 (Independent Forensic Auditor)*
*All numerical claims based on stdout evidence only.*